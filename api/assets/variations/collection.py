import asyncio
import json
import re

from pymongo import ReadPreference
from slugify.slugify import slugify
from werkzeug.datastructures import MultiDict

from api import APIError, APIHandler
from api.assets.document import BaseCollectionHandler, BaseDocumentHandler
from blueprints.assets.models import Asset, Variation
from workers.tasks import GenerateVariationTask
from transforms import get_transform

__all__ = [
    'CollectionHandler',
    'TransformManyHandler'
]


# Constants

ALLOWED_SLUGIFY_CHARACTERS = re.compile(r'[^-_a-z0-9]+')


# Handlers

class BaseVariationsHandler:

    def validate_variations(self, asset_type, variations):
        """
        Validate and the given map of variations (if valid the variations are
        returned.
        """

        # Check the structure of the variations is valid
        if not isinstance(variations, dict):
            raise APIError(
                'invalid_request',
                hint='Request body JSON must be an object.'
            )

        if len(variations) == 0:
            raise APIError(
                'invalid_request',
                hint='At least one variation is required.'
            )

        elif len(variations) > self.config['MAX_VARIATIONS_PER_REQUEST']:
            raise APIError(
                'invalid_request',
                hint=(
                    'The maximum number of variations that can be added in '
                    'single request is '
                    f"{self.config['MAX_VARIATIONS_PER_REQUEST']}."
                )
            )

        for name, transforms in variations.items():

            # Check the name of the variation is valid
            slug = slugify(
                name,
                regex_pattern=ALLOWED_SLUGIFY_CHARACTERS,
            )

            # Unlike slugify we allow dashes at the start/end of the variation
            # name, so we strip dashes before the test.
            if slug != name.strip('-'):
                raise APIError(
                    'invalid_request',
                    hint=f'Not a valid variation name: {name}.'
                )

            # Check the required number of transforms have been provided
            if len(transforms) == 0:
                raise APIError(
                    'invalid_request',
                    hint=(
                        'At least one transform per variation is required: '
                        f'{name}.'
                    )
                )

            for i, transform in enumerate(transforms):

                # Check transform structure
                if not (
                    len(transform) == 2
                    and isinstance(transform[0], str)
                    and isinstance(transform[1], dict)
                ):
                    raise APIError(
                        'invalid_request',
                        hint=(
                            f'Invalid transform structure: {transform} '
                            f'({name}).'
                        )
                    )

                # Check the transform exists
                transform_cls = get_transform(asset_type, transform[0])
                if not transform_cls:
                    raise APIError(
                        'invalid_request',
                        hint=(
                            f'Unknown transform: {asset_type}:{transform[0]} '
                            f'({name}).'
                        )
                    )

                # Check only the last transform in the list is flagged as a
                # final transform.
                if transform_cls.final and i < len(transforms) - 1:
                    raise APIError(
                        'invalid_request',
                        hint=(
                            'Final transform not set as last transform: '
                            f'{asset_type}:{transform[0]} ({name}).'
                        )
                    )

                if not transform_cls.final and i == len(transforms) - 1:
                    raise APIError(
                        'invalid_request',
                        hint=(
                            f'Last transform in list is not final: {name}'
                        )
                    )

                # Check the settings for the transform are correct
                settings_form = transform_cls.get_settings_form_cls()(
                    MultiDict({
                        k: v for k, v in transform[1].items()
                        if v is not None
                    })
                )
                if not settings_form.validate():
                    raise APIError(
                        'invalid_request',
                        hint=(
                            'Invalid settings for transform: '
                            f'{asset_type}:{transform[0]} ({name}).'
                        ),
                        arg_errors=settings_form.errors
                    )

        return variations


class CollectionHandler(BaseDocumentHandler, BaseVariationsHandler):

    async def put(self, uid):
        """Generate variations for an asset"""

        asset = self.get_asset(
            uid,
            projection={
                '_id': True,
                'type': True,
                'expires': True
            }
        )

        # Extract the variations from the variations argument
        try:
            raw_variations = json.loads(self.get_body_argument('variations'))
        except ValueError:
            raise APIError(
                'invalid_request',
                hint='Variations argument is not valid JSON.'
            )

        variations = self.validate_variations(asset.type, raw_variations)

        # Add a set of tasks to generate the asset variations
        notification_url = self.get_body_argument('notification_url', None)

        tasks = []
        task_names = []
        for variation_name, transforms in variations.items():

            task = GenerateVariationTask(
                self.account._id,
                asset._id,
                variation_name,
                transforms,
                notification_url
            )

            if notification_url:
                tasks.append(self.add_task_and_forget(task))
            else:
                tasks.append(self.add_task_and_wait(task))

            task_names.append(variation_name)

        if notification_url:

            # Fire and forget
            await asyncio.gather(*tasks)
            self.finish()

        else:

            # Wait for response
            events = await asyncio.gather(*tasks)

            # Collect any errors
            errors = {}
            for i, event in enumerate(events):
                if not event:
                    errors[task_names[i]] = ['Connection lost']

                elif event.type == 'task_error':
                    errors[task_names[i]] = [event.reason]

            if errors:
                raise APIError('error', arg_errors=errors)

            # Fetch the asset again now the variations have been generated
            with Asset.with_options(read_preference=ReadPreference.PRIMARY):
                asset = self.get_asset(
                    uid,
                    projection={
                        'uid': True,
                        'expires': True,
                        'ext': True,
                        'meta': True,
                        'name': True,
                        'variations': {
                            '$sub.': Variation
                        }
                    }
                )

            # Handle image expiry
            if not asset:
                raise APIError(
                    'not_found',
                    hint=(
                        'Asset expired whilst variations where being '
                        'generated.'
                    )
                )

            json_type = asset.to_json_type()

            self.write({
                'uid': json_type['uid'],
                'variations': json_type['variations']
            })


class TransformManyHandler(BaseCollectionHandler, BaseVariationsHandler):

    async def put(self):
        """Generate variations for one or more assets"""

        assets = self.get_assets(
            projection={
                '_id': True,
                'type': True,
                'uid': True
            }
        )

        # Extract the variations from the variations argument
        try:
            raw_variations = json.loads(self.get_body_argument('variations'))
        except ValueError:
            raise APIError(
                'invalid_request',
                hint='Variations argument is not valid JSON.'
            )

        # Peek to determine if the user wants the variations applied globally
        # or locally.
        if self.get_body_argument('local', False):

            # Variations must be defined for each uid
            uids = set(self.get_body_arguments('uids'))
            variation_keys = set(list(raw_variations.keys()))

            if uids != variation_keys:
                raise APIError(
                    'invalid_request',
                    hint='Each uid must be assigned a variation.'
                )

            variations = {
                a.uid: self.validate_variations(a.type, raw_variations[a.uid])
                for a in assets
            }

        else:
            # Global application

            # Ensure all assets are of the same type
            asset_types = set([a.type for a in assets])
            if len(asset_types) > 1:
                raise APIError(
                    'invalid_request',
                    hint='All assets must be of the same type.'
                )

            local_variations = self.validate_variations(
                asset_types.pop(),
                raw_variations
            )
            variations = {a.uid: local_variations for a in assets}

        # Add a set of tasks to generate the asset variations
        notification_url = self.get_body_argument('notification_url', None)

        tasks = []
        task_names = []

        for asset in assets:

            local_variations = variations[asset.uid]
            for variation_name, transforms in local_variations.items():

                task = GenerateVariationTask(
                    self.account._id,
                    asset._id,
                    variation_name,
                    transforms,
                    notification_url
                )

                if notification_url:
                    tasks.append(self.add_task_and_forget(task))
                else:
                    tasks.append(self.add_task_and_wait(task))

                task_names.append(f'{asset.uid}:{variation_name}')

        if notification_url:

            # Fire and forget
            await asyncio.gather(*tasks)
            self.finish()

        else:

            # Wait for response
            events = await asyncio.gather(*tasks)

            # Collect any errors
            errors = {}
            for i, event in enumerate(events):
                if not event:
                    errors[task_names[i]] = ['Connection lost']

                elif event.type == 'task_error':
                    errors[task_names[i]] = [event.reason]

            if errors:
                raise APIError('error', arg_errors=errors)

            # Fetch the asset again now the variations have been generated
            with Asset.with_options(read_preference=ReadPreference.PRIMARY):
                assets = self.get_assets(
                    projection={
                        'uid': True,
                        'expires': True,
                        'ext': True,
                        'meta': True,
                        'name': True,
                        'variations': {
                            '$sub.': Variation
                        }
                    }
                )

            results = [a.to_json_type() for a in assets]

            self.write({
                'results': [
                    {
                        'uid': r['uid'],
                        'variations': r['variations']
                    }
                    for r in results
                ]
            })

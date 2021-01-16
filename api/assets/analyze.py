import asyncio
import json

from pymongo import ReadPreference
from werkzeug.datastructures import MultiDict

from analyzers import get_analyzer
from api import APIError, APIHandler
from blueprints.assets.models import Asset
from workers.tasks import AnalyzeTask

from .document import BaseCollectionHandler, BaseDocumentHandler

__all__ = [
    'AnalyzeHandler',
    'AnalyzeManyHandler'
]


# Handlers

class BaseAnalyzeHandler:

    def validate_analyzers(self, asset_type, analyzers):
        """
        Validate the given list of analyzers (if valid the analyzers are
        returned.
        """

        # Check the structure of the analyzers is valid
        if not isinstance(analyzers, list):
            raise APIError(
                'invalid_request',
                hint='Request body JSON must be a list.'
            )

        if len(analyzers) == 0:
            raise APIError(
                'invalid_request',
                hint='At least one analyzer is required.'
            )

        # Check each analyzer is valid
        for analyzer in analyzers:

            # Check structure
            if not (
                len(analyzer) == 2
                and isinstance(analyzer[0], str)
                and isinstance(analyzer[1], dict)
            ):
                raise APIError(
                    'invalid_request',
                    hint=f'Invalid analyzer structure: {analyzer}'
                )

            # Check the analyzer exists
            analyzer_cls = get_analyzer(asset_type, analyzer[0])
            if not analyzer_cls:
                raise APIError(
                    'invalid_request',
                    hint=f'Unknown analyzer: {asset_type}:{analyzer[0]}.'
                )

            # Check the settings for the analyzer are correct
            settings_form = analyzer_cls.get_settings_form_cls()(
                MultiDict({
                    k: v for k, v in analyzer[1].items()
                        if v is not None
                })
            )
            if not settings_form.validate():
                raise APIError(
                    'invalid_request',
                    hint=(
                        'Invalid settings for analyzer: '
                        f'{asset_type}:{analyzer[0]}.'
                    ),
                    arg_errors=settings_form.errors
                )

        return analyzers


class AnalyzeHandler(BaseDocumentHandler, BaseAnalyzeHandler):

    async def post(self, uid):
        """Analyze the asset for additional meta data"""

        asset = self.get_asset(
            uid,
            projection={
                '_id': True,
                'type': True,
                'expires': True
            }
        )

        # Extract the analyzers from the request body
        try:
            raw_analyzers = json.loads(self.get_body_argument('analyzers'))
        except:
            raise APIError(
                'invalid_request',
                hint='Analyzers argument is not valid JSON.'
            )

        analyzers = self.validate_analyzers(asset.type, raw_analyzers)

        # Add a task to perform the asset analysis
        notification_url = self.get_body_argument('notification_url', None)

        task = AnalyzeTask(
            self.account._id,
            asset._id,
            analyzers,
            notification_url
        )

        if notification_url:

            # Fire and forget
            await self.add_task_and_forget(task)
            self.finish()

        else:

            # Wait for response
            event = await self.add_task_and_wait(task)

            if not event:
                raise APIError('error', 'Connection lost')

            elif event.type == 'task_error':
                raise APIError('error', event.reason)

            # Fetch the asset again now the analysis is complete
            with Asset.with_options(read_preference=ReadPreference.PRIMARY):
                asset = self.get_asset(
                    uid,
                    projection={
                        'uid': True,
                        'expires': True,
                        'ext': True,
                        'meta': True,
                        'name': True
                    }
                )

            # Handle image expiry
            if not asset:
                raise APIError(
                    'not_found',
                    hint='Asset expired whilst being analyzed'
                )

            json_type = asset.to_json_type()

            self.write({
                'uid': json_type['uid'],
                'meta': json_type['meta']
            })


class AnalyzeManyHandler(BaseCollectionHandler, BaseAnalyzeHandler):

    async def post(self):
        """Analyze one for more asset for additional meta data"""

        assets = self.get_assets(
            projection={
                '_id': True,
                'type': True,
                'expires': True,
                'uid': True
            }
        )

        # Extract the analyzers from the request body
        try:
            raw_analyzers = json.loads(self.get_body_argument('analyzers'))
        except:
            raise APIError(
                'invalid_request',
                hint='Analyzers argument is not valid JSON.'
            )

        # Peek to determine if the user wants the variations applied globally
        # or locally.
        if self.get_body_argument('local', False):

            # Variations must be defined for each uid
            uids = set(self.get_body_arguments('uids'))
            analyzer_keys = set(list(raw_analyzers.keys()))

            if uids != analyzer_keys:
                raise APIError(
                    'invalid_request',
                    hint='Each uid must be assigned a list of analyzers.'
                )

            analyzers = {
                a.uid: self.validate_analyzers(a.type, raw_analyzers[a.uid])
                for a in assets
            }

        else:
            # Global application

            # Ensure all assets are the same type / base type (file)
            asset_types = set([a.type for a in assets if a.type != 'file'])
            if len(asset_types) > 1:
                raise APIError(
                    'invalid_request',
                    hint=(
                        'All assets must be of the same type / base type '
                        '(file)'
                    )
                )

            local_analyzers = self.validate_analyzers(
                asset_types.pop(),
                raw_analyzers
            )
            analyzers = {a.uid: local_analyzers for a in assets}

        # Add a set of tasks to generate the asset variations
        notification_url = self.get_body_argument('notification_url', None)

        tasks = []
        task_names = []

        for asset in assets:

            task = AnalyzeTask(
                self.account._id,
                asset._id,
                analyzers[asset.uid],
                notification_url
            )

            if notification_url:
                tasks.append(self.add_task_and_forget(task))
            else:
                tasks.append(self.add_task_and_wait(task))

            task_names.append(asset.uid)

        if notification_url:

            # Fire and forget
            await self.add_task_and_forget(task)
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

            # Fetch the assets again now the analysis is complete
            with Asset.with_options(read_preference=ReadPreference.PRIMARY):
                assets = self.get_assets(
                    projection={
                        'uid': True,
                        'expires': True,
                        'ext': True,
                        'meta': True,
                        'name': True
                    }
                )

            # Handle image expiry
            if not asset:
                raise APIError(
                    'not_found',
                    hint='Asset expired whilst being analyzed'
                )

            results = [a.to_json_type() for a in assets]

            self.write({
                'results': [
                    {
                        'uid': r['uid'],
                        'meta': r['meta']
                    }
                    for r in results
                ]
            })

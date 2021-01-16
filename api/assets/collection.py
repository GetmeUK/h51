import asyncio
import imghdr
import io
import mimetypes
import os
import re
import time

import clamd
from manhattan.formatters.text import remove_accents
from manhattan.forms import BaseForm, fields, validators
from manhattan.utils.chrono import today_tz
from mongoframes import And, In, Not, Q
import mutagen
from PIL import Image
from slugify.slugify import slugify

from api import APIError, APIHandler
from api.utils import PaginationForm, paginate, to_multi_dict
from blueprints.accounts.models import Account, Stats
from blueprints.assets.models import Asset, Variation

__all__ = ['CollectionHandler']


# Constants

ALLOWED_SLUGIFY_CHARACTERS = re.compile(r'[^-a-z0-9\/]+')


# Forms

def uid_to_object_id(uid):
    """Coerce a UID for an asset to the asset's ObjectId"""

    ids = Asset.ids(Q.uid == uid)
    if not ids:
        raise ValueError('Not a valid uid.')

    return ids[0]


class ManyForm(PaginationForm):

    after = fields.HiddenField(coerce=uid_to_object_id)

    before = fields.HiddenField(coerce=uid_to_object_id)

    q = fields.StringField(
        'Q',
        validators=[validators.Optional()]
    )

    backend = fields.StringField(
        'backend',
        validators=[validators.AnyOf('any', 'public', 'secure')],
        default='any'
    )

    type = fields.StringField(
        'type',
        validators=[validators.Optional()]
    )


class PutForm(BaseForm):

    name = fields.StringField(
        'name',
        validators=[validators.Optional()]
    )

    expire = fields.IntegerField(
        'expire',
        validators=[
            validators.Optional(),
            validators.NumberRange(min=1)
        ]
    )

    secure = fields.BooleanField('secure')


# Handlers

class BaseCollectionHandler(APIHandler):

    DEFAULT_PROJECTION = {
        'variations': {
            '$sub.': Variation
        }
    }

    def get_assets(self, projection=None):
        """
        Return a list of assets given (as JSON) in the form argument `assets`.
        """

        uids = self.get_body_arguments('uids')
        if not uids:
            raise APIError(
                'invalid_request',
                hint=f'No uids provided.'
            )

        # Fetch the asset
        return Asset.many(
            And(
                Q.account == self.account,
                In(Q.uid, uids),
                Not(Q.expires <= time.time())
            ),
            projection=(projection or self.DEFAULT_PROJECTION)
        )

    def get_backend(self, secure=False):
        """
        Return the storage backend for the account. Raise an error if the
        request backend isn't configured.
        """

        backend_type = 'secure' if secure else 'public'

        account = Account.by_id(
            self.account._id,
            projection={f'{backend_type}_backend_settings': True}
        )

        backend = getattr(account, f'{backend_type}_backend', None)

        if not backend:
            raise APIError(
                'invalid_request',
                hint=f'No backend configured for {backend_type} storage.'
            )

        return backend


class CollectionHandler(BaseCollectionHandler):

    def get(self):

        # Validate the arguments
        form = ManyForm(to_multi_dict(self.request.query_arguments))
        if not form.validate():
            raise APIError(
                'invalid_request',
                arg_errors=form.errors
            )

        form_data = form.data

        # Build the document query
        query_stack = [Q.account == self.account]

        if form_data['q']:
            q = form_data['q']
            q_match = re.compile(re.escape(remove_accents(q)), re.I)
            query_stack.append(Q.name == q_match)

        if form_data['backend'] == 'public':
            query_stack.append(Q.secure == True)
        if form_data['backend'] == 'secure':
            query_stack.append(Q.secure == False)

        if form_data['type']:
            query_stack.append(Q.type == form_data['type'])

        # Get the paginated results
        response = paginate(
            Asset,
            query_stack,
            self.request,
            before=form_data['before'],
            after=form_data['after'],
            limit=form_data['limit'],
            projection={
                'created': True,
                'modified': True,
                'name': True,
                'secure': True,
                'type': True,
                'uid': True,
                'ext': True
            }
        )

        self.write(response)

    async def put(self):
        """Store the uploaded file as an asset"""

        # Make sure a file was received
        files = self.request.files.get('file')
        if not files:
            raise APIError(
                'invalid_request',
                arg_errors={'file': ['No file received.']}
            )
        file = files[0]

        # Validate the arguments
        form = PutForm(to_multi_dict(self.request.body_arguments))
        if not form.validate():
            raise APIError(
                'invalid_request',
                arg_errors=form.errors
            )

        if self.config['ANTI_VIRUS_ENABLED']:

            # Check the file for viruses
            av_client = clamd.ClamdUnixSocket(
                self.config['ANTI_VIRUS_CLAMD_PATH']
            )
            av_scan_result = av_client.instream(io.BytesIO(file.body))

            if av_scan_result['stream'][0] == 'FOUND':
                raise APIError(
                    'invalid_request',
                    arg_errors={
                        'file': ['File appears to be a virus.']
                    }
                )

        form_data = form.data

        # Create a name for the asset
        fname, fext = os.path.splitext(file.filename)
        name = slugify(
            form_data['name'] or fname,
            regex_pattern=ALLOWED_SLUGIFY_CHARACTERS,
            max_length=200
        )

        # Determine the files extension
        ext = fext[1:] if fext else imghdr.what(file.filename, file.body)

        # Determine the asset type/content type for the image
        content_type = mimetypes.guess_type(f'f.{ext}')[0] \
                or 'application/octet-stream'
        asset_type = self.config['CONTENT_TYPE_TO_TYPES'].get(
            content_type,
            'file'
        )

        # Build the meta data for the asset
        meta = {
            'filename': file.filename,
            'length': len(file.body)
        }

        if asset_type == 'audio':
            try:
                au_file = io.BytesIO(file.body)
                au_file.name = file.filename
                au = mutagen.File(au_file)

            except:
                raise APIError(
                    'invalid_request',
                    arg_errors={
                        'file': ['Unable to open the file as an audio file.']
                    }
                )

            if au is not None:
                meta['audio'] = {
                    'channels': getattr(au.info, 'channels', -1),
                    'length': getattr(au.info, 'length', -1),
                    'mode': {
                        0: 'stereo',
                        1: 'joint_stereo',
                        2: 'dual_channel',
                        3: 'mono'
                    }.get(getattr(au.info, 'mode', ''), ''),
                    'sample_rate': getattr(au.info, 'sample_rate', -1)
                }

        if asset_type == 'image':

            im = None

            try:
                im = Image.open(io.BytesIO(file.body))
                meta['image'] = {
                    'mode': im.mode,
                    'size': im.size
                }

            except:
                raise APIError(
                    'invalid_request',
                    arg_errors={
                        'file': ['Unable to open the file as an image.']
                    }
                )

            finally:
                if im:
                    im.close()

        # Create the asset
        asset = Asset(
            uid=Asset.generate_uid(),
            account=self.account,
            secure=form_data['secure'],
            name=name,
            ext=ext,
            type=asset_type,
            content_type=content_type,
            expires=(time.time() + form_data['expire'])
                    if form_data['expire'] else None,
            meta=meta
        )

        # Store the file
        backend = self.get_backend(asset.secure)

        await backend.async_store(
            io.BytesIO(file.body),
            asset.store_key,
            loop=asyncio.get_event_loop()
        )

        # Save the asset
        asset.insert()

        # Update the asset stats
        Stats.inc(
            self.account,
            today_tz(tz=self.config['TIMEZONE']),
            {
                'assets': 1,
                'length': asset.meta['length']
            }
        )

        self.write(asset.to_json_type())

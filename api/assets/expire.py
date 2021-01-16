from datetime import datetime
import time

from manhattan.forms import BaseForm, fields, validators
from mongoframes import In, Q

from api import APIError, APIHandler
from api.utils import to_multi_dict
from blueprints.assets.models import Asset

from .document import BaseDocumentHandler

__all__ = [
    'ExpireHandler',
    'ExpireManyHandler'
]


# Forms

class ExpireForm(BaseForm):

    seconds = fields.IntegerField(
        'seconds',
        validators=[validators.NumberRange(min=0)]
    )


# Handlers

class ExpireHandler(BaseDocumentHandler):

    def post(self, uid):
        """
        Set a timeout for the asset. After the timeout has expired the asset
        will be automatically deleted.

        NOTE: The files associated with expired assets are delete periodically
        and therefore may still temporarily be available after the asset has
        expired and is not longer available via the API.
        """

        asset = self.get_asset(
            uid,
            projection={
                'uid': True,
                'expires': True
            }
        )

        # Validate the arguments
        form = ExpireForm(to_multi_dict(self.request.body_arguments))
        if not form.validate():
            raise APIError(
                'invalid_request',
                arg_errors=form.errors
            )

        form_data = form.data

        # Update the expires timestamp for the asset
        asset.expires = time.time() + form_data['seconds']
        asset.update('expires', 'modified')

        self.write({
            'uid': asset.uid,
            'expires': asset.expires
        })


class ExpireManyHandler(BaseDocumentHandler):

    def post(self):
        """
        Removes any existing timeout for one or more existing assets making
        the assets persistent.

        Set a timeout for one or more assets. After the timeout has expired
        the assets will be automatically deleted.

        NOTE: The files associated with expired assets are delete periodically
        and therefore may still temporarily be available after the asset has
        expired and is not longer available via the API.
        """

        assets = self.get_assets(projection={'uid': True})

        # Validate the arguments
        form = ExpireForm(to_multi_dict(self.request.body_arguments))
        if not form.validate():
            raise APIError(
                'invalid_request',
                arg_errors=form.errors
            )

        form_data = form.data

        # Update the expires timestamp for the asset
        expires = time.time() + form_data['seconds']
        Asset.get_collection().update(
            In(Q._id, [a._id for a in assets]).to_dict(),
            {
                '$set': {
                    'expires': time.time() + form_data['seconds'],
                    'modified': datetime.utcnow()
                }
            },
            multi=True
        )

        self.write({
            'results': [
                {
                    'uid': a.uid,
                    'expires': expires
                }
                for a in assets
            ]
        })


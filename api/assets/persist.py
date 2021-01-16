from datetime import datetime
import time

from mongoframes import In, Q

from api import APIError, APIHandler
from blueprints.assets.models import Asset

from .collection import BaseCollectionHandler
from .document import BaseDocumentHandler

__all__ = [
    'PersistHandler',
    'PersistManyHandler'
]


class PersistHandler(BaseDocumentHandler):

    def post(self, uid):
        """
        Removes any existing timeout for an asset making the asset persistent.
        """

        asset = self.get_asset(
            uid,
            projection={
                'uid': True,
                'expires': True
            }
        )

        # Clear the expires timestamp (if there is one)
        Asset.get_collection().update(
            {'_id': asset._id},
            {
                '$set': {'modified': datetime.utcnow()},
                '$unset': {'expires': ''}
            }
        )

        self.write({
            'uid': asset.uid,
            'expires': None
        })


class PersistManyHandler(BaseDocumentHandler):

    def post(self):
        """
        Removes any existing timeout for one or more existing assets making
        the assets persistent.
        """

        assets = self.get_assets(projection={'uid': True})

        # Clear the expires timestamp (if there is one) for the assets
        Asset.get_collection().update(
            In(Q._id, [a._id for a in assets]).to_dict(),
            {
                '$set': {'modified': datetime.utcnow()},
                '$unset': {'expires': ''}
            },
            multi=True
        )

        self.write({
            'results': [
                {
                    'uid': a.uid,
                    'expires': None
                }
                for a in assets
            ]
        })

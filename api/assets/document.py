from mongoframes import And, Q

from api import APIError, APIHandler
from blueprints.accounts.models import Account
from blueprints.assets.models import Asset, Variation

from .collection import BaseCollectionHandler

__all__ = ['DocumentHandler']


class BaseDocumentHandler(BaseCollectionHandler):

    DEFAULT_PROJECTION = {
        'variations': {
            '$sub.': Variation
        }
    }

    def get_asset(self, uid, projection=None):
        """
        Get the asset for the given `uid` and raise an error if no asset is
        found.
        """

        assert not projection or 'expires' in projection, \
                '`expires` must be included by the projection'

        # Fetch the asset
        asset = Asset.one(
            And(
                Q.account == self.account,
                Q.uid == uid
            ),
            projection=(projection or self.DEFAULT_PROJECTION)
        )
        if not asset or asset.expired:
            raise APIError(
                'not_found',
                hint=f'Asset not found for uid: {uid}.'
            )

        return asset

    def get_variation(self, asset, name):
        """
        Return the named variation from the asset and raise an error if the
        variation does not exists.
        """

        variation = asset.variations.get(name)
        if not variation:
            raise APIError(
                'not_found',
                hint=f'Variation not found: {name}'
            )

        return variation


class DocumentHandler(BaseDocumentHandler):

    def get(self, uid):
        """Fetch an asset"""
        asset = self.get_asset(uid)
        self.write(asset.to_json_type())

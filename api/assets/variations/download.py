import asyncio
from mongoframes import And, Q

from api import APIError, APIHandler
from api.assets.document import BaseDocumentHandler
from blueprints.accounts.models import Account
from blueprints.assets.models import Asset, Variation

__all__ = ['DownloadHandler']


class DownloadHandler(BaseDocumentHandler):

    async def get(self, uid, variation_name):
        """Download an asset's file"""

        asset = self.get_asset(
            uid,
            projection={
                'expires': True,
                'name': True,
                'secure': True,
                'uid': True,
                f'variations.{variation_name}': {
                    '$sub': Variation,
                    'content_type': True,
                    'ext': True,
                    'version': True
                }
            }
        )

        variation = self.get_variation(asset, variation_name)

        # Downlad the file
        backend = self.get_backend(asset.secure)

        file = await backend.async_retrieve(
            variation.get_store_key(asset, variation_name),
            loop=asyncio.get_event_loop()
        )

        self.set_header(
            'Content-Type',
            variation.content_type or 'application/octet-stream'
        )
        self.write(file)

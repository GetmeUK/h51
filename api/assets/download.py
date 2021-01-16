import asyncio
from mongoframes import And, Q

from api import APIError, APIHandler
from blueprints.accounts.models import Account
from blueprints.assets.models import Asset

from .document import BaseDocumentHandler

__all__ = ['DownloadHandler']


class DownloadHandler(BaseDocumentHandler):

    async def get(self, uid):
        """Download an asset's file"""
        asset = self.get_asset(
            uid,
            projection={
                'ext': True,
                'name': True,
                'secure': True,
                'uid': True,
                'content_type': True,
                'expires': True
            }
        )

        # Downlad the file
        backend = self.get_backend(asset.secure)

        file = await backend.async_retrieve(
            asset.store_key,
            loop=asyncio.get_event_loop()
        )

        self.set_header(
            'Content-Type',
            asset.content_type or 'application/octet-stream'
        )
        self.write(file)

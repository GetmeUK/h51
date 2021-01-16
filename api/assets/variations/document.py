import asyncio

from manhattan.utils.chrono import today_tz
from mongoframes import And, Q

from api import APIError, APIHandler
from api.assets.document import BaseDocumentHandler
from blueprints.accounts.models import Account, Stats
from blueprints.assets.models import Asset, Variation

__all__ = ['DocumentHandler']


class DocumentHandler(BaseDocumentHandler):

    async def delete(self, uid, variation_name):
        """Remove the variation from the asset"""

        asset = self.get_asset(
            uid,
            projection={
                'expires': True,
                'name': True,
                'secure': True,
                'uid': True,
                f'variations.{variation_name}': {'$sub': Variation}
            }
        )

        variation = self.get_variation(asset, variation_name)

        # Remove file for the variation
        backend = self.get_backend(asset.secure)

        await backend.async_delete(
            variation.get_store_key(asset, variation_name),
            loop=asyncio.get_event_loop()
        )

        # Remove the variation from the asset
        Asset.get_collection().update(
            (Q._id == asset._id).to_dict(),
            {
                '$unset': {
                    f'variations.{variation_name}': ''
                }
            }
        )

        # Update the asset stats
        Stats.inc(
            self.account,
            today_tz(tz=self.config['TIMEZONE']),
            {
                'variations': -1,
                'length': -variation.meta['length']
            }
        )

        self.set_status(204)
        self.finish()

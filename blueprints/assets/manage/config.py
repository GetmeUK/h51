from bson.objectid import ObjectId
from flask import request
from manhattan.manage import config
from manhattan.nav import Nav, NavItem

from blueprints.assets.manage import blueprint
from blueprints.assets.models import Asset

__all__ = ['AssetConfig']


class AssetConfig(config.ManageConfig):

    frame_cls = Asset
    blueprint = blueprint

    @classmethod
    def tabs(cls, view_type, document=None):
        tabs = Nav.local_menu()

        if view_type in ['variations', 'view']:

            tabs.add(
                NavItem(
                    'Details',
                    endpoint=AssetConfig.get_endpoint('view'),
                    view_args={'asset': document._id}
                )
            )

            tabs.add(
                NavItem(
                    f'Variations ({len(document.variations or {})})',
                    endpoint=AssetConfig.get_endpoint('variations'),
                    view_args={'asset': document._id}
                )
            )

        return tabs


# Nav rules

@Nav.rule
def not_expired(**view_args):
    """
    This action is only available against assets that have not expired.
    """

    asset_id = view_args.get('asset', request.args.get('asset'))

    if asset_id:

        asset = Asset.by_id(
            ObjectId(asset_id),
            projection={'expires': True}
        )

        if asset:
            return not asset.expired

    return False

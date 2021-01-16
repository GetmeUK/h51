from manhattan.manage import config
from manhattan.nav import Nav, NavItem

from blueprints.accounts.manage import blueprint
from blueprints.accounts.models import Account

__all__ = ['AccountConfig']


class AccountConfig(config.ManageConfig):

    frame_cls = Account
    blueprint = blueprint

    @classmethod
    def tabs(cls, view_type, document=None):
        tabs = Nav.local_menu()

        if view_type in ['api_log', 'change_log', 'activity', 'view']:

            tabs.add(
                NavItem(
                    'Details',
                    endpoint=AccountConfig.get_endpoint('view'),
                    view_args={'account': document._id}
                )
            )

            tabs.add(
                NavItem(
                    'Activity',
                    endpoint=AccountConfig.get_endpoint('activity'),
                    view_args={'account': document._id}
                )
            )

            tabs.add(
                NavItem(
                    'API log',
                    endpoint=AccountConfig.get_endpoint('api_log'),
                    view_args={'account': document._id}
                )
            )

            tabs.add(
                NavItem(
                    'Change log',
                    endpoint=AccountConfig.get_endpoint('change_log'),
                    view_args={'account': document._id}
                )
            )

        return tabs

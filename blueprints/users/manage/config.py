from flask import abort, g, request
from manhattan.manage import config
from manhattan.nav import Nav, NavItem

from blueprints.users.manage import blueprint
from blueprints.users.models import User

__all__ = ['UserConfig']


class UserConfig(config.ManageConfig):

    frame_cls = User
    blueprint = blueprint
    titleize = lambda d: d.full_name

    @classmethod
    def tabs(cls, view_type, document=None):
        tabs = Nav.local_menu()

        if view_type in ['activity_log', 'change_log', 'view']:

            tabs.add(
                NavItem(
                    'Details',
                    endpoint=UserConfig.get_endpoint('view'),
                    view_args={'user': document._id}
                )
            )

            tabs.add(
                NavItem(
                    'Activity log',
                    endpoint=UserConfig.get_endpoint('activity_log'),
                    view_args={'user': document._id}
                )
            )

            tabs.add(
                NavItem(
                    'Change log',
                    endpoint=UserConfig.get_endpoint('change_log'),
                    view_args={'user': document._id}
                )
            )

        return tabs


# Nav rules

@Nav.rule
def not_me(**view_args):
    """Don't allow me to call this view with myself as the target"""
    return str(g.user._id) != request.values.get('user')

@Nav.rule
def mfa_enabled(**view_args):
    return g.user.mfa_enabled

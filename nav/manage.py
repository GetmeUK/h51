"""
Primary navigation menu for the manage area.
"""

from manhattan.nav import Nav, NavItem
from mongoframes import Q

from blueprints.accounts.manage.config import AccountConfig
from blueprints.assets.manage.config import AssetConfig
from blueprints.users.manage.config import UserConfig


# Define the primary menu
menu = Nav.menu('manage')


# Dashboard
menu.add(NavItem('Dashboard', UserConfig.get_endpoint('dashboard')))

# Assets

assets_group = Nav.menu('assets_group')
assets_group.label = 'Assets'
assets_group.data = {'group': True}
menu.add(assets_group)

# Assets > Assets
assets_group.add(NavItem('Assets', AssetConfig.get_endpoint('list')))

# Admin

admin_group = Nav.menu('admin_group')
admin_group.label = 'Admin'
admin_group.data = {'group': True}
menu.add(admin_group)

# Accounts > Accounts
admin_group.add(NavItem('Accounts', AccountConfig.get_endpoint('list')))

# Admin > Users
admin_group.add(NavItem('Users', UserConfig.get_endpoint('list')))


# Define the manage user menu
user_menu = Nav.menu('manage_user')

user_menu.add(
    NavItem('Update my profile', UserConfig.get_endpoint('update_my_profile'))
)

user_menu.add(NavItem('Security', UserConfig.get_endpoint('security')))

sign_out_group = user_menu.add(NavItem(data={'group': True}))
sign_out_group.add(
    NavItem('Sign out',
        UserConfig.get_endpoint('sign_out'),
        data={'icon': 'sign-out'}
    )
)

"""
Delete a user.
"""

from manhattan.nav import Nav
from manhattan.users import views

from blueprints.users.manage.config import UserConfig


# Chains
delete_chains = views.delete_chains.copy()

# Set the URL
UserConfig.add_view_rule('/users/delete', 'delete', delete_chains)

# Set the nav rules
Nav.apply(UserConfig.get_endpoint('delete'), ['not_me'])

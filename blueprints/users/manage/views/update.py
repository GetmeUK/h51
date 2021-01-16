"""
Update a user.
"""

from manhattan.nav import Nav
from manhattan.users import views

from blueprints.users.manage.config import UserConfig


# Chains
update_chains = views.update_chains.copy()

# Set the URL
UserConfig.add_view_rule('/users/update', 'update', update_chains)

# Set the nav rules
Nav.apply(UserConfig.get_endpoint('update'), ['not_me'])

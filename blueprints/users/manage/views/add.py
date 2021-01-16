"""
Add a user.
"""

from manhattan.users import views

from blueprints.users.manage.config import UserConfig


# Chains
add_chains = views.add_chains.copy()

# Set the URL
UserConfig.add_view_rule('/users/add', 'add', add_chains)

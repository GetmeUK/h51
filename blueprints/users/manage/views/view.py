"""
View a user.
"""

from manhattan.users import views

from blueprints.users.manage.config import UserConfig


# Chains
view_chains = views.view_chains.copy()

# Set the URL
UserConfig.add_view_rule('/users/view', 'view', view_chains)

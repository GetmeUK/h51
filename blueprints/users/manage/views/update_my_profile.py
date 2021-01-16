"""
Allow a user to update their profile.
"""

from manhattan.users import views

from blueprints.users.manage.config import UserConfig


# Chains
update_my_profile_chains = views.update_my_profile_chains.copy()

# Set the URL
UserConfig.add_view_rule(
    '/update-my-profile',
    'update_my_profile',
    update_my_profile_chains
)

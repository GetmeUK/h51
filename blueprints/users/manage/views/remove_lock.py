"""
Remove a lock from a user.
"""

from manhattan.users import views

from blueprints.users.manage.config import UserConfig


# Chains
remove_lock_chains = views.remove_lock_chains.copy()

# Set the URL
UserConfig.add_view_rule(
    '/users/remove-lock',
    'remove_lock',
    remove_lock_chains
)

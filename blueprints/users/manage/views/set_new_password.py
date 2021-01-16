"""
Allow users to set a new password.
"""

from manhattan.users import views

from blueprints.users.manage.config import UserConfig


# Chains
set_new_password_chains = views.set_new_password_chains.copy()

# Set the URL
UserConfig.add_view_rule(
    '/set-new-password',
    'set_new_password',
    set_new_password_chains
)

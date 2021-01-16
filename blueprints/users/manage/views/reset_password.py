"""
Allow users to request a link to reset their password with.
"""


from manhattan.users import views

from blueprints.users.manage.config import UserConfig


# Chains
reset_password_chains = views.reset_password_chains.copy()

# Set the URL
UserConfig.add_view_rule(
    '/reset-password',
    'reset_password',
    reset_password_chains,
)

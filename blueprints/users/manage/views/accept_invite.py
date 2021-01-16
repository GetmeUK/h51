"""
Allow users to accept an invite to join the application.
"""

from manhattan.users import views

from blueprints.users.manage.config import UserConfig


# Chains
accept_invite_chains = views.accept_invite_chains.copy()

# Set the URL
UserConfig.add_view_rule(
    '/accept-invite',
    'accept_invite',
    accept_invite_chains
)

"""
Resend an invite to a user.
"""

from manhattan.users import views

from blueprints.users.manage.config import UserConfig


# Chains
resend_invite_chains = views.resend_invite_chains.copy()

# Set the URL
UserConfig.add_view_rule(
    '/users/resend-invite',
    'resend_invite',
    resend_invite_chains
)

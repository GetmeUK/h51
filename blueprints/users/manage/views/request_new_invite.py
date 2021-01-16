"""
Allow users to request a new invite.
"""

from manhattan.users import views

from blueprints.users.manage.config import UserConfig


# Chains
request_new_invite_chains = views.request_new_invite_chains.copy()

# Set the URL
UserConfig.add_view_rule(
    '/request-new-invite',
    'request_new_invite',
    request_new_invite_chains
)

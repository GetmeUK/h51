"""
Revoke a user's session.
"""

from manhattan.users import views

from blueprints.users.manage.config import UserConfig


# Chains
revoke_session_chains = views.revoke_session_chains.copy()

# Set the URLs

UserConfig.add_view_rule(
    '/users/revoke-session',
    'revoke_session',
    revoke_session_chains
)

UserConfig.add_view_rule(
    '/users/revoke-my-session',
    'revoke_my_session',
    revoke_session_chains
)

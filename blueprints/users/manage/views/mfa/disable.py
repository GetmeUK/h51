"""
Disable multi-factor authentication (MFA) for the user.
"""

from manhattan.nav import Nav
from manhattan.users import views

from blueprints.users.manage.config import UserConfig


# Chains
disable_chains = views.mfa.disable_chains.copy()

# Set the URL
UserConfig.add_view_rule(
    '/security/mfa/disable',
    'mfa_disable',
    disable_chains
)

# Set the nav rules
Nav.apply(UserConfig.get_endpoint('mfa_disable'), ['mfa_enabled'])

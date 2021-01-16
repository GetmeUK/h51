"""
View the user's recovery codes.
"""

from manhattan.nav import Nav
from manhattan.users import views

from blueprints.users.manage.config import UserConfig


# Chains
recovery_codes_chains = views.mfa.recovery_codes_chains.copy()

# Set the URL
UserConfig.add_view_rule(
    '/security/mfa/recovery-codes',
    'mfa_recovery_codes',
    recovery_codes_chains
)

# Set the nav rules
Nav.apply(UserConfig.get_endpoint('mfa_recovery_codes'), ['mfa_enabled'])


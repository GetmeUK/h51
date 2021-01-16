"""
Regenerate the user's list of recovery codes.
"""

from manhattan.nav import Nav
from manhattan.users import views

from blueprints.users.manage.config import UserConfig


# Chains
regenerate_recovery_codes_chains \
        = views.mfa.regenerate_recovery_codes_chains.copy()

# Set URL
UserConfig.add_view_rule(
    '/security/mfa/regenerate-recovery-codes',
    'mfa_regenerate_recovery_codes',
    regenerate_recovery_codes_chains
)

# Set nav rules
Nav.apply(
    UserConfig.get_endpoint('mfa_regenerate_recovery_codes'),
    ['mfa_enabled']
)

"""
Download a text file containing the user's recovery codes.
"""

from manhattan.nav import Nav
from manhattan.users import views

from blueprints.users.manage.config import UserConfig


# Chains
download_recovery_codes_chains \
        = views.mfa.download_recovery_codes_chains.copy()

# Set the URL
UserConfig.add_view_rule(
    '/security/mfa/download-recovery-codes',
    'mfa_download_recovery_codes',
    download_recovery_codes_chains
)

# Set nav rules
Nav.apply(
    UserConfig.get_endpoint('mfa_download_recovery_codes'),
    ['mfa_enabled']
)

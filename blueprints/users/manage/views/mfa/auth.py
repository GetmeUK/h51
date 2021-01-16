"""
Authorize the user using a secondary mechanism.
"""

from manhattan.nav import Nav
from manhattan.users import views

from blueprints.users.manage.config import UserConfig


# Chains
auth_chains = views.mfa.auth_chains.copy()

# Set the URL
UserConfig.add_view_rule('/security/mfa/auth', 'mfa_auth', auth_chains)

# Set nav rules
Nav.apply(UserConfig.get_endpoint('mfa_auth'), ['mfa_enabled'])

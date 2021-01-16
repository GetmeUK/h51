"""
Enable multi-factor authentication (MFA) for the user.
"""

from flask import g
from manhattan.nav import Nav
from manhattan.users import views

from blueprints.users.manage.config import UserConfig


# Chains
enable_chains = views.mfa.enable_chains.copy()

# Set the URL
UserConfig.add_view_rule('/security/mfa/enable', 'mfa_enable', enable_chains)

# Set nav rules
Nav.apply(UserConfig.get_endpoint('mfa_enable'), ['not_mfa_enabled'])

@Nav.rule
def not_mfa_enabled(**view_args):
    return not g.user.mfa_enabled

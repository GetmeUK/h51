"""
Display the change log for a account.
"""

from manhattan.manage.views import generic
from manhattan.nav import Nav

from blueprints.accounts.manage.config import AccountConfig


# Chains
change_log_chains = generic.change_log.copy()

# Set URL
AccountConfig.add_view_rule('/accounts/change-log', 'change_log', change_log_chains)

"""
Display the change log for a user.
"""

from manhattan.users import views

from blueprints.users.manage.config import UserConfig


# Chains
change_log_chains = views.change_log_chains.copy()

# Set the URL
UserConfig.add_view_rule('/users/change-log', 'change_log', change_log_chains)

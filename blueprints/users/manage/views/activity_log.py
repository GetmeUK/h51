"""
Display the activity log for a user.
"""

from manhattan.users import views

from blueprints.users.manage.config import UserConfig


# Chains
activity_log_chains = views.activity_log_chains.copy()

# Set the URL
UserConfig.add_view_rule(
    '/users/activity-log',
    'activity_log',
    activity_log_chains
)

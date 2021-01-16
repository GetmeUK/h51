"""
Allow a user to change their password, view, enable and disable their
multi-factor authentication and
"""

from manhattan.users import views

from blueprints.users.manage.config import UserConfig


# Chains
security_chains = views.security_chains.copy()

# Set the URLs
UserConfig.add_view_rule('/security', 'security', security_chains)

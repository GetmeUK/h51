"""
Allow users to sign-in.
"""

from manhattan.users import views

from blueprints.users.manage.config import UserConfig


# Chains
sign_in_chains = views.sign_in_chains.copy()

# Set the URL
UserConfig.add_view_rule('/sign-in', 'sign_in', sign_in_chains)

"""
Sign the current user out.
"""

from manhattan.users import views

from blueprints.users.manage.config import UserConfig


# Chains
sign_out_chains = views.sign_out_chains.copy()

# Set the URL
UserConfig.add_view_rule('/sign-out', 'sign_out', sign_out_chains)

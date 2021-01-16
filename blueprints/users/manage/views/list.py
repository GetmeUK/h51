"""
List users.
"""

from manhattan.nav import Nav
from manhattan.users import views

from blueprints.users.manage.config import UserConfig


# Chains
list_chains = views.list_chains.copy()

# Set the URL
UserConfig.add_view_rule('/users', 'list', list_chains)

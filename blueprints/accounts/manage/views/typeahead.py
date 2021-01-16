"""
Typeahead for accounts.
"""

from manhattan.manage.views import generic

from blueprints.accounts.manage.config import AccountConfig


# Customize the chain
typeahead_chains = generic.typeahead.copy()

# Configure the view
initial_state = dict(
    typeahead_field='name'
)

# Set the URL
AccountConfig.add_view_rule(
    '/accounts/typeahead',
    'typeahead',
    typeahead_chains,
    initial_state
)

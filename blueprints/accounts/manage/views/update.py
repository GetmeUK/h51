"""
Update an account.
"""

from manhattan.forms import fields, validators
from manhattan.manage.views import generic

from blueprints.accounts.manage.config import AccountConfig
from blueprints.accounts.manage.views.add import AddForm
from blueprints.accounts.models import Account


# Forms

class UpdateForm(AddForm):

    pass


# Chains
update_chains = generic.update.copy()

# Configure the view
initial_state = dict(
    form_cls=UpdateForm
)

# Set URL
AccountConfig.add_view_rule(
    '/accounts/update',
    'update',
    update_chains,
    initial_state
)

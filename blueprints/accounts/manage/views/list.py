"""
List accounts.
"""

from manhattan.forms import BaseForm, fields
from manhattan.forms.utils import sort_by_choices
from manhattan.manage.views import generic
from manhattan.nav import Nav, NavItem

from blueprints.accounts.manage.config import AccountConfig


# Forms

class ListForm(BaseForm):

    page = fields.IntegerField('Page', default=1)

    q = fields.StringField('Search')

    sort_by = fields.SelectField(
        'Sort by',
        choices=sort_by_choices([
            ('name', 'Name')
        ]),
        default='name'
    )


# Chains
list_chains = generic.list.copy()

# Configure the view
initial_state = dict(
    collation={
        'locale': 'en',
        'strength': 2
    },
    form_cls=ListForm,
    projection={
        'name': True
    },
    search_fields=['name']
)

# Set URL
AccountConfig.add_view_rule(
    '/accounts',
    'list',
    list_chains,
    initial_state
)

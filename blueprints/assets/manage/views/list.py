"""
List assets.
"""

from datetime import datetime
import operator
import time

from flask import current_app
from manhattan.forms import BaseForm, fields, utils
from manhattan.forms.utils import sort_by_choices
from manhattan.manage.views import generic
from manhattan.nav import Nav, NavItem
from mongoframes import And, Not, Q

from blueprints.accounts.models import Account
from blueprints.assets.manage.config import AssetConfig


# Forms

class TypeList:
    """Simple iterator to return the list of asset types available"""

    def __iter__(self):

        type_options = [
            (t, t.capitalize())
            for t in set(current_app.config['CONTENT_TYPE_TO_TYPES'].values())
        ]
        type_options.append(('file', 'File'))
        type_options.sort(key=operator.itemgetter(1))
        type_options.insert(0, ('', 'Any'))

        for type_option in type_options:
            yield type_option


class Filters(BaseForm):

    account = fields.HiddenField(coerce=utils.to_object_id)
    account_typeahead = fields.StringField(
        'Account',
        render_kw={
            'autocomplete': 'typeahead',
            'data-mh-typeahead': True,
            'data-mh-typeahead--list':'/accounts/typeahead',
            'data-mh-typeahead--fetch': 'ajax',
            'data-mh-typeahead--input': 'setHidden',
            'data-mh-typeahead--filter': 'contains',
            'data-mh-typeahead--hidden-selector': '[name="filters-account"]',
            'data-mh-typeahead--auto-first': True,
            'data-mh-typeahead--must-match': True
        }
    )

    type = fields.SelectField(
        'Type',
        choices=TypeList(),
        default=''
    )

    storage = fields.SelectField(
        'Storage',
        choices=[
            ('', 'Any'),
            ('public', 'Public'),
            ('secure', 'Secure')
        ],
        default=''
    )

    def filter_account_typeahead(filter_form, form, field):
        pass

    def filter_storage(filter_form, form, field):

        if field.data == 'public':
            return Q.secure == False

        if field.data == 'secure':
            return Q.secure == True


class ListForm(BaseForm):

    page = fields.IntegerField('Page', default=1)

    q = fields.StringField('Search')

    sort_by = fields.SelectField(
        'Sort by',
        choices=sort_by_choices([('created', 'Created')]),
        default='-created'
    )

    filters = fields.FormField(Filters)


# Chains
list_chains = generic.list.copy()

# Custom overrides

@list_chains.link
def filter(state):
    generic.list.chains['get'].super(state)

    if state.query:
        state.query = And(
            Not(Q.expires <= time.time()),
            state.query
        )

    else:
        state.query = Not(Q.expires <= time.time())

# Configure the view
initial_state = dict(
    form_cls=ListForm,
    projection={
        'created': True,
        'account': {
            '$ref': Account,
            'name': True
        },
        'secure': True,
        'name': True,
        'uid': True,
        'ext': True,
        'type': True,
        'expires': True
    },
    search_fields=['name', 'uid']
)

# Set URL
AssetConfig.add_view_rule(
    '/assets',
    'list',
    list_chains,
    initial_state
)

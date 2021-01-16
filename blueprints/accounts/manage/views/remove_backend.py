"""
Remove the public or secure backend for an account.
"""

from flask import flash, request
from manhattan.chains import Chain, ChainMgr
from manhattan.manage.views import factories, generic, utils as manage_utils
from manhattan.nav import NavItem
from mongoframes import Q

from blueprints.accounts.manage.config import AccountConfig
from blueprints.accounts.models import Account


# Define the chains
remove_backend_chains = ChainMgr()

# GET
remove_backend_chains['get'] = Chain([
    'config',
    'authenticate',
    'get_type',
    'get_document',
    'decorate',
    'render_template'
])

# POST
remove_backend_chains['post'] = Chain([
    'config',
    'authenticate',
    'get_type',
    'get_document',
    'clear_backend_settings',
    'redirect'
])

remove_backend_chains.set_link(factories.config(projection=None))
remove_backend_chains.set_link(factories.authenticate())
remove_backend_chains.set_link(factories.get_document())
remove_backend_chains.set_link(
    factories.render_template('remove_backend.html')
)
remove_backend_chains.set_link(factories.redirect('view', include_id=True))

@remove_backend_chains.link
def decorate(state):
    state.decor = manage_utils.base_decor(
        state.manage_config,
        'remove_backend',
        state.provider
    )

    # Title
    state.decor['title'] = f'Remove {state.type} backend for {state.account}'

    # Breadcrumbs
    state.decor['breadcrumbs'].add(
        NavItem('Accounts', AccountConfig.get_endpoint('list'))
    )
    state.decor['breadcrumbs'].add(
        NavItem(
            'Account details',
            AccountConfig.get_endpoint('view'),
            {'account': state.account._id}
        )
    )
    state.decor['breadcrumbs'].add(NavItem(f'Remove {state.type} backend'))

@remove_backend_chains.link
def get_type(state):
    
    state.type = request.values.get('type')

    assert state.type in ['public', 'secure'], 'Unknown type'

    # Modify the update fields configured based on the type
    state.update_fields = [f'{state.type}_backend_settings']

@remove_backend_chains.link
def clear_backend_settings(state):

    backend_field_name = f'{state.type}_backend_settings'
    state.account.logged_update(
        state.manage_user,
        {f'{state.type}_backend_settings': None},
        f'{state.type}_backend_settings'
    )

    flash(f'{state.type.capitalize()} backend removed')


# Configure the view
initial_state = dict()

# Set URL
AccountConfig.add_view_rule(
    '/accounts/remove-backend',
    'remove_backend',
    remove_backend_chains,
    initial_state
)

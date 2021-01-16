"""
Cycle the API key for the account.
"""

import secrets

from flask import flash
from manhattan.chains import Chain, ChainMgr
from manhattan.comparable.change_log import ChangeLogEntry
from manhattan.manage.views import factories, generic, utils as manage_utils
from manhattan.nav import NavItem
from mongoframes import Q

from blueprints.accounts.manage.config import AccountConfig
from blueprints.accounts.models import Account


# Define the chains
cycle_api_access_chains = ChainMgr()

# GET
cycle_api_access_chains['get'] = Chain([
    'config',
    'authenticate',
    'get_document',
    'decorate',
    'render_template'
])

# POST
cycle_api_access_chains['post'] = Chain([
    'config',
    'authenticate',
    'get_document',
    'cycle_api_key',
    'redirect'
])

cycle_api_access_chains.set_link(factories.config(projection=None))
cycle_api_access_chains.set_link(factories.authenticate())
cycle_api_access_chains.set_link(factories.get_document())
cycle_api_access_chains.set_link(
    factories.render_template('cycle_api_key.html')
)
cycle_api_access_chains.set_link(factories.redirect('view', include_id=True))

@cycle_api_access_chains.link
def decorate(state):
    state.decor = manage_utils.base_decor(
        state.manage_config,
        'cycle_api_access',
        state.provider
    )

    # Title
    state.decor['title'] = f'Cycle API key for {state.account}'

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
    state.decor['breadcrumbs'].add(NavItem('Cycle API key'))

@cycle_api_access_chains.link
def cycle_api_key(state):

    state.account.logged_update(
        state.manage_user,
        {'api_key': secrets.token_urlsafe(128)},
        'api_key'
    )

    # Log the change
    entry = ChangeLogEntry({
        'type': 'NOTE',
        'documents': [state.account],
        'user': state.manage_user
    })
    entry.add_note('API key cycled')
    entry.insert()

    flash(f'API key cycled')


# Configure the view
initial_state = dict(
    projection={
        'name': True,
        'api_key': True
    }
)

# Set URL
AccountConfig.add_view_rule(
    '/accounts/cycle-api-key',
    'cycle_api_key',
    cycle_api_access_chains,
    initial_state
)

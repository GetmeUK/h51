"""
View an API log entry.
"""

from datetime import datetime
import json

from flask import abort, current_app, request
from manhattan.manage.views import factories, generic
from manhattan.nav import NavItem

from blueprints.accounts.manage.config import AccountConfig


# Chains
entry_chains = generic.view.copy()
entry_chains.insert_link(
    'get_document',
    'get_api_log_entry',
    after=True
)

# Factory overrides
entry_chains.set_link(
    factories.render_template('api_log/entry.html')
)

# Custom overrides

@entry_chains.link
def decorate(state):
    generic.view.chains['get'].get_link('decorate')(state)

    state.decor['title'] = f'View API log entry for {state.account}'
    state.decor['actions'] = None

    # Breadcrumbs
    state.decor['breadcrumbs'] = NavItem()
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
    state.decor['breadcrumbs'].add(
        NavItem(
            'API Log',
            AccountConfig.get_endpoint('api_log'),
            {'account': state.account._id}
        )
    )
    state.decor['breadcrumbs'].add(NavItem('Entry'))

@entry_chains.link
def get_api_log_entry(state):

    # Find the log entry
    log_entry_id = request.args.get('log_entry')
    keys = [
        state.account.get_api_log_key('succeeded'),
        state.account.get_api_log_key('failed')
    ]

    for key in keys:
        log_entries = current_app.redis.lrange(key, 0, -1)
        log_entries = [json.loads(e) for e in log_entries]

        for log_entry in log_entries:
            if log_entry['id'] == log_entry_id:
                state.log_entry = log_entry
                break

        if state.log_entry:
            break

    if not state.log_entry:
        abort(404, 'Log entry not found')

    # Format called and call times values
    state.log_entry['call_time'] \
            = f'{state.log_entry["call_time"] * 1000:.1f}ms'
    state.log_entry['called'] = datetime.utcfromtimestamp(log_entry['called'])


# Set URL
AccountConfig.add_view_rule(
    '/accounts/api-log/entry',
    'api_log_entry',
    entry_chains
)

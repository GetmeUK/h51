"""
View the API logs (succeeded and failed) for the account.
"""

from datetime import datetime
import json

from flask import current_app
from manhattan.manage.views import factories, generic
from manhattan.nav import NavItem

from blueprints.accounts.manage.config import AccountConfig


# Utils

def fetch_log_entries(key):
    """Return log entries for the given key"""

    # Fetch the entries from Redis
    log_entries = current_app.redis.lrange(key, 0, -1)
    log_entries = [json.loads(e) for e in log_entries]

    # Format called and call times values
    for log_entry in log_entries:
        log_entry['call_time'] = f'{log_entry["call_time"] * 1000:.1f}ms'
        log_entry['called'] = datetime.utcfromtimestamp(log_entry['called'])

    return log_entries

# Chains
log_chains = generic.view.copy()
log_chains.insert_link(
    'get_document',
    'get_api_log',
    after=True
)

# Factory overrides
log_chains.set_link(
    factories.render_template('api_log/log.html')
)

# Custom overrides

@log_chains.link
def decorate(state):
    generic.view.chains['get'].get_link('decorate')(state)
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
    state.decor['breadcrumbs'].add(NavItem('API log'))


@log_chains.link
def get_api_log(state):

    # Succeeded
    state.succeeded_log = fetch_log_entries(
        state.account.get_api_log_key('succeeded')
    )

    # Failed
    state.failed_log = fetch_log_entries(
        state.account.get_api_log_key('failed')
    )

# Set URL
AccountConfig.add_view_rule(
    '/accounts/api-log',
    'api_log',
    log_chains
)

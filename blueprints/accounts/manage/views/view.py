"""
View an account.
"""

from manhattan.manage.views import generic
from manhattan.utils.chrono import today_tz
from mongoframes import Q

from blueprints.accounts.manage.config import AccountConfig
from blueprints.accounts.models import Stats
from blueprints.assets.models import Asset


# Chains
view_chains = generic.view.copy()
view_chains['get'].insert_link('get_document', 'get_highlights', after=True)


# Custom overrides

@view_chains.link
def get_highlights(state):

    # Get the stats for the account
    api_call_keys = Stats.get_key_range(today_tz(), 'days', 7, 'api_calls')

    state.has_stats = False
    stats = Stats.one(
        Q.scope == state.account,
        projection={
            'values.all.assets': True,
            'values.all.length': True,
            'values.all.variations': True,
            **{f'values.{k}': True for k in api_call_keys}
        }
    )

    if stats:
        state.has_stats = True
        state.highlights = {
            'api_calls': stats.sum_stats(api_call_keys),
            'assets': stats.get_stat('all.assets'),
            'length': stats.get_stat('all.length'),
            'variations': stats.get_stat('all.variations')
        }


# Set URL
AccountConfig.add_view_rule('/accounts/view', 'view', view_chains)

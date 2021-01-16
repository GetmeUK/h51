"""
View the activity metrics for an account.
"""

from flask import request
from manhattan.manage.views import factories, generic
from manhattan.utils.chrono import today_tz
from mongoframes import Q

from blueprints.accounts.manage.config import AccountConfig
from blueprints.accounts.models import Stats


# Chains
activity_chains = generic.view.copy()
activity_chains['get'].insert_link('get_document', 'get_metrics', after=True)

# Factory overrides
activity_chains.set_link(factories.render_template('activity.html'))

# Custom overrides

@activity_chains.link
def decorate(state):
    generic.view.chains['get'].get_link('decorate')(state)

    # Remove actions from the page
    state.decor['actions'] = None

@activity_chains.link
def get_metrics(state):

    # Determine the period to view
    unit = 'days'
    length = 90
    state.period = '90d'

    if request.args.get('period') == '12m':
        unit = 'months'
        length = 12
        state.period = '12m'

    elif request.args.get('period') == '10y':
        unit = 'years'
        length = 10
        state.period = '10y'

    # Build the keys required for the period
    today = today_tz()
    api_call_keys = Stats.get_key_range(today, unit, length, 'api_calls')
    asset_keys = Stats.get_key_range(today, unit, length, 'assets')
    length_keys = Stats.get_key_range(today, unit, length, 'length')
    variations_keys = Stats.get_key_range(today, unit, length, 'variations')

    # Get the stats for the account
    state.has_stats = False
    stats = Stats.one(
        Q.scope == state.account,
        projection={
            **{f'values.{k}': True for k in api_call_keys},
            **{f'values.{k}': True for k in asset_keys},
            **{f'values.{k}': True for k in length_keys},
            **{f'values.{k}': True for k in variations_keys}
        }
    )

    if stats:
        state.has_stats = True

        # Build the period totals
        state.totals = {
            'api_calls': stats.sum_stats(api_call_keys),
            'assets': stats.sum_stats(asset_keys),
            'length': stats.sum_stats(length_keys),
            'variations': stats.sum_stats(variations_keys)
        }

        # Build the chart data
        color = {
            'backgroundColor': '#67B3DA64',
            'borderColor': '#67B3DA',
            'pointBackgroundColor': '#67B3DA64',
            'pointBorderColor': '#67B3DA'
        }

        state.data_series = {
            'api_calls': {
                'datasets': [{
                    'data': stats.get_series(api_call_keys),
                    **color
                }],
                'labels': stats.get_series_labels(api_call_keys)
            },
            'assets': {
                'datasets': [{
                    'data': stats.get_series(asset_keys),
                    **color
                }],
                'labels': stats.get_series_labels(asset_keys)
            },
            'length': {
                'datasets': [{
                    'data': [
                        round(v / 1000000, 2)
                        for v in stats.get_series(length_keys)
                    ],
                    **color
                }],
                'labels': stats.get_series_labels(length_keys)
            },
            'variations': {
                'datasets': [{
                    'data': stats.get_series(variations_keys),
                    **color
                }],
                'labels': stats.get_series_labels(variations_keys)
            }
        }


# Set URL
AccountConfig.add_view_rule('/accounts/activity', 'activity', activity_chains)

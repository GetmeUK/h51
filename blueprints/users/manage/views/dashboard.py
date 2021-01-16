"""
Activity dashboard.
"""

from flask import current_app, request
from manhattan.chains import Chain, ChainMgr
from manhattan.manage.views import factories, utils as manage_utils
from manhattan.nav import Nav, NavItem
from manhattan.utils.chrono import today_tz
from mongoframes import Q
from swm.monitors import get_tasks, get_workers

from blueprints.accounts.models import Stats
from blueprints.users.manage.config import UserConfig
from workers.tasks import AnalyzeTask, GenerateVariationTask
from workers.workers import AssetWorker


# Chains

dashboard_chains = ChainMgr()

dashboard_chains['get'] = Chain([
    'authenticate',
    'decorate',
    'get_activity',
    'get_workers_and_tasks',
    'render_template'
    ])

dashboard_chains.set_link(factories.authenticate())
dashboard_chains.set_link(factories.render_template('dashboard.html'))

@dashboard_chains.link
def decorate(state):
    state.decor = manage_utils.base_decor(state.manage_config, 'dashboard')
    state.decor['title'] = 'Dashboard'
    state.decor['breadcrumbs'].add(NavItem('Dashboard', ''))

@dashboard_chains.link
def get_activity(state):

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
        Q.scope == 'all',
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

@dashboard_chains.link
def get_workers_and_tasks(state):
    state.tasks = len(get_tasks(
        current_app.redis,
        AnalyzeTask,
        GenerateVariationTask
    ))
    state.workers = len(get_workers(current_app.redis, AssetWorker))

# Set URL
UserConfig.add_view_rule('/', 'dashboard', dashboard_chains)

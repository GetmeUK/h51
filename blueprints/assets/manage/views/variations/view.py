"""
View a variation for an asset.
"""

from flask import abort, request
from manhattan.manage.views import factories, generic
from manhattan.nav import Nav, NavItem

from blueprints.assets.manage.config import AssetConfig
from blueprints.assets.models import Variation


# Chains
view_chains = generic.view.copy()
view_chains['get'].insert_link(
    'get_document',
    'get_variation',
    after=True
)

# Factory overrides
view_chains.set_link(
    factories.render_template('variations/view.html'))

# Custom overrides

@view_chains.link
def decorate(state):
    generic.view['get'].super(state)

    state.decor['title'] = state.variation.get_store_key(
        state.asset,
        state.variation_name
    )

    # Download
    state.decor['actions'] = NavItem()
    state.decor['actions'].add(
        NavItem(
            'Download',
            AssetConfig.get_endpoint('download_variation'),
            view_args={
                'asset': state.asset._id,
                'variation': state.variation_name
            }
        )
    )

    # Breadcrumbs
    state.decor['breadcrumbs'] = NavItem()
    state.decor['breadcrumbs'].add(
        NavItem('Assets', AssetConfig.get_endpoint('list'))
    )
    state.decor['breadcrumbs'].add(
        NavItem(
            'Asset details',
            AssetConfig.get_endpoint('view'),
            {'asset': state.asset._id}
        )
    )
    state.decor['breadcrumbs'].add(
        NavItem(
            'Variations',
            AssetConfig.get_endpoint('variations'),
            {'asset': state.asset._id}
        )
    )
    state.decor['breadcrumbs'].add(NavItem('View'))

@view_chains.link
def get_variation(state):

    state.variation_name = request.args.get('variation')

    if state.asset.variations:
        state.variation = state.asset.variations.get(state.variation_name)

    if not state.variation:
        abort(404, f'Variation not found: {state.variation_name}')


# Configure the view
initial_state = dict(
    projection={
        'variations': {
            '$sub.': Variation
        }
    }
)

# Set URL
AssetConfig.add_view_rule(
    '/assets/variations/view',
    'view_variation',
    view_chains,
    initial_state
)

# Set nav rules
Nav.apply(AssetConfig.get_endpoint('view_variation'), ['not_expired'])


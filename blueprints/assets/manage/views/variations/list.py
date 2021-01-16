"""
View variations for an asset.
"""

from manhattan.manage.views import factories, generic
from manhattan.nav import Nav, NavItem

from blueprints.assets.manage.config import AssetConfig
from blueprints.assets.models import Variation


# Chains
list_chains = generic.view.copy()

# Factory overrides
list_chains.set_link(factories.render_template('variations/list.html'))

# Custom overrides

@list_chains.link
def decorate(state):
    generic.view['get'].super(state)

    # Remove actions
    state.decor['actions'] = None

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
    state.decor['breadcrumbs'].add(NavItem('Variations'))

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
    '/assets/variations',
    'variations',
    list_chains,
    initial_state
)

# Set nav rules
Nav.apply(AssetConfig.get_endpoint('variations'), ['not_expired'])

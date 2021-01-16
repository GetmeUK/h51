"""
View a asset.
"""

from manhattan.manage.views import generic
from manhattan.nav import Nav, NavItem

from blueprints.assets.manage.config import AssetConfig
from blueprints.accounts.models import Account


# Chains
view_chains = generic.view.copy()

# Custom overrides

@view_chains.link
def decorate(state):
    generic.view['get'].super(state)

    # Download
    state.decor['actions'].add(
        NavItem(
            'Download',
            AssetConfig.get_endpoint('download'),
            view_args={'asset': state.asset._id}
        )
    )


# Configure the view
initial_state = dict(
    projection={
        'account': {
            '$ref': Account,
            'name': True,
            'public_backend_settings': True,
            'secure_backend_settings': True
        }
    }
)

# Set URL
AssetConfig.add_view_rule('/assets/view', 'view', view_chains, initial_state)

# Set nav rules
Nav.apply(AssetConfig.get_endpoint('view'), ['not_expired'])

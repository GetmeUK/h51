"""
Delete a asset.
"""

import time

from manhattan.manage.views import generic
from manhattan.nav import Nav

from blueprints.assets.manage.config import AssetConfig


# Chains
delete_chains = generic.delete.copy()

@delete_chains.link
def delete_document(state):

    # Set the asset to expire now
    state.asset.expires = time.time() - 1
    state.asset.update('expires', 'modified')


# Set URL
AssetConfig.add_view_rule('/assets/delete', 'delete', delete_chains)

# Set nav rules
Nav.apply(AssetConfig.get_endpoint('delete'), ['not_expired'])

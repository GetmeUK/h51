"""
Download the file associated with a variation of an asset.
"""

import io

from flask import abort, flash, redirect, request, send_file, url_for
from manhattan.chains import Chain, ChainMgr
from manhattan.manage.views import factories, generic, utils as manage_utils
from manhattan.nav import Nav, NavItem
from mongoframes import Q

from blueprints.accounts.models import Account
from blueprints.assets.models import Variation
from blueprints.assets.manage.config import AssetConfig


# Define the chains
download_chains = ChainMgr()

download_chains['get'] = Chain([
    'config',
    'authenticate',
    'get_document',
    'get_variation',
    'download'
])

download_chains.set_link(factories.config(projection=None))
download_chains.set_link(factories.authenticate())
download_chains.set_link(factories.get_document())

@download_chains.link
def download(state):

    # Get the backend required to download the asset
    backend_type = 'secure' if state.asset.secure else 'public'
    backend = getattr(state.asset.account, f'{backend_type}_backend', None)

    # If the backend isn't configured redirect the user to the view page and
    # notify them of the issue.
    if not backend:
        flash('No backend configured for the asset!', 'error')

        return redirect(
            url_for(
                AssetConfig.get_endpoint('view_variation'),
                asset=state.asset._id,
                variation=state.variation_name
            )
        )

    # Download the file
    store_key = state.variation.get_store_key(
        state.asset,
        state.variation_name
    )
    file = backend.retrieve(store_key)

    # Send the file to the user
    r = send_file(
        io.BytesIO(file),
        mimetype=state.variation.content_type or 'application/octet-stream',
        as_attachment=True,
        attachment_filename=store_key
    )

    return r

@download_chains.link
def get_variation(state):

    state.variation_name = request.args.get('variation')

    if state.asset.variations:
        state.variation = state.asset.variations.get(state.variation_name)

    if not state.variation:
        abort(404, f'Variation not found: {state.variation_name}')


# Configure the view
initial_state = dict(
    projection={
        'created': True,
        'account': {
            '$ref': Account,
            'public_backend_settings': True,
            'secure_backend_settings': True
        },
        'secure': True,
        'name': True,
        'uid': True,
        'ext': True,
        'type': True,
        'expires': True,
        'variations': {
            '$sub.': Variation
        }
    }
)

# Set URL
AssetConfig.add_view_rule(
    '/assets/variations/download',
    'download_variation',
    download_chains,
    initial_state
)

# Set nav rules
Nav.apply(AssetConfig.get_endpoint('download_variation'), ['not_expired'])


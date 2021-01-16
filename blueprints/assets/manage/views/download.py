"""
Download the file associated with an asset.
"""

import io

from flask import flash, redirect, send_file, url_for
from manhattan.chains import Chain, ChainMgr
from manhattan.manage.views import factories, generic, utils as manage_utils
from manhattan.nav import Nav, NavItem
from mongoframes import Q

from blueprints.assets.manage.config import AssetConfig
from blueprints.accounts.models import Account


# Define the chains
download_chains = ChainMgr()

download_chains['get'] = Chain([
    'config',
    'authenticate',
    'get_document',
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
            url_for(AssetConfig.get_endpoint('view'), asset=state.asset._id)
        )

    # Download the file
    file = backend.retrieve(state.asset.store_key)

    # Send the file to the user
    r = send_file(
        io.BytesIO(file),
        mimetype=state.asset.content_type or 'application/octet-stream',
        as_attachment=True,
        attachment_filename=state.asset.store_key
    )

    return r


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
        'expires': True
    }
)

# Set URL
AssetConfig.add_view_rule(
    '/assets/download',
    'download',
    download_chains,
    initial_state
)

# Set nav rules
Nav.apply(AssetConfig.get_endpoint('download'), ['not_expired'])


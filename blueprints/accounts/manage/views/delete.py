"""
Delete a account.
"""

from datetime import datetime
import time

from manhattan.manage.views import generic
from manhattan.nav import Nav
from mongoframes import Q

from blueprints.accounts.manage.config import AccountConfig
from blueprints.assets.models import Asset


# Chains
delete_chains = generic.delete.copy()

@delete_chains.link
def delete_document(state):

    Asset.get_collection().update_many(
        (Q.account == state.account._id).to_dict(),
        {
            '$set': {
                'expires': time.time() - 1,
                'modified': datetime.utcnow()
            }
        }
    )

    generic.delete['post'].super(state)


# Set URL
AccountConfig.add_view_rule('/accounts/delete', 'delete', delete_chains)

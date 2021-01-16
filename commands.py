
from manhattan.manage import commands as manage

from blueprints.accounts.manage import commands as accounts
from blueprints.assets.manage import commands as assets
from blueprints.users.manage import commands as users
from dispatcher import create_dispatcher


def create_app(env):
    dispatcher = create_dispatcher(env)

    # Register commands with the app
    accounts.add_commands(dispatcher.app)
    assets.add_commands(dispatcher.app)
    manage.add_commands(dispatcher.app)
    users.add_commands(dispatcher.app)

    return dispatcher.app

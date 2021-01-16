from datetime import datetime, timezone

from flask import Blueprint, g, session

__all__ = ['blueprint']


blueprint = Blueprint('manage_users', __name__, template_folder='templates')


# Hooks

@blueprint.before_app_request
def before_app_request(*args, **kwargs):
    from blueprints.users.models import User

    # Get the user by session
    user = User.from_session()
    if user:
        # Set the user against the global context
        g.user = user

    else:
        # Clear invalid session token
        if session.get(User.get_session_token_key()):
            del session[User.get_session_token_key()]


# Define imports here to prevent cross import clashes

from . import commands
from . import views

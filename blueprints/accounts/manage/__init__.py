from flask import Blueprint

__all__ = ['blueprint']


blueprint = Blueprint('manage_accounts', __name__, template_folder='templates')


from . import commands
from . import views

"""
Update the public or secure settings for a backend associated with the account.
"""

import operator

from flask import current_app, flash, request
from jinja2 import Markup
from manhattan.forms import BaseForm, fields, validators
from manhattan.manage.views import factories, generic
from manhattan.nav import Nav
from mongoframes import Q

from backends import get_backends
from blueprints.accounts.manage.config import AccountConfig
from blueprints.accounts.models import Account


# Forms

class BackendList:
    """Simple iterator to return the list of backends available"""

    def __iter__(self):

        backend_options = sorted(
            [
                (
                    k,
                    Markup(f'<b>{k.capitalize()}</b><br>{v.__doc__.strip()}')
                )
                for k, v in get_backends().items()
            ],
            key=operator.itemgetter(1)
        )

        for backend_option in backend_options:
            yield backend_option


class SelectBackendForm(BaseForm):

    backend = fields.RadioField(
        '',
        choices=BackendList(),
        validators=[validators.Required()],
        default=lambda: current_app.config['DEFAULT_BACKEND']
    )


# Chains
update_backend_settings_chains = generic.update.copy()
update_backend_settings_chains.insert_link(
    'get_document',
    'get_type'
)
update_backend_settings_chains.insert_link(
    'get_document',
    'get_backend',
    after=True
)

# Factory overrides
update_backend_settings_chains.set_link(
    factories.render_template('update_backend_settings.html')
)

# Custom overrides

@update_backend_settings_chains.link
def decorate(state):
    generic.update.chains['get'].get_link('decorate')(state)

    if state.backend:
        state.decor['title'] = \
                f'Update {state.type} backend for {state.account}'
        state.decor['breadcrumbs'].children[-1].label \
            = f'Update {state.type} backend settings'

    else:
        state.decor['title'] \
                = f'Select {state.type} backend for {state.account}'
        state.decor['breadcrumbs'].children[-1].label \
                = f'Select {state.type} backend'

@update_backend_settings_chains.link
def get_type(state):

    state.type = request.values.get('type')

    assert state.type in ['public', 'secure'], 'Unknown type'

    # Modify the update fields configured based on the type
    state.update_fields = [f'{state.type}_backend_settings']

@update_backend_settings_chains.link
def get_backend(state):

    backend_name = None
    backend_field_name = f'{state.type}_backend_settings'

    if state.account and getattr(state.account, backend_field_name):
        backend_name = state.account[backend_field_name].get('_backend')

    else:
        backend_name = request.values.get('backend')

    if backend_name:
        state.backend = get_backends().get(backend_name)

@update_backend_settings_chains.link
def init_form(state):

    if state.backend:
        state.form = state.backend.get_settings_form_cls()(
            request.form,
            data=getattr(state.account, f'{state.type}_backend_settings')
        )

    else:
        state.form = SelectBackendForm(request.form, obj=state.account)

@update_backend_settings_chains.link
def build_form_data(state):

    backend_settings = state.form.data
    backend_settings['_backend'] = state.backend.name

    state.form_data = {f'{state.type}_backend_settings': backend_settings}


# Configure the view
initial_state = dict()

# Set URL
AccountConfig.add_view_rule(
    '/accounts/update-api-settings',
    'update_backend_settings',
    update_backend_settings_chains,
    initial_state
)

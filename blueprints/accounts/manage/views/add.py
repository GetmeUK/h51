"""
Add an account.
"""

import ipaddress
import secrets

from manhattan.forms import BaseForm, fields, validators
from manhattan.manage.views import generic

from blueprints.accounts.manage.config import AccountConfig
from blueprints.accounts.models import Account


# Forms

class AddForm(BaseForm):

    name = fields.StringField(
        'Name',
        validators=[
            validators.Required(),
            validators.UniqueDocument(
                Account,
                case_sensitive=False
            )
        ]
    )

    api_rate_limit_per_second = fields.IntegerField(
        'Rate limit (per second)',
        validators=[validators.Optional()]
    )

    api_allowed_ip_addresses = fields.StringListField(
        'Allowed IP addresses',
        validators=[validators.Optional()]
    )

    def validate_api_rate_limit_per_second(form, field):

        if field.data and field.data < 1:
            raise validators.ValidationError(
                'The rate limit must be set to 1 or more'
            )

    def validate_api_allowed_ip_addresses(form, field):

        for ip_address in field.data:
            try:
                ipaddress.ip_address(ip_address)
            except ValueError:
                raise validators.ValidationError(
                    'Not a valid IP address: ' + ip_address
                )


# Chains
add_chains = generic.add.copy()

@add_chains.link
def build_form_data(state):
    generic.add['post'].super(state)

    # Generate an API key for the account
    state.form_data['api_key'] = secrets.token_urlsafe(128)


# Configure the view
initial_state = dict(
    form_cls=AddForm
)

# Set URL
AccountConfig.add_view_rule(
    '/accounts/add',
    'add',
    add_chains,
    initial_state
)

import click
from flask import Flask
from flask.cli import AppGroup
from manhattan.comparable.change_log import ChangeLogEntry
from manhattan.users.views.add import AddForm

from blueprints.users.models import User

__all__ = ['add_commands']



# Create a group for all user commands
users_cli = AppGroup('users')
def add_commands(app):
    app.cli.add_command(users_cli)


@users_cli.command('add')
@click.argument('first_name')
@click.argument('last_name')
@click.argument('email')
@click.argument('password')
def create_super(first_name, last_name, email, password):
    """Create a super user for the application"""

    form = AddForm(
        first_name=first_name,
        last_name=last_name,
        email=email,
        password=password,
        confirm_password=password,
        csrf_enabled=False
    )
    form._user_cls = User

    if not form.validate():
        # Output any errors to the terminal
        for field, errors in form.errors.items():
            print(field, '-', ' '.join(errors))
        return

    # Add the user
    user = User({
        'first_name': first_name,
        'last_name': last_name,
        'email': email,
    })

    # The password needs to be set as an attribute
    user.password = password
    user.insert()

    # Log the change
    entry = ChangeLogEntry({
        'type': 'ADDED',
        'documents': [user],
        'user': None,
    })

    entry.insert()

    print('User added')

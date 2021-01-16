from datetime import datetime, timedelta
import json

from flask import Flask, current_app
from flask.cli import AppGroup

from blueprints.accounts.models import Account

__all__ = ['add_commands']


# Create a group for all account commands
accounts_cli = AppGroup('accounts')
def add_commands(app):
    app.cli.add_command(accounts_cli)


@accounts_cli.command('trim-api-logs')
def trim_api_logs():
    """
    Ensure the API logs for all accounts do not contain entries that exceed the
    maximum retention period.

    CRON: This task should be run daily during less active periods.
    """

    trim_after = datetime.utcnow() \
            - current_app.config['API_LOG_RETENTION_PERIOD']

    for account_id in Account.ids():

        keys = [
            f'log:succeeded:{account_id}',
            f'log:failed:{account_id}'
        ]

        for key in keys:
            log_entries = current_app.redis.lrange(key, 0, -1)
            log_entries = [json.loads(e) for e in log_entries]

            for i, log_entry in enumerate(log_entries):
                called = datetime.utcfromtimestamp(log_entry['called'])

                if called <= trim_after:
                    current_app.redis.ltrim(key, 0, i - 1)
                    break

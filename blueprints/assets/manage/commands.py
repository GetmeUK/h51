import logging
import os
import subprocess
import sys
import time

import click
from flask import current_app
from flask.cli import AppGroup
from manhattan.utils.chrono import today_tz
from mongoframes import And, In, Q
from swm import monitors

from blueprints.accounts.models import Account, Stats
from blueprints.assets.models import Asset, Variation
from workers.tasks import AnalyzeTask, GenerateVariationTask
from workers.workers import AssetWorker

__all__ = ['add_commands']


# Create a group for all asset commands
assets_cli = AppGroup('assets')
def add_commands(app):
    app.cli.add_command(assets_cli)

@assets_cli.command('clear-tasks')
@click.option('-f', '--force', is_flag=True)
def clear_tasks(force):
    """
    Clear tasks from the stack, by default only unassigned tasks are cleared,
    however, using the force option will clear all tasks.
    """

    tasks = monitors.get_tasks(
        current_app.redis,
        AnalyzeTask,
        GenerateVariationTask
    )

    for task in tasks:
        if force or not task.assigned_to:
            current_app.redis.delete(task.id)
            current_app.redis.delete(task.lock_key)

@assets_cli.command('monitor-tasks')
def monitor_tasks():
    """
    Monitor the number of tasks, the age of tasks, and the number of workers
    assigned to complete the tasks and send a warning if any of these metrics
    fall safe boundaries.

    CRON: It's recommend to run the monitor as a cron task frequently (e.g
    every 5 minutes) on at least two nodes.
    """

    tasks = monitors.get_tasks(
        current_app.redis,
        AnalyzeTask,
        GenerateVariationTask
    )

    # Check the number of incompleted tasks
    if len(tasks) > current_app.config['WARNINGS_MAX_TASKS']:
        logging.warning(f'High volume of tasks: {len(tasks)} tasks')
        return

    # Check for long running tasks
    for task in tasks:
        age = (time.time_ns() - task.timestamp) / (10 ** 9)
        if age > current_app.config['WARNINGS_MAX_TASK_AGE']:
            logging.warning(f'Long running task(s): running for {age} seconds')
            return

    # If there are incomplete tasks check there is at least one worker running
    # to process it.
    workers = monitors.get_workers(current_app.redis, AssetWorker)

    if len(workers) == 0 and tasks:
        logging.warning('No workers running to process pending tasks')
        return

@assets_cli.command('purge')
def purge():
    """Purge assets that have expired"""

    # Get expired assets
    now = time.time()
    max_delete_period = 48 * 60 * 60

    assets = Asset.many(
        And(
            Q.expires <= now,
            Q.expires > now - max_delete_period,
        ),
        projection={
            'expires': True,
            'ext': True,
            'meta.length': True,
            'name': True,
            'secure': True,
            'uid': True,
            'variations': {'$sub.': Variation},
            'account': {
                '$ref': Account,
                'public_backend_settings': True,
                'secure_backend_settings': True
            }
        }
    )

    # Delete the assets
    for asset in assets:

        variation_count = 0
        length = asset.meta['length']

        # Remove all stored files for the asset
        if asset.secure:
            backend = asset.account.secure_backend
        else:
            backend = asset.account.public_backend

        if backend:

            if asset.variations:

                # Count the variations for the asset
                variation_count = len(asset.variations)

                for variation_name, variation in asset.variations.items():

                    # Tally up the assets total footprint
                    length += variation.meta['length']

                    # Remove variation files
                    backend.delete(variation.get_store_key(asset, variation_name))

            # Remove the asset file
            backend.delete(asset.store_key)

        # Delete the asset from the database
        asset.delete()

        # Update the asset stats
        Stats.inc(
            asset.account,
            today_tz(),
            {
                'assets': -1,
                'variations': -variation_count,
                'length': -length
            }
        )

@assets_cli.command('shutdown-workers')
def shutdown_workers():
    """Shutdown all asset workers"""
    monitors.shutdown_workers(current_app.redis, AssetWorker)

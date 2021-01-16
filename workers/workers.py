import json
import logging
import os
import random
import traceback
import socket

from flask import Config
import mongoframes
import pymongo
import redis
import redis.sentinel
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from swm.workers import BaseWorker

from blueprints.accounts.models import Account
from blueprints.assets.models import Variation

from .tasks import AnalyzeTask, GenerateVariationTask

__all__ = ['AssetWorker']


class AssetWorker(BaseWorker):
    """
    A worker for performing asset tasks (running analyzers and filters).
    """

    def __init__(self, env, idle_lifespan):

        # Load settings
        self.config = Config(os.path.dirname(os.path.realpath(__file__)))
        # There may be overiding settings specific to the server we are running on
        servername = socket.gethostname().split('.')[0]
        if servername and os.path.isfile(f'settings/workers/{env}_{servername}.py'):
            self.config.from_object(f'settings.workers.{env}_{servername}.Config')
        else:
            self.config.from_object(f'settings.workers.{env}.Config')

        # Sentry (logging)
        if self.config.get('SENTRY_DSN'):

            sentry_logging = LoggingIntegration(
                level=logging.INFO,
                event_level=logging.WARNING
            )

            self.sentry = sentry_sdk.init(
                self.config.get('SENTRY_DSN'),
                integrations=[
                    sentry_logging,
                    RedisIntegration()
                ]
            )

        # Mongo database
        self.mongo = pymongo.MongoClient(self.config.get('MONGO_URI'))
        self.db = self.mongo.get_default_database()
        mongoframes.Frame._client = self.mongo

        if self.config.get('MONGO_PASSWORD'):
            self.db.authenticate(
                self.config.get('MONGO_USERNAME'),
                self.config.get('MONGO_PASSWORD')
            )

        # Redis
        if self.config['REDIS_USE_SENTINEL']:
            sentinel = redis.sentinel.Sentinel(
                self.config['REDIS_ADDRESS'],
                db=self.config['REDIS_DB'],
                password=self.config['REDIS_PASSWORD'],
                decode_responses=True
            )
            conn = sentinel.master_for(self.config['REDIS_SENTINEL_MASTER'])

        else:
            conn = redis.StrictRedis(
                host=self.config['REDIS_ADDRESS'][0],
                port=self.config['REDIS_ADDRESS'][1],
                db=self.config['REDIS_DB'],
                password=self.config['REDIS_PASSWORD'],
                decode_responses=True
            )

        super().__init__(
            conn,
            [AnalyzeTask, GenerateVariationTask],
            broadcast_channel='h51_events',
            max_status_interval=self.config['ASSET_WORKER_MAX_STATUS_INTERVAL'],
            max_spawn_time=self.config['ASSET_WORKER_MAX_SPAWN_TIME'],
            sleep_interval=self.config['ASSET_WORKER_SLEEP_INTERVAL'],
            idle_lifespan=idle_lifespan,
            population_control=self.config['ASSET_WORKER_POPULATION_CONTROL'],
            population_spawner=self.config['ASSET_WORKER_POPULATION_SPAWNER']
        )

    def analyze(self, task):
        """Analyze an asset"""
        asset = task.get_asset(
            projection={
                'variations': {'$sub.': Variation}
            }
        )

        file = task.get_file()

        history = []
        for analyzer in task.get_analyzers(asset):
            analyzer.analyze(self.config, asset, file, history)
            history.append(analyzer)

        if task.notification_url:

            # POST the result to the notification URL
            account = Account.by_id(
                asset.account,
                projection={'api_key': True}
            )

            task.post_notification(
                account.api_key,
                json.dumps(asset.to_json_type())
            )

        return {}

    def do_task(self, task):

        if isinstance(task, AnalyzeTask):
            return self.analyze(task)

        elif isinstance(task, GenerateVariationTask):
            return self.generate_variation(task)

    def generate_variation(self, task):
        """Generate variation for the asset"""

        asset = task.get_asset(
            projection={
                'variations': {
                    '$sub.': Variation
                }
            }
        )

        file = task.get_file()
        native_file = None

        history = []
        for transform in task.get_transforms(asset):
            native_file = transform.transform(
                self.config,
                asset,
                file,
                task.variation_name,
                native_file,
                history
            )
            history.append(transform)

        if task.notification_url:

            # POST the result to the notification URL
            account = Account.by_id(
                asset.account,
                projection={'api_key': True}
            )

            task.post_notification(
                account.api_key,
                json.dumps(asset.to_json_type())
            )

        return {}

    def get_tasks(self):

        tasks = super().get_tasks()
        pairs = list(tasks.items())

        # Randomize tasks to prevent large tasks hogging all the workers
        random.shuffle(pairs)

        tasks = dict(pairs)

        return tasks

    def on_error(self, task_id, error):
        super().on_error(task_id, error)

        if self.config['DEBUG']:
            traceback.print_exc()
            print(error)

        else:
            if self.config.get('SENTRY_DSN'):
                sentry_sdk.capture_exception(error)

    def on_spawn_error(self, error):

        if self.config['DEBUG']:
            super().on_spawn_error(error)

        else:
            if self.config.get('SENTRY_DSN'):
                sentry_sdk.capture_exception(error)

    @classmethod
    def get_id_prefix(cls):
        return 'h51_asset_worker'

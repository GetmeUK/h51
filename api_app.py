import argparse
import asyncio
import json
import logging
import os

import aioredis
from flask import Config
import mongoframes
import pymongo
import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.tornado import TornadoIntegration
import swm

import api


# Classes

class Application(swm.servers.Application):
    """
    The API application.
    """

    def __init__(self, env):

        # Load settings
        self.config = Config(os.path.dirname(os.path.realpath(__file__)))
        self.config.from_object(f'settings.servers.{env}.Config')

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
                    TornadoIntegration(),
                    RedisIntegration()
                ]
            )

        # Initialize application
        super().__init__(
            [

                # Assets (collection)
                (r'/assets', api.assets.CollectionHandler),
                (r'/assets/analyze', api.assets.AnalyzeManyHandler),
                (r'/assets/expire', api.assets.ExpireManyHandler),
                (r'/assets/persist', api.assets.PersistManyHandler),
                (
                    r'/assets/transform',
                    api.assets.variations.TransformManyHandler
                ),

                # Assets (document)
                (r'/assets/(\w+)', api.assets.DocumentHandler),
                (r'/assets/(\w+)/analyze', api.assets.AnalyzeHandler),
                (r'/assets/(\w+)/download', api.assets.DownloadHandler),
                (r'/assets/(\w+)/expire', api.assets.ExpireHandler),
                (r'/assets/(\w+)/persist', api.assets.PersistHandler),

                # Assets > Variations
                (
                    r'/assets/(\w+)/variations',
                    api.assets.variations.CollectionHandler
                ),
                (
                    r'/assets/(\w+)/variations/(\w+)',
                    api.assets.variations.DocumentHandler
                ),
                (
                    r'/assets/(\w+)/variations/(\w+)/download',
                    api.assets.variations.DownloadHandler
                )
            ],
            debug=self.config.get('DEBUG'),
            default_handler_class=api.APIErrorHandler,
            default_handler_args={'status_code': 404}
        )

        loop = asyncio.get_event_loop()

        # Set up redis connections
        self._redis = loop.run_until_complete(self._get_redis(loop))
        self._redis_sub = loop.run_until_complete(self._get_redis(loop))

        # Set up the event listener
        loop.run_until_complete(
            self.listen_for_task_events(self._redis_sub, 'h51_events')
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

    async def _get_redis(self, loop):

        if self.config['REDIS_USE_SENTINEL']:
            sentinel = await aioredis.create_sentinel(
                self.config.get('REDIS_ADDRESS'),
                db=self.config.get('REDIS_DB'),
                password=self.config['REDIS_PASSWORD'],
                loop=loop
            )
            return sentinel.master_for(self.config['REDIS_SENTINEL_MASTER'])

        else:
            return await aioredis.create_redis_pool(
                self.config.get('REDIS_ADDRESS'),
                db=self.config.get('REDIS_DB'),
                password=self.config['REDIS_PASSWORD'],
                loop=loop
            )


# Functions

def create_app(env):
    return Application(env)


# Main

if __name__ == '__main__':

    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='API application')
    parser.add_argument(
        '-e',
        '--env',
        choices=['staging', 'local', 'production', 'test'],
        default='local',
        dest='env',
        required=False
        )
    parser.add_argument(
        '-p',
        '--port',
        default=5005,
        dest='port',
        required=False,
        type=int
        )
    args = parser.parse_args()

    # Create the application
    app = create_app(args.env)

    app.listen(args.port, max_buffer_size=app.config['MAX_BUFFER_SIZE'])
    asyncio.get_event_loop().run_forever()

"""
Initialization of the manage application.
"""

import argparse
import datetime
import logging

from flask import Flask, render_template, url_for
import jinja2
from jinja2.environment import create_cache
from manhattan import assets, formatters, forms, manage, nav
import mongoframes
import pymongo
from redis import StrictRedis
from redis.sentinel import Sentinel
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from werkzeug.middleware.proxy_fix import ProxyFix

__all__ = ['create_app']



def create_app(env):
    """Manage (backend) application factory"""

    # Create the app
    app = Flask(__name__)

    # Configure the application
    app.config['ENV'] = env
    app.config.from_object(f'settings.monitors.{env}.Config')

    config(app)
    jinja(app)
    blueprints(app)

    # Import the nav menu to define it
    from nav import manage

    return app


# Steps

def blueprints(app):
    """Register the blueprints for the application"""
    manage.utils.load_blueprints(
        app,
        'manage',
        app.config.get('MANAGE_BLUEPRINTS', [])
    )

def config(app):
    """Configure the application"""

    # Sentry (logging)
    if app.config.get('SENTRY_DSN'):

        sentry_logging = LoggingIntegration(
            level=logging.INFO,
            event_level=logging.WARNING
        )

        app.sentry = sentry_sdk.init(
            app.config.get('SENTRY_DSN'),
            integrations=[
                sentry_logging,
                FlaskIntegration(),
                RedisIntegration()
            ]
        )

    # Database (mongo and mongoframes)
    app.mongo = pymongo.MongoClient(app.config['MONGO_URI'])
    app.db = app.mongo.get_default_database()
    mongoframes.Frame._client = app.mongo

    # Database authentication
    if app.config.get('MONGO_PASSWORD'):
        app.db.authenticate(
            app.config.get('MONGO_USERNAME'),
            app.config.get('MONGO_PASSWORD')
            )

    # Database (redis)
    if app.config['REDIS_USE_SENTINEL']:
        sentinel = Sentinel(
            app.config['REDIS_ADDRESS'],
            db=app.config['REDIS_DB'],
            password=app.config['REDIS_PASSWORD'],
            decode_responses=True
        )
        app.redis = sentinel.master_for(app.config['REDIS_SENTINEL_MASTER'])

    else:
        app.redis = StrictRedis(
            host=app.config['REDIS_ADDRESS'][0],
            port=app.config['REDIS_ADDRESS'][1],
            db=app.config['REDIS_DB'],
            password=app.config['REDIS_PASSWORD'],
            decode_responses=True
        )

    # CSRF protection
    forms.CSRF.init_app(app)

    # Manage
    app.manage = manage.Manage(app)

    # Email
    if 'EMAIL_BACKEND' in app.config:
        app.mailer = app.config['EMAIL_BACKEND'].Mailer(
            **app.config.get('EMAIL_BACKEND_SETTINGS')
            )

    # Set the application's default date format for form fields
    forms.fields.DateField.default_format = app.config.get('DATE_FORMAT')

    # Fixes

    # Increase the default cache size for jinja templates
    app.jinja_env.cache = create_cache(1000)

    # REMOTE_ADDR when running behind a proxy server
    app.wsgi_app = ProxyFix(app.wsgi_app)

def jinja(app):
    """Configure the jinja environment"""

    # Loader
    app.jinja_loader = jinja2.ChoiceLoader([
        app.jinja_loader,
        jinja2.PackageLoader('manhattan.manage'),
        jinja2.PackageLoader('manhattan.users')
    ])

    # Globals
    app.jinja_env.globals.update(
        dict(
            get_dashboard_url=lambda: url_for('manage_users.dashboard'),
            get_static_asset=assets.static.get_static_asset(
                'webpack/manage/static-assets.json'
            ),
            menu=nav.Nav.menu,
            nav=nav.Nav.query
        )
    )

    # Context processors
    @app.context_processor
    def add_context():
        return dict(
            now=datetime.datetime.now()
            # @@...
        )

    # Filters
    app.jinja_env.filters.update({
        'humanize_bytes': formatters.numbers.humanize_bytes
    })

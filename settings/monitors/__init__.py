
from datetime import timedelta

from manhattan.mail.backends import memory
from manhattan.users.settings import DefaultConfig as UserDefaultConfig
from manhattan.utils.cache import RedisCache

from settings import BaseConfig


class DefaultConfig(BaseConfig, UserDefaultConfig):

    # Backends
    DEFAULT_BACKEND = 'local'

    # Blueprints
    MANAGE_BLUEPRINTS = [
        'accounts',
        'assets',
        'users'
    ]

    # Caching
    SEND_FILE_MAX_AGE_DEFAULT = 0

    # Email
    EMAIL_BACKEND = memory
    EMAIL_BACKEND_SETTINGS = {}
    EMAIL_FROM = ''

    # Networking
    PREFERRED_URL_SCHEME = 'https'
    SERVER_NAME = ''

    # Project
    PROJECT_NAME = 'H51'

    # Security
    CSRF_SECRET_KEY = ''
    CSRF_TIME_LIMIT = timedelta(minutes=120)
    PERMANENT_SESSION_LIFETIME = timedelta(days=14)
    SECRET_KEY = ''

    # Users
    USER_FAILED_SIGN_IN_CACHE = RedisCache(db=1)
    USER_MFA_FAILED_AUTH_CACHE = RedisCache(db=1)
    USER_MFA_ISSUER = ''
    USER_MFA_SCOPED_SESSION_CACHE = RedisCache(db=1)

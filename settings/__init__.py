from datetime import timedelta
import mimetypes

# Fix for missing mimetypes
mimetypes.add_type('text/csv', '.csv')
mimetypes.add_type('image/webp', '.webp')


class BaseConfig:

    # API
    API_LOG_RETENTION_PERIOD = timedelta(days=90)
    API_MAX_LOG_ENTRIES = 100
    API_RATE_LIMIT_PER_SECOND = 100

    # Assets
    CONTENT_TYPE_TO_TYPES = {
        'audio/mpeg': 'audio',
        'audio/ogg': 'audio',
        'image/bmp': 'image',
        'image/gif': 'image',
        'image/jpeg': 'image',
        'image/png': 'image',
        'image/tiff': 'image',
        'image/webp': 'image',
    }

    # Database
    MONGO_URI = 'mongodb://localhost:27017/h51'
    MONGO_USERNAME = 'h51'
    MONGO_PASSWORD = ''

    REDIS_ADDRESS = ('127.0.0.1', 6379)
    REDIS_DB = 1
    REDIS_PASSWORD = None
    REDIS_USE_SENTINEL = False
    REDIS_SENTINEL_MASTER = None

    # Date/Time
    DATE_FORMAT = '%-d %B %Y'
    TIMEZONE = 'Europe/London'

    # Debugging
    DEBUG = False
    SENTRY_DSN = ''

    # Warnings
    WARNINGS_MAX_TASK_AGE = 60
    WARNINGS_MAX_TASKS = 25

import asyncio
import json
import time
import uuid

from manhattan.utils.chrono import today_tz
from mongoframes import Q
import swm
import tornado.web

__all__ = [
    'APIError',
    'APIHandler',
    'APIErrorHandler',
]


class APIError(tornado.web.HTTPError):
    """
    Use `APIError` instead of `HTTPError` to raise an error within API
    handlers. The extended exception allows more detailed error information to
    be returned to the caller.
    """

    # A map of possible error types and their associated HTTP response codes
    ERROR_TYPES = {
        'error': 500,
        'forbidden': 403,
        'invalid_request': 400,
        'not_found': 404,
        'request_limit_exceeded': 429,
        'unauthorized': 401
    }

    def __init__(self, error_type, hint=None, arg_errors=None):

        assert error_type in self.ERROR_TYPES

        # The type of error
        self.error_type = error_type

        # A developer provided hint as to the cause of the error (optional)
        self.hint = hint

        # A map of errors for each invalid argument (optional)
        self.arg_errors = arg_errors

        super().__init__(self.ERROR_TYPES[error_type])

    def to_json_type(self):
        """Return a JSON safe representation of the error"""
        json_error = {'error_type': self.error_type}

        if self.hint:
            json_error['hint'] = self.hint

        if self.arg_errors:
            json_error['arg_errors'] = self.arg_errors

        return json_error

    @classmethod
    def from_status_code(cls, status_code):
        for k, v in cls.ERROR_TYPES.items():
            if v == status_code:
                return cls(k)


class APIHandler(swm.servers.RequestHandler):
    """
    A base handler for API
    """

    @property
    def account(self):
        return getattr(self, '_account', None)

    @property
    def config(self):
        return self.application.config

    def check_xsrf_cookie(self) -> None:
        # XSRF is not checked for API requests
        pass

    def compute_etag(self):
        # Prevent automatic setting of etag and 304 responses
        return None

    def initialize(self):

        # The account associated with the caller
        self._account = None

        # A log of messages written so far this request
        self._write_log = ''

        # A timer used to time taken for the call
        self._call_timer = time.time()

    def on_finish(self):
        # Build the log entry

        # If there's no associated account we don't log the request
        if not self.account:
            return

        # Request
        request_snapshot = {'__body__': {}}
        for key, value in self.request.arguments.items():
            request_snapshot[key] = [v.decode('utf8') for v in value]

        # Response
        response_snapshot = None
        content_type = self._headers.get('Content-Type', '').split(';')[0]
        if content_type.lower() == 'application/json':
            response_snapshot = json.loads(self._write_log)

        log_entry = json.dumps({
            'id': str(uuid.uuid4()),
            'call_time': time.time() - self._call_timer,
            'called': time.time(),
            'ip_address': self.request.headers.get('X-Real-Ip', ''),
            'method': self.request.method,
            'path': self.request.path,
            'request': request_snapshot,
            'response': response_snapshot,
            'status_code': self._status_code
        })

        # Log the entry
        log_key = self.account.get_api_log_key(
            'succeeded' if str(self._status_code)[0] == '2' else 'failed'
        )
        multi = self.redis.multi_exec()
        multi.lpush(log_key, log_entry)
        multi.ltrim(log_key, 0, self.config['API_MAX_LOG_ENTRIES'])
        asyncio.create_task(multi.execute())

    async def prepare(self):

        from blueprints.accounts.models import Account, Stats

        # (Re)Set the account attribute
        self._account = None

        # (Re)Set the write log
        self._write_log = ''

        # (Re)Set the call timer
        self._call_timer = time.time()

        # Check a valid API key has been provided
        api_key = self.request.headers.get('X-H51-APIKey')

        if not api_key:
            raise APIError('unauthorized', 'No authorization key provided.')

        # Find the calling account
        account = Account.one(
            Q.api_key == api_key,
            projection={
                'api_allowed_ip_addresses': True,
                'api_rate_limit_per_second': True
            }
        )

        # Store a reference to the account document against the request handler
        self._account = account

        if not account:
            raise APIError('unauthorized', 'API key not recognized.')

        if account.api_allowed_ip_addresses:

            # Check the caller's IP address is allowed
            ip_address = self.request.headers.get('X-Real-Ip', '')
            if ip_address not in account.api_allowed_ip_addresses:
                raise APIError(
                    'forbidden',
                    (
                        f'The IP address {ip_address} is not allowed to call '
                        'the API for this account.'
                    )
                )

        # Record this request
        rate_key = account.get_rate_key()
        ttl = await self.redis.pttl(rate_key)

        if ttl > 0:
            await self.redis.incr(rate_key)

        else:
            multi = self.redis.multi_exec()
            multi.incr(rate_key)
            multi.expire(rate_key, 1)
            await multi.execute()

        # Apply rate limit
        request_count = int((await self.redis.get(rate_key)) or 0)
        rate_limit = account.api_rate_limit_per_second \
                or self.config['API_RATE_LIMIT_PER_SECOND']

        if request_count > rate_limit:
            raise APIError('request_limit_exceeded')

        # Set the remaining requests allowed this second in the response
        # headers.
        rate_key_reset = max(0, ttl / 1000.0)
        rate_key_reset += time.time()

        self.set_header('X-H51-RateLimit-Limit', str(rate_limit))
        self.set_header(
            'X-H51-RateLimit-Remaining',
            str(rate_limit - request_count)
        )
        self.set_header('X-H51-RateLimit-Reset', str(rate_key_reset))

        # Update the API call stats
        Stats.inc(
            account,
            today_tz(tz=self.config['TIMEZONE']),
            {'api_calls': 1}
        )

    def write(self, chunk):
        super().write(chunk)

        # Set the write log
        self._write_log = b''.join(self._write_buffer)

    def write_error(self, status_code, **kwargs):

        if self.settings.get('serve_traceback') and 'exc_info' in kwargs:

            # In debug mode we return a traceback
            return super().write_error(status_code, **kwargs)

        # Handle API errors
        if 'api_error' in kwargs:
            self.set_status(status_code)
            self.write(kwargs['api_error'])
            return self.finish()

        # Handle HTTP errors that can be mapped to API errors
        api_error = APIError.from_status_code(status_code)
        if api_error:
            self.set_status(status_code)
            self.write(api_error.to_json_type())
            return self.finish()

        # Handle all other error types
        return super().write_error(status_code, **kwargs)

    def _handle_request_exception(self, e):

        if isinstance(e, APIError):
            self.send_error(
                e.status_code,
                reason=e.error_type,
                api_error=e.to_json_type()
            )

        super()._handle_request_exception(e)


class APIErrorHandler(APIHandler):

    def initialize(self, status_code):
        self.set_status(status_code)

    def prepare(self):
        api_error = APIError.from_status_code(self._status_code)
        if api_error:
            raise api_error

        raise tornado.web.HTTPError(self._status_code)


# API handlers should be imported here

from . import assets

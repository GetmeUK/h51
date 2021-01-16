
import datetime

from manhattan.comparable import ComparableFrame
from mongoframes import ASC, Frame, IndexModel, Q
from mongoframes.queries import to_refs

from backends import get_backend

__all__ = [
    'Account',
    'Stats'
]


class Account(ComparableFrame):
    """
    Accounts provide storage configuration for assets and access to the API.
    """

    _fields = {

        # A unique name used to identify the account
        'name',

        # An API key required to authenticate calls to the API
        'api_key',

        # A list of IP addresses that the API is allowed to be called from for
        # this account.
        'api_allowed_ip_addresses',

        # API request rate limit
        'api_rate_limit_per_second',

        # Settings for the public and secure storage backends that will be
        # used to store files.
        'public_backend_settings',
        'secure_backend_settings'
    }

    _uncompared_fields = ComparableFrame._uncompared_fields | {
        'api_key'
    }

    _indexes = [
        IndexModel([('api_key', ASC)], unique=True),
        IndexModel(
            [('name', ASC)],
            collation={
                'locale': 'en',
                'strength': 2
            },
            unique=True
        )
    ]

    def __str__(self):
        return self.name

    @property
    def public_backend(self):
        if self.public_backend_settings:
            backend_cls = get_backend(self.public_backend_settings['_backend'])
            if backend_cls:
                return backend_cls(**self.public_backend_settings)

    @property
    def secure_backend(self):
        if self.secure_backend_settings:
            backend_cls = get_backend(self.secure_backend_settings['_backend'])
            if backend_cls:
                return backend_cls(**self.secure_backend_settings)

    def get_api_log_key(self, status):
        """
        Return a unique key for the application/account that can be used to
        store/retrieve API call logs.
        """

        assert status in ['succeeded', 'failed'], \
                'Status must be either succeeded or failed.'

        if status == 'succeeded':
            return f'h51_api_log:{self._id}:succeeded'

        return f'h51_api_log:{self._id}:failed'

    def get_rate_key(self):
        """
        Return a unique key for the application/account that can be used to
        record the request rate.
        """
        return f'h51_rate:{self._id}:requests_in_last_second'

    @staticmethod
    def _on_insert(sender, frames):

        for frame in frames:
            frame.api_allowed_ip_addresses = \
                    frame.api_allowed_ip_addresses or []


Account.listen('insert', Account._on_insert)


class Stats(Frame):
    """
    A collection that holds stats about account usage.
    """

    _fields = {

        # The scope of the stat (for example all or an account Id)
        'scope',

        # A dictionary holding
        'values',
    }

    _indexes = [
        IndexModel([('scope', ASC)], unique=True)
    ]

    def __str__(self):
        return self.scope

    def get_series_labels(self, keys):
        """Return a list of labels for a data series for the given keys"""
        labels = []
        date_str_len = len(keys[0].split('.', 1)[0])

        for key in reversed(keys):
            date_str = key[:date_str_len]

            if date_str_len == 4:
                labels.append(date_str)

            elif len(date_str) == 7:
                date = datetime.datetime.strptime(f'{date_str}-01', '%Y-%m-%d')
                labels.append(date.strftime('%b, %y'))

            elif len(date_str) == 10:
                date = datetime.datetime.strptime(date_str, '%Y-%m-%d')
                labels.append(date.strftime('%-d %b'))

        return labels

    def get_series(self, keys):
        """Return a data series for the given keys"""
        return list(reversed([self.get_stat(k) for k in keys]))

    def get_stat(self, key):
        """Return the given stat from values or 0 if the stat does not exist"""
        values = self.values
        for k in key.split('.'):
            if k in values:
                values = values[k]
            else:
                return 0

        return values

    def sum_stats(self, keys):
        """Return the sum of the given keys"""
        return sum(self.get_series(keys))

    @classmethod
    def get_key_range(cls, date, unit, length, stat):
        """
        Return a list of keys for the specified unit (days, months, years),
        length, and stat starting from the given date.
        """

        keys = []

        year = date.year
        month = date.month

        if unit == 'days':
            while length > 0:
                keys.append(f'{date}.{stat}')
                date -= datetime.timedelta(days=1)
                length -= 1

        elif unit == 'months':
            while length > 0:
                keys.append(f'{year}-{str(month).zfill(2)}.{stat}')

                month -= 1
                if month < 1:
                    month = 12
                    year -= 1

                length -= 1

        elif unit == 'years':
            keys = [
                f'{y}.{stat}' for y in range(year, year - length, -1)
            ]

        return keys

    @classmethod
    def get_inc_keys(cls, date, stat):
        """
        Get a list of keys that need to be used when incrementing stats for
        the given account, date and stat.
        """

        keys = []
        date_str = str(date)
        for timeframe in ['all', date_str[:4], date_str[:7], date_str]:
            keys.append(f'{timeframe}.{stat}')

        return keys

    @classmethod
    def inc(cls, account, date, stats):
        """Increment the given stats (`{stat1: amount1, stat2: amount2}`)"""

        incs = {}
        for stat, amount in stats.items():
            for key in cls.get_inc_keys(date, stat):
                incs[f'values.{key}'] = amount

        for scope in ['all', to_refs(account)]:
            cls.get_collection().update(
                (Q.scope == scope).to_dict(),
                {
                    '$set': {'scope': scope},
                    '$inc': incs
                },
                w=0,
                upsert=True
            )

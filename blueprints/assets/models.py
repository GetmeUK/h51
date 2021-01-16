from datetime import datetime, timezone
import time

from mongoframes import ASC, DESC, Frame, IndexModel, SubFrame
import numpy
from shortuuid import ShortUUID

__all__ = [
    'Asset',
    'Variation'
]


class Asset(Frame):
    """
    An asset stored by Hangar51. Assets describe a file uploaded to Hangar51
    including any associated variations of the file created.
    """

    # The character set and length used to generate unique Ids for the asset
    UID_CHARSET = 'abcdefghijklmnopqrstuvwxyz0123456789'
    UID_LENGTH = 6

    _fields = {

        # The date/time the asset was modified
        'created',
        'modified',

        # The account the asset is associated with
        'account',

        # A flag indicating if the asset was stored using the secure (as
        # opposed to the public) backend.
        'secure',

        # The name of the asset
        'name',

        # A unique url safe Id for the asset
        'uid',

        # The file extension for the asset (without the '.')
        'ext',

        # The core assets type
        'type',

        # The content type (e.g image/png)
        'content_type',

        # The date/time as a timestamp the asset should expire (if not set the
        # asset is considered permanent).
        'expires',

        # A dictionary of meta data extracted from the file (the contents
        # varies depending on the type of file and applied meta expansions).
        'meta',

        # A list of variations generated for the asset
        'variations'
    }

    _private_fields = {'_id', 'account'}

    _indexes = [
        IndexModel([('account', ASC), ('uid', ASC)], unique=True),
        IndexModel([('created', ASC)]),
        IndexModel([('expires', ASC)]),
        IndexModel([('name', ASC)]),
        IndexModel([('secure', ASC)]),
        IndexModel([('type', ASC)])
    ]

    def __str__(self):
        return self.store_key

    @property
    def expires_dt(self):
        if self.expires:
            dt = datetime.fromtimestamp(self.expires)
            dt.replace(tzinfo=timezone.utc)
            return dt

    @property
    def expired(self):
        if self.expires is None:
            return False
        return self.expires <= time.time()

    @property
    def store_key(self):
        return '.'.join([
            self.name,
            self.uid,
            self.ext
        ])

    def to_json_type(self):
        data = super().to_json_type()

        # Set the store key for the assets and any variations
        data['store_key'] = self.store_key

        for name, variation in (self.variations or {}).items():
            data['variations'][name]['store_key'] = variation.get_store_key(
                self,
                name
            )

        return data

    @classmethod
    def generate_uid(cls):
        if not hasattr(cls, '_uid_generator'):
            cls._uid_generator = ShortUUID(cls.UID_CHARSET)
        return cls._uid_generator.uuid()[:cls.UID_LENGTH]

Asset.listen('insert', Asset.timestamp_insert)
Asset.listen('update', Asset.timestamp_update)


class Variation(SubFrame):
    """
    A variation of an asset where the file has been transfromed by one or more
    transforms.
    """

    _fields = {
        # The content type (e.g image/png)
        'content_type',

        # The file extension for the asset (without the '.')
        'ext',

        # A dictionary of meta data extract from the file (the contents varies
        # depending on the type of file and applied transforms).
        'meta',

        # The variation version. Versions are used so that if a variation is
        # modified the new version will have a different store key and URL
        # which avoids issues with file caching in browsers.
        #
        # However, it possible to set a variation as versionless (where
        # version is `None`), this would typically be used when generating
        # imagery on the fly using the variations name (stored against the
        # asset) as the transforms ensure (in most cases) the variation name
        # is unique.
        'version'
    }

    def get_store_key(self, asset, name):
        """Return the store key for the asset"""

        parts = [
            asset.name,
            asset.uid,
            name,
            self.ext
        ]

        if self.version:
            parts.insert(-1, self.version)

        return '.'.join(parts)

    @classmethod
    def next_version(cls, current_version=None):
        version = int(current_version or '000', 36)
        return numpy.base_repr(version + 1, 36).zfill(3).lower()

from datetime import datetime
import mimetypes
import pkgutil

from manhattan.utils.chrono import today_tz
from mongoframes import Q

from blueprints.accounts.models import Account, Stats
from blueprints.assets.models import Asset, Variation

__all__ = [

    # Classes
    'BaseTransform',

    # Functions
    'get_transform',
    'get_transforms'
]


# Meta

class BaseTransformMeta(type):
    """
    The metaclass for transforms ensures all transforms derived from the
    `BaseTransform` register themselves on import.

    We auto import all python files within the transforms directory and any of
    its sub-directories.
    """

    def __new__(meta, name, bases, dct):

        cls = super().__new__(meta, name, bases, dct)

        if name != 'BaseTransform' and bases and not cls.exclude_from_register:

            # Register the transform
            BaseTransform._transforms[f'{cls.asset_type}:{cls.name}'] = cls

        return cls


# Classes

class BaseTransform(metaclass=BaseTransformMeta):
    """
    The `BaseTransform` class allows different types of transform to be used
    to modify an image.

    Different transforms should inherit from the base `BaseTransform` class
    and override its methods.
    """

    # Each transform must specify which type of asset it can be used to
    # transform.
    asset_type = 'file'

    # Flag indicating if the transform should be exluded from the register
    # (useful when defining base classes).
    exclude_from_register = False

    # Flag indicating if this transform must be the final transform in a list
    # of transforms to generate a variation. Transforms that output a
    # variation (for example by calling `_store_variation`) should be set as
    # `final` transforms. By nature of this rule there can only ever be one
    # final transform.
    final = False

    # Each transform must have a unique name
    name = ''

    # A table of registered transforms (excluding the `BaseTransform`)
    _transforms = {}

    def transform(
        self,
        config,
        asset,
        file,
        variation_name,
        native_file
    ):
        """
        Perform the transform of the asset, this method should return a tuple
        of `native_file`.
        """
        raise NotImplementedError()

    def _store_variation(
        self,
        config,
        asset,
        variation_name,
        versioned,
        ext,
        meta,
        file
    ):
        """
        Store a new variation of the asset. This method both stores the
        variation (and removes any existing variation with the same name) as
        well as updating the asset's `variations` field with details of the
        new variation.
        """

        # Get the account and backend associated with the asset
        account = Account.by_id(
            asset.account,
            projection={
                'public_backend_settings': True,
                'secure_backend_settings': True
            }
        )

        if asset.secure:
            backend = account.secure_backend
        else:
            backend = account.public_backend

        assert backend, 'No backend configured for the asset'

        # Ensure the asset's variation value is a dictionary (in case it's
        # never been set before).
        if not asset.variations:
            asset.variations = {}

        # Create the new variation
        old_variation = asset.variations.get(variation_name)

        new_variation = Variation(
            content_type=mimetypes.guess_type(f'f.{ext}')[0] if ext else '',
            ext=ext,
            meta=meta,
            version=(
                Variation.next_version(
                    old_variation.version if old_variation else None
                )
                if versioned else None
            )
        )

        # Store the new variation
        new_store_key = new_variation.get_store_key(asset, variation_name)
        file.seek(0)
        backend.store(file, new_store_key)

        # Add the new variation's details to the asset's `variations` field
        asset.variations[variation_name] = new_variation
        asset.modified = datetime.utcnow()

        # Apply the updated to the database
        Asset.get_collection().update(
            (Q._id == asset._id).to_dict(),
            {
                '$set': {
                    f'variations.{variation_name}': \
                            new_variation.to_json_type(),
                    'modified': asset.modified
                }
            }
        )

        # Remove the existing variation
        if old_variation:
            old_store_key = old_variation.get_store_key(asset, variation_name)
            if new_store_key != old_store_key:
                backend.delete(old_store_key)

        # Update the asset stats
        new_length = new_variation.meta['length']
        old_length = 0
        if old_variation:
            old_length = old_variation.meta['length']

        Stats.inc(
            account,
            today_tz(tz=config['TIMEZONE']),
            {
                'variations': 0 if old_variation else 1,
                'length': new_length - old_length
            }
        )

    @classmethod
    def get_settings_form_cls(cls):
        """
        Return a form class that can be used to validate the settings for the
        transform.
        """
        raise NotImplementedError()


# Functions

def get_transform(asset_type, name):
    """Return the named transform for the given asset type"""
    return get_transforms().get(f'{asset_type}:{name}')

def get_transforms():
    """
    Return a dictionary of available transforms
    `{'asset_type:name': transform_cls}`.
    """
    return dict(BaseTransform._transforms)


# Import all transforms defined within the transforms directory

path = pkgutil.extend_path(__path__, __name__)
for _, modname, _ in pkgutil.walk_packages(path=path, prefix=f'{__name__}.'):
      __import__(modname)

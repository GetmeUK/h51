from datetime import datetime
import pkgutil

from mongoframes import Q

from blueprints.assets.models import Asset


__all__ = [

    # Classes
    'BaseAnalyzer',

    # Functions
    'get_analyzer',
    'get_analyzers'
]


# Meta

class BaseAnalyzerMeta(type):
    """
    The metaclass for analyzers ensures all analyzers derived from the
    `BaseAnalyzer` register themselves on import.

    We auto import all python files within the analyzers directory and any of
    its sub-directories.
    """

    def __new__(meta, name, bases, dct):

        cls = super().__new__(meta, name, bases, dct)

        if name != 'BaseAnalyzer' and bases and not cls.exclude_from_register:

            # Register the analyzer
            BaseAnalyzer._analyzers[f'{cls.asset_type}:{cls.name}'] = cls

        return cls


# Classes

class BaseAnalyzer(metaclass=BaseAnalyzerMeta):
    """
    The `BaseAnalyzer` class allows different types of analyzers to be used
    to derive additional meta data from an asset.

    Different analyzers should inherit from the base `BaseAnalyzer` class and
    override its methods.
    """

    # Each analyzer must specify which type of asset it can be used to
    # analyze. However, the file asset type is a special case and means the
    # analyzer can be applied to any asset type.
    asset_type = 'file'

    # Flag indicating if the analyzer should be exluded from the register
    # (useful when defining base classes).
    exclude_from_register = False

    # Each analyzer must have a unique name
    name = ''

    # A table of registered analyzers (excluding the `BaseAnalyzer`)
    _analyzers = {}

    def analyze(self, config, asset, file):
        """Perform the analysis of the asset"""
        raise NotImplementedError()

    def _add_to_meta(self, asset, data):
        """Add the specified data to the asset's meta"""

        # Modify the asset instance
        if self.asset_type not in asset.meta:
            asset.meta[self.asset_type] = {}

        asset.meta[self.asset_type][self.name] = data
        asset.modified = datetime.utcnow()

        # Apply the updated to the database
        Asset.get_collection().update(
            (Q._id == asset._id).to_dict(),
            {
                '$set': {
                    f'meta.{self.asset_type}.{self.name}': data,
                    'modified': asset.modified
                }
            }
        )

    @classmethod
    def get_settings_form_cls(cls):
        """
        Return a form class that can be used to validate the settings for the
        analyzer.
        """
        raise NotImplementedError()


# Functions

def get_analyzer(asset_type, name):
    """Return the named analyzer for the given asset type"""
    return get_analyzers().get(
        f'{asset_type}:{name}',
        get_analyzers().get(f'file:{name}')
    )

def get_analyzers():
    """
    Return a dictionary of available analyzers
    `{'asset_type:name': analyzer_cls}`.
    """
    return BaseAnalyzer._analyzers.copy()


# Import all analyzers defined within the analyzers directory

path = pkgutil.extend_path(__path__, __name__)
for _, modname, _ in pkgutil.walk_packages(path=path, prefix=f'{__name__}.'):
      __import__(modname)

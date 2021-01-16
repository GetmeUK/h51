import pkgutil

__all__ = [

    # Classes
    'BaseBackend',

    # Functions
    'get_backend',
    'get_backends'
]


# Meta

class BaseBackendMeta(type):
    """
    The metaclass for backends ensures all backends derived from the
    `BaseBackend` register themselves on import.

    We auto import all python files within the backends directory and any of
    its sub-directories.
    """

    def __new__(meta, name, bases, dct):

        cls = super().__new__(meta, name, bases, dct)

        if name != 'BaseBackend' and bases and not cls.exclude_from_register:

            # Register the backend
            BaseBackend._backends[cls.name] = cls

        return cls


# Classes

class BaseBackend(metaclass=BaseBackendMeta):
    """
    The `BaseBackend` class allows different types of storage models to be used
    for asset storage.

    Different backends should inherit from the base `BaseBackend` class and
    override its methods.
    """

    # Each backend must have a unique name
    name = ''

    # Flag indicating if the backend should be exluded from the register
    # (useful when defining base classes).
    exclude_from_register = False

    # A table of registered backends (excluding the `BaseBackend`
    _backends = {}

    def __init__(self, **kw):
        raise NotImplementedError()

    def delete(self, key):
        """Delete a file from the store"""
        raise NotImplementedError()

    def retrieve(self, key):
        """Retrieve a file from the store"""
        raise NotImplementedError()

    def store(self, f, key):
        """Store a file"""
        raise NotImplementedError()

    async def async_delete(self, key, loop=None):
        """Asynchronous delete a file from the store"""
        raise NotImplementedError()

    async def async_retrieve(self, key, loop=None):
        """Asynchronous retrieve a file from the store"""
        raise NotImplementedError()

    async def async_store(self, f, key, loop=None):
        """Asynchronous store a file"""
        raise NotImplementedError()

    @classmethod
    def get_settings_form_cls(cls):
        """
        Return a form class that can be used to validate the settings for the
        backend.
        """
        raise NotImplementedError()


# Functions

def get_backend(name):
    """Return the named backend"""
    return get_backends().get(name)

def get_backends():
    """Return a dictionary of available backends `{name: backend_cls}`"""
    return BaseBackend._backends.copy()


# Import all backends defined within the backends directory

path = pkgutil.extend_path(__path__, __name__)
for _, modname, _ in pkgutil.walk_packages(path=path, prefix=f'{__name__}.'):
      __import__(modname)

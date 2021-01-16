import io
import os

from manhattan.forms import BaseForm, fields, validators

from . import BaseBackend

__all__ = ['LocalBackend']


class SettingsForm(BaseForm):

    files_path = fields.StringField(
        'Files path',
        [validators.Required()]
    )

    def validate_files_path(form, field):
        # Check the path given for the asset root exists

        if not field.data:
            return

        if field.data[0] != '/':
            raise validators.ValidationError('Path must be absolute')

        if not os.path.exists(field.data):
            raise validators.ValidationError('Path does not exist.')


class LocalBackend(BaseBackend):
    """
    Store file on the local file system.
    """

    name = 'local'

    def __init__(self, files_path, **kw):
        self.files_path = files_path

    def is_safe_key(self, key):
        """Return True if the given file path is safe"""
        path = os.path.realpath(os.path.join(self.files_path, key))
        return os.path.commonprefix((path, self.files_path)) == self.files_path

    def delete(self, key):
        """Delete a file from the store"""

        if not self.is_safe_key(key):
            raise PermissionError('Not a safe key')

        # Remove the file if it exists
        path = os.path.join(self.files_path, key)

        if os.path.exists(path):
            os.remove(path)

    def retrieve(self, key):
        """Retrieve a file from the store"""

        if not self.is_safe_key(key):
            raise PermissionError('Not a safe key')

        # Return the file as a byte stream
        path =  os.path.join(self.files_path, key)
        with open(path, 'rb') as f:
            stream = f.read()

        return stream

    def store(self, f, key):
        """Store a file"""

        if not self.is_safe_key(key):
            raise PermissionError('Not a safe key')

        # Determine the storage location
        path, filename = os.path.split(key)
        path = os.path.join(self.files_path, path)

        # Ensure the location exists
        os.makedirs(path, exist_ok=True)

        # Save the file
        with open(os.path.join(path, filename), 'wb') as store:
            store.write(f.read())

    async def async_delete(self, key, loop=None):
        """Asynchronous delete a file from the store"""
        self.delete(key)

    async def async_retrieve(self, key, loop=None):
        """Asynchronous retrieve a file from the store"""
        return self.retrieve(key)

    async def async_store(self, f, key, loop=None):
        """Asynchronous store a file"""
        self.store(f, key)

    @classmethod
    def get_settings_form_cls(cls):
        return SettingsForm

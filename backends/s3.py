import io
import mimetypes
import os
import uuid

import aiobotocore
import botocore.exceptions
import botocore.session
from manhattan.forms import BaseForm, fields, validators

from . import BaseBackend

__all__ = ['S3Backend']


class SettingsForm(BaseForm):

    access_key = fields.StringField(
        'Access key',
        [validators.Required()]
    )

    secret_key = fields.StringField(
        'Secret key',
        [validators.Required()]
    )

    bucket = fields.StringField(
        'Bucket',
        [validators.Required()]
    )

    region = fields.StringField(
        'Region',
        [validators.Required()],
        default='eu-west-1'
    )

    def validate_access_key(form, field):

        access_key = field.data
        secret_key = form.secret_key.data
        bucket = form.bucket.data
        region = form.region.data

        if access_key and secret_key and bucket and region:

            client = botocore.session.get_session().create_client(
                's3',
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name=region
            )

            try:
                data = b'Hey, Hope you have a nice day! your friend Hangar51.'
                key = f'hangar51-settings-test-{uuid.uuid4().hex}'

                # Check we can write to the the bucket
                client.put_object(Bucket=bucket, Key=key, Body=data)

                # Check we can retrieve from the bucket
                client.get_object(Bucket=bucket, Key=key)

                # Check we can delete from the bucket
                client.delete_object(Bucket=bucket, Key=key)

            except (
                    botocore.exceptions.BotoCoreError,
                    botocore.exceptions.ClientError
                ) as e:

                raise validators.ValidationError(str(e))


class S3Backend(BaseBackend):
    """
    Store file on AWS S3.
    """

    name = 's3'

    def __init__(
        self,
        access_key,
        secret_key,
        bucket,
        region,
        **kw
    ):

        self.access_key = access_key
        self.secret_key = secret_key
        self.bucket = bucket
        self.region = region

    def delete(self, key):
        """Delete a file from the store"""
        self._get_client().delete_object(Bucket=self.bucket, Key=key)

    def retrieve(self, key):
        """Retrieve a file from the store"""
        r = self._get_client().get_object(Bucket=self.bucket, Key=key)
        return r['Body'].read()

    def store(self, f, key):
        """Store a file"""

        kwargs = {}
        content_type = mimetypes.guess_type(key)[0]
        if content_type:
            kwargs['ContentType'] = content_type

        self._get_client().put_object(
            Bucket=self.bucket,
            Key=key,
            Body=f,
            CacheControl='max-age=%d, public' % (365 * 24 * 60 * 60),
            **kwargs
        )

    async def async_delete(self, key, loop=None):
        """Asynchronous delete a file from the store"""
        async with self._get_async_client(loop) as client:
            await client.delete_object(Bucket=self.bucket, Key=key)

    async def async_retrieve(self, key, loop=None):
        """Asynchronous retrieve a file from the store"""
        async with self._get_async_client(loop) as client:
            r = await client.get_object(Bucket=self.bucket, Key=key)

            async with r['Body'] as stream:
                return await stream.read()

    async def async_store(self, f, key, loop=None):
        """Asynchronous store a file"""
        async with self._get_async_client(loop) as client:

            kwargs = {}
            content_type = mimetypes.guess_type(key)[0]
            if content_type:
                kwargs['ContentType'] = content_type

            await client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=f,
                CacheControl='max-age=%d, public' % (365 * 24 * 60 * 60),
                **kwargs
            )

    def _get_client(self):
        """Return an s3 client for the backend"""
        return botocore.session.get_session().create_client(
            's3',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region
        )

    def _get_async_client(self, loop=None):
        """Return an asynchronous s3 client for the backend"""
        return aiobotocore.get_session().create_client(
            's3',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name=self.region
        )

    @classmethod
    def get_settings_form_cls(cls, **config):
        return SettingsForm

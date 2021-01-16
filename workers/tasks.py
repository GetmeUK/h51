import hashlib
import time

from bson.objectid import ObjectId
import requests
from swm import tasks

from analyzers import get_analyzer
from blueprints.accounts.models import Account
from blueprints.assets.models import Asset
from transforms import get_transform

__all__ = [
    'AnalyzeTask',
    'GenerateVariationTask'
]


class AssetTask(tasks.BaseTask):

    def __init__(self, account_id, asset_id, notification_url=None):
        super().__init__()

        # The Id of the account the task was created for
        self._account_id = account_id

        # The Id of the asset the task will be run against
        self._asset_id = asset_id

        # A URL to POST to when the task is completed
        self._notification_url = notification_url

    @property
    def account_id(self):
        return self._account_id

    @property
    def asset_id(self):
        return self._asset_id

    @property
    def notification_url(self):
        return self._notification_url

    def get_asset(self, projection=None):
        """Get the asset the task will be run against"""
        return Asset.by_id(self.asset_id, projection=projection)

    def get_file(self):
        """Get the file for the asset the task will be run against"""

        account = Account.by_id(
            self.account_id,
            projection={
                'public_backend_settings': True,
                'secure_backend_settings': True
            }
        )

        asset = self.get_asset(
            projection={
                'secure': True,
                'name': True,
                'uid': True,
                'ext': True
            }
        )

        if asset.secure:
            backend = account.secure_backend
        else:
            backend = account.public_backend

        assert backend, 'No backend configured for the asset'

        return backend.retrieve(asset.store_key)

    def post_notification(self, api_key, body):
        """POST the given body to the requested notification URL"""

        if not self._notification_url:
            return

        # Generate the signature
        timestamp = str(int(time.time()))
        signature = hashlib.sha1()
        signature.update(
            ''.join([
                timestamp,
                body,
                api_key
            ]).encode('utf8')
        )

        try:
            r = requests.post(
                self._notification_url,
                data=body,
                headers={
                    'X-H51-Timestamp': timestamp,
                    'X-H51-Signature': signature.hexdigest()
                }
            )

        except requests.exceptions.HTTPError:
            # Ignore failures to call the notification URL
            pass

    def to_json_type(self):
        data = super().to_json_type()
        data['account_id'] = str(self.account_id)
        data['asset_id'] = str(self.asset_id)
        data['notification_url'] = self._notification_url
        return data

    @classmethod
    def from_json_type(cls, data):
        data['account_id'] = ObjectId(data['account_id'])
        data['asset_id'] = ObjectId(data['asset_id'])
        data['notification_url'] = data['notification_url']
        return super().from_json_type(data)

    @classmethod
    def get_id_prefix(cls):
        return 'h51_asset_task'


class AnalyzeTask(AssetTask):
    """
    A task to analyze an asset.
    """

    def __init__(self, account_id, asset_id, analyzers, notification_url=None):
        super().__init__(account_id, asset_id, notification_url)

        # A list of analyzers `[(analyzer_name, init_args), ...]` that the task
        # must run against the asset.
        self._analyzers = analyzers

    def get_analyzers(self, asset):
        for name, settings in self._analyzers:
            yield get_analyzer(asset.type, name)(**settings)

    def to_json_type(self):
        data = super().to_json_type()
        data['analyzers'] = self._analyzers
        return data

    @classmethod
    def get_id_prefix(cls):
        return 'h51_analyze_task'


class GenerateVariationTask(AssetTask):
    """
    A task to generate a variation for an asset.
    """

    def __init__(
        self,
        account_id,
        asset_id,
        variation_name,
        transforms,
        notification_url=None
    ):
        super().__init__(account_id, asset_id, notification_url)

        # The name of the variation to be generated
        self._variation_name = variation_name

        # The transforms to perform to generate the variation
        self._transforms = transforms

    @property
    def variation_name(self):
        return self._variation_name

    def get_transforms(self, asset):
        for name, settings in self._transforms:
            yield get_transform(asset.type, name)(**settings)

    def to_json_type(self):
        data = super().to_json_type()
        data['variation_name'] = self._variation_name
        data['transforms'] = self._transforms
        return data

    @classmethod
    def get_id_prefix(cls):
        return 'h51_generate_variation_task'

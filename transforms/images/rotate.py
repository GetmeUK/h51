from manhattan.forms import BaseForm, fields, validators
from PIL import Image

from transforms.images import BaseImageTransform

__all__ = ['RotateTransform']


class SettingsForm(BaseForm):

    degrees = fields.IntegerField(
        'angle',
        validators=[
            validators.Required(),
            validators.AnyOf([90, 180, 270])
        ]
    )


class RotateTransform(BaseImageTransform):
    """
    Rotate an image.
    """

    asset_type = 'image'
    name = 'rotate'

    def __init__(self, degrees):

        # The number of degrees to rotate the image
        self.degrees = degrees

    def transform(self, config, asset, file, variation_name, frames, history):
        frames = self._get_frames(file, frames)

        for i, frame in enumerate(frames):

            frames[i] = frame.transpose(
                getattr(Image, f'ROTATE_{360 - self.degrees}')
            )

        return frames

    @classmethod
    def get_settings_form_cls(cls):
        return SettingsForm

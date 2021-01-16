from manhattan.forms import BaseForm, fields, validators
from PIL import Image

from transforms.images import BaseImageTransform

__all__ = ['CropTransform']


class SettingsForm(BaseForm):

    top = fields.FloatField(
        'top',
        validators=[validators.NumberRange(min=0, max=1)]
    )

    left = fields.FloatField(
        'left',
        validators=[validators.NumberRange(min=0, max=1)]
    )

    bottom = fields.FloatField(
        'bottom',
        validators=[validators.NumberRange(min=0, max=1)]
    )

    right = fields.FloatField(
        'right',
        validators=[validators.NumberRange(min=0, max=1)]
    )


class CropTransform(BaseImageTransform):
    """
    Crop an image.
    """

    asset_type = 'image'
    name = 'crop'

    def __init__(self, top, left, bottom, right):

        # The region of the image to crop described as a decimal percentage
        # of the image's dimensions.
        self.top = top
        self.left = left
        self.bottom = bottom
        self.right = right

    def transform(self, config, asset, file, variation_name, frames, history):
        frames = self._get_frames(file, frames)

        for i, frame in enumerate(frames):
            frames[i] = frame.crop([
                int(self.left * frame.size[0]),
                int(self.top * frame.size[1]),
                int(self.right * frame.size[0]),
                int(self.bottom * frame.size[1])
            ])

        return frames

    @classmethod
    def get_settings_form_cls(cls):
        return SettingsForm

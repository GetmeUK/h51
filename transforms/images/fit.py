from manhattan.forms import BaseForm, fields, validators
from PIL import Image

from transforms.images import BaseImageTransform

__all__ = ['FitTransform']


class SettingsForm(BaseForm):

    width = fields.IntegerField(
        'width',
        validators=[validators.NumberRange(min=0)]
    )

    height = fields.IntegerField(
        'width',
        validators=[validators.NumberRange(min=0)]
    )

    resample = fields.StringField(
        'resample',
        validators=[
            validators.Optional(),
            validators.AnyOf(['NEAREST', 'BILINEAR', 'BICUBIC', 'LANCZOS'])
        ]
    )


class FitTransform(BaseImageTransform):
    """
    Fit an image to a width/height.
    """

    asset_type = 'image'
    name = 'fit'

    def __init__(self, width, height, resample=None):

        # The width and height of the rectangle to fit the image within
        self.height = height
        self.width = width

        # The filter used when resampling the image
        self.resample = resample

    def transform(self, config, asset, file, variation_name, frames, history):
        frames = self._get_frames(file, frames)

        for i, frame in enumerate(frames):

            resample = self.resample
            if not resample:

                # Set the default value for resample based on the frame's
                # color mode.
                resample = 'NEAREST' if frame.mode == 'P' else 'LANCZOS'

            if frame.mode == 'P' and resample != 'NEAREST':

                # Convert the frame to a color mode suitable for the
                # specified resample filter.
                if 'transparency' in frame.info:
                    frame = frame.convert('RGBA')
                else:
                    frame = frame.convert('RGB')

            # Fit the frame
            frame.thumbnail(
                [self.width, self.height],
                getattr(Image, resample)
            )

            frames[i] = frame

        return frames

    @classmethod
    def get_settings_form_cls(cls):
        return SettingsForm

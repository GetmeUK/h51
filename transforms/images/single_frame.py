from manhattan.forms import BaseForm, fields, validators
from PIL import Image

from transforms.images import BaseImageTransform

__all__ = ['SingleFrameTransform']


class SettingsForm(BaseForm):

    frame_number = fields.IntegerField(
        'frame_number',
        validators=[validators.Optional()],
        default=0
    )


class SingleFrameTransform(BaseImageTransform):
    """
    Extract a single frame from an animated image.
    """

    asset_type = 'image'
    name = 'single_frame'

    def __init__(self, frame_number=0):

        # The frame number to extract from the animation
        self.frame_number = frame_number

    def transform(self, config, asset, file, variation_name, frames, history):
        frames = self._get_frames(file, frames)

        # Wrap the frame number to ensure it's within the total number of
        # frames.
        last = max(1, len(frames) - 1)
        frame_number = (self.frame_number - last) % last

        # Extract the frame
        frames = [frames[frame_number]]

        return frames

    @classmethod
    def get_settings_form_cls(cls):
        return SettingsForm

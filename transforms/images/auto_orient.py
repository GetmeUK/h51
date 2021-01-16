import io

from manhattan.forms import BaseForm, fields, validators
from PIL import Image

from transforms.images import BaseImageTransform

__all__ = ['RotateTransform']


# Constants

ORIENTATION_TAG = 274
ORIENTATION_TRANSFORMS = {
    2: [Image.FLIP_LEFT_RIGHT],
    3: [Image.ROTATE_180],
    4: [Image.FLIP_TOP_BOTTOM],
    5: [Image.FLIP_LEFT_RIGHT, Image.ROTATE_90],
    6: [Image.ROTATE_270],
    7: [Image.FLIP_TOP_BOTTOM, Image.ROTATE_90],
    8: [Image.ROTATE_90]
}


class SettingsForm(BaseForm):

    pass


class AutoOrientTransform(BaseImageTransform):
    """
    Auto orient an image based on its Exif (Exchangeable image file format)
    data.
    """

    asset_type = 'image'
    name = 'auto_orient'

    def transform(self, config, asset, file, variation_name, frames, history):
        frames = self._get_frames(file, frames)

        # Exif data must be extracted from the source image
        image = Image.open(io.BytesIO(file))

        exif = None
        if hasattr(image, '_getexif'):
            try:
                exif = image._getexif()

            except:
                # Reading Exif data is experimental in Pillow and can
                # potentially throw errors, we don't care if we fail to
                # get Exif data so in this case a catch all for errors
                # is acceptable.
                pass

        transforms = []
        if exif and exif.get(ORIENTATION_TAG):
            transforms = ORIENTATION_TRANSFORMS.get(
                exif.get(ORIENTATION_TAG),
                []
            )

        if transforms:

            # Transform the frames of the image to orient it
            for i, frame in enumerate(frames):
                for transform in transforms:
                    frames[i] = frame.transpose(transform)

        return frames

    @classmethod
    def get_settings_form_cls(cls):
        return SettingsForm



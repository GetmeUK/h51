from manhattan.forms import BaseForm, fields, validators
from PIL import Image

from transforms.images import BaseImageTransform

__all__ = ['FocalPointCropTransform']


class SettingsForm(BaseForm):

    aspect_ratio = fields.FloatField(
        'aspect_ratio',
        validators=[validators.Optional()]
    )

    padding_top = fields.FloatField(
        'padding_top',
        validators=[
            validators.Optional(),
            validators.NumberRange(min=0)
        ],
        default=0
    )

    padding_left = fields.FloatField(
        'padding_left',
        validators=[
            validators.Optional(),
            validators.NumberRange(min=0)
        ],
        default=0
    )

    padding_bottom = fields.FloatField(
        'padding_bottom',
        validators=[
            validators.Optional(),
            validators.NumberRange(min=0)
        ],
        default=0
    )

    padding_right = fields.FloatField(
        'padding_right',
        validators=[
            validators.Optional(),
            validators.NumberRange(min=0)
        ],
        default=0
    )

    def validate_aspect_ratio(form, field):

        if field.data:
            if (
                form.padding_top.data
                or form.padding_left.data
                or form.padding_bottom.data
                or form.padding_right.data
            ):
                raise validators.ValidationError(
                    'Not applicable when padding has been specified.'
                )


class FocalPointCropTransform(BaseImageTransform):
    """
    Crop an image using around it's focal point (if no focal point is defined
    for the image the entire image will be considered the focal point).
    """

    asset_type = 'image'
    name = 'focal_point_crop'

    def __init__(
        self,
        aspect_ratio=None,
        padding_top=0,
        padding_left=0,
        padding_bottom=0,
        padding_right=0,
        as_fallback=False
    ):

        # The aspect ratio to crop the image to, if an aspect ratio isn't
        # provided then the image will be cropped around the focal point.
        self.aspect_ratio = aspect_ratio

        # The padding (as a decimal percentage of the focal point) to apply
        # around the image. If an aspect ratio is defined then padding values
        # will be ignored.
        self.padding_top = padding_top
        self.padding_left = padding_left
        self.padding_bottom = padding_bottom
        self.padding_right = padding_right

        # Flag indicating if the crop should only be applied if no other crop
        # transfrom has proceeded this one.
        self.as_fallback = as_fallback

    def transform(self, config, asset, file, variation_name, frames, history):
        frames = self._get_frames(file, frames)

        if self.as_fallback:

            # As the focal point crop is being applied as a fallback only
            # apply the crop if no previous crop transform has been applied.
            for past_transform in history:
                if past_transform.name == 'crop':
                    return frames

        size = frames[0].size

        # Get the focal point for the image
        fp = asset.meta['image'].get(
            'focal_point',
            {
                'top': 0,
                'left': 0,
                'bottom': 1,
                'right': 1
            }
        )

        crop_region = [0, 0, 1, 1]

        if self.aspect_ratio:

            # Crop to the specified aspect ratio
            crop_ratio = self.aspect_ratio
            image_ratio = size[0] / size[1]

            # Find the center of the focal point
            center = [
                (fp['left'] + ((fp['right'] - fp['left']) / 2)) * size[0],
                (fp['top'] + ((fp['bottom'] - fp['top']) / 2)) * size[1]
            ]

            # Define the crop region
            if image_ratio < crop_ratio:
                crop_rect = [
                    [0, center[1] - int((size[0] / crop_ratio) / 2)],
                    [size[0], int(size[0] / crop_ratio)]
                ]
                crop_rect[0][1] = max(
                    0,
                    min(crop_rect[0][1], size[1] - crop_rect[1][1])
                )

            else:
                crop_rect = [
                    [center[0] - int(int(size[1] * crop_ratio) / 2), 0],
                    [int(size[1] * crop_ratio), size[1]]
                ]
                crop_rect[0][0] = max(
                    0,
                    min(crop_rect[0][0], size[0] - crop_rect[1][0])
                )

            crop_region = [
                crop_rect[0][0],
                crop_rect[0][1],
                crop_rect[0][0] + crop_rect[1][0],
                crop_rect[0][1] + crop_rect[1][1]
            ]

        else:

            # Crop to the focal point (allowing for padding)
            pad = {
                'top': self.padding_top,
                'left': self.padding_left,
                'bottom': self.padding_bottom,
                'right': self.padding_right
            }

            crop_size = [
                fp['right'] - fp['left'],
                fp['bottom'] - fp['top'],
            ]

            crop_region = [
                (fp['left'] - (pad['left'] * crop_size[0])) * size[0],
                (fp['top'] - (pad['top'] * crop_size[1])) * size[1],
                (fp['right'] + (pad['right'] * crop_size[0])) * size[0],
                (fp['bottom'] + (pad['bottom'] * crop_size[1])) * size[1]
            ]

        # Crop the image
        for i, frame in enumerate(frames):
            frames[i] = frame.crop(crop_region)

        return frames

    @classmethod
    def get_settings_form_cls(cls):
        return SettingsForm

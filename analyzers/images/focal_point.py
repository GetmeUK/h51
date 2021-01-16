import io

from manhattan.forms import BaseForm, fields, validators
from PIL import Image

from analyzers import BaseAnalyzer

from .utils import (
    convert_to_gray_cv,
    detect_faces,
    detect_points_of_interest
)

__all__ = ['FocalPointAnalyzer']


class SettingsForm(BaseForm):

    top = fields.FloatField(
        'top',
        validators=[
            validators.Optional(),
            validators.NumberRange(min=0, max=1)
        ]
    )

    left = fields.FloatField(
        'left',
        validators=[
            validators.Optional(),
            validators.NumberRange(min=0, max=1)
        ]
    )

    bottom = fields.FloatField(
        'top',
        validators=[
            validators.Optional(),
            validators.NumberRange(min=0, max=1)
        ]
    )

    right = fields.FloatField(
        'left',
        validators=[
            validators.Optional(),
            validators.NumberRange(min=0, max=1)
        ]
    )

    def validate_bottom(form, field):
        if form.top.data and field.data:
            if form.top.data > field.data:
                raise validators.ValidationError(
                    'Value must be equal to or greater than `top`.'
                )

    def validate_right(form, field):
        if form.left.data and field.data:
            if form.left.data > field.data:
                raise validators.ValidationError(
                    'Value must be equal to or greater than `left`.'
                )

    def validate(self, *args, **kwargs):

        success = super().validate(*args, **kwargs)

        if success:

            # Validate that all or None of the focal point coordinates were
            # given.

            self._errors = {}

            coords = []
            for field_name in ['top', 'left', 'bottom', 'right']:
                coord = getattr(self, field_name).data
                if coord is not None:
                    coords.append(coord)

            if len(coords) not in [0, 4]:
                self._errors['focal_point'] = (
                    'Incomplete set of coordinates, a full set of `top`, '
                    '`left`, `bottom`, `right` must be specified or no '
                    'coordinates at all.'
                )
                success = False

        return success


class FocalPointAnalyzer(BaseAnalyzer):
    """
    Detect the focal point within the image, by default the analyzer will
    automatically detect the focal point, however, the caller can also supply
    a focal point.

    The analyzer can be used with the `focal_point_crop` transform in order to
    generate a variation that is cropped based on the detected/supplied focal
    point.
    """

    asset_type = 'image'
    name = 'focal_point'

    def __init__(self, top=None, left=None, bottom=None, right=None):

        # The coordinates of the focal point given as decimal percentages of
        # the images dimensions.
        self.top = top
        self.left = left
        self.bottom = bottom
        self.right = right

    def analyze(self, config, asset, file, history):
        # Load the image
        image = Image.open(io.BytesIO(file))

        if self.top:

            # Focal point was supplied manually, no detection required.
            self._add_to_meta(
                asset,
                {
                    'top': self.top,
                    'left': self.left,
                    'bottom': self.bottom,
                    'right': self.right
                }
            )

            return

        # Auto detect focal point (default to the center of the image)
        focal_point = {
            'top': int(image.size[1] / 2),
            'left': int(image.size[0] / 2),
            'bottom': int(image.size[1] / 2),
            'right': int(image.size[0] / 2)
        }

        # Apply an upper limit to the size of the image
        image.thumbnail(
            config.get('FOCAL_POINT_MAX_DIMENSIONS', [1000, 1000]),
            Image.BICUBIC
        )

        # Convert the image to a format suitable for face and points of
        # interest detection.
        cv_image = convert_to_gray_cv(image)

        # Detect faces
        faces = detect_faces(
            cv_image,
            config.get('FOCAL_POINT_FACES_CLASSIFIER'),
            config.get('FOCAL_POINT_FACES_CV_ARGS')
        )

        if faces:

            # Find the largest face as this will be used as the focal point
            faces.sort(key=lambda x: x[2] * x[3], reverse=True)
            focal_point = {
                'top': faces[0][1],
                'left': faces[0][0],
                'bottom': faces[0][1] + faces[0][3],
                'right': faces[0][0] + faces[0][2]
            }

        else:

            # Detect points of interest
            points = detect_points_of_interest(
                cv_image,
                config.get('FOCAL_POINT_POINTS_OF_INTEREST_CV_ARGS')
            )

            if points:
                focal_point = {
                    'top': min(p[1] for p in points),
                    'left': min(p[0] for p in points),
                    'bottom': max(p[1] for p in points),
                    'right': max(p[0] for p in points)
                }

        # Convert focal point to decimal percentages
        focal_point = {
            'top': focal_point['top'] / image.size[1],
            'left': focal_point['left'] / image.size[0],
            'bottom': focal_point['bottom'] / image.size[1],
            'right': focal_point['right'] / image.size[0]
        }

        self._add_to_meta(asset, focal_point)

    @classmethod
    def get_settings_form_cls(cls):
        return SettingsForm

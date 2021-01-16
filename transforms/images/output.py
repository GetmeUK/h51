import io

from manhattan.forms import BaseForm, fields, validators
from PIL import Image

from transforms.images import BaseImageTransform

__all__ = ['Ouput']


# A table of supported image formats and their associated file extension
IMAGE_FORMATS = {
    'GIF': 'gif',
    'JPEG': 'jpg',
    'PNG': 'png',
    'WebP': 'webp'
}


class SettingsForm(BaseForm):

    image_format = fields.StringField(
        'image_format',
        validators=[
            validators.Required(),
            validators.AnyOf(IMAGE_FORMATS.keys())
        ]
    )

    quality = fields.IntegerField(
        'quality',
        validators=[
            validators.Optional(),
            validators.NumberRange(min=0, max=100)
        ],
        default=80
    )

    lossless = fields.BooleanField('lossless')

    progressive = fields.BooleanField('progressive')

    versioned = fields.BooleanField('versioned')


class OutputTransform(BaseImageTransform):
    """
    Output an image variation.
    """

    asset_type = 'image'
    final = True
    name = 'output'

    def __init__(
        self,
        image_format,
        quality=80,
        lossless=False,
        progressive=False,
        versioned=True
    ):

        # The image format to store the variation as
        self.image_format = image_format

        # The image quality (0-100) to use
        self.quality = quality

        # Whether to use lossy or lossless image compression
        self.lossless = lossless

        # Whether or not the image should be saved using baseline or
        # progressive encoding (JPEG).
        self.progressive = progressive

        # Whether the variation should stored with a version
        self.versioned = versioned

    def transform(self, config, asset, file, variation_name, frames, history):
        frames = self._get_frames(file, frames)

        # Write the image to file in the given format
        new_file = io.BytesIO()

        if self.image_format == 'GIF':

            save_args = {}

            if len(frames) > 1:

                # Build animation arguments
                base_duration = frames[0].info.get('duration', 100)
                save_args['duration'] = [
                    f.info.get('duration', base_duration)
                    for f in frames
                ]
                save_args['loop'] = frames[0].info.get('loop', 0)
                save_args['save_all'] = True

            if 'transparency' in frames[0].info:

                # Extract transparency color
                save_args['transparency'] \
                        = frames[0].info['transparency']

                if type(save_args['transparency']) is bytes:
                    save_args['transparency'] = int.from_bytes(
                        save_args['transparency'],
                        'big'
                    )

            # Convert frames to P mode
            for i, frame in enumerate(frames):
                if frame.mode != 'P':
                    frames[i] = frame.convert('P')

            if len(frames) > 1:
                # Add the frames of animation to the save args
                save_args['append_images'] = frames[1:]

            frames[0].save(
                new_file,
                format=self.image_format,
                optimze=True,
                disposal=2,
                **save_args
            )

        elif self.image_format == 'JPEG':
            image = frames[0]

            if image.mode != 'RGB':
                image = image.convert('RGBA').convert('RGB')

            image.save(
                new_file,
                format=self.image_format,
                optimize=True,
                progressive=self.progressive,
                quality=self.quality
            )

        elif self.image_format == 'PNG':
            image = frames[0]
            image.save(
                new_file,
                format=self.image_format,
                optimize=True
            )

        elif self.image_format == 'WebP':

            save_args = {}

            if len(frames) > 1:

                # Build animation arguments
                base_duration = frames[0].info.get('duration', 100)
                save_args['duration'] = [
                    f.info.get('duration', base_duration)
                    for f in frames
                ]
                save_args['loop'] = frames[0].info.get('loop', 0)
                save_args['save_all'] = True

            if 'background' in frames[0].info:

                # Extract background color
                save_args['background'] = frames[0].info['background']
                if type(save_args['background']) is int:
                    palette = frames[0].getpalette()

                    if palette:
                        palette = list(zip(*([iter(palette)] * 3)))
                        save_args['background'] = (
                            *palette[save_args['background']],
                            255
                        )

                    else:

                        # If there's no longer a palette associated with the
                        # frame (e.g the colour mode changed from 'P' then
                        # don't set a background color.
                        del frames[0].info['background']
                        del save_args['background']

            # Convert frames to RGB(A) mode
            for i, frame in enumerate(frames):
                if frame.mode not in ['RGB', 'RGBA']:
                    if 'transparency' in frames[i].info:
                        frames[i] = frame.convert('RGBA')
                    else:
                        frames[i] = frame.convert('RGB')

            if len(frames) > 1:
                # Add the frames of animation to the save args
                save_args['append_images'] = frames[1:]

            frames[0].save(
                new_file,
                allow_mixed=True,
                format=self.image_format,
                lossless=self.lossless,
                quality=self.quality,
                minimize_size=True,
                optimize=True,
                **save_args
            )

        ext = IMAGE_FORMATS[self.image_format]

        self._store_variation(
            config,
            asset,
            variation_name,
            self.versioned,
            ext,
            {
                'length': new_file.getbuffer().nbytes,
                'image': {
                    'mode': frames[0].mode,
                    'size': frames[0].size
                }
            },
            new_file
        )

    @classmethod
    def get_settings_form_cls(cls):
        return SettingsForm

import io

from PIL import Image, ImageSequence

from transforms import BaseTransform

__all__ = ['BaseImageTransform']


class BaseImageTransform(BaseTransform):
    """
    A base transform for image assets, this class should be inherited from
    when writing transforms for raster images.
    """

    asset_type = 'image'

    def _get_frames(self, file, frames):
        """
        Return the given frames or if frames is None use the file to create a
        list of frames to return.
        """

        if frames:
            return frames

        image = Image.open(io.BytesIO(file))

        frames = []
        for frame in range(getattr(image, 'n_frames', 1)):
            image.seek(frame)
            image.load()
            frames.append(image.copy())

        return frames

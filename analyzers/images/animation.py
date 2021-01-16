import io

from manhattan.forms import BaseForm
from PIL import Image

from analyzers import BaseAnalyzer

__all__ = ['AnimationAnalyzer']


class SettingsForm(BaseForm):

    pass


class AnimationAnalyzer(BaseAnalyzer):
    """
    Extract animation information for an animated image.
    """

    asset_type = 'image'
    name = 'animation'

    def analyze(self, config, asset, file, history):
        # Load the image
        image = Image.open(io.BytesIO(file))

        durations = [image.info.get('duration', 0)]
        for frame in range(1, getattr(image, 'n_frames', 1)):
            image.seek(frame)
            image.load()
            durations.append(
                image.info.get('duration', image.info.get('duration', 0))
            )

        # Reset frame
        image.seek(0)
        image.load()

        self._add_to_meta(
            asset,
            {
                'frames': getattr(image, 'n_frames', 1),
                'durations': durations,
                'loop': image.info.get('loop', 0)
            }
        )

    @classmethod
    def get_settings_form_cls(cls):
        return SettingsForm

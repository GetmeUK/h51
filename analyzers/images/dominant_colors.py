import io
import operator

from manhattan.forms import BaseForm, fields, validators
import numpy
from PIL import Image
from sklearn.cluster import MiniBatchKMeans

from analyzers import BaseAnalyzer

__all__ = ['DominantColors']


class SettingsForm(BaseForm):

    max_colors = fields.IntegerField(
        'max_colors',
        validators=[
            validators.Optional(),
            validators.NumberRange(min=1, max=32)
        ],
        default=8
    )

    min_weight = fields.FloatField(
        'min_weight',
        validators=[
            validators.Optional(),
            validators.NumberRange(min=0, max=1)
        ],
        default=0.015
    )

    max_sample_size = fields.IntegerField(
        'max_colors',
        validators=[
            validators.Optional(),
            validators.NumberRange(min=0)
        ],
        default=512
    )


class DominantColorsAnalyzer(BaseAnalyzer):
    """
    Extract a set of dominant colors from the image.
    """

    asset_type = 'image'
    name = 'dominant_colors'

    def __init__(self, max_colors=8, min_weight=0.015, max_sample_size=512):

        # The maximum number of dominant colors that will be found for the
        # image.
        self.max_colors = max_colors

        # The minimum weight for a cluster/color to be consider a dominant
        # color.
        self.min_weight = min_weight

        # The maximum size of the image to analyze. Image size effects the time
        # required to analyze an image but the accuracy of the set of dominant
        # colors does not increase significantly for very large images.
        #
        # If `max_sample_size` is set to 1024 then the analyzer will fit
        # (resize if necessary and retaining the images aspect ratio) to a
        # rectangle 1024x1024 pixel in size.
        #
        self.max_sample_size = max_sample_size

    def analyze(self, config, asset, file, history):
        # Load the image
        image = Image.open(io.BytesIO(file))

        # Ensure the image is no larger than the maximum sample size
        if self.max_sample_size:
            image.thumbnail(
                [
                    self.max_sample_size,
                    self.max_sample_size
                ],
                Image.HAMMING
            )

        # Ensure the image is in RGB color mode
        if image.mode == 'P':
            image = image.convert('RGBA').convert('RGB')

        if image.mode != 'RGB':
            image = image.convert('RGB')

        # Extract the dominant colors from the image
        image_uint8 = numpy.array(image.getdata(), numpy.uint8)
        clusters = MiniBatchKMeans(
            n_clusters=min(self.max_colors, image_uint8.shape[0])
        )
        clusters.fit(image_uint8)

        # Create a histogram of the number of occurance of each color cluster
        # within the image.
        hist, hist_len = numpy.histogram(
            clusters.labels_,
            bins=numpy.arange(0, len(numpy.unique(clusters.labels_)) + 1)
        )

        # Normalize the histogram
        hist = hist.astype('float')
        hist /= hist.sum()

        # Build the list of colors found as a list of tuple of the form
        # `[(rgb, weight), ...]`.
        colors = []
        for (weight, center) in zip(hist, clusters.cluster_centers_):
            colors.append((center.astype('uint8').tolist(), weight))

        # Remove colors with less than the required minimum weight
        colors = [c for c in colors if c[1] > self.min_weight]

        # Sort the colors by weight (most dominant first)
        colors.sort(key=operator.itemgetter(1), reverse=True)

        # Convert colours to a more simple to understand format
        colors = [{'rgb': c[0], 'weight': c[1]} for c in colors]

        self._add_to_meta(asset, {'colors': colors})

    @classmethod
    def get_settings_form_cls(cls):
        return SettingsForm

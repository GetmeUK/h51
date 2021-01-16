
from settings import BaseConfig


class DefaultConfig(BaseConfig):

    # NOTE: Antivirus scanning requires clamav to be installed on any machine
    # that will perform virus scans. Details can be found against the
    # clamd PYPI page (https://pypi.org/project/clamd/).
    ANTI_VIRUS_CLAMD_PATH = ''
    ANTI_VIRUS_ENABLED = False

    MAX_VARIATIONS_PER_REQUEST = 10

    MAX_BUFFER_SIZE = 1024 * 1024 * 100

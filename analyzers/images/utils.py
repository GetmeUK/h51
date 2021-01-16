"""
A set of utils for image transforms.
"""

import os

import cv2
import numpy

__all__ = [
    'convert_to_gray_cv',
    'detect_points_of_interest'
]


# CONSTANTS

DEFAULT_FACE_CLASSIFIER = cv2.CascadeClassifier(
    os.path.join(
        os.path.dirname(__file__),
        'data/cascades',
        'haarcascade_frontalface_alt2'
    ) + '.xml'
)


def convert_to_gray_cv(image):
    """
    Take the given PIL image and return a grayscale CV image (suitable for
    feature detection.)
    """

    image = image.copy()
    if image.mode != 'RGB':
        image = image.convert('RGBA').convert('RGB')

    return cv2.cvtColor(numpy.array(image), cv2.COLOR_RGB2GRAY)

def detect_faces(image, classifier=None, cv_args=None):
    """Return a list of faces detected within the given image"""
    equ_image = cv2.equalizeHist(image)
    faces = (classifier or DEFAULT_FACE_CLASSIFIER).detectMultiScale(
        equ_image,
        **{
            'scaleFactor': 1.05,
            'minNeighbors': 4,
            'flags': 0,
            'minSize': (30, 30),
            **(cv_args or {})
        }
    )

    if len(faces) == 0:
        return []

    return faces.tolist()


def detect_points_of_interest(image, cv_args=None):
    """Return a list of points of interest detected within the given image"""
    points = cv2.goodFeaturesToTrack(
        image,
        mask=None,
        **{
            'maxCorners': 20,
            'qualityLevel': 0.04,
            'minDistance': 1.0,
            'blockSize': 3,
            'gradientSize': 3,
            **(cv_args or {})
        }
    )

    if points is None:
        return []

    return numpy.reshape(points, (-1, 2)).tolist()

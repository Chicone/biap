import numpy as np
from PIL import Image

from backend.vision.preprocessing import (
    invert_image,
    normalize_to_uint8,
    to_grayscale,
)


def test_to_grayscale_from_rgb_array():
    image = np.zeros((10, 20, 3), dtype=np.uint8)

    gray = to_grayscale(image)

    assert gray.shape == (10, 20)
    assert gray.dtype == np.uint8


def test_to_grayscale_from_pil_image():
    image = Image.new("RGB", (20, 10))

    gray = to_grayscale(image)

    assert gray.shape == (10, 20)
    assert gray.dtype == np.uint8


def test_normalize_to_uint8():
    image = np.array([[0, 5], [10, 15]], dtype=np.float32)

    normalized = normalize_to_uint8(image)

    assert normalized.dtype == np.uint8
    assert normalized.min() == 0
    assert normalized.max() == 255


def test_normalize_constant_image():
    image = np.ones((10, 20), dtype=np.float32) * 5

    normalized = normalize_to_uint8(image)

    assert normalized.dtype == np.uint8
    assert normalized.min() == 0
    assert normalized.max() == 0


def test_invert_image():
    image = np.array([[0, 255]], dtype=np.uint8)

    inverted = invert_image(image)

    assert inverted[0, 0] == 255
    assert inverted[0, 1] == 0
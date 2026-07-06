from pathlib import Path

import numpy as np
from PIL import Image

from backend.vision.io import (
    image_info,
    is_grayscale,
    load_image,
    load_image_as_array,
    numpy_to_pil,
    pil_to_numpy,
)


TEST_IMAGE_PATH = Path("data/external/BBBC038/stage1_train/0a7d30b252359a10fd298b638b90cb9ada3acced4e0c0e5a3692013f432ee4e9/images/0a7d30b252359a10fd298b638b90cb9ada3acced4e0c0e5a3692013f432ee4e9.png")


def test_load_image():
    image = load_image(TEST_IMAGE_PATH)

    assert image is not None
    assert isinstance(image, Image.Image)
    assert image.width > 0
    assert image.height > 0


def test_load_image_as_array():
    array = load_image_as_array(TEST_IMAGE_PATH)

    assert isinstance(array, np.ndarray)
    assert array.size > 0


def test_pil_to_numpy():
    image = load_image(TEST_IMAGE_PATH)

    array = pil_to_numpy(image)

    assert isinstance(array, np.ndarray)
    assert array.shape[0] == image.height
    assert array.shape[1] == image.width


def test_numpy_to_pil():
    array = np.zeros((10, 20), dtype=np.uint8)

    image = numpy_to_pil(array)

    assert isinstance(image, Image.Image)
    assert image.width == 20
    assert image.height == 10


def test_is_grayscale_with_numpy_array():
    array = np.zeros((10, 20), dtype=np.uint8)

    assert is_grayscale(array) is True


def test_is_grayscale_with_rgb_array():
    array = np.zeros((10, 20, 3), dtype=np.uint8)

    assert is_grayscale(array) is False


def test_image_info_for_pil_image():
    image = load_image(TEST_IMAGE_PATH)

    info = image_info(image)

    assert info["type"] == "PIL"
    assert info["width"] == image.width
    assert info["height"] == image.height
    assert "mode" in info


def test_image_info_for_numpy_array():
    array = np.zeros((10, 20), dtype=np.uint8)

    info = image_info(array)

    assert info["type"] == "numpy"
    assert info["shape"] == array.shape
    assert info["dtype"] == "uint8"
    assert info["ndim"] == 2
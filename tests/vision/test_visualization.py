import numpy as np

from backend.vision.visualization import (
    blend_images,
    label_to_rgb,
    overlay_mask,
)


def test_label_to_rgb():
    mask = np.array(
        [[0, 1],
         [1, 0]],
        dtype=np.uint8
    )

    rgb = label_to_rgb(mask)

    assert rgb.shape == (2, 2, 3)
    assert rgb.dtype == np.uint8

    # Background pixel
    assert np.array_equal(rgb[0, 0], [0, 0, 0])

    # Foreground pixel
    assert np.array_equal(rgb[0, 1], [255, 0, 0])


def test_blend_images():
    image = np.zeros((10, 10, 3), dtype=np.uint8)
    overlay = np.ones((10, 10, 3), dtype=np.uint8) * 255

    blended = blend_images(image, overlay)

    assert blended.shape == image.shape
    assert blended.dtype == np.uint8

    # Halfway between black and white
    assert np.all(blended == 127)


def test_overlay_mask():
    image = np.zeros((10, 10, 3), dtype=np.uint8)

    mask = np.zeros((10, 10), dtype=np.uint8)
    mask[2:5, 2:5] = 1

    result = overlay_mask(image, mask)

    assert result.shape == image.shape
    assert result.dtype == np.uint8

    # Inside the mask → should contain red
    assert result[3, 3, 0] > 0

    # Outside the mask → should remain black
    assert np.array_equal(result[0, 0], [0, 0, 0])
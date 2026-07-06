import numpy as np
from backend.vision.segmentation import connected_components
from backend.vision.segmentation import threshold, segment_otsu
from skimage.filters import threshold_otsu


def test_threshold():
    image = np.array(
        [[20, 80, 140],
         [170, 255, 60]],
        dtype=np.uint8
    )

    binary = threshold(image, 128)

    expected = np.array(
        [[0, 0, 1],
         [1, 1, 0]],
        dtype=np.uint8
    )

    assert np.array_equal(binary, expected)


def test_connected_components():
  mask = np.array(
    [
      [0, 0, 1, 1, 0],
      [0, 0, 1, 1, 0],
      [0, 0, 0, 0, 0],
      [1, 1, 0, 1, 0],
      [1, 1, 0, 1, 0],
    ],
    dtype=np.uint8,
  )

  labels = connected_components(mask)

  # Three objects should be detected
  assert labels.max() == 3

  # Background remains 0
  assert labels[0, 0] == 0

  # First object
  assert labels[0, 2] == 1

  # Second object
  assert labels[3, 0] == 2

  # Third object
  assert labels[3, 3] == 3

  def test_otsu_threshold():
    image = np.array(
      [
        [10, 12, 15],
        [200, 210, 220],
      ],
      dtype=np.uint8,
    )

    binary = threshold_otsu(image)

    assert binary.shape == image.shape
    assert binary.dtype == np.uint8
    assert binary.max() == 1
    assert binary.min() == 0

  def test_segment_otsu():
    image = np.array(
      [
        [10, 10, 10],
        [200, 200, 200],
      ],
      dtype=np.uint8,
    )

    binary = segment_otsu(image)

    expected = np.array(
      [
        [0, 0, 0],
        [1, 1, 1],
      ],
      dtype=np.uint8,
    )

    assert np.array_equal(binary, expected)


def test_segment_otsu_dark():
  image = np.array(
    [
      [10, 10, 10],
      [200, 200, 200],
    ],
    dtype=np.uint8,
  )

  binary = segment_otsu(image, foreground="dark")

  expected = np.array(
    [
      [1, 1, 1],
      [0, 0, 0],
    ],
    dtype=np.uint8,
  )

  assert np.array_equal(binary, expected)
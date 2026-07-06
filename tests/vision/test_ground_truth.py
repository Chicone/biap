from pathlib import Path

from backend.vision.ground_truth import get_ground_truth_masks


def test_get_ground_truth_masks():
    mask_dir = Path("tests/data/masks")

    masks = get_ground_truth_masks(mask_dir)

    assert isinstance(masks, list)
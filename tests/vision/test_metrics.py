import numpy as np

from backend.vision.metrics import (
    dice_coefficient,
    iou,
    precision,
    recall,
)


def test_perfect_match():
    gt = np.array([[1, 0], [1, 0]], dtype=np.uint8)
    pred = gt.copy()

    assert iou(pred, gt) == 1.0
    assert dice_coefficient(pred, gt) == 1.0
    assert precision(pred, gt) == 1.0
    assert recall(pred, gt) == 1.0


def test_no_overlap():
    gt = np.array([[1, 1], [0, 0]], dtype=np.uint8)
    pred = np.array([[0, 0], [1, 1]], dtype=np.uint8)

    assert iou(pred, gt) == 0.0
    assert dice_coefficient(pred, gt) == 0.0
    assert precision(pred, gt) == 0.0
    assert recall(pred, gt) == 0.0


def test_partial_overlap():
    gt = np.array([[1, 1], [0, 0]], dtype=np.uint8)
    pred = np.array([[1, 0], [1, 0]], dtype=np.uint8)

    assert np.isclose(iou(pred, gt), 1 / 3)
    assert np.isclose(dice_coefficient(pred, gt), 0.5)
    assert np.isclose(precision(pred, gt), 0.5)
    assert np.isclose(recall(pred, gt), 0.5)
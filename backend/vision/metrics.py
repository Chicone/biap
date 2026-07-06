import numpy as np


def iou(prediction: np.ndarray, ground_truth: np.ndarray) -> float:
    """
    Intersection over Union (Jaccard Index).
    """
    intersection = np.logical_and(prediction, ground_truth).sum()
    union = np.logical_or(prediction, ground_truth).sum()

    if union == 0:
        return 1.0

    return intersection / union


def dice_coefficient(prediction: np.ndarray, ground_truth: np.ndarray) -> float:
    """
    Dice Similarity Coefficient.
    """
    intersection = np.logical_and(prediction, ground_truth).sum()

    total = prediction.sum() + ground_truth.sum()

    if total == 0:
        return 1.0

    return (2 * intersection) / total


def precision(prediction: np.ndarray, ground_truth: np.ndarray) -> float:
    """
    Precision = TP / (TP + FP)
    """
    tp = np.logical_and(prediction, ground_truth).sum()
    fp = np.logical_and(prediction, np.logical_not(ground_truth)).sum()

    if tp + fp == 0:
        return 1.0

    return tp / (tp + fp)


def recall(prediction: np.ndarray, ground_truth: np.ndarray) -> float:
    """
    Recall = TP / (TP + FN)
    """
    tp = np.logical_and(prediction, ground_truth).sum()
    fn = np.logical_and(np.logical_not(prediction), ground_truth).sum()

    if tp + fn == 0:
        return 1.0

    return tp / (tp + fn)
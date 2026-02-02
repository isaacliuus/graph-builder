"""Evaluation metrics for extraction quality."""


def precision(true_positives: int, false_positives: int) -> float:
    """Calculate precision: TP / (TP + FP).

    Args:
        true_positives: Number of correctly identified items.
        false_positives: Number of incorrectly identified items.

    Returns:
        Precision score between 0.0 and 1.0, or 0.0 if no predictions.
    """
    total = true_positives + false_positives
    if total == 0:
        return 0.0
    return true_positives / total


def recall(true_positives: int, false_negatives: int) -> float:
    """Calculate recall: TP / (TP + FN).

    Args:
        true_positives: Number of correctly identified items.
        false_negatives: Number of missed items.

    Returns:
        Recall score between 0.0 and 1.0, or 0.0 if no ground truth items.
    """
    total = true_positives + false_negatives
    if total == 0:
        return 0.0
    return true_positives / total


def f1_score(prec: float, rec: float) -> float:
    """Calculate F1 score: 2 * (precision * recall) / (precision + recall).

    Args:
        prec: Precision score.
        rec: Recall score.

    Returns:
        F1 score between 0.0 and 1.0, or 0.0 if both inputs are zero.
    """
    total = prec + rec
    if total == 0:
        return 0.0
    return 2 * (prec * rec) / total

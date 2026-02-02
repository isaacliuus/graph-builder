"""Evaluation module for measuring extraction quality."""

from graph_builder.evaluation.dataset import (
    GroundTruthDocument,
    GroundTruthEntity,
    GroundTruthRelationship,
    load_dataset,
)
from graph_builder.evaluation.evaluator import (
    DocumentResult,
    EvaluationResult,
    Evaluator,
)
from graph_builder.evaluation.metrics import f1_score, precision, recall

__all__ = [
    "GroundTruthDocument",
    "GroundTruthEntity",
    "GroundTruthRelationship",
    "load_dataset",
    "DocumentResult",
    "EvaluationResult",
    "Evaluator",
    "precision",
    "recall",
    "f1_score",
]

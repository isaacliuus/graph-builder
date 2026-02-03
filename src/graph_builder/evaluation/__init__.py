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
from graph_builder.evaluation.clause_dataset import (
    GroundTruthClause,
    GroundTruthContractDocument,
    load_clause_dataset,
)
from graph_builder.evaluation.clause_evaluator import (
    ClauseDocumentResult,
    ClauseEvaluationResult,
    ClauseEvaluator,
    calculate_boundary_iou,
)

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
    "GroundTruthClause",
    "GroundTruthContractDocument",
    "load_clause_dataset",
    "ClauseDocumentResult",
    "ClauseEvaluationResult",
    "ClauseEvaluator",
    "calculate_boundary_iou",
]

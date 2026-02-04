"""Evaluator for clause extraction quality assessment."""

from dataclasses import dataclass, field
from pathlib import Path

from graph_builder.clauses.base import ClauseExtractor
from graph_builder.models import Clause, ClauseType
from graph_builder.parsing.base import DocumentParser

from .clause_dataset import GroundTruthClause, GroundTruthContractDocument
from .metrics import f1_score, precision, recall


# Map ground truth type strings to ClauseType enum
CLAUSE_TYPE_MAP: dict[str, ClauseType] = {
    "DEFINITIONS": ClauseType.DEFINITIONS,
    "CONFIDENTIALITY": ClauseType.CONFIDENTIALITY,
    "TERMINATION": ClauseType.TERMINATION,
    "INDEMNIFICATION": ClauseType.INDEMNIFICATION,
    "LIABILITY": ClauseType.LIABILITY,
    "GOVERNING_LAW": ClauseType.GOVERNING_LAW,
    "DISPUTE_RESOLUTION": ClauseType.DISPUTE_RESOLUTION,
    "FORCE_MAJEURE": ClauseType.FORCE_MAJEURE,
    "PAYMENT": ClauseType.PAYMENT,
    "INTELLECTUAL_PROPERTY": ClauseType.INTELLECTUAL_PROPERTY,
    "WARRANTIES": ClauseType.WARRANTIES,
    "REPRESENTATIONS": ClauseType.REPRESENTATIONS,
    "NOTICES": ClauseType.NOTICES,
    "TERM_AND_TERMINATION": ClauseType.TERM_AND_TERMINATION,
    "OTHER": ClauseType.OTHER,
}


def normalize_clause_type(type_str: str) -> ClauseType:
    """Normalize a clause type string to ClauseType enum."""
    return CLAUSE_TYPE_MAP.get(type_str.upper(), ClauseType.OTHER)


def calculate_boundary_iou(
    extracted_start: int,
    extracted_end: int,
    gt_start: int,
    gt_end: int,
) -> float:
    """Calculate Intersection over Union for paragraph boundaries.

    Args:
        extracted_start: Start paragraph index of extracted clause.
        extracted_end: End paragraph index of extracted clause.
        gt_start: Start paragraph index of ground truth clause.
        gt_end: End paragraph index of ground truth clause.

    Returns:
        IoU score between 0.0 and 1.0.
    """
    # Calculate intersection
    intersection_start = max(extracted_start, gt_start)
    intersection_end = min(extracted_end, gt_end)
    intersection = max(0, intersection_end - intersection_start)

    # Calculate union
    union_start = min(extracted_start, gt_start)
    union_end = max(extracted_end, gt_end)
    union = union_end - union_start

    if union == 0:
        return 1.0 if intersection == 0 else 0.0

    return intersection / union


@dataclass
class ClauseDocumentResult:
    """Evaluation results for a single contract document."""

    document_id: str
    detection_tp: int = 0
    detection_fp: int = 0
    detection_fn: int = 0
    type_correct: int = 0
    type_total: int = 0
    boundary_ious: list[float] = field(default_factory=list)
    extracted_clauses: list = field(default_factory=list)
    ground_truth_clauses: list = field(default_factory=list)


@dataclass
class ClauseEvaluationResult:
    """Overall clause evaluation results."""

    detection_precision: float
    detection_recall: float
    detection_f1: float
    type_accuracy: float
    mean_boundary_iou: float
    details: dict[str, ClauseDocumentResult] = field(default_factory=dict)

    def to_dict(self, include_debug: bool = False) -> dict:
        """Convert results to a dictionary.

        Args:
            include_debug: If True, include extracted clauses.
        """
        result = {
            "detection_precision": self.detection_precision,
            "detection_recall": self.detection_recall,
            "detection_f1": self.detection_f1,
            "type_accuracy": self.type_accuracy,
            "mean_boundary_iou": self.mean_boundary_iou,
            "details": {},
        }

        for doc_id, doc_result in self.details.items():
            doc_dict = {
                "document_id": doc_result.document_id,
                "detection_tp": doc_result.detection_tp,
                "detection_fp": doc_result.detection_fp,
                "detection_fn": doc_result.detection_fn,
                "type_correct": doc_result.type_correct,
                "type_total": doc_result.type_total,
                "mean_boundary_iou": (
                    sum(doc_result.boundary_ious) / len(doc_result.boundary_ious)
                    if doc_result.boundary_ious
                    else 0.0
                ),
            }
            if include_debug:
                doc_dict["extracted_clauses"] = doc_result.extracted_clauses
                doc_dict["ground_truth_clauses"] = doc_result.ground_truth_clauses
            result["details"][doc_id] = doc_dict

        return result


class ClauseEvaluator:
    """Evaluates clause extraction quality against ground truth datasets."""

    def __init__(
        self,
        parser: DocumentParser | dict[str, DocumentParser],
        extractor: ClauseExtractor,
        base_path: Path | None = None,
    ):
        """Initialize the evaluator.

        Args:
            parser: Document parser to use for loading files. Can be a single
                parser or a dict mapping file extensions (e.g., ".docx", ".pdf")
                to their respective parsers.
            extractor: Clause extractor to evaluate.
            base_path: Base path for resolving relative file paths.
        """
        self._parser = parser
        self._parsers: dict[str, DocumentParser] | None = None
        if isinstance(parser, dict):
            self._parsers = parser
        self.extractor = extractor
        self.base_path = base_path or Path.cwd()

    def _get_parser_for_file(self, file_path: Path) -> DocumentParser:
        """Get the appropriate parser for a file based on its extension."""
        if self._parsers is not None:
            ext = file_path.suffix.lower()
            if ext not in self._parsers:
                raise ValueError(
                    f"No parser registered for extension: {ext}. "
                    f"Available: {list(self._parsers.keys())}"
                )
            return self._parsers[ext]
        return self._parser  # type: ignore[return-value]

    def evaluate(
        self, dataset: list[GroundTruthContractDocument]
    ) -> ClauseEvaluationResult:
        """Evaluate clause extraction against a ground truth dataset.

        Args:
            dataset: List of ground truth contract documents.

        Returns:
            ClauseEvaluationResult with metrics.
        """
        total_detection_tp = 0
        total_detection_fp = 0
        total_detection_fn = 0
        total_type_correct = 0
        total_type_total = 0
        all_boundary_ious: list[float] = []
        details: dict[str, ClauseDocumentResult] = {}

        for gt_doc in dataset:
            doc_result = self._evaluate_document(gt_doc)
            details[gt_doc.id] = doc_result

            total_detection_tp += doc_result.detection_tp
            total_detection_fp += doc_result.detection_fp
            total_detection_fn += doc_result.detection_fn
            total_type_correct += doc_result.type_correct
            total_type_total += doc_result.type_total
            all_boundary_ious.extend(doc_result.boundary_ious)

        detection_prec = precision(total_detection_tp, total_detection_fp)
        detection_rec = recall(total_detection_tp, total_detection_fn)
        detection_f1 = f1_score(detection_prec, detection_rec)
        type_acc = total_type_correct / total_type_total if total_type_total > 0 else 0.0
        mean_iou = sum(all_boundary_ious) / len(all_boundary_ious) if all_boundary_ious else 0.0

        return ClauseEvaluationResult(
            detection_precision=detection_prec,
            detection_recall=detection_rec,
            detection_f1=detection_f1,
            type_accuracy=type_acc,
            mean_boundary_iou=mean_iou,
            details=details,
        )

    def _evaluate_document(
        self, gt_doc: GroundTruthContractDocument
    ) -> ClauseDocumentResult:
        """Evaluate clause extraction on a single document."""
        file_path = self.base_path / gt_doc.file

        # Parse and extract
        parser = self._get_parser_for_file(file_path)
        document = parser.parse(file_path)
        extracted_clauses = self.extractor.extract(document)

        # Match clauses
        detection_tp, detection_fp, detection_fn, matches = self._match_clauses(
            extracted_clauses, gt_doc.clauses
        )

        # Calculate type accuracy and boundary IoU for matched clauses
        type_correct = 0
        type_total = len(matches)
        boundary_ious: list[float] = []

        for extracted, gt in matches:
            # Type accuracy
            gt_type = normalize_clause_type(gt.type)
            if extracted.type == gt_type:
                type_correct += 1

            # Boundary IoU (if paragraph info available)
            if gt.start_paragraph is not None and gt.end_paragraph is not None:
                paragraphs = document.metadata.get("paragraphs", [])
                extracted_para_idx = extracted.location.paragraph_index
                # Estimate end paragraph from extracted clause
                extracted_end_para = self._estimate_end_paragraph(
                    extracted, paragraphs
                )
                iou = calculate_boundary_iou(
                    extracted_para_idx,
                    extracted_end_para,
                    gt.start_paragraph,
                    gt.end_paragraph,
                )
                boundary_ious.append(iou)

        return ClauseDocumentResult(
            document_id=gt_doc.id,
            detection_tp=detection_tp,
            detection_fp=detection_fp,
            detection_fn=detection_fn,
            type_correct=type_correct,
            type_total=type_total,
            boundary_ious=boundary_ious,
            extracted_clauses=[
                {
                    "type": c.type.value,
                    "section_number": c.location.section_number,
                    "section_title": c.location.section_title,
                    "confidence": c.confidence,
                }
                for c in extracted_clauses
            ],
            ground_truth_clauses=[
                {
                    "type": c.type,
                    "section_number": c.section_number,
                    "title": c.title,
                }
                for c in gt_doc.clauses
            ],
        )

    def _match_clauses(
        self,
        extracted: list[Clause],
        ground_truth: list[GroundTruthClause],
    ) -> tuple[int, int, int, list[tuple[Clause, GroundTruthClause]]]:
        """Match extracted clauses against ground truth.

        Matching is based on section number (primary) or title similarity.

        Returns:
            Tuple of (true_positives, false_positives, false_negatives, matches)
            where matches is a list of (extracted, ground_truth) pairs.
        """
        matched_gt: set[int] = set()
        matched_extracted: set[int] = set()
        matches: list[tuple[Clause, GroundTruthClause]] = []

        # First pass: match by section number
        for i, ext in enumerate(extracted):
            ext_section = ext.location.section_number
            if not ext_section:
                continue

            for j, gt in enumerate(ground_truth):
                if j in matched_gt:
                    continue
                if gt.section_number and ext_section == gt.section_number:
                    matched_gt.add(j)
                    matched_extracted.add(i)
                    matches.append((ext, gt))
                    break

        # Second pass: match remaining by title similarity
        for i, ext in enumerate(extracted):
            if i in matched_extracted:
                continue
            ext_title = (ext.location.section_title or "").lower().strip()
            if not ext_title:
                continue

            for j, gt in enumerate(ground_truth):
                if j in matched_gt:
                    continue
                gt_title = (gt.title or "").lower().strip()
                if gt_title and ext_title in gt_title:
                    matched_gt.add(j)
                    matched_extracted.add(i)
                    matches.append((ext, gt))
                    break

        true_positives = len(matches)
        false_positives = len(extracted) - len(matched_extracted)
        false_negatives = len(ground_truth) - len(matched_gt)

        return true_positives, false_positives, false_negatives, matches

    def _estimate_end_paragraph(
        self, clause: Clause, paragraphs: list[dict]
    ) -> int:
        """Estimate the end paragraph index for a clause."""
        end_char = clause.location.end_char
        for i, para in enumerate(paragraphs):
            if para.get("end_char", 0) >= end_char:
                return i + 1
        return len(paragraphs)

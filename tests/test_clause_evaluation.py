"""Unit tests for clause evaluation."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

from graph_builder.models import Document, Clause, ClauseType, ClauseLocation
from graph_builder.evaluation.clause_dataset import (
    GroundTruthClause,
    GroundTruthContractDocument,
    load_clause_dataset,
)
from graph_builder.evaluation.clause_evaluator import (
    ClauseEvaluator,
    ClauseEvaluationResult,
    ClauseDocumentResult,
    calculate_boundary_iou,
    normalize_clause_type,
)


class TestGroundTruthModels:
    """Tests for ground truth clause models."""

    def test_ground_truth_clause_creation(self):
        """Test creating a ground truth clause."""
        clause = GroundTruthClause(
            type="DEFINITIONS",
            section_number="1",
            title="Definitions",
            start_paragraph=0,
            end_paragraph=5,
        )
        assert clause.type == "DEFINITIONS"
        assert clause.section_number == "1"
        assert clause.title == "Definitions"
        assert clause.start_paragraph == 0
        assert clause.end_paragraph == 5

    def test_ground_truth_clause_optional_fields(self):
        """Test that optional fields default to None."""
        clause = GroundTruthClause(type="OTHER")
        assert clause.section_number is None
        assert clause.title is None
        assert clause.start_paragraph is None
        assert clause.end_paragraph is None

    def test_ground_truth_document_creation(self):
        """Test creating a ground truth document."""
        doc = GroundTruthContractDocument(
            id="contract1",
            file="sample.docx",
            clauses=[
                GroundTruthClause(type="DEFINITIONS"),
                GroundTruthClause(type="CONFIDENTIALITY"),
            ],
        )
        assert doc.id == "contract1"
        assert doc.file == "sample.docx"
        assert len(doc.clauses) == 2


class TestLoadClauseDataset:
    """Tests for loading clause datasets from JSON."""

    def test_load_dataset(self, tmp_path):
        """Test loading a valid dataset file."""
        dataset_file = tmp_path / "dataset.json"
        dataset_file.write_text(
            """
            {
                "documents": [
                    {
                        "id": "doc1",
                        "file": "contract1.docx",
                        "clauses": [
                            {
                                "type": "DEFINITIONS",
                                "section_number": "1",
                                "title": "Definitions",
                                "start_paragraph": 0,
                                "end_paragraph": 5
                            },
                            {
                                "type": "CONFIDENTIALITY",
                                "section_number": "2"
                            }
                        ]
                    }
                ]
            }
            """
        )

        dataset = load_clause_dataset(dataset_file)

        assert len(dataset) == 1
        assert dataset[0].id == "doc1"
        assert dataset[0].file == "contract1.docx"
        assert len(dataset[0].clauses) == 2
        assert dataset[0].clauses[0].type == "DEFINITIONS"
        assert dataset[0].clauses[0].section_number == "1"
        assert dataset[0].clauses[1].type == "CONFIDENTIALITY"

    def test_load_dataset_missing_file(self, tmp_path):
        """Test that missing file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_clause_dataset(tmp_path / "nonexistent.json")

    def test_load_empty_dataset(self, tmp_path):
        """Test loading an empty dataset."""
        dataset_file = tmp_path / "empty.json"
        dataset_file.write_text('{"documents": []}')

        dataset = load_clause_dataset(dataset_file)
        assert dataset == []


class TestBoundaryIoU:
    """Tests for boundary IoU calculation."""

    def test_perfect_match(self):
        """Test IoU for perfect boundary match."""
        iou = calculate_boundary_iou(0, 5, 0, 5)
        assert iou == 1.0

    def test_no_overlap(self):
        """Test IoU for non-overlapping boundaries."""
        iou = calculate_boundary_iou(0, 5, 10, 15)
        assert iou == 0.0

    def test_partial_overlap(self):
        """Test IoU for partially overlapping boundaries."""
        # Extracted: [0, 6), Ground truth: [3, 9)
        # Intersection: [3, 6) = 3
        # Union: [0, 9) = 9
        iou = calculate_boundary_iou(0, 6, 3, 9)
        assert iou == pytest.approx(3 / 9)

    def test_extracted_contains_gt(self):
        """Test IoU when extracted contains ground truth."""
        # Extracted: [0, 10), Ground truth: [2, 8)
        # Intersection: [2, 8) = 6
        # Union: [0, 10) = 10
        iou = calculate_boundary_iou(0, 10, 2, 8)
        assert iou == pytest.approx(6 / 10)

    def test_gt_contains_extracted(self):
        """Test IoU when ground truth contains extracted."""
        # Extracted: [2, 8), Ground truth: [0, 10)
        # Intersection: [2, 8) = 6
        # Union: [0, 10) = 10
        iou = calculate_boundary_iou(2, 8, 0, 10)
        assert iou == pytest.approx(6 / 10)

    def test_zero_length_boundaries(self):
        """Test IoU with zero-length boundaries."""
        iou = calculate_boundary_iou(0, 0, 0, 0)
        assert iou == 1.0


class TestNormalizeClauseType:
    """Tests for clause type normalization."""

    def test_normalize_known_types(self):
        """Test normalizing known clause types."""
        assert normalize_clause_type("DEFINITIONS") == ClauseType.DEFINITIONS
        assert normalize_clause_type("CONFIDENTIALITY") == ClauseType.CONFIDENTIALITY
        assert normalize_clause_type("TERMINATION") == ClauseType.TERMINATION

    def test_normalize_case_insensitive(self):
        """Test that normalization is case-insensitive."""
        assert normalize_clause_type("definitions") == ClauseType.DEFINITIONS
        assert normalize_clause_type("Definitions") == ClauseType.DEFINITIONS

    def test_normalize_unknown_type(self):
        """Test that unknown types normalize to OTHER."""
        assert normalize_clause_type("UNKNOWN") == ClauseType.OTHER
        assert normalize_clause_type("RANDOM") == ClauseType.OTHER


class TestClauseDocumentResult:
    """Tests for ClauseDocumentResult dataclass."""

    def test_default_values(self):
        """Test default values for document result."""
        result = ClauseDocumentResult(document_id="doc1")
        assert result.document_id == "doc1"
        assert result.detection_tp == 0
        assert result.detection_fp == 0
        assert result.detection_fn == 0
        assert result.type_correct == 0
        assert result.type_total == 0
        assert result.boundary_ious == []


class TestClauseEvaluationResult:
    """Tests for ClauseEvaluationResult dataclass."""

    def test_to_dict_basic(self):
        """Test converting result to dictionary."""
        result = ClauseEvaluationResult(
            detection_precision=0.8,
            detection_recall=0.75,
            detection_f1=0.77,
            type_accuracy=0.9,
            mean_boundary_iou=0.85,
        )

        d = result.to_dict()

        assert d["detection_precision"] == 0.8
        assert d["detection_recall"] == 0.75
        assert d["detection_f1"] == 0.77
        assert d["type_accuracy"] == 0.9
        assert d["mean_boundary_iou"] == 0.85

    def test_to_dict_with_details(self):
        """Test converting result with details."""
        doc_result = ClauseDocumentResult(
            document_id="doc1",
            detection_tp=5,
            detection_fp=1,
            detection_fn=2,
            extracted_clauses=[{"type": "DEFINITIONS"}],
            ground_truth_clauses=[{"type": "DEFINITIONS"}],
        )
        result = ClauseEvaluationResult(
            detection_precision=0.8,
            detection_recall=0.7,
            detection_f1=0.75,
            type_accuracy=0.9,
            mean_boundary_iou=0.8,
            details={"doc1": doc_result},
        )

        d = result.to_dict(include_debug=False)
        assert "extracted_clauses" not in d["details"]["doc1"]

        d = result.to_dict(include_debug=True)
        assert "extracted_clauses" in d["details"]["doc1"]


class TestClauseEvaluator:
    """Tests for ClauseEvaluator class."""

    @pytest.fixture
    def mock_parser(self):
        """Create a mock document parser."""
        parser = MagicMock()
        doc = Document(
            content="1. Definitions\nTerms defined below.\n2. Confidentiality\nKeep secrets.",
            metadata={
                "paragraphs": [
                    {
                        "index": 0,
                        "text": "1. Definitions",
                        "is_heading": True,
                        "section_number": "1",
                        "start_char": 0,
                        "end_char": 14,
                    },
                    {
                        "index": 1,
                        "text": "Terms defined below.",
                        "is_heading": False,
                        "section_number": None,
                        "start_char": 15,
                        "end_char": 35,
                    },
                    {
                        "index": 2,
                        "text": "2. Confidentiality",
                        "is_heading": True,
                        "section_number": "2",
                        "start_char": 36,
                        "end_char": 54,
                    },
                    {
                        "index": 3,
                        "text": "Keep secrets.",
                        "is_heading": False,
                        "section_number": None,
                        "start_char": 55,
                        "end_char": 68,
                    },
                ],
            },
        )
        parser.parse.return_value = doc
        return parser

    @pytest.fixture
    def mock_extractor(self):
        """Create a mock clause extractor."""
        extractor = MagicMock()

        def extract(doc):
            return [
                Clause(
                    content="1. Definitions\nTerms defined below.",
                    type=ClauseType.DEFINITIONS,
                    location=ClauseLocation(
                        paragraph_index=0,
                        section_number="1",
                        section_title="Definitions",
                        start_char=0,
                        end_char=35,
                    ),
                    document_id=doc.id,
                ),
                Clause(
                    content="2. Confidentiality\nKeep secrets.",
                    type=ClauseType.CONFIDENTIALITY,
                    location=ClauseLocation(
                        paragraph_index=2,
                        section_number="2",
                        section_title="Confidentiality",
                        start_char=36,
                        end_char=68,
                    ),
                    document_id=doc.id,
                ),
            ]

        extractor.extract = extract
        return extractor

    def test_evaluate_perfect_match(self, mock_parser, mock_extractor, tmp_path):
        """Test evaluation with perfect extraction match."""
        # Create dummy file
        test_file = tmp_path / "test.docx"
        test_file.touch()

        dataset = [
            GroundTruthContractDocument(
                id="doc1",
                file="test.docx",
                clauses=[
                    GroundTruthClause(
                        type="DEFINITIONS",
                        section_number="1",
                        title="Definitions",
                    ),
                    GroundTruthClause(
                        type="CONFIDENTIALITY",
                        section_number="2",
                        title="Confidentiality",
                    ),
                ],
            )
        ]

        evaluator = ClauseEvaluator(mock_parser, mock_extractor, base_path=tmp_path)
        result = evaluator.evaluate(dataset)

        assert result.detection_precision == 1.0
        assert result.detection_recall == 1.0
        assert result.detection_f1 == 1.0
        assert result.type_accuracy == 1.0

    def test_evaluate_with_false_positives(self, mock_parser, mock_extractor, tmp_path):
        """Test evaluation when extractor finds extra clauses."""
        test_file = tmp_path / "test.docx"
        test_file.touch()

        # Ground truth has only one clause
        dataset = [
            GroundTruthContractDocument(
                id="doc1",
                file="test.docx",
                clauses=[
                    GroundTruthClause(
                        type="DEFINITIONS",
                        section_number="1",
                    ),
                ],
            )
        ]

        evaluator = ClauseEvaluator(mock_parser, mock_extractor, base_path=tmp_path)
        result = evaluator.evaluate(dataset)

        # 1 true positive, 1 false positive
        assert result.detection_precision == 0.5
        assert result.detection_recall == 1.0

    def test_evaluate_with_false_negatives(self, mock_parser, mock_extractor, tmp_path):
        """Test evaluation when extractor misses clauses."""
        test_file = tmp_path / "test.docx"
        test_file.touch()

        # Ground truth has extra clause not in extraction
        dataset = [
            GroundTruthContractDocument(
                id="doc1",
                file="test.docx",
                clauses=[
                    GroundTruthClause(type="DEFINITIONS", section_number="1"),
                    GroundTruthClause(type="CONFIDENTIALITY", section_number="2"),
                    GroundTruthClause(type="TERMINATION", section_number="3"),
                ],
            )
        ]

        evaluator = ClauseEvaluator(mock_parser, mock_extractor, base_path=tmp_path)
        result = evaluator.evaluate(dataset)

        # 2 true positives, 1 false negative
        assert result.detection_precision == 1.0
        assert result.detection_recall == pytest.approx(2 / 3)

    def test_evaluate_type_accuracy(self, mock_parser, tmp_path):
        """Test type accuracy calculation."""
        test_file = tmp_path / "test.docx"
        test_file.touch()

        # Create extractor that returns wrong type
        wrong_type_extractor = MagicMock()

        def extract_wrong(doc):
            return [
                Clause(
                    content="1. Definitions\nTerms defined below.",
                    type=ClauseType.OTHER,  # Wrong type!
                    location=ClauseLocation(
                        paragraph_index=0,
                        section_number="1",
                        section_title="Definitions",
                        start_char=0,
                        end_char=35,
                    ),
                    document_id=doc.id,
                ),
            ]

        wrong_type_extractor.extract = extract_wrong

        dataset = [
            GroundTruthContractDocument(
                id="doc1",
                file="test.docx",
                clauses=[
                    GroundTruthClause(
                        type="DEFINITIONS",
                        section_number="1",
                    ),
                ],
            )
        ]

        evaluator = ClauseEvaluator(mock_parser, wrong_type_extractor, base_path=tmp_path)
        result = evaluator.evaluate(dataset)

        # Clause detected but type is wrong
        assert result.detection_precision == 1.0
        assert result.type_accuracy == 0.0

    def test_match_by_section_number(self, mock_parser, mock_extractor, tmp_path):
        """Test that clauses are matched by section number."""
        test_file = tmp_path / "test.docx"
        test_file.touch()

        dataset = [
            GroundTruthContractDocument(
                id="doc1",
                file="test.docx",
                clauses=[
                    GroundTruthClause(
                        type="DEFINITIONS",
                        section_number="1",
                        # No title provided
                    ),
                ],
            )
        ]

        evaluator = ClauseEvaluator(mock_parser, mock_extractor, base_path=tmp_path)
        result = evaluator.evaluate(dataset)

        # Should match by section number
        assert result.details["doc1"].detection_tp == 1

    def test_match_by_title(self, mock_parser, tmp_path):
        """Test that clauses can be matched by title."""
        test_file = tmp_path / "test.docx"
        test_file.touch()

        # Extractor returns clause without section number
        title_extractor = MagicMock()

        def extract_no_section(doc):
            return [
                Clause(
                    content="Definitions\nTerms defined.",
                    type=ClauseType.DEFINITIONS,
                    location=ClauseLocation(
                        paragraph_index=0,
                        section_number=None,  # No section number
                        section_title="Definitions",
                        start_char=0,
                        end_char=30,
                    ),
                    document_id=doc.id,
                ),
            ]

        title_extractor.extract = extract_no_section

        dataset = [
            GroundTruthContractDocument(
                id="doc1",
                file="test.docx",
                clauses=[
                    GroundTruthClause(
                        type="DEFINITIONS",
                        section_number=None,  # No section number in GT either
                        title="Definitions",
                    ),
                ],
            )
        ]

        evaluator = ClauseEvaluator(mock_parser, title_extractor, base_path=tmp_path)
        result = evaluator.evaluate(dataset)

        # Should match by title
        assert result.details["doc1"].detection_tp == 1

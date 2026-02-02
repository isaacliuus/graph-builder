"""Unit tests for evaluation module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from graph_builder.evaluation import (
    Evaluator,
    EvaluationResult,
    GroundTruthDocument,
    GroundTruthEntity,
    GroundTruthRelationship,
    f1_score,
    load_dataset,
    precision,
    recall,
)
from graph_builder.models.entity import Entity, EntityType
from graph_builder.models.relationship import Relationship, RelationshipType


class TestMetrics:
    def test_precision_basic(self):
        assert precision(8, 2) == 0.8

    def test_precision_perfect(self):
        assert precision(10, 0) == 1.0

    def test_precision_zero(self):
        assert precision(0, 10) == 0.0

    def test_precision_no_predictions(self):
        assert precision(0, 0) == 0.0

    def test_recall_basic(self):
        assert recall(8, 2) == 0.8

    def test_recall_perfect(self):
        assert recall(10, 0) == 1.0

    def test_recall_zero(self):
        assert recall(0, 10) == 0.0

    def test_recall_no_ground_truth(self):
        assert recall(0, 0) == 0.0

    def test_f1_score_basic(self):
        # precision=0.8, recall=0.8 -> F1=0.8
        assert abs(f1_score(0.8, 0.8) - 0.8) < 0.0001

    def test_f1_score_perfect(self):
        assert f1_score(1.0, 1.0) == 1.0

    def test_f1_score_zero(self):
        assert f1_score(0.0, 0.0) == 0.0

    def test_f1_score_unbalanced(self):
        # precision=1.0, recall=0.5 -> F1=0.667
        result = f1_score(1.0, 0.5)
        assert abs(result - 0.6667) < 0.001


class TestDataset:
    def test_load_dataset(self):
        data = {
            "documents": [
                {
                    "id": "doc1",
                    "content": "Test content",
                    "entities": [{"name": "Test", "type": "ORG"}],
                    "relationships": [
                        {"source": "A", "target": "B", "type": "RELATED_TO"}
                    ],
                }
            ]
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            temp_path = Path(f.name)

        try:
            dataset = load_dataset(temp_path)
            assert len(dataset) == 1
            assert dataset[0].id == "doc1"
            assert dataset[0].content == "Test content"
            assert len(dataset[0].entities) == 1
            assert dataset[0].entities[0].name == "Test"
            assert dataset[0].entities[0].type == "ORG"
            assert len(dataset[0].relationships) == 1
            assert dataset[0].relationships[0].source == "A"
        finally:
            temp_path.unlink()

    def test_load_dataset_empty(self):
        data = {"documents": []}

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump(data, f)
            temp_path = Path(f.name)

        try:
            dataset = load_dataset(temp_path)
            assert len(dataset) == 0
        finally:
            temp_path.unlink()

    def test_load_dataset_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_dataset(Path("/nonexistent/path.json"))


class TestEvaluator:
    @pytest.fixture
    def mock_entity_extractor(self):
        extractor = MagicMock()
        return extractor

    @pytest.fixture
    def mock_rel_extractor(self):
        extractor = MagicMock()
        return extractor

    @pytest.fixture
    def sample_gt_document(self):
        return GroundTruthDocument(
            id="doc1",
            content="Apple Inc. was founded by Steve Jobs.",
            entities=[
                GroundTruthEntity(name="Apple Inc.", type="ORG"),
                GroundTruthEntity(name="Steve Jobs", type="PERSON"),
            ],
            relationships=[
                GroundTruthRelationship(
                    source="Steve Jobs", target="Apple Inc.", type="FOUNDED"
                )
            ],
        )

    def test_evaluate_perfect_entities(
        self, mock_entity_extractor, mock_rel_extractor, sample_gt_document
    ):
        # Setup mock to return perfect entity matches
        entity1 = Entity(name="Apple Inc.", type=EntityType.ORGANIZATION)
        entity2 = Entity(name="Steve Jobs", type=EntityType.PERSON)
        mock_entity_extractor.extract.return_value = [entity1, entity2]
        mock_rel_extractor.extract.return_value = []

        evaluator = Evaluator(mock_entity_extractor, mock_rel_extractor)
        result = evaluator.evaluate([sample_gt_document])

        assert result.entity_precision == 1.0
        assert result.entity_recall == 1.0
        assert result.entity_f1 == 1.0

    def test_evaluate_partial_entities(
        self, mock_entity_extractor, mock_rel_extractor, sample_gt_document
    ):
        # Setup mock to return only one matching entity
        entity1 = Entity(name="Apple Inc.", type=EntityType.ORGANIZATION)
        mock_entity_extractor.extract.return_value = [entity1]
        mock_rel_extractor.extract.return_value = []

        evaluator = Evaluator(mock_entity_extractor, mock_rel_extractor)
        result = evaluator.evaluate([sample_gt_document])

        assert result.entity_precision == 1.0  # 1/1
        assert result.entity_recall == 0.5  # 1/2
        assert abs(result.entity_f1 - 0.6667) < 0.001

    def test_evaluate_with_false_positives(
        self, mock_entity_extractor, mock_rel_extractor, sample_gt_document
    ):
        # Setup mock to return extra entities
        entity1 = Entity(name="Apple Inc.", type=EntityType.ORGANIZATION)
        entity2 = Entity(name="Steve Jobs", type=EntityType.PERSON)
        entity3 = Entity(name="Cupertino", type=EntityType.LOCATION)  # Extra
        mock_entity_extractor.extract.return_value = [entity1, entity2, entity3]
        mock_rel_extractor.extract.return_value = []

        evaluator = Evaluator(mock_entity_extractor, mock_rel_extractor)
        result = evaluator.evaluate([sample_gt_document])

        assert abs(result.entity_precision - 0.6667) < 0.001  # 2/3
        assert result.entity_recall == 1.0  # 2/2
        assert result.entity_f1 == 0.8  # 2 * (0.667 * 1.0) / (0.667 + 1.0)

    def test_evaluate_relationships(
        self, mock_entity_extractor, mock_rel_extractor, sample_gt_document
    ):
        # Setup entities
        entity1 = Entity(name="Apple Inc.", type=EntityType.ORGANIZATION)
        entity2 = Entity(name="Steve Jobs", type=EntityType.PERSON)
        mock_entity_extractor.extract.return_value = [entity1, entity2]

        # Setup relationship
        rel = Relationship(
            source_id=entity2.id,
            target_id=entity1.id,
            type=RelationshipType.FOUNDED,
        )
        mock_rel_extractor.extract.return_value = [rel]

        evaluator = Evaluator(mock_entity_extractor, mock_rel_extractor)
        result = evaluator.evaluate([sample_gt_document])

        assert result.relationship_precision == 1.0
        assert result.relationship_recall == 1.0
        assert result.relationship_f1 == 1.0

    def test_evaluate_no_extracted(
        self, mock_entity_extractor, mock_rel_extractor, sample_gt_document
    ):
        mock_entity_extractor.extract.return_value = []
        mock_rel_extractor.extract.return_value = []

        evaluator = Evaluator(mock_entity_extractor, mock_rel_extractor)
        result = evaluator.evaluate([sample_gt_document])

        assert result.entity_precision == 0.0
        assert result.entity_recall == 0.0
        assert result.entity_f1 == 0.0

    def test_evaluate_empty_dataset(
        self, mock_entity_extractor, mock_rel_extractor
    ):
        evaluator = Evaluator(mock_entity_extractor, mock_rel_extractor)
        result = evaluator.evaluate([])

        assert result.entity_precision == 0.0
        assert result.entity_recall == 0.0
        assert result.entity_f1 == 0.0

    def test_evaluation_result_to_dict(self):
        result = EvaluationResult(
            entity_precision=0.8,
            entity_recall=0.9,
            entity_f1=0.85,
            relationship_precision=0.7,
            relationship_recall=0.6,
            relationship_f1=0.65,
        )
        result_dict = result.to_dict()

        assert result_dict["entity_precision"] == 0.8
        assert result_dict["entity_recall"] == 0.9
        assert result_dict["entity_f1"] == 0.85
        assert result_dict["relationship_precision"] == 0.7
        assert result_dict["relationship_recall"] == 0.6
        assert result_dict["relationship_f1"] == 0.65

    def test_entity_type_normalization(
        self, mock_entity_extractor, mock_rel_extractor
    ):
        # Test that different type formats match correctly
        gt_doc = GroundTruthDocument(
            id="doc1",
            content="Test",
            entities=[
                GroundTruthEntity(name="Test Org", type="ORGANIZATION"),
                GroundTruthEntity(name="Test Loc", type="LOCATION"),
            ],
            relationships=[],
        )

        # Extractor returns ORG and LOC (short forms)
        entity1 = Entity(name="Test Org", type=EntityType.ORGANIZATION)
        entity2 = Entity(name="Test Loc", type=EntityType.LOCATION)
        mock_entity_extractor.extract.return_value = [entity1, entity2]
        mock_rel_extractor.extract.return_value = []

        evaluator = Evaluator(mock_entity_extractor, mock_rel_extractor)
        result = evaluator.evaluate([gt_doc])

        assert result.entity_precision == 1.0
        assert result.entity_recall == 1.0


def _spacy_model_installed() -> bool:
    """Check if spaCy model is installed."""
    try:
        import spacy
        spacy.load("en_core_web_sm")
        return True
    except OSError:
        return False


class TestEvaluatorIntegration:
    """Integration tests using real spaCy extractor."""

    @pytest.fixture
    def spacy_extractors(self):
        from graph_builder.extraction import (
            SpacyEntityExtractor,
            SpacyRelationshipExtractor,
        )
        return SpacyEntityExtractor(), SpacyRelationshipExtractor()

    @pytest.mark.skipif(not _spacy_model_installed(), reason="spaCy model not installed")
    def test_evaluate_with_spacy(self, spacy_extractors):
        entity_extractor, rel_extractor = spacy_extractors

        dataset = [
            GroundTruthDocument(
                id="doc1",
                content="Apple Inc. was founded by Steve Jobs in Cupertino.",
                entities=[
                    GroundTruthEntity(name="Apple Inc.", type="ORG"),
                    GroundTruthEntity(name="Steve Jobs", type="PERSON"),
                    GroundTruthEntity(name="Cupertino", type="LOC"),
                ],
                relationships=[],
            )
        ]

        evaluator = Evaluator(entity_extractor, rel_extractor)
        result = evaluator.evaluate(dataset)

        # spaCy should find at least some entities
        assert result.entity_recall > 0
        assert isinstance(result.entity_precision, float)
        assert isinstance(result.entity_f1, float)

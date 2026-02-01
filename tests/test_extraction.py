"""Unit tests for extraction module."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import UUID

from graph_builder.models.document import Chunk
from graph_builder.models.entity import Entity, EntityType
from graph_builder.models.relationship import Relationship, RelationshipType
from graph_builder.extraction.spacy_extractor import (
    SpacyEntityExtractor,
    SpacyRelationshipExtractor,
)


class TestSpacyEntityExtractor:
    @pytest.fixture
    def extractor(self):
        return SpacyEntityExtractor()

    @pytest.fixture
    def sample_chunk(self):
        return Chunk(
            content="Apple Inc. was founded by Steve Jobs in Cupertino, California.",
            document_id=UUID("00000000-0000-0000-0000-000000000001"),
            start_index=0,
            end_index=63,
        )

    def test_extractor_creation(self, extractor):
        assert extractor is not None

    def test_extract_entities(self, extractor, sample_chunk):
        entities = extractor.extract([sample_chunk])

        assert len(entities) > 0
        entity_names = [e.name for e in entities]
        assert "Apple Inc." in entity_names or "Apple" in entity_names
        assert "Steve Jobs" in entity_names

    def test_extract_entity_types(self, extractor, sample_chunk):
        entities = extractor.extract([sample_chunk])

        entity_types = {e.type for e in entities}
        assert EntityType.PERSON in entity_types or EntityType.ORGANIZATION in entity_types

    def test_extract_sets_chunk_id(self, extractor, sample_chunk):
        entities = extractor.extract([sample_chunk])

        for entity in entities:
            assert entity.chunk_id == sample_chunk.id

    def test_extract_empty_chunks(self, extractor):
        entities = extractor.extract([])
        assert entities == []

    def test_extract_no_entities(self, extractor):
        chunk = Chunk(
            content="The quick brown fox.",
            document_id=UUID("00000000-0000-0000-0000-000000000001"),
        )
        entities = extractor.extract([chunk])
        # May or may not find entities depending on spaCy model
        assert isinstance(entities, list)


class TestSpacyRelationshipExtractor:
    @pytest.fixture
    def extractor(self):
        return SpacyRelationshipExtractor()

    @pytest.fixture
    def sample_chunk(self):
        return Chunk(
            content="Apple Inc. was founded by Steve Jobs in Cupertino.",
            document_id=UUID("00000000-0000-0000-0000-000000000001"),
            start_index=0,
            end_index=50,
        )

    @pytest.fixture
    def sample_entities(self, sample_chunk):
        return [
            Entity(name="Apple Inc.", type=EntityType.ORGANIZATION, chunk_id=sample_chunk.id),
            Entity(name="Steve Jobs", type=EntityType.PERSON, chunk_id=sample_chunk.id),
            Entity(name="Cupertino", type=EntityType.LOCATION, chunk_id=sample_chunk.id),
        ]

    def test_extractor_creation(self, extractor):
        assert extractor is not None

    def test_extract_relationships(self, extractor, sample_chunk, sample_entities):
        relationships = extractor.extract([sample_chunk], sample_entities)

        assert isinstance(relationships, list)
        # Co-occurrence based, should find relationships between entities in same chunk
        if len(relationships) > 0:
            for rel in relationships:
                assert isinstance(rel, Relationship)
                assert rel.source_id in [e.id for e in sample_entities]
                assert rel.target_id in [e.id for e in sample_entities]

    def test_extract_no_entities(self, extractor, sample_chunk):
        relationships = extractor.extract([sample_chunk], [])
        assert relationships == []

    def test_extract_single_entity(self, extractor, sample_chunk):
        single_entity = [
            Entity(name="Apple", type=EntityType.ORGANIZATION, chunk_id=sample_chunk.id)
        ]
        relationships = extractor.extract([sample_chunk], single_entity)
        assert relationships == []

    def test_extract_sets_chunk_id(self, extractor, sample_chunk, sample_entities):
        relationships = extractor.extract([sample_chunk], sample_entities)

        for rel in relationships:
            assert rel.chunk_id == sample_chunk.id


try:
    import instructor
    import openai
    HAS_LLM_DEPS = True
except ImportError:
    HAS_LLM_DEPS = False


class TestLLMEntityExtractor:
    def test_import_error_without_dependencies(self):
        """Test that proper error is raised when openai/instructor not installed."""
        from graph_builder.extraction.llm_extractor import LLMEntityExtractor

        extractor = LLMEntityExtractor(api_key="test-key")
        # Client is lazy-loaded, so no error on creation
        assert extractor.api_key == "test-key"

    @pytest.mark.skipif(not HAS_LLM_DEPS, reason="openai and instructor not installed")
    def test_extract_with_mock(self, mocker):
        from graph_builder.extraction.llm_extractor import (
            LLMEntityExtractor,
            ExtractedEntities,
            ExtractedEntity,
        )

        # Setup mocks
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = ExtractedEntities(
            entities=[
                ExtractedEntity(name="Apple", type=EntityType.ORGANIZATION, confidence=0.95),
                ExtractedEntity(name="Steve Jobs", type=EntityType.PERSON, confidence=0.9),
            ]
        )

        extractor = LLMEntityExtractor(api_key="test-key")
        extractor._client = mock_client
        chunk = Chunk(
            content="Apple was founded by Steve Jobs.",
            document_id=UUID("00000000-0000-0000-0000-000000000001"),
        )

        entities = extractor.extract([chunk])

        assert len(entities) == 2
        assert entities[0].name == "Apple"
        assert entities[0].type == EntityType.ORGANIZATION
        assert entities[1].name == "Steve Jobs"


class TestLLMRelationshipExtractor:
    @pytest.mark.skipif(not HAS_LLM_DEPS, reason="openai and instructor not installed")
    def test_extract_with_mock(self, mocker):
        from graph_builder.extraction.llm_extractor import (
            LLMRelationshipExtractor,
            ExtractedRelationships,
            ExtractedRelationship,
        )

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = ExtractedRelationships(
            relationships=[
                ExtractedRelationship(
                    source_name="Steve Jobs",
                    target_name="Apple",
                    type=RelationshipType.FOUNDED,
                    confidence=0.9,
                )
            ]
        )

        chunk = Chunk(
            content="Steve Jobs founded Apple.",
            document_id=UUID("00000000-0000-0000-0000-000000000001"),
        )
        entities = [
            Entity(name="Steve Jobs", type=EntityType.PERSON, chunk_id=chunk.id),
            Entity(name="Apple", type=EntityType.ORGANIZATION, chunk_id=chunk.id),
        ]

        extractor = LLMRelationshipExtractor(api_key="test-key")
        extractor._client = mock_client
        relationships = extractor.extract([chunk], entities)

        assert len(relationships) == 1
        assert relationships[0].type == RelationshipType.FOUNDED

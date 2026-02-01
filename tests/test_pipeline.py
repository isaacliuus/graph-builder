"""Integration tests for the pipeline."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from uuid import UUID

from graph_builder.models.document import Document, Chunk
from graph_builder.models.entity import Entity, EntityType
from graph_builder.models.relationship import Relationship, RelationshipType
from graph_builder.models.graph import KnowledgeGraph
from graph_builder.pipeline.base import PipelineContext
from graph_builder.pipeline.pipeline import Pipeline
from graph_builder.pipeline.builder import PipelineBuilder


class TestPipelineContext:
    def test_context_creation(self):
        docs = [Document(content="Test")]
        ctx = PipelineContext(documents=docs)

        assert ctx.documents == docs
        assert ctx.chunks == []
        assert ctx.entities == []
        assert ctx.relationships == []
        assert ctx.graph is not None  # default_factory creates empty KnowledgeGraph


class TestPipeline:
    @pytest.fixture
    def mock_chunker(self):
        chunker = Mock()
        chunker.chunk.return_value = [
            Chunk(
                content="Test chunk",
                document_id=UUID("00000000-0000-0000-0000-000000000001"),
            )
        ]
        return chunker

    @pytest.fixture
    def mock_entity_extractor(self):
        extractor = Mock()
        extractor.extract.return_value = [
            Entity(name="Apple", type=EntityType.ORGANIZATION),
            Entity(name="Steve Jobs", type=EntityType.PERSON),
        ]
        return extractor

    @pytest.fixture
    def mock_relationship_extractor(self):
        extractor = Mock()
        extractor.extract.return_value = []
        return extractor

    @pytest.fixture
    def mock_graph_builder(self):
        builder = Mock()
        builder.build.return_value = KnowledgeGraph()
        return builder

    def test_pipeline_creation(
        self,
        mock_chunker,
        mock_entity_extractor,
        mock_relationship_extractor,
        mock_graph_builder,
    ):
        pipeline = Pipeline(
            chunker=mock_chunker,
            entity_extractor=mock_entity_extractor,
            relationship_extractor=mock_relationship_extractor,
            graph_builder=mock_graph_builder,
        )
        assert pipeline is not None

    def test_pipeline_run(
        self,
        mock_chunker,
        mock_entity_extractor,
        mock_relationship_extractor,
        mock_graph_builder,
    ):
        pipeline = Pipeline(
            chunker=mock_chunker,
            entity_extractor=mock_entity_extractor,
            relationship_extractor=mock_relationship_extractor,
            graph_builder=mock_graph_builder,
        )

        docs = [Document(content="Apple was founded by Steve Jobs.")]
        graph = pipeline.run(docs)

        assert isinstance(graph, KnowledgeGraph)
        mock_chunker.chunk.assert_called_once()
        mock_entity_extractor.extract.assert_called_once()
        mock_relationship_extractor.extract.assert_called_once()
        mock_graph_builder.build.assert_called_once()

    def test_pipeline_run_with_context(
        self,
        mock_chunker,
        mock_entity_extractor,
        mock_relationship_extractor,
        mock_graph_builder,
    ):
        pipeline = Pipeline(
            chunker=mock_chunker,
            entity_extractor=mock_entity_extractor,
            relationship_extractor=mock_relationship_extractor,
            graph_builder=mock_graph_builder,
        )

        docs = [Document(content="Test content")]
        context = pipeline.run_with_context(docs)

        assert isinstance(context, PipelineContext)
        assert len(context.chunks) > 0
        assert len(context.entities) > 0
        assert context.graph is not None


class TestPipelineBuilder:
    def test_builder_creation(self):
        builder = PipelineBuilder()
        assert builder is not None

    def test_builder_missing_chunker(self):
        builder = PipelineBuilder()
        builder._entity_extractor = Mock()
        builder._relationship_extractor = Mock()
        builder._graph_builder = Mock()

        with pytest.raises(ValueError, match="Chunker is required"):
            builder.build()

    def test_builder_missing_entity_extractor(self):
        builder = PipelineBuilder()
        builder._chunker = Mock()
        builder._relationship_extractor = Mock()
        builder._graph_builder = Mock()

        with pytest.raises(ValueError, match="Entity extractor is required"):
            builder.build()

    def test_builder_fluent_api(self):
        chunker = Mock()
        entity_ext = Mock()
        rel_ext = Mock()
        graph_builder = Mock()

        pipeline = (
            PipelineBuilder()
            .with_chunker(chunker)
            .with_entity_extractor(entity_ext)
            .with_relationship_extractor(rel_ext)
            .with_graph_builder(graph_builder)
            .build()
        )

        assert isinstance(pipeline, Pipeline)

    def test_default_pipeline(self):
        pipeline = PipelineBuilder.default()

        assert isinstance(pipeline, Pipeline)
        assert pipeline.chunker is not None
        assert pipeline.entity_extractor is not None
        assert pipeline.relationship_extractor is not None
        assert pipeline.graph_builder is not None

    @patch("graph_builder.extraction.llm_extractor.LLMEntityExtractor")
    @patch("graph_builder.extraction.llm_extractor.LLMRelationshipExtractor")
    def test_llm_pipeline(self, mock_rel_ext, mock_entity_ext):
        mock_entity_ext.return_value = Mock()
        mock_rel_ext.return_value = Mock()

        # Import after patching
        from graph_builder.pipeline.builder import PipelineBuilder as PB

        pipeline = PB.with_llm(api_key="test-key", model="gpt-4")

        assert isinstance(pipeline, Pipeline)


class TestPipelineIntegration:
    """End-to-end integration tests using real components."""

    def test_full_pipeline_with_spacy(self):
        """Test the full pipeline with spaCy extraction."""
        pipeline = PipelineBuilder.default()

        docs = [
            Document(
                content="Apple Inc. was founded by Steve Jobs in Cupertino, California.",
                source="test.txt",
            )
        ]

        context = pipeline.run_with_context(docs)

        # Verify chunks were created
        assert len(context.chunks) >= 1

        # Verify entities were extracted
        assert len(context.entities) >= 2
        entity_names = [e.name.lower() for e in context.entities]
        assert any("apple" in name for name in entity_names)
        assert any("steve jobs" in name for name in entity_names)

        # Verify graph was built
        assert context.graph is not None
        assert context.graph.node_count >= 2

    def test_pipeline_with_multiple_documents(self):
        """Test pipeline with multiple input documents."""
        pipeline = PipelineBuilder.default()

        docs = [
            Document(content="Apple was founded by Steve Jobs.", source="doc1.txt"),
            Document(content="Microsoft was founded by Bill Gates.", source="doc2.txt"),
        ]

        context = pipeline.run_with_context(docs)

        # Should have entities from both documents
        entity_names = [e.name.lower() for e in context.entities]
        assert any("apple" in name or "steve" in name for name in entity_names)
        assert any("microsoft" in name or "bill" in name for name in entity_names)

    def test_pipeline_preserves_entity_chunk_mapping(self):
        """Test that entities are properly linked to their source chunks."""
        pipeline = PipelineBuilder.default()

        docs = [Document(content="Steve Jobs founded Apple in Cupertino.")]
        context = pipeline.run_with_context(docs)

        for entity in context.entities:
            assert entity.chunk_id is not None
            # Verify the chunk_id references an actual chunk
            chunk_ids = [c.id for c in context.chunks]
            assert entity.chunk_id in chunk_ids

    def test_pipeline_entity_deduplication(self):
        """Test that duplicate entities are properly deduplicated in the graph."""
        pipeline = PipelineBuilder.default()

        # Text that mentions "Apple" multiple times
        docs = [
            Document(
                content="Apple released the iPhone. Apple is headquartered in Cupertino. Apple was founded by Steve Jobs."
            )
        ]

        context = pipeline.run_with_context(docs)

        # Graph should deduplicate "Apple" entries
        apple_nodes = [
            n for n in context.graph.nodes.values()
            if "apple" in n.canonical_name
        ]
        assert len(apple_nodes) <= 2  # At most Apple Inc. and Apple (product references)

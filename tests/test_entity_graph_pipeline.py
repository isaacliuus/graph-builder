"""Tests for EntityGraphPipeline."""

from pathlib import Path
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from graph_builder.models.document import Document, Chunk
from graph_builder.models.entity import Entity, EntityType
from graph_builder.models.graph import KnowledgeGraph
from graph_builder.pipeline.entity_graph_pipeline import EntityGraphPipeline

try:
    import rapidfuzz  # noqa: F401
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

pytestmark = pytest.mark.skipif(not HAS_RAPIDFUZZ, reason="rapidfuzz not installed")


def _make_pipeline(graphdb=None):
    chunk_id_1 = uuid4()
    chunk_id_2 = uuid4()

    chunks = [
        Chunk(id=chunk_id_1, content="Alice and Bob work together.", document_id=uuid4()),
        Chunk(id=chunk_id_2, content="Alice and Charlie are friends.", document_id=uuid4()),
    ]

    raw_entities = [
        Entity(name="Alice", type=EntityType.PERSON, confidence=0.9, chunk_id=chunk_id_1),
        Entity(name="Bob", type=EntityType.PERSON, confidence=0.8, chunk_id=chunk_id_1),
        Entity(name="Alice", type=EntityType.PERSON, confidence=0.95, chunk_id=chunk_id_2),
        Entity(name="Charlie", type=EntityType.PERSON, confidence=0.7, chunk_id=chunk_id_2),
    ]

    # Mocks
    chunker = MagicMock()
    chunker.chunk.return_value = chunks

    entity_extractor = MagicMock()
    entity_extractor.extract.return_value = raw_entities

    from graph_builder.merging.fuzzy_merger import FuzzyEntityMerger
    from graph_builder.graph.networkx_builder import NetworkXGraphBuilder

    merger = FuzzyEntityMerger(threshold=85.0)
    graph_builder = NetworkXGraphBuilder(deduplicate=False)

    pipeline = EntityGraphPipeline(
        chunker=chunker,
        entity_extractor=entity_extractor,
        entity_merger=merger,
        graph_builder=graph_builder,
        graphdb=graphdb,
    )

    return pipeline


class TestEntityGraphPipeline:
    def test_full_run(self):
        pipeline = _make_pipeline()
        docs = [Document(content="test")]

        graph = pipeline.run(docs)

        assert isinstance(graph, KnowledgeGraph)
        # Alice should be merged into one entity, so 3 unique entities
        assert len(graph.nodes) == 3

    def test_run_with_context_has_metadata(self):
        pipeline = _make_pipeline()
        docs = [Document(content="test")]

        context = pipeline.run_with_context(docs)

        assert "merge_stats" in context.metadata
        stats = context.metadata["merge_stats"]
        assert stats["raw_entity_count"] == 4
        assert stats["merged_entity_count"] == 3
        assert stats["entities_reduced"] == 1
        assert stats["relationship_count"] > 0

    def test_cooccurrence_relationships_created(self):
        pipeline = _make_pipeline()
        docs = [Document(content="test")]

        context = pipeline.run_with_context(docs)

        # Alice-Bob (chunk1), Alice-Charlie (chunk2) = 2 relationships
        assert len(context.relationships) == 2

    def test_graphdb_sync_called(self):
        graphdb = MagicMock()
        pipeline = _make_pipeline(graphdb=graphdb)
        docs = [Document(content="test")]

        pipeline.run(docs)

        graphdb.sync.assert_called_once()

    def test_graphdb_not_called_when_none(self):
        pipeline = _make_pipeline(graphdb=None)
        docs = [Document(content="test")]

        # Should not raise
        pipeline.run(docs)

    def test_run_from_files_with_parser(self):
        pipeline = _make_pipeline()

        # Mock parser
        parsed_doc = Document(content="Parsed contract content.")
        parser = MagicMock()
        parser.parse.return_value = parsed_doc
        pipeline.parser = parser

        file_paths = [Path("contract.pdf")]
        graph = pipeline.run_from_files(file_paths)

        parser.parse.assert_called_once_with(Path("contract.pdf"))
        assert isinstance(graph, KnowledgeGraph)

    def test_run_from_files_without_parser_raises(self):
        pipeline = _make_pipeline()

        with pytest.raises(ValueError, match="No parser configured"):
            pipeline.run_from_files([Path("contract.pdf")])

    def test_clause_stats_in_metadata(self):
        pipeline = _make_pipeline()

        # Override chunker to return chunks with clause metadata
        chunk_id = uuid4()
        chunks_with_clause_meta = [
            Chunk(
                id=chunk_id,
                content="Some clause content.",
                document_id=uuid4(),
                metadata={"clause_type": "CONFIDENTIALITY"},
            ),
        ]
        pipeline.chunker.chunk.return_value = chunks_with_clause_meta

        # Override entity extractor for these chunks
        pipeline.entity_extractor.extract.return_value = [
            Entity(name="Alice", type=EntityType.PERSON, confidence=0.9, chunk_id=chunk_id),
        ]

        docs = [Document(content="test")]
        context = pipeline.run_with_context(docs)

        assert "clause_stats" in context.metadata
        assert context.metadata["clause_stats"]["clause_count"] == 1
        assert context.metadata["clause_stats"]["clause_types"]["CONFIDENTIALITY"] == 1

"""Unit tests for data models."""

import pytest
from uuid import UUID

from graph_builder.models.document import Document, Chunk
from graph_builder.models.entity import Entity, EntityType
from graph_builder.models.relationship import Relationship, RelationshipType
from graph_builder.models.graph import KnowledgeGraph, GraphNode, GraphEdge


class TestDocument:
    def test_document_creation(self):
        doc = Document(content="Test content", source="test.txt")
        assert doc.content == "Test content"
        assert doc.source == "test.txt"
        assert isinstance(doc.id, UUID)

    def test_document_default_source(self):
        doc = Document(content="Test")
        assert doc.source == ""

    def test_document_metadata(self):
        doc = Document(content="Test", metadata={"key": "value"})
        assert doc.metadata == {"key": "value"}


class TestChunk:
    def test_chunk_creation(self):
        doc = Document(content="Full content")
        chunk = Chunk(
            content="Partial",
            document_id=doc.id,
            start_index=0,
            end_index=7,
        )
        assert chunk.content == "Partial"
        assert chunk.document_id == doc.id
        assert chunk.start_index == 0
        assert chunk.end_index == 7

    def test_chunk_has_unique_id(self):
        chunk1 = Chunk(content="A", document_id=UUID("00000000-0000-0000-0000-000000000001"))
        chunk2 = Chunk(content="B", document_id=UUID("00000000-0000-0000-0000-000000000001"))
        assert chunk1.id != chunk2.id


class TestEntity:
    def test_entity_creation(self):
        entity = Entity(name="Apple Inc.", type=EntityType.ORGANIZATION)
        assert entity.name == "Apple Inc."
        assert entity.type == EntityType.ORGANIZATION
        assert entity.confidence == 1.0
        assert isinstance(entity.id, UUID)

    def test_entity_canonical_name(self):
        entity = Entity(name="  Steve Jobs  ", type=EntityType.PERSON)
        assert entity.canonical_name == "steve jobs"

    def test_entity_types(self):
        assert EntityType.PERSON.value == "PERSON"
        assert EntityType.ORGANIZATION.value == "ORG"
        assert EntityType.LOCATION.value == "LOC"
        assert EntityType.DATE.value == "DATE"

    def test_entity_with_chunk_id(self):
        chunk_id = UUID("00000000-0000-0000-0000-000000000001")
        entity = Entity(name="Test", type=EntityType.OTHER, chunk_id=chunk_id)
        assert entity.chunk_id == chunk_id


class TestRelationship:
    def test_relationship_creation(self):
        source_id = UUID("00000000-0000-0000-0000-000000000001")
        target_id = UUID("00000000-0000-0000-0000-000000000002")
        rel = Relationship(
            source_id=source_id,
            target_id=target_id,
            type=RelationshipType.WORKS_FOR,
        )
        assert rel.source_id == source_id
        assert rel.target_id == target_id
        assert rel.type == RelationshipType.WORKS_FOR
        assert rel.weight == 1.0
        assert rel.confidence == 1.0

    def test_relationship_types(self):
        assert RelationshipType.WORKS_FOR.value == "WORKS_FOR"
        assert RelationshipType.FOUNDED.value == "FOUNDED"
        assert RelationshipType.LOCATED_IN.value == "LOCATED_IN"

    def test_relationship_with_description(self):
        rel = Relationship(
            source_id=UUID("00000000-0000-0000-0000-000000000001"),
            target_id=UUID("00000000-0000-0000-0000-000000000002"),
            type=RelationshipType.ACQUIRED,
            description="Acquired in 2014",
        )
        assert rel.description == "Acquired in 2014"


class TestKnowledgeGraph:
    def test_empty_graph(self):
        graph = KnowledgeGraph()
        assert graph.node_count == 0
        assert graph.edge_count == 0

    def test_add_entity(self):
        graph = KnowledgeGraph()
        entity = Entity(name="Apple", type=EntityType.ORGANIZATION)
        node = graph.add_entity(entity)

        assert graph.node_count == 1
        assert node.id == entity.id
        assert node.name == "Apple"
        assert node.canonical_name == "apple"

    def test_add_relationship(self):
        graph = KnowledgeGraph()
        entity1 = Entity(name="Steve Jobs", type=EntityType.PERSON)
        entity2 = Entity(name="Apple", type=EntityType.ORGANIZATION)
        graph.add_entity(entity1)
        graph.add_entity(entity2)

        rel = Relationship(
            source_id=entity1.id,
            target_id=entity2.id,
            type=RelationshipType.FOUNDED,
        )
        edge = graph.add_relationship(rel)

        assert graph.edge_count == 1
        assert edge.source_id == entity1.id
        assert edge.target_id == entity2.id

    def test_add_relationship_missing_source(self):
        graph = KnowledgeGraph()
        entity = Entity(name="Apple", type=EntityType.ORGANIZATION)
        graph.add_entity(entity)

        rel = Relationship(
            source_id=UUID("00000000-0000-0000-0000-000000000099"),
            target_id=entity.id,
            type=RelationshipType.RELATED_TO,
        )
        edge = graph.add_relationship(rel)
        assert edge is None
        assert graph.edge_count == 0

    def test_add_relationship_missing_target(self):
        graph = KnowledgeGraph()
        entity = Entity(name="Apple", type=EntityType.ORGANIZATION)
        graph.add_entity(entity)

        rel = Relationship(
            source_id=entity.id,
            target_id=UUID("00000000-0000-0000-0000-000000000099"),
            type=RelationshipType.RELATED_TO,
        )
        edge = graph.add_relationship(rel)
        assert edge is None

    def test_get_node_by_canonical_name(self):
        graph = KnowledgeGraph()
        entity = Entity(name="Steve Jobs", type=EntityType.PERSON)
        graph.add_entity(entity)

        node = graph.get_node_by_canonical_name("steve jobs")
        assert node is not None
        assert node.name == "Steve Jobs"

        node = graph.get_node_by_canonical_name("  STEVE JOBS  ")
        assert node is not None

    def test_get_node_by_canonical_name_not_found(self):
        graph = KnowledgeGraph()
        node = graph.get_node_by_canonical_name("nonexistent")
        assert node is None


class TestGraphNode:
    def test_from_entity(self):
        entity = Entity(
            name="Apple Inc.",
            type=EntityType.ORGANIZATION,
            confidence=0.95,
            metadata={"source": "test"},
        )
        node = GraphNode.from_entity(entity)

        assert node.id == entity.id
        assert node.name == "Apple Inc."
        assert node.canonical_name == "apple inc."
        assert node.type == EntityType.ORGANIZATION
        assert node.confidence == 0.95
        assert node.metadata == {"source": "test"}


class TestGraphEdge:
    def test_from_relationship(self):
        rel = Relationship(
            source_id=UUID("00000000-0000-0000-0000-000000000001"),
            target_id=UUID("00000000-0000-0000-0000-000000000002"),
            type=RelationshipType.WORKS_FOR,
            weight=0.8,
            confidence=0.9,
            description="Employee",
        )
        edge = GraphEdge.from_relationship(rel)

        assert edge.source_id == rel.source_id
        assert edge.target_id == rel.target_id
        assert edge.type == RelationshipType.WORKS_FOR
        assert edge.weight == 0.8
        assert edge.confidence == 0.9
        assert edge.description == "Employee"

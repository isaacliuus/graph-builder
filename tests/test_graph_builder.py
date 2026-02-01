"""Unit tests for graph building module."""

import pytest
from uuid import UUID

from graph_builder.models.entity import Entity, EntityType
from graph_builder.models.relationship import Relationship, RelationshipType
from graph_builder.models.graph import KnowledgeGraph
from graph_builder.graph.networkx_builder import NetworkXGraphBuilder


class TestNetworkXGraphBuilder:
    @pytest.fixture
    def builder(self):
        return NetworkXGraphBuilder()

    @pytest.fixture
    def sample_entities(self):
        return [
            Entity(name="Apple Inc.", type=EntityType.ORGANIZATION),
            Entity(name="Steve Jobs", type=EntityType.PERSON),
            Entity(name="Cupertino", type=EntityType.LOCATION),
        ]

    @pytest.fixture
    def sample_relationships(self, sample_entities):
        return [
            Relationship(
                source_id=sample_entities[1].id,  # Steve Jobs
                target_id=sample_entities[0].id,  # Apple
                type=RelationshipType.FOUNDED,
            ),
            Relationship(
                source_id=sample_entities[0].id,  # Apple
                target_id=sample_entities[2].id,  # Cupertino
                type=RelationshipType.LOCATED_IN,
            ),
        ]

    def test_builder_creation(self, builder):
        assert builder is not None
        assert builder.deduplicate is True

    def test_build_graph(self, builder, sample_entities, sample_relationships):
        graph = builder.build(sample_entities, sample_relationships)

        assert isinstance(graph, KnowledgeGraph)
        assert graph.node_count == 3
        assert graph.edge_count == 2

    def test_build_empty_graph(self, builder):
        graph = builder.build([], [])

        assert graph.node_count == 0
        assert graph.edge_count == 0

    def test_build_entities_only(self, builder, sample_entities):
        graph = builder.build(sample_entities, [])

        assert graph.node_count == 3
        assert graph.edge_count == 0

    def test_deduplication(self, builder):
        entities = [
            Entity(name="Apple", type=EntityType.ORGANIZATION),
            Entity(name="apple", type=EntityType.ORGANIZATION),  # Duplicate
            Entity(name="  APPLE  ", type=EntityType.ORGANIZATION),  # Duplicate
        ]

        graph = builder.build(entities, [])

        assert graph.node_count == 1

    def test_no_deduplication(self):
        builder = NetworkXGraphBuilder(deduplicate=False)
        entities = [
            Entity(name="Apple", type=EntityType.ORGANIZATION),
            Entity(name="apple", type=EntityType.ORGANIZATION),
        ]

        graph = builder.build(entities, [])

        assert graph.node_count == 2

    def test_relationship_remapping_after_dedup(self, builder):
        entity1 = Entity(name="Apple", type=EntityType.ORGANIZATION)
        entity2 = Entity(name="apple", type=EntityType.ORGANIZATION)  # Duplicate
        entity3 = Entity(name="Steve Jobs", type=EntityType.PERSON)

        # Relationship references the duplicate
        rel = Relationship(
            source_id=entity3.id,
            target_id=entity2.id,  # Points to duplicate
            type=RelationshipType.FOUNDED,
        )

        graph = builder.build([entity1, entity2, entity3], [rel])

        assert graph.node_count == 2  # Apple + Steve Jobs
        assert graph.edge_count == 1  # Relationship remapped to entity1

    def test_to_networkx(self, builder, sample_entities, sample_relationships):
        graph = builder.build(sample_entities, sample_relationships)
        nx_graph = builder.to_networkx(graph)

        assert nx_graph.number_of_nodes() == 3
        assert nx_graph.number_of_edges() == 2

    def test_to_networkx_node_attributes(self, builder, sample_entities):
        graph = builder.build(sample_entities, [])
        nx_graph = builder.to_networkx(graph)

        for node_id, attrs in nx_graph.nodes(data=True):
            assert "name" in attrs
            assert "canonical_name" in attrs
            assert "type" in attrs
            assert "confidence" in attrs

    def test_to_networkx_edge_attributes(self, builder, sample_entities, sample_relationships):
        graph = builder.build(sample_entities, sample_relationships)
        nx_graph = builder.to_networkx(graph)

        for source, target, attrs in nx_graph.edges(data=True):
            assert "type" in attrs
            assert "weight" in attrs
            assert "confidence" in attrs

    def test_from_networkx(self, builder, sample_entities, sample_relationships):
        graph = builder.build(sample_entities, sample_relationships)
        nx_graph = builder.to_networkx(graph)

        restored_graph = builder.from_networkx(nx_graph)

        assert restored_graph.node_count == graph.node_count
        assert restored_graph.edge_count == graph.edge_count

    def test_invalid_relationship_dropped(self, builder, sample_entities):
        rel = Relationship(
            source_id=UUID("00000000-0000-0000-0000-000000000099"),
            target_id=sample_entities[0].id,
            type=RelationshipType.RELATED_TO,
        )

        graph = builder.build(sample_entities, [rel])

        assert graph.node_count == 3
        assert graph.edge_count == 0  # Invalid relationship not added

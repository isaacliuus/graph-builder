"""Tests for co-occurrence relationship generation."""

from uuid import uuid4

from graph_builder.merging.cooccurrence import create_cooccurrence_relationships
from graph_builder.models.entity import Entity, EntityType
from graph_builder.models.relationship import RelationshipType


def _entity(name: str, chunk_id=None):
    return Entity(name=name, type=EntityType.PERSON, chunk_id=chunk_id)


class TestCooccurrenceRelationships:
    def test_same_chunk_creates_relationship(self):
        chunk_id = uuid4()
        e1 = _entity("Alice", chunk_id=chunk_id)
        e2 = _entity("Bob", chunk_id=chunk_id)

        rels = create_cooccurrence_relationships([e1, e2])

        assert len(rels) == 1
        assert rels[0].type == RelationshipType.RELATED_TO
        assert {rels[0].source_id, rels[0].target_id} == {e1.id, e2.id}
        assert rels[0].weight == 1.0

    def test_weight_accumulation_across_chunks(self):
        chunk1 = uuid4()
        chunk2 = uuid4()
        e1_id = uuid4()
        e2_id = uuid4()

        e1_c1 = Entity(id=e1_id, name="Alice", type=EntityType.PERSON, chunk_id=chunk1)
        e2_c1 = Entity(id=e2_id, name="Bob", type=EntityType.PERSON, chunk_id=chunk1)
        e1_c2 = Entity(id=e1_id, name="Alice", type=EntityType.PERSON, chunk_id=chunk2)
        e2_c2 = Entity(id=e2_id, name="Bob", type=EntityType.PERSON, chunk_id=chunk2)

        rels = create_cooccurrence_relationships([e1_c1, e2_c1, e1_c2, e2_c2])

        assert len(rels) == 1
        assert rels[0].weight == 2.0

    def test_no_self_edges(self):
        chunk_id = uuid4()
        e_id = uuid4()
        e1 = Entity(id=e_id, name="Alice", type=EntityType.PERSON, chunk_id=chunk_id)
        e2 = Entity(id=e_id, name="Alice", type=EntityType.PERSON, chunk_id=chunk_id)

        rels = create_cooccurrence_relationships([e1, e2])

        assert len(rels) == 0

    def test_entities_without_chunk_id_skipped(self):
        e1 = _entity("Alice", chunk_id=None)
        e2 = _entity("Bob", chunk_id=None)

        rels = create_cooccurrence_relationships([e1, e2])

        assert len(rels) == 0

    def test_empty_input(self):
        rels = create_cooccurrence_relationships([])

        assert rels == []

    def test_different_chunks_no_relationship(self):
        e1 = _entity("Alice", chunk_id=uuid4())
        e2 = _entity("Bob", chunk_id=uuid4())

        rels = create_cooccurrence_relationships([e1, e2])

        assert len(rels) == 0

    def test_three_entities_same_chunk(self):
        chunk_id = uuid4()
        e1 = _entity("Alice", chunk_id=chunk_id)
        e2 = _entity("Bob", chunk_id=chunk_id)
        e3 = _entity("Charlie", chunk_id=chunk_id)

        rels = create_cooccurrence_relationships([e1, e2, e3])

        # 3 choose 2 = 3 relationships
        assert len(rels) == 3

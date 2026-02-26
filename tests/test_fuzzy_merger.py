"""Tests for FuzzyEntityMerger."""

import pytest
from uuid import uuid4

from graph_builder.models.entity import Entity, EntityType

try:
    import rapidfuzz  # noqa: F401
    HAS_RAPIDFUZZ = True
except ImportError:
    HAS_RAPIDFUZZ = False

pytestmark = pytest.mark.skipif(not HAS_RAPIDFUZZ, reason="rapidfuzz not installed")


def _entity(name: str, entity_type: EntityType = EntityType.PERSON, confidence: float = 1.0, chunk_id=None):
    return Entity(name=name, type=entity_type, confidence=confidence, chunk_id=chunk_id)


class TestFuzzyEntityMerger:
    def test_identical_entities_merged(self):
        from graph_builder.merging.fuzzy_merger import FuzzyEntityMerger

        merger = FuzzyEntityMerger(threshold=85.0)
        e1 = _entity("Steve Jobs")
        e2 = _entity("Steve Jobs")
        merged, id_map = merger.merge([e1, e2])

        assert len(merged) == 1
        assert id_map[e1.id] == merged[0].id
        assert id_map[e2.id] == merged[0].id

    def test_similar_entities_merged(self):
        from graph_builder.merging.fuzzy_merger import FuzzyEntityMerger

        merger = FuzzyEntityMerger(threshold=80.0)
        e1 = _entity("Steve Jobs")
        e2 = _entity("Steve P. Jobs")
        merged, id_map = merger.merge([e1, e2])

        assert len(merged) == 1
        assert id_map[e1.id] == id_map[e2.id]

    def test_different_types_not_merged(self):
        from graph_builder.merging.fuzzy_merger import FuzzyEntityMerger

        merger = FuzzyEntityMerger(threshold=85.0)
        e1 = _entity("Apple", entity_type=EntityType.ORGANIZATION)
        e2 = _entity("Apple", entity_type=EntityType.PRODUCT)
        merged, id_map = merger.merge([e1, e2])

        assert len(merged) == 2
        assert id_map[e1.id] != id_map[e2.id]

    def test_below_threshold_not_merged(self):
        from graph_builder.merging.fuzzy_merger import FuzzyEntityMerger

        merger = FuzzyEntityMerger(threshold=95.0)
        e1 = _entity("John Smith")
        e2 = _entity("Jane Smith")
        merged, _id_map = merger.merge([e1, e2])

        assert len(merged) == 2

    def test_highest_confidence_selected_as_primary(self):
        from graph_builder.merging.fuzzy_merger import FuzzyEntityMerger

        merger = FuzzyEntityMerger(threshold=85.0)
        e1 = _entity("Steve Jobs", confidence=0.7)
        e2 = _entity("Steve Jobs", confidence=0.95)
        merged, id_map = merger.merge([e1, e2])

        assert len(merged) == 1
        assert merged[0].id == e2.id
        assert merged[0].confidence == 0.95
        assert id_map[e1.id] == e2.id

    def test_merged_names_in_metadata(self):
        from graph_builder.merging.fuzzy_merger import FuzzyEntityMerger

        merger = FuzzyEntityMerger(threshold=85.0)
        e1 = _entity("Steve Jobs", confidence=0.9)
        e2 = _entity("Steve Jobs", confidence=0.5)
        merged, _id_map = merger.merge([e1, e2])

        assert len(merged) == 1
        assert "merged_names" in merged[0].metadata
        assert e2.name in merged[0].metadata["merged_names"]

    def test_id_mapping_completeness(self):
        from graph_builder.merging.fuzzy_merger import FuzzyEntityMerger

        merger = FuzzyEntityMerger(threshold=85.0)
        entities = [
            _entity("Alice"),
            _entity("Bob"),
            _entity("Alice"),
        ]
        merged, id_map = merger.merge(entities)

        # Every input ID must be in the mapping
        for e in entities:
            assert e.id in id_map
        # All mapped IDs must be primary entity IDs
        primary_ids = {e.id for e in merged}
        for mapped_id in id_map.values():
            assert mapped_id in primary_ids

    def test_no_merged_names_for_singletons(self):
        from graph_builder.merging.fuzzy_merger import FuzzyEntityMerger

        merger = FuzzyEntityMerger(threshold=85.0)
        e1 = _entity("Alice")
        merged, _id_map = merger.merge([e1])

        assert len(merged) == 1
        assert "merged_names" not in merged[0].metadata

    def test_empty_input(self):
        from graph_builder.merging.fuzzy_merger import FuzzyEntityMerger

        merger = FuzzyEntityMerger(threshold=85.0)
        merged, id_map = merger.merge([])

        assert merged == []
        assert id_map == {}

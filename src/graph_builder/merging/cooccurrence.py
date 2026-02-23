"""Co-occurrence based relationship generation."""

from collections import defaultdict
from itertools import combinations
from uuid import UUID

from graph_builder.models.entity import Entity
from graph_builder.models.relationship import Relationship, RelationshipType


def create_cooccurrence_relationships(entities: list[Entity]) -> list[Relationship]:
    """Create RELATED_TO relationships for entities that co-occur in the same chunk.

    Entities sharing a chunk_id are considered co-occurring. The weight of each
    relationship equals the number of chunks the pair co-occurs in. Self-edges
    and entities without a chunk_id are skipped.
    """
    # Group entities by chunk_id
    by_chunk: dict[UUID, list[Entity]] = defaultdict(list)
    for entity in entities:
        if entity.chunk_id is not None:
            by_chunk[entity.chunk_id].append(entity)

    # Count co-occurrences per normalized pair
    pair_counts: dict[tuple[UUID, UUID], int] = defaultdict(int)
    for chunk_entities in by_chunk.values():
        # Get unique entity IDs in this chunk
        unique_ids = list({e.id for e in chunk_entities})
        for a, b in combinations(unique_ids, 2):
            pair = (min(a, b), max(a, b))
            pair_counts[pair] += 1

    # Build relationships
    relationships: list[Relationship] = []
    for (source_id, target_id), weight in pair_counts.items():
        relationships.append(
            Relationship(
                source_id=source_id,
                target_id=target_id,
                type=RelationshipType.RELATED_TO,
                weight=float(weight),
            )
        )

    return relationships

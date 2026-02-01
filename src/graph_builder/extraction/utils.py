"""Utility functions for extraction module."""

from graph_builder.models.entity import Entity


def group_entities_by_chunk(entities: list[Entity]) -> dict[str, list[Entity]]:
    """Group entities by their chunk ID.

    Args:
        entities: List of entities to group.

    Returns:
        Dictionary mapping chunk ID strings to lists of entities.
    """
    entities_by_chunk: dict[str, list[Entity]] = {}
    for entity in entities:
        if entity.chunk_id:
            chunk_key = str(entity.chunk_id)
            if chunk_key not in entities_by_chunk:
                entities_by_chunk[chunk_key] = []
            entities_by_chunk[chunk_key].append(entity)
    return entities_by_chunk

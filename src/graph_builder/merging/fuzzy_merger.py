"""Fuzzy entity merger using token sort ratio similarity."""

from uuid import UUID

from graph_builder.models.entity import Entity, EntityType


class FuzzyEntityMerger:
    """Merges similar entities using fuzzy string matching.

    Groups entities by type, then uses greedy clustering with
    rapidfuzz token_sort_ratio to merge entities whose canonical
    names exceed the similarity threshold.
    """

    def __init__(self, threshold: float = 85.0):
        self.threshold = threshold

    def merge(self, entities: list[Entity]) -> tuple[list[Entity], dict[UUID, UUID]]:
        """Merge similar entities and return merged list with ID mapping.

        Returns:
            A tuple of (merged_entities, id_mapping) where id_mapping maps
            every input entity ID to its primary (merged) entity ID.
        """
        from rapidfuzz.fuzz import token_sort_ratio

        # Group entities by type
        by_type: dict[EntityType, list[Entity]] = {}
        for entity in entities:
            by_type.setdefault(entity.type, []).append(entity)

        merged_entities: list[Entity] = []
        id_mapping: dict[UUID, UUID] = {}

        for _entity_type, group in by_type.items():
            clusters = self._cluster(group, token_sort_ratio)
            for cluster in clusters:
                primary = self._select_primary(cluster)
                merged_names = [e.name for e in cluster if e.id != primary.id]
                if merged_names:
                    primary = primary.model_copy(
                        update={
                            "metadata": {
                                **primary.metadata,
                                "merged_names": merged_names,
                            }
                        }
                    )
                merged_entities.append(primary)
                for entity in cluster:
                    id_mapping[entity.id] = primary.id

        return merged_entities, id_mapping

    def _cluster(
        self, entities: list[Entity], scorer: object
    ) -> list[list[Entity]]:
        """Greedy clustering: seed entity picks up all unassigned matches."""
        assigned: set[int] = set()
        clusters: list[list[Entity]] = []

        for i, seed in enumerate(entities):
            if i in assigned:
                continue
            cluster = [seed]
            assigned.add(i)
            for j, candidate in enumerate(entities):
                if j in assigned:
                    continue
                score = scorer(seed.canonical_name, candidate.canonical_name)
                if score >= self.threshold:
                    cluster.append(candidate)
                    assigned.add(j)
            clusters.append(cluster)

        return clusters

    @staticmethod
    def _select_primary(cluster: list[Entity]) -> Entity:
        """Select the entity with highest confidence as primary."""
        return max(cluster, key=lambda e: e.confidence)

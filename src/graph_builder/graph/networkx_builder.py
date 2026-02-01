"""NetworkX-based graph builder implementation."""

from uuid import UUID
import networkx as nx

from graph_builder.models.entity import Entity
from graph_builder.models.relationship import Relationship
from graph_builder.models.graph import KnowledgeGraph, GraphNode, GraphEdge
from graph_builder.graph.base import GraphBuilderBase


class NetworkXGraphBuilder(GraphBuilderBase):
    """Graph builder that creates a KnowledgeGraph and can export to NetworkX."""

    def __init__(self, deduplicate: bool = True):
        self.deduplicate = deduplicate

    def build(
        self, entities: list[Entity], relationships: list[Relationship]
    ) -> KnowledgeGraph:
        """Build a knowledge graph from entities and relationships."""
        graph = KnowledgeGraph()

        # Track canonical names to entity IDs for deduplication
        canonical_to_id: dict[str, UUID] = {}
        id_mapping: dict[UUID, UUID] = {}  # Maps old IDs to deduplicated IDs

        for entity in entities:
            if self.deduplicate:
                if entity.canonical_name in canonical_to_id:
                    # Map this entity's ID to the existing entity
                    id_mapping[entity.id] = canonical_to_id[entity.canonical_name]
                    continue
                canonical_to_id[entity.canonical_name] = entity.id

            graph.add_entity(entity)
            id_mapping[entity.id] = entity.id

        # Add relationships with ID remapping
        for relationship in relationships:
            source_id = id_mapping.get(relationship.source_id)
            target_id = id_mapping.get(relationship.target_id)

            if source_id and target_id:
                # Create a new relationship with remapped IDs
                remapped_rel = Relationship(
                    id=relationship.id,
                    source_id=source_id,
                    target_id=target_id,
                    type=relationship.type,
                    weight=relationship.weight,
                    confidence=relationship.confidence,
                    description=relationship.description,
                    chunk_id=relationship.chunk_id,
                    metadata=relationship.metadata,
                )
                graph.add_relationship(remapped_rel)

        return graph

    def to_networkx(self, graph: KnowledgeGraph) -> nx.DiGraph:
        """Convert a KnowledgeGraph to a NetworkX DiGraph."""
        G = nx.DiGraph()

        for node_id, node in graph.nodes.items():
            G.add_node(
                str(node_id),
                name=node.name,
                canonical_name=node.canonical_name,
                type=node.type.value,
                confidence=node.confidence,
                **node.metadata,
            )

        for edge in graph.edges:
            G.add_edge(
                str(edge.source_id),
                str(edge.target_id),
                type=edge.type.value,
                weight=edge.weight,
                confidence=edge.confidence,
                description=edge.description,
                **edge.metadata,
            )

        return G

    def from_networkx(self, G: nx.DiGraph) -> KnowledgeGraph:
        """Create a KnowledgeGraph from a NetworkX DiGraph."""
        from graph_builder.models.entity import EntityType
        from graph_builder.models.relationship import RelationshipType

        graph = KnowledgeGraph()

        for node_id, attrs in G.nodes(data=True):
            node = GraphNode(
                id=UUID(node_id),
                name=attrs.get("name", ""),
                canonical_name=attrs.get("canonical_name", ""),
                type=EntityType(attrs.get("type", "OTHER")),
                confidence=attrs.get("confidence", 1.0),
                metadata={
                    k: v
                    for k, v in attrs.items()
                    if k not in ("name", "canonical_name", "type", "confidence")
                },
            )
            graph.nodes[node.id] = node

        for source, target, attrs in G.edges(data=True):
            edge = GraphEdge(
                source_id=UUID(source),
                target_id=UUID(target),
                type=RelationshipType(attrs.get("type", "RELATED_TO")),
                weight=attrs.get("weight", 1.0),
                confidence=attrs.get("confidence", 1.0),
                description=attrs.get("description", ""),
                metadata={
                    k: v
                    for k, v in attrs.items()
                    if k not in ("type", "weight", "confidence", "description")
                },
            )
            graph.edges.append(edge)  # pylint: disable=no-member

        return graph

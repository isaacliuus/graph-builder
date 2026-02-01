"""Knowledge graph models."""

from uuid import UUID
from pydantic import BaseModel, Field

from graph_builder.models.entity import Entity, EntityType
from graph_builder.models.relationship import Relationship, RelationshipType


class GraphNode(BaseModel):
    """A node in the knowledge graph."""

    id: UUID
    name: str
    canonical_name: str
    type: EntityType
    confidence: float = 1.0
    metadata: dict = Field(default_factory=dict)

    @classmethod
    def from_entity(cls, entity: Entity) -> "GraphNode":
        """Create a graph node from an entity."""
        return cls(
            id=entity.id,
            name=entity.name,
            canonical_name=entity.canonical_name,
            type=entity.type,
            confidence=entity.confidence,
            metadata=entity.metadata,
        )


class GraphEdge(BaseModel):
    """An edge in the knowledge graph."""

    # node ids
    source_id: UUID
    target_id: UUID
    type: RelationshipType
    weight: float = 1.0
    confidence: float = 1.0
    description: str = ""
    metadata: dict = Field(default_factory=dict)

    @classmethod
    def from_relationship(cls, relationship: Relationship) -> "GraphEdge":
        """Create a graph edge from a relationship."""
        return cls(
            source_id=relationship.source_id,
            target_id=relationship.target_id,
            type=relationship.type,
            weight=relationship.weight,
            confidence=relationship.confidence,
            description=relationship.description,
            metadata=relationship.metadata,
        )


class KnowledgeGraph(BaseModel):
    """A knowledge graph containing nodes and edges."""

    nodes: dict[UUID, GraphNode] = Field(default_factory=dict)
    edges: list[GraphEdge] = Field(default_factory=list)

    def add_entity(self, entity: Entity) -> GraphNode:
        """Add an entity as a node to the graph."""
        node = GraphNode.from_entity(entity)
        self.nodes[node.id] = node
        return node

    def add_relationship(self, relationship: Relationship) -> GraphEdge | None:
        """Add a relationship as an edge to the graph."""
        if relationship.source_id not in self.nodes:
            return None
        if relationship.target_id not in self.nodes:
            return None
        edge = GraphEdge.from_relationship(relationship)
        self.edges.append(edge)  # pylint: disable=no-member
        return edge

    def get_node_by_canonical_name(self, canonical_name: str) -> GraphNode | None:
        """Find a node by its canonical name."""
        for node in self.nodes.values():  # pylint: disable=no-member
            if node.canonical_name == canonical_name.lower().strip():
                return node
        return None

    @property
    def node_count(self) -> int:
        """Number of nodes in the graph."""
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        """Number of edges in the graph."""
        return len(self.edges)

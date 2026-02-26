"""Base classes and protocols for the pipeline."""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable
from uuid import UUID

from graph_builder.models.document import Document, Chunk
from graph_builder.models.entity import Entity
from graph_builder.models.relationship import Relationship, RelationshipType
from graph_builder.models.graph import KnowledgeGraph, GraphNode, GraphEdge


@dataclass
class PipelineContext:
    """Context passed through the pipeline stages."""

    documents: list[Document] = field(default_factory=list)
    chunks: list[Chunk] = field(default_factory=list)
    entities: list[Entity] = field(default_factory=list)
    relationships: list[Relationship] = field(default_factory=list)
    graph: KnowledgeGraph = field(default_factory=KnowledgeGraph)
    metadata: dict = field(default_factory=dict)


@runtime_checkable
class PipelineStage(Protocol):  # pylint: disable=too-few-public-methods
    """Protocol for pipeline stages."""

    def process(self, context: PipelineContext) -> PipelineContext:
        """Process the context and return the updated context."""


@runtime_checkable
class Chunker(Protocol):  # pylint: disable=too-few-public-methods
    """Protocol for text chunkers."""

    def chunk(self, documents: list[Document]) -> list[Chunk]:
        """Split documents into chunks."""


@runtime_checkable
class EntityExtractor(Protocol):  # pylint: disable=too-few-public-methods
    """Protocol for entity extractors."""

    def extract(self, chunks: list[Chunk]) -> list[Entity]:
        """Extract entities from chunks."""


@runtime_checkable
class EntityMerger(Protocol):  # pylint: disable=too-few-public-methods
    """Protocol for entity mergers that deduplicate/merge similar entities."""

    def merge(self, entities: list[Entity]) -> tuple[list[Entity], dict[UUID, UUID]]:
        """Merge similar entities, returning merged list and ID mapping."""


@runtime_checkable
class RelationshipExtractor(Protocol):  # pylint: disable=too-few-public-methods
    """Protocol for relationship extractors."""

    def extract(self, chunks: list[Chunk], entities: list[Entity]) -> list[Relationship]:
        """Extract relationships between entities."""


@runtime_checkable
class GraphBuilder(Protocol):  # pylint: disable=too-few-public-methods
    """Protocol for graph builders."""

    def build(
        self, entities: list[Entity], relationships: list[Relationship]
    ) -> KnowledgeGraph:
        """Build a knowledge graph from entities and relationships."""


@runtime_checkable
class GraphDB(Protocol):
    """Protocol for graph database implementations."""

    def connect(self) -> None:
        """Establish connection to the database."""

    def close(self) -> None:
        """Close the database connection."""

    def sync(self, graph: KnowledgeGraph) -> None:
        """Synchronize a KnowledgeGraph to the database."""

    def create_node(self, node: GraphNode) -> GraphNode:
        """Create a node in the database."""

    def get_node(self, node_id: UUID) -> GraphNode | None:
        """Get a node by its ID."""

    def get_node_by_canonical_name(self, canonical_name: str) -> GraphNode | None:
        """Get a node by its canonical name."""

    def update_node(self, node: GraphNode) -> GraphNode:
        """Update an existing node."""

    def delete_node(self, node_id: UUID) -> bool:
        """Delete a node by its ID."""

    def create_edge(self, edge: GraphEdge) -> GraphEdge:
        """Create an edge in the database."""

    def get_edges(
        self,
        source_id: UUID | None = None,
        target_id: UUID | None = None,
    ) -> list[GraphEdge]:
        """Get edges, optionally filtered by source and/or target."""

    def delete_edge(
        self,
        source_id: UUID,
        target_id: UUID,
        edge_type: RelationshipType | None = None,
    ) -> bool:
        """Delete an edge between two nodes."""

    def create_nodes_batch(self, nodes: list[GraphNode]) -> list[GraphNode]:
        """Create multiple nodes in a single batch operation."""

    def create_edges_batch(self, edges: list[GraphEdge]) -> list[GraphEdge]:
        """Create multiple edges in a single batch operation."""

    def load_graph(self) -> KnowledgeGraph:
        """Load all nodes and edges from the database."""

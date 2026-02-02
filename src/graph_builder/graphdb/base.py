"""Abstract base class for graph database implementations."""

from abc import ABC, abstractmethod
from typing import Self
from uuid import UUID

from graph_builder.models.graph import GraphEdge, GraphNode, KnowledgeGraph
from graph_builder.models.relationship import RelationshipType


class GraphDBBase(ABC):
    """Abstract base class for graph database implementations.

    Provides CRUD operations for nodes and edges, batch operations,
    and synchronization with KnowledgeGraph objects.

    Supports context manager protocol for connection handling:

        with MyGraphDB(host="localhost") as db:
            db.sync(graph)
    """

    @abstractmethod
    def connect(self) -> None:
        """Establish connection to the database."""

    @abstractmethod
    def close(self) -> None:
        """Close the database connection."""

    def __enter__(self) -> Self:
        """Enter context manager, connecting to the database."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager, closing the connection."""
        self.close()

    @abstractmethod
    def sync(self, graph: KnowledgeGraph) -> None:
        """Synchronize a KnowledgeGraph to the database.

        This is an idempotent operation that creates or updates all nodes
        and edges from the graph.

        Args:
            graph: The KnowledgeGraph to persist.
        """

    @abstractmethod
    def create_node(self, node: GraphNode) -> GraphNode:
        """Create a node in the database.

        Args:
            node: The node to create.

        Returns:
            The created node.
        """

    @abstractmethod
    def get_node(self, node_id: UUID) -> GraphNode | None:
        """Get a node by its ID.

        Args:
            node_id: The UUID of the node.

        Returns:
            The node if found, None otherwise.
        """

    @abstractmethod
    def get_node_by_canonical_name(self, canonical_name: str) -> GraphNode | None:
        """Get a node by its canonical name.

        Args:
            canonical_name: The canonical name to search for.

        Returns:
            The node if found, None otherwise.
        """

    @abstractmethod
    def update_node(self, node: GraphNode) -> GraphNode:
        """Update an existing node.

        Args:
            node: The node with updated values.

        Returns:
            The updated node.
        """

    @abstractmethod
    def delete_node(self, node_id: UUID) -> bool:
        """Delete a node by its ID.

        Args:
            node_id: The UUID of the node to delete.

        Returns:
            True if the node was deleted, False if not found.
        """

    @abstractmethod
    def create_edge(self, edge: GraphEdge) -> GraphEdge:
        """Create an edge in the database.

        Args:
            edge: The edge to create.

        Returns:
            The created edge.
        """

    @abstractmethod
    def get_edges(
        self,
        source_id: UUID | None = None,
        target_id: UUID | None = None,
    ) -> list[GraphEdge]:
        """Get edges, optionally filtered by source and/or target.

        Args:
            source_id: Filter by source node ID.
            target_id: Filter by target node ID.

        Returns:
            List of matching edges.
        """

    @abstractmethod
    def delete_edge(
        self,
        source_id: UUID,
        target_id: UUID,
        edge_type: RelationshipType | None = None,
    ) -> bool:
        """Delete an edge between two nodes.

        Args:
            source_id: The source node ID.
            target_id: The target node ID.
            edge_type: Optional type to filter by. If None, deletes all edges
                between the nodes.

        Returns:
            True if any edge was deleted, False otherwise.
        """

    @abstractmethod
    def create_nodes_batch(self, nodes: list[GraphNode]) -> list[GraphNode]:
        """Create multiple nodes in a single batch operation.

        Args:
            nodes: List of nodes to create.

        Returns:
            List of created nodes.
        """

    @abstractmethod
    def create_edges_batch(self, edges: list[GraphEdge]) -> list[GraphEdge]:
        """Create multiple edges in a single batch operation.

        Args:
            edges: List of edges to create.

        Returns:
            List of created edges.
        """

    @abstractmethod
    def load_graph(self) -> KnowledgeGraph:
        """Load all nodes and edges from the database into a KnowledgeGraph.

        Returns:
            A KnowledgeGraph containing all data from the database.
        """

    def clear(self) -> None:
        """Delete all nodes and edges from the database.

        Default implementation loads all nodes and deletes them individually.
        Subclasses should override with a more efficient implementation.
        """
        graph = self.load_graph()
        for node_id in graph.nodes:
            self.delete_node(node_id)

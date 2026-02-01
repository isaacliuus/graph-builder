"""Memgraph graph database implementation using the Bolt protocol."""

import json
from typing import Any
from uuid import UUID

from graph_builder.graphdb.base import GraphDBBase
from graph_builder.models.entity import EntityType
from graph_builder.models.graph import GraphEdge, GraphNode, KnowledgeGraph
from graph_builder.models.relationship import RelationshipType


class MemgraphGraphDB(GraphDBBase):
    """Memgraph graph database implementation.

    Uses the neo4j Python driver (compatible with Memgraph's Bolt protocol).
    The driver is lazy-loaded to avoid import errors when neo4j is not installed.

    Example:
        with MemgraphGraphDB(host="localhost", port=7687) as db:
            db.sync(graph)

        # Or manually manage connection:
        db = MemgraphGraphDB(host="localhost")
        db.connect()
        try:
            db.sync(graph)
        finally:
            db.close()
    """

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        host: str = "localhost",
        port: int = 7687,
        username: str = "",
        password: str = "",
        database: str = "memgraph",
        encrypted: bool = False,
    ):
        """Initialize MemgraphGraphDB.

        Args:
            host: Memgraph server hostname.
            port: Memgraph Bolt port.
            username: Username for authentication.
            password: Password for authentication.
            database: Database name (Memgraph uses "memgraph" by default).
            encrypted: Whether to use encrypted connection.
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.database = database
        self.encrypted = encrypted
        self._driver = None

    @property
    def driver(self):
        """Lazy load the neo4j driver."""
        if self._driver is None:
            try:
                # pylint: disable=import-outside-toplevel
                from neo4j import GraphDatabase
            except ImportError as err:
                raise ImportError(
                    "Memgraph support requires the 'neo4j' package. "
                    "Install with: pip install neo4j"
                ) from err

            uri = f"bolt://{self.host}:{self.port}"
            auth = (self.username, self.password) if self.username else None
            self._driver = GraphDatabase.driver(
                uri,
                auth=auth,
                encrypted=self.encrypted,
            )
        return self._driver

    def connect(self) -> None:
        """Establish connection and verify connectivity."""
        self.driver.verify_connectivity()

    def close(self) -> None:
        """Close the database connection."""
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    def sync(self, graph: KnowledgeGraph) -> None:
        """Synchronize a KnowledgeGraph to the database.

        Uses MERGE for idempotent create/update operations.
        """
        nodes = list(graph.nodes.values())
        if nodes:
            self.create_nodes_batch(nodes)
        if graph.edges:
            self.create_edges_batch(graph.edges)

    def create_node(self, node: GraphNode) -> GraphNode:
        """Create or update a node using MERGE."""
        query = """
        MERGE (n:Entity {id: $id})
        SET n.name = $name,
            n.canonical_name = $canonical_name,
            n.type = $type,
            n.confidence = $confidence,
            n.metadata = $metadata
        RETURN n
        """
        params = self._node_to_params(node)
        with self.driver.session(database=self.database) as session:
            session.run(query, params)
        return node

    def get_node(self, node_id: UUID) -> GraphNode | None:
        """Get a node by its ID."""
        query = """
        MATCH (n:Entity {id: $id})
        RETURN n
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(query, {"id": str(node_id)})
            record = result.single()
            if record is None:
                return None
            return self._record_to_node(record["n"])

    def get_node_by_canonical_name(self, canonical_name: str) -> GraphNode | None:
        """Get a node by its canonical name."""
        query = """
        MATCH (n:Entity {canonical_name: $canonical_name})
        RETURN n
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(
                query, {"canonical_name": canonical_name.lower().strip()}
            )
            record = result.single()
            if record is None:
                return None
            return self._record_to_node(record["n"])

    def update_node(self, node: GraphNode) -> GraphNode:
        """Update an existing node."""
        return self.create_node(node)

    def delete_node(self, node_id: UUID) -> bool:
        """Delete a node and its relationships by ID."""
        query = """
        MATCH (n:Entity {id: $id})
        DETACH DELETE n
        RETURN count(n) as deleted
        """
        with self.driver.session(database=self.database) as session:
            result = session.run(query, {"id": str(node_id)})
            record = result.single()
            return record["deleted"] > 0

    def create_edge(self, edge: GraphEdge) -> GraphEdge:
        """Create or update an edge using MERGE with dynamic relationship type."""
        query = f"""
        MATCH (source:Entity {{id: $source_id}})
        MATCH (target:Entity {{id: $target_id}})
        MERGE (source)-[r:{edge.type.value}]->(target)
        SET r.weight = $weight,
            r.confidence = $confidence,
            r.description = $description,
            r.metadata = $metadata
        RETURN r
        """
        params = self._edge_to_params(edge)
        with self.driver.session(database=self.database) as session:
            session.run(query, params)
        return edge

    def get_edges(
        self,
        source_id: UUID | None = None,
        target_id: UUID | None = None,
    ) -> list[GraphEdge]:
        """Get edges, optionally filtered by source and/or target."""
        conditions = []
        params: dict[str, Any] = {}

        if source_id is not None:
            conditions.append("source.id = $source_id")
            params["source_id"] = str(source_id)
        if target_id is not None:
            conditions.append("target.id = $target_id")
            params["target_id"] = str(target_id)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
        MATCH (source:Entity)-[r]->(target:Entity)
        {where_clause}
        RETURN source.id as source_id, target.id as target_id,
               type(r) as rel_type, r.weight as weight,
               r.confidence as confidence, r.description as description,
               r.metadata as metadata
        """

        edges = []
        with self.driver.session(database=self.database) as session:
            result = session.run(query, params)
            for record in result:
                edges.append(self._record_to_edge(record))
        return edges

    def delete_edge(
        self,
        source_id: UUID,
        target_id: UUID,
        edge_type: RelationshipType | None = None,
    ) -> bool:
        """Delete an edge between two nodes."""
        if edge_type is not None:
            query = f"""
            MATCH (source:Entity {{id: $source_id}})-[r:{edge_type.value}]->(target:Entity {{id: $target_id}})
            DELETE r
            RETURN count(r) as deleted
            """
        else:
            query = """
            MATCH (source:Entity {id: $source_id})-[r]->(target:Entity {id: $target_id})
            DELETE r
            RETURN count(r) as deleted
            """

        params = {"source_id": str(source_id), "target_id": str(target_id)}
        with self.driver.session(database=self.database) as session:
            result = session.run(query, params)
            record = result.single()
            return record["deleted"] > 0

    def create_nodes_batch(self, nodes: list[GraphNode]) -> list[GraphNode]:
        """Create multiple nodes using UNWIND for efficiency."""
        if not nodes:
            return []

        query = """
        UNWIND $nodes as node
        MERGE (n:Entity {id: node.id})
        SET n.name = node.name,
            n.canonical_name = node.canonical_name,
            n.type = node.type,
            n.confidence = node.confidence,
            n.metadata = node.metadata
        """
        params = {"nodes": [self._node_to_params(n) for n in nodes]}
        with self.driver.session(database=self.database) as session:
            session.run(query, params)
        return nodes

    def create_edges_batch(self, edges: list[GraphEdge]) -> list[GraphEdge]:
        """Create multiple edges, grouped by relationship type for efficiency."""
        if not edges:
            return []

        edges_by_type: dict[RelationshipType, list[GraphEdge]] = {}
        for edge in edges:
            edges_by_type.setdefault(edge.type, []).append(edge)

        with self.driver.session(database=self.database) as session:
            for rel_type, typed_edges in edges_by_type.items():
                query = f"""
                UNWIND $edges as edge
                MATCH (source:Entity {{id: edge.source_id}})
                MATCH (target:Entity {{id: edge.target_id}})
                MERGE (source)-[r:{rel_type.value}]->(target)
                SET r.weight = edge.weight,
                    r.confidence = edge.confidence,
                    r.description = edge.description,
                    r.metadata = edge.metadata
                """
                params = {"edges": [self._edge_to_params(e) for e in typed_edges]}
                session.run(query, params)

        return edges

    def load_graph(self) -> KnowledgeGraph:
        """Load all nodes and edges from the database."""
        graph = KnowledgeGraph()

        with self.driver.session(database=self.database) as session:
            node_result = session.run("MATCH (n:Entity) RETURN n")
            for record in node_result:
                node = self._record_to_node(record["n"])
                graph.nodes[node.id] = node

            edge_query = """
            MATCH (source:Entity)-[r]->(target:Entity)
            RETURN source.id as source_id, target.id as target_id,
                   type(r) as rel_type, r.weight as weight,
                   r.confidence as confidence, r.description as description,
                   r.metadata as metadata
            """
            edge_result = session.run(edge_query)
            for record in edge_result:
                edge = self._record_to_edge(record)
                graph.edges.append(edge)  # pylint: disable=no-member

        return graph

    def clear(self) -> None:
        """Delete all nodes and edges from the database."""
        with self.driver.session(database=self.database) as session:
            session.run("MATCH (n) DETACH DELETE n")

    def _node_to_params(self, node: GraphNode) -> dict[str, Any]:
        """Convert a GraphNode to query parameters."""
        return {
            "id": str(node.id),
            "name": node.name,
            "canonical_name": node.canonical_name,
            "type": node.type.value,
            "confidence": node.confidence,
            "metadata": json.dumps(node.metadata),
        }

    def _record_to_node(self, node_data: Any) -> GraphNode:
        """Convert a neo4j node record to a GraphNode."""
        metadata = node_data.get("metadata", "{}")
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        return GraphNode(
            id=UUID(node_data["id"]),
            name=node_data["name"],
            canonical_name=node_data["canonical_name"],
            type=EntityType(node_data["type"]),
            confidence=node_data.get("confidence", 1.0),
            metadata=metadata,
        )

    def _edge_to_params(self, edge: GraphEdge) -> dict[str, Any]:
        """Convert a GraphEdge to query parameters."""
        return {
            "source_id": str(edge.source_id),
            "target_id": str(edge.target_id),
            "weight": edge.weight,
            "confidence": edge.confidence,
            "description": edge.description,
            "metadata": json.dumps(edge.metadata),
        }

    def _record_to_edge(self, record: Any) -> GraphEdge:
        """Convert a neo4j edge record to a GraphEdge."""
        metadata = record.get("metadata", "{}")
        if isinstance(metadata, str):
            metadata = json.loads(metadata)

        return GraphEdge(
            source_id=UUID(record["source_id"]),
            target_id=UUID(record["target_id"]),
            type=RelationshipType(record["rel_type"]),
            weight=record.get("weight", 1.0),
            confidence=record.get("confidence", 1.0),
            description=record.get("description", ""),
            metadata=metadata,
        )

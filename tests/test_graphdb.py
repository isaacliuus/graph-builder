"""Tests for the graphdb module."""

import json
import sys
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from graph_builder.models.entity import EntityType
from graph_builder.models.relationship import RelationshipType
from graph_builder.models.graph import GraphNode, GraphEdge, KnowledgeGraph
from graph_builder.graphdb.base import GraphDBBase


class TestGraphDBBase:
    """Tests for GraphDBBase ABC."""

    def test_cannot_instantiate_abstract_class(self):
        """GraphDBBase cannot be instantiated directly."""
        with pytest.raises(TypeError):
            GraphDBBase()  # type: ignore

    def test_context_manager_calls_connect_and_close(self):
        """Context manager should call connect on enter and close on exit."""

        class ConcreteDB(GraphDBBase):
            def __init__(self):
                self.connected = False
                self.closed = False

            def connect(self):
                self.connected = True

            def close(self):
                self.closed = True

            def sync(self, graph):
                pass

            def create_node(self, node):
                return node

            def get_node(self, node_id):
                return None

            def get_node_by_canonical_name(self, canonical_name):
                return None

            def update_node(self, node):
                return node

            def delete_node(self, node_id):
                return True

            def create_edge(self, edge):
                return edge

            def get_edges(self, source_id=None, target_id=None):
                return []

            def delete_edge(self, source_id, target_id, edge_type=None):
                return True

            def create_nodes_batch(self, nodes):
                return nodes

            def create_edges_batch(self, edges):
                return edges

            def load_graph(self):
                return KnowledgeGraph()

        db = ConcreteDB()
        assert not db.connected
        assert not db.closed

        with db:
            assert db.connected
            assert not db.closed

        assert db.closed


class TestMemgraphGraphDB:
    """Tests for MemgraphGraphDB with mocked driver."""

    @pytest.fixture
    def mock_neo4j(self):
        """Create a mock neo4j module and driver."""
        mock_driver = MagicMock()
        mock_graph_database = MagicMock()
        mock_graph_database.driver.return_value = mock_driver

        mock_neo4j_module = MagicMock()
        mock_neo4j_module.GraphDatabase = mock_graph_database

        with patch.dict(sys.modules, {"neo4j": mock_neo4j_module}):
            yield mock_driver, mock_graph_database

    @pytest.fixture
    def sample_node(self):
        """Create a sample GraphNode."""
        return GraphNode(
            id=uuid4(),
            name="Apple Inc.",
            canonical_name="apple inc.",
            type=EntityType.ORGANIZATION,
            confidence=0.95,
            metadata={"source": "test"},
        )

    @pytest.fixture
    def sample_edge(self, sample_node):
        """Create a sample GraphEdge."""
        target_id = uuid4()
        return GraphEdge(
            source_id=sample_node.id,
            target_id=target_id,
            type=RelationshipType.FOUNDED,
            weight=1.0,
            confidence=0.9,
            description="Founded the company",
            metadata={"test": True},
        )

    def test_lazy_driver_loading(self, mock_neo4j):
        """Driver should be lazy-loaded on first access."""
        mock_driver, _ = mock_neo4j
        from graph_builder.graphdb.memgraph import MemgraphGraphDB

        db = MemgraphGraphDB(host="localhost", port=7687)
        # Driver not loaded yet
        assert db._driver is None

        # Access driver
        _ = db.driver
        assert db._driver is not None

    def test_connect_verifies_connectivity(self, mock_neo4j):
        """Connect should verify driver connectivity."""
        mock_driver, _ = mock_neo4j
        from graph_builder.graphdb.memgraph import MemgraphGraphDB

        db = MemgraphGraphDB()
        db.connect()

        mock_driver.verify_connectivity.assert_called_once()

    def test_close_closes_driver(self, mock_neo4j):
        """Close should close the driver and reset it."""
        mock_driver, _ = mock_neo4j
        from graph_builder.graphdb.memgraph import MemgraphGraphDB

        db = MemgraphGraphDB()
        _ = db.driver  # Initialize driver
        db.close()

        mock_driver.close.assert_called_once()
        assert db._driver is None

    def test_create_node_uses_merge(self, mock_neo4j, sample_node):
        """Create node should use MERGE for idempotent operation."""
        mock_driver, _ = mock_neo4j
        from graph_builder.graphdb.memgraph import MemgraphGraphDB

        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        db = MemgraphGraphDB()
        result = db.create_node(sample_node)

        assert result == sample_node
        mock_session.run.assert_called_once()
        query = mock_session.run.call_args[0][0]
        assert "MERGE" in query
        assert "Entity" in query

    def test_get_node_returns_none_when_not_found(self, mock_neo4j):
        """Get node should return None when node doesn't exist."""
        mock_driver, _ = mock_neo4j
        from graph_builder.graphdb.memgraph import MemgraphGraphDB

        mock_session = MagicMock()
        mock_result = MagicMock()
        mock_result.single.return_value = None
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        db = MemgraphGraphDB()
        result = db.get_node(uuid4())

        assert result is None

    def test_get_node_returns_node_when_found(self, mock_neo4j, sample_node):
        """Get node should return GraphNode when found."""
        mock_driver, _ = mock_neo4j
        from graph_builder.graphdb.memgraph import MemgraphGraphDB

        mock_session = MagicMock()
        mock_record = MagicMock()
        mock_record.__getitem__ = MagicMock(
            return_value={
                "id": str(sample_node.id),
                "name": sample_node.name,
                "canonical_name": sample_node.canonical_name,
                "type": sample_node.type.value,
                "confidence": sample_node.confidence,
                "metadata": json.dumps(sample_node.metadata),
            }
        )
        mock_result = MagicMock()
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        db = MemgraphGraphDB()
        result = db.get_node(sample_node.id)

        assert result is not None
        assert result.id == sample_node.id
        assert result.name == sample_node.name

    def test_delete_node_uses_detach_delete(self, mock_neo4j):
        """Delete node should use DETACH DELETE."""
        mock_driver, _ = mock_neo4j
        from graph_builder.graphdb.memgraph import MemgraphGraphDB

        mock_session = MagicMock()
        mock_record = MagicMock()
        mock_record.__getitem__ = MagicMock(return_value=1)
        mock_result = MagicMock()
        mock_result.single.return_value = mock_record
        mock_session.run.return_value = mock_result
        mock_driver.session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        db = MemgraphGraphDB()
        result = db.delete_node(uuid4())

        assert result is True
        query = mock_session.run.call_args[0][0]
        assert "DETACH DELETE" in query

    def test_create_nodes_batch_uses_unwind(self, mock_neo4j, sample_node):
        """Batch node creation should use UNWIND."""
        mock_driver, _ = mock_neo4j
        from graph_builder.graphdb.memgraph import MemgraphGraphDB

        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        db = MemgraphGraphDB()
        nodes = [sample_node]
        result = db.create_nodes_batch(nodes)

        assert result == nodes
        query = mock_session.run.call_args[0][0]
        assert "UNWIND" in query

    def test_create_edges_batch_groups_by_type(self, mock_neo4j, sample_edge):
        """Batch edge creation should group edges by type."""
        mock_driver, _ = mock_neo4j
        from graph_builder.graphdb.memgraph import MemgraphGraphDB

        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        db = MemgraphGraphDB()
        edge2 = GraphEdge(
            source_id=uuid4(),
            target_id=uuid4(),
            type=RelationshipType.WORKS_FOR,
            weight=1.0,
            confidence=0.8,
        )
        edges = [sample_edge, edge2]
        result = db.create_edges_batch(edges)

        assert result == edges
        # Should be called twice, once per edge type
        assert mock_session.run.call_count == 2

    def test_sync_creates_nodes_and_edges(self, mock_neo4j, sample_node, sample_edge):
        """Sync should create all nodes and edges."""
        mock_driver, _ = mock_neo4j
        from graph_builder.graphdb.memgraph import MemgraphGraphDB

        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        db = MemgraphGraphDB()
        graph = KnowledgeGraph()
        graph.nodes[sample_node.id] = sample_node
        graph.edges.append(sample_edge)

        db.sync(graph)

        # Should create nodes first, then edges
        assert mock_session.run.call_count >= 2

    def test_clear_deletes_all_nodes(self, mock_neo4j):
        """Clear should delete all nodes with DETACH DELETE."""
        mock_driver, _ = mock_neo4j
        from graph_builder.graphdb.memgraph import MemgraphGraphDB

        mock_session = MagicMock()
        mock_driver.session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        db = MemgraphGraphDB()
        db.clear()

        query = mock_session.run.call_args[0][0]
        assert "MATCH (n) DETACH DELETE n" in query

    def test_load_graph_returns_knowledge_graph(self, mock_neo4j, sample_node):
        """Load graph should return a KnowledgeGraph with nodes and edges."""
        mock_driver, _ = mock_neo4j
        from graph_builder.graphdb.memgraph import MemgraphGraphDB

        mock_session = MagicMock()

        # Mock node query result
        mock_node_record = MagicMock()
        mock_node_record.__getitem__ = MagicMock(
            return_value={
                "id": str(sample_node.id),
                "name": sample_node.name,
                "canonical_name": sample_node.canonical_name,
                "type": sample_node.type.value,
                "confidence": sample_node.confidence,
                "metadata": json.dumps(sample_node.metadata),
            }
        )
        mock_node_result = MagicMock()
        mock_node_result.__iter__ = MagicMock(return_value=iter([mock_node_record]))

        # Mock edge query result (empty)
        mock_edge_result = MagicMock()
        mock_edge_result.__iter__ = MagicMock(return_value=iter([]))

        mock_session.run.side_effect = [mock_node_result, mock_edge_result]
        mock_driver.session.return_value.__enter__ = MagicMock(
            return_value=mock_session
        )
        mock_driver.session.return_value.__exit__ = MagicMock(return_value=False)

        db = MemgraphGraphDB()
        graph = db.load_graph()

        assert isinstance(graph, KnowledgeGraph)
        assert len(graph.nodes) == 1
        assert sample_node.id in graph.nodes


class TestImportError:
    """Tests for import error handling."""

    def test_import_error_without_neo4j(self):
        """Should raise ImportError with helpful message when neo4j not installed."""
        # Remove neo4j from sys.modules if present
        original_modules = {}
        for key in list(sys.modules.keys()):
            if key == "neo4j" or key.startswith("neo4j."):
                original_modules[key] = sys.modules.pop(key)

        try:
            # Force reimport of memgraph module
            import importlib

            if "graph_builder.graphdb.memgraph" in sys.modules:
                del sys.modules["graph_builder.graphdb.memgraph"]

            from graph_builder.graphdb.memgraph import MemgraphGraphDB

            db = MemgraphGraphDB()

            # Mock import to fail
            def mock_import(name, *args, **kwargs):
                if name == "neo4j":
                    raise ImportError("No module named 'neo4j'")
                return original_import(name, *args, **kwargs)

            import builtins

            original_import = builtins.__import__
            builtins.__import__ = mock_import

            try:
                with pytest.raises(ImportError) as exc_info:
                    _ = db.driver

                assert "neo4j" in str(exc_info.value)
            finally:
                builtins.__import__ = original_import
        finally:
            # Restore original modules
            sys.modules.update(original_modules)


class TestProtocolCompliance:
    """Tests for protocol compliance."""

    def test_memgraph_implements_graphdb_protocol(self):
        """MemgraphGraphDB should implement the GraphDB protocol."""
        from graph_builder.pipeline.base import GraphDB
        from graph_builder.graphdb.memgraph import MemgraphGraphDB

        # Protocol check using isinstance with runtime_checkable
        db = MemgraphGraphDB()
        assert isinstance(db, GraphDB)

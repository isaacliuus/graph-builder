"""Tests for the graphdb factory module."""

import sys
from unittest.mock import MagicMock, patch

import pytest


class TestCreateGraphdbFromSettings:
    """Tests for create_graphdb_from_settings function."""

    def test_returns_none_when_disabled(self):
        """Should return None when use_graphdb is False."""
        mock_settings = MagicMock()
        mock_settings.use_graphdb = False

        with patch(
            "graph_builder.config.settings.get_settings", return_value=mock_settings
        ):
            from graph_builder.graphdb.factory import create_graphdb_from_settings

            result = create_graphdb_from_settings()

            assert result is None

    def test_creates_memgraph_when_enabled(self):
        """Should create and connect MemgraphGraphDB when use_graphdb is True."""
        mock_settings = MagicMock()
        mock_settings.use_graphdb = True
        mock_settings.memgraph_host = "testhost"
        mock_settings.memgraph_port = 7688
        mock_settings.memgraph_username = "user"
        mock_settings.memgraph_password = "pass"
        mock_settings.memgraph_database = "testdb"
        mock_settings.memgraph_encrypted = True

        mock_driver = MagicMock()
        mock_graph_database = MagicMock()
        mock_graph_database.driver.return_value = mock_driver

        mock_neo4j_module = MagicMock()
        mock_neo4j_module.GraphDatabase = mock_graph_database

        with patch(
            "graph_builder.config.settings.get_settings", return_value=mock_settings
        ):
            with patch.dict(sys.modules, {"neo4j": mock_neo4j_module}):
                from graph_builder.graphdb.factory import create_graphdb_from_settings

                result = create_graphdb_from_settings()

                assert result is not None
                assert result.host == "testhost"
                assert result.port == 7688
                assert result.username == "user"
                assert result.password == "pass"
                assert result.database == "testdb"
                assert result.encrypted is True
                mock_driver.verify_connectivity.assert_called_once()

    def test_uses_default_settings(self):
        """Should use default settings values."""
        mock_settings = MagicMock()
        mock_settings.use_graphdb = True
        mock_settings.memgraph_host = "localhost"
        mock_settings.memgraph_port = 7687
        mock_settings.memgraph_username = ""
        mock_settings.memgraph_password = ""
        mock_settings.memgraph_database = "memgraph"
        mock_settings.memgraph_encrypted = False

        mock_driver = MagicMock()
        mock_graph_database = MagicMock()
        mock_graph_database.driver.return_value = mock_driver

        mock_neo4j_module = MagicMock()
        mock_neo4j_module.GraphDatabase = mock_graph_database

        with patch(
            "graph_builder.config.settings.get_settings", return_value=mock_settings
        ):
            with patch.dict(sys.modules, {"neo4j": mock_neo4j_module}):
                from graph_builder.graphdb.factory import create_graphdb_from_settings

                result = create_graphdb_from_settings()

                assert result is not None
                assert result.host == "localhost"
                assert result.port == 7687


class TestPipelineBuilderWithGraphDB:
    """Tests for PipelineBuilder integration with GraphDB from settings."""

    def test_default_pipeline_without_graphdb(self):
        """Default pipeline should not have graphdb when disabled."""
        mock_settings = MagicMock()
        mock_settings.use_graphdb = False

        with patch(
            "graph_builder.config.settings.get_settings", return_value=mock_settings
        ):
            from graph_builder.pipeline.builder import PipelineBuilder

            pipeline = PipelineBuilder.default()

            assert pipeline.graphdb is None

    def test_default_pipeline_with_graphdb(self):
        """Default pipeline should have graphdb when enabled."""
        mock_settings = MagicMock()
        mock_settings.use_graphdb = True
        mock_settings.memgraph_host = "localhost"
        mock_settings.memgraph_port = 7687
        mock_settings.memgraph_username = ""
        mock_settings.memgraph_password = ""
        mock_settings.memgraph_database = "memgraph"
        mock_settings.memgraph_encrypted = False

        mock_driver = MagicMock()
        mock_graph_database = MagicMock()
        mock_graph_database.driver.return_value = mock_driver

        mock_neo4j_module = MagicMock()
        mock_neo4j_module.GraphDatabase = mock_graph_database

        with patch(
            "graph_builder.config.settings.get_settings", return_value=mock_settings
        ):
            with patch.dict(sys.modules, {"neo4j": mock_neo4j_module}):
                from graph_builder.pipeline.builder import PipelineBuilder

                pipeline = PipelineBuilder.default()

                assert pipeline.graphdb is not None

    @patch("graph_builder.extraction.llm_extractor.LLMEntityExtractor")
    @patch("graph_builder.extraction.llm_extractor.LLMRelationshipExtractor")
    def test_llm_pipeline_without_graphdb(self, mock_rel_ext, mock_entity_ext):
        """LLM pipeline should not have graphdb when disabled."""
        mock_entity_ext.return_value = MagicMock()
        mock_rel_ext.return_value = MagicMock()

        mock_settings = MagicMock()
        mock_settings.use_graphdb = False

        with patch(
            "graph_builder.config.settings.get_settings", return_value=mock_settings
        ):
            from graph_builder.pipeline.builder import PipelineBuilder

            pipeline = PipelineBuilder.with_llm(api_key="test-key")

            assert pipeline.graphdb is None

    @patch("graph_builder.extraction.llm_extractor.LLMEntityExtractor")
    @patch("graph_builder.extraction.llm_extractor.LLMRelationshipExtractor")
    def test_llm_pipeline_with_graphdb(self, mock_rel_ext, mock_entity_ext):
        """LLM pipeline should have graphdb when enabled."""
        mock_entity_ext.return_value = MagicMock()
        mock_rel_ext.return_value = MagicMock()

        mock_settings = MagicMock()
        mock_settings.use_graphdb = True
        mock_settings.memgraph_host = "localhost"
        mock_settings.memgraph_port = 7687
        mock_settings.memgraph_username = ""
        mock_settings.memgraph_password = ""
        mock_settings.memgraph_database = "memgraph"
        mock_settings.memgraph_encrypted = False

        mock_driver = MagicMock()
        mock_graph_database = MagicMock()
        mock_graph_database.driver.return_value = mock_driver

        mock_neo4j_module = MagicMock()
        mock_neo4j_module.GraphDatabase = mock_graph_database

        with patch(
            "graph_builder.config.settings.get_settings", return_value=mock_settings
        ):
            with patch.dict(sys.modules, {"neo4j": mock_neo4j_module}):
                from graph_builder.pipeline.builder import PipelineBuilder

                pipeline = PipelineBuilder.with_llm(api_key="test-key")

                assert pipeline.graphdb is not None

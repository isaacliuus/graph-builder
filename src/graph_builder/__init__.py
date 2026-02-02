"""Knowledge Graph Builder - A modular pipeline for entity and relationship extraction."""

from graph_builder.models.document import Document, Chunk
from graph_builder.models.entity import Entity, EntityType
from graph_builder.models.relationship import Relationship, RelationshipType
from graph_builder.models.graph import KnowledgeGraph, GraphNode, GraphEdge
from graph_builder.pipeline.builder import PipelineBuilder
from graph_builder.graphdb.base import GraphDBBase

__all__ = [
    "Document",
    "Chunk",
    "Entity",
    "EntityType",
    "Relationship",
    "RelationshipType",
    "KnowledgeGraph",
    "GraphNode",
    "GraphEdge",
    "PipelineBuilder",
    "GraphDBBase",
    "MemgraphGraphDB",
]


def __getattr__(name: str):
    """Lazy load MemgraphGraphDB to avoid import errors when neo4j is not installed."""
    if name == "MemgraphGraphDB":
        from graph_builder.graphdb.memgraph import MemgraphGraphDB

        return MemgraphGraphDB
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

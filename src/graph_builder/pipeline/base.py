"""Base classes and protocols for the pipeline."""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from graph_builder.models.document import Document, Chunk
from graph_builder.models.entity import Entity
from graph_builder.models.relationship import Relationship
from graph_builder.models.graph import KnowledgeGraph


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
class PipelineStage(Protocol):
    """Protocol for pipeline stages."""

    def process(self, context: PipelineContext) -> PipelineContext:
        """Process the context and return the updated context."""
        ...


@runtime_checkable
class Chunker(Protocol):
    """Protocol for text chunkers."""

    def chunk(self, documents: list[Document]) -> list[Chunk]:
        """Split documents into chunks."""
        ...


@runtime_checkable
class EntityExtractor(Protocol):
    """Protocol for entity extractors."""

    def extract(self, chunks: list[Chunk]) -> list[Entity]:
        """Extract entities from chunks."""
        ...


@runtime_checkable
class RelationshipExtractor(Protocol):
    """Protocol for relationship extractors."""

    def extract(self, chunks: list[Chunk], entities: list[Entity]) -> list[Relationship]:
        """Extract relationships between entities."""
        ...


@runtime_checkable
class GraphBuilder(Protocol):
    """Protocol for graph builders."""

    def build(
        self, entities: list[Entity], relationships: list[Relationship]
    ) -> KnowledgeGraph:
        """Build a knowledge graph from entities and relationships."""
        ...

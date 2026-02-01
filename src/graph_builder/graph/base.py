"""Base class for graph builders."""

from abc import ABC, abstractmethod

from graph_builder.models.entity import Entity
from graph_builder.models.relationship import Relationship
from graph_builder.models.graph import KnowledgeGraph


class GraphBuilderBase(ABC):  # pylint: disable=too-few-public-methods
    """Abstract base class for graph builders."""

    @abstractmethod
    def build(
        self, entities: list[Entity], relationships: list[Relationship]
    ) -> KnowledgeGraph:
        """Build a knowledge graph from entities and relationships."""

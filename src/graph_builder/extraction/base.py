"""Base classes for extractors."""

from abc import ABC, abstractmethod

from graph_builder.models.document import Chunk
from graph_builder.models.entity import Entity
from graph_builder.models.relationship import Relationship


class EntityExtractorBase(ABC):  # pylint: disable=too-few-public-methods
    """Abstract base class for entity extractors."""

    @abstractmethod
    def extract(self, chunks: list[Chunk]) -> list[Entity]:
        """Extract entities from chunks."""


class RelationshipExtractorBase(ABC):  # pylint: disable=too-few-public-methods
    """Abstract base class for relationship extractors."""

    @abstractmethod
    def extract(
        self, chunks: list[Chunk], entities: list[Entity]
    ) -> list[Relationship]:
        """Extract relationships between entities."""

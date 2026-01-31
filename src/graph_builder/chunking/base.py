"""Base class for chunkers."""

from abc import ABC, abstractmethod

from graph_builder.models.document import Document, Chunk


class ChunkerBase(ABC):
    """Abstract base class for text chunkers."""

    @abstractmethod
    def chunk(self, documents: list[Document]) -> list[Chunk]:
        """Split documents into chunks."""
        pass

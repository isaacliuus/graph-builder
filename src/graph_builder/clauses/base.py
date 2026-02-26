"""Base protocol for clause extractors."""

from typing import Protocol, runtime_checkable

from graph_builder.models import Document, Clause


@runtime_checkable
class ClauseExtractor(Protocol):
    """Protocol for clause extraction implementations."""

    def extract(self, document: Document) -> list[Clause]:
        """Extract clauses from a document.

        Args:
            document: Document to extract clauses from. Should have paragraph
                metadata from DocxParser for best results.

        Returns:
            List of extracted clauses with location information.
        """
        ...

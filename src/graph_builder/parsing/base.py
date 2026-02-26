"""Base protocol for document parsers."""

from pathlib import Path
from typing import Protocol, runtime_checkable

from graph_builder.models import Document


@runtime_checkable
class DocumentParser(Protocol):
    """Protocol for document parsing implementations."""

    def parse(self, file_path: Path) -> Document:
        """Parse a document file and return a Document model.

        Args:
            file_path: Path to the document file.

        Returns:
            Document with content and metadata extracted from the file.
        """
        ...

    def supports(self, file_path: Path) -> bool:
        """Check if this parser supports the given file type.

        Args:
            file_path: Path to the document file.

        Returns:
            True if this parser can handle the file type.
        """
        ...

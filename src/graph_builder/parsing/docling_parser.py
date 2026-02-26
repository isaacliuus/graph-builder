"""Parser for PDF files using Docling."""

from pathlib import Path

from graph_builder.models import Document
from graph_builder.parsing.utils import MARKDOWN_HEADING_PATTERN as _MARKDOWN_HEADING_PATTERN
from graph_builder.parsing.utils import SECTION_NUMBER_PATTERN as _SECTION_NUMBER_PATTERN
from graph_builder.parsing.utils import parse_markdown, validate_file


class DoclingPdfParser:
    """Parser for .pdf files using Docling.

    Docling is an open-source document parsing library by IBM that provides
    excellent PDF understanding with advanced table, OCR, and formula support.
    It outputs markdown which is then parsed into paragraph metadata.
    """

    SUPPORTED_EXTENSIONS = {".pdf"}
    SECTION_NUMBER_PATTERN = _SECTION_NUMBER_PATTERN
    HEADING_PATTERN = _MARKDOWN_HEADING_PATTERN

    def __init__(self) -> None:
        """Initialize the parser."""
        self._docling = None

    @property
    def docling(self):
        """Lazy-load docling module."""
        if self._docling is None:
            try:
                from docling.document_converter import DocumentConverter

                self._docling = {"DocumentConverter": DocumentConverter}
            except ImportError as e:
                raise ImportError(
                    "Docling is required for Docling PDF parsing. "
                    "Install it with: uv sync --extra docling"
                ) from e
        return self._docling

    def supports(self, file_path: Path) -> bool:
        """Check if this parser supports the given file type."""
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def parse(self, file_path: Path) -> Document:
        """Parse a .pdf file using Docling and return a Document model.

        Args:
            file_path: Path to the .pdf file.

        Returns:
            Document with content and paragraph metadata.

        Raises:
            ValueError: If file type is not supported.
            FileNotFoundError: If file does not exist.
        """
        file_path = validate_file(Path(file_path), self.SUPPORTED_EXTENSIONS)

        # Extract markdown content using Docling
        md_content = self._extract_with_docling(file_path)

        # Parse markdown into paragraphs
        paragraphs_data, content_parts = parse_markdown(md_content)

        full_content = "\n".join(content_parts)

        return Document(
            content=full_content,
            source=str(file_path),
            metadata={
                "file_type": "pdf",
                "file_name": file_path.name,
                "parser": "docling",
                "paragraphs": paragraphs_data,
                "paragraph_count": len(paragraphs_data),
            },
        )

    def _parse_markdown(self, md_content: str) -> tuple[list[dict], list[str]]:
        """Parse markdown content into paragraph metadata (delegates to utils)."""
        return parse_markdown(md_content)

    def _extract_with_docling(self, file_path: Path) -> str:
        """Extract markdown content from PDF using Docling.

        Args:
            file_path: Path to the PDF file.

        Returns:
            Extracted markdown content.
        """
        DocumentConverter = self.docling["DocumentConverter"]

        converter = DocumentConverter()
        result = converter.convert(str(file_path))

        return result.document.export_to_markdown()


class DoclingParser(DoclingPdfParser):
    """Parser for both .pdf and .docx files using Docling.

    Extends DoclingPdfParser to also handle .docx files, since Docling's
    DocumentConverter supports both formats natively.
    """

    SUPPORTED_EXTENSIONS = {".pdf", ".docx"}

    def parse(self, file_path: Path) -> Document:
        """Parse a .pdf or .docx file using Docling."""
        doc = super().parse(file_path)
        # Set file_type based on actual suffix
        suffix = Path(file_path).suffix.lower()
        doc.metadata["file_type"] = suffix.lstrip(".")
        return doc

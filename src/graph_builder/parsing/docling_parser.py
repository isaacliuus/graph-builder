"""Parser for PDF files using Docling."""

import re
from pathlib import Path

from graph_builder.models import Document


class DoclingPdfParser:
    """Parser for .pdf files using Docling.

    Docling is an open-source document parsing library by IBM that provides
    excellent PDF understanding with advanced table, OCR, and formula support.
    It outputs markdown which is then parsed into paragraph metadata.
    """

    SUPPORTED_EXTENSIONS = {".pdf"}
    SECTION_NUMBER_PATTERN = re.compile(r"^(\d+(?:\.\d+)*\.?)\s+")

    # Markdown heading pattern (e.g., "# Heading", "## Subheading")
    HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$")

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
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not self.supports(file_path):
            raise ValueError(
                f"Unsupported file type: {file_path.suffix}. "
                f"Supported: {self.SUPPORTED_EXTENSIONS}"
            )

        # Extract markdown content using Docling
        md_content = self._extract_with_docling(file_path)

        # Parse markdown into paragraphs
        paragraphs_data, content_parts = self._parse_markdown(md_content)

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

    def _parse_markdown(self, md_content: str) -> tuple[list[dict], list[str]]:
        """Parse markdown content into paragraph metadata.

        Args:
            md_content: Markdown content from Docling.

        Returns:
            Tuple of (paragraphs_data, content_parts).
        """
        paragraphs_data = []
        content_parts = []
        current_char_offset = 0

        # Split by double newlines to get logical paragraphs
        # But also handle single lines that are headings
        lines = md_content.split("\n")
        current_para = []

        for line in lines:
            stripped = line.strip()

            # Check if this is a heading
            heading_match = self.HEADING_PATTERN.match(stripped)

            if heading_match:
                # Flush any accumulated paragraph first
                if current_para:
                    para_text = " ".join(current_para).strip()
                    if para_text:
                        para_data = self._create_paragraph_data(
                            para_text,
                            len(paragraphs_data),
                            current_char_offset,
                            is_heading=False,
                        )
                        paragraphs_data.append(para_data)
                        content_parts.append(para_text)
                        current_char_offset += len(para_text) + 1
                    current_para = []

                # Process heading
                heading_level = len(heading_match.group(1))
                heading_text = heading_match.group(2).strip()

                if heading_text:
                    para_data = self._create_paragraph_data(
                        heading_text,
                        len(paragraphs_data),
                        current_char_offset,
                        is_heading=True,
                        heading_level=heading_level,
                    )
                    paragraphs_data.append(para_data)
                    content_parts.append(heading_text)
                    current_char_offset += len(heading_text) + 1

            elif stripped:
                # Regular text line
                current_para.append(stripped)

            else:
                # Empty line - paragraph break
                if current_para:
                    para_text = " ".join(current_para).strip()
                    if para_text:
                        para_data = self._create_paragraph_data(
                            para_text,
                            len(paragraphs_data),
                            current_char_offset,
                            is_heading=False,
                        )
                        paragraphs_data.append(para_data)
                        content_parts.append(para_text)
                        current_char_offset += len(para_text) + 1
                    current_para = []

        # Flush any remaining paragraph
        if current_para:
            para_text = " ".join(current_para).strip()
            if para_text:
                para_data = self._create_paragraph_data(
                    para_text,
                    len(paragraphs_data),
                    current_char_offset,
                    is_heading=False,
                )
                paragraphs_data.append(para_data)
                content_parts.append(para_text)

        return paragraphs_data, content_parts

    def _create_paragraph_data(
        self,
        text: str,
        index: int,
        start_char: int,
        is_heading: bool,
        heading_level: int | None = None,
    ) -> dict:
        """Create paragraph metadata dict.

        Args:
            text: Paragraph text.
            index: Paragraph index.
            start_char: Starting character offset.
            is_heading: Whether this is a heading.
            heading_level: Heading level (1-6) if applicable.

        Returns:
            Paragraph metadata dict.
        """
        # Extract section number from text
        section_match = self.SECTION_NUMBER_PATTERN.match(text)
        section_number = section_match.group(1).rstrip(".") if section_match else None

        # Determine style
        if is_heading:
            if heading_level and heading_level <= 2:
                style = f"Heading {heading_level}"
            else:
                style = "Heading"
        else:
            style = "Normal"

        return {
            "index": index,
            "text": text,
            "style": style,
            "is_heading": is_heading,
            "section_number": section_number,
            "start_char": start_char,
            "end_char": start_char + len(text),
        }


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

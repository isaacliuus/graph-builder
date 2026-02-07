"""Parser for PDF files using MinerU."""

import re
import tempfile
from pathlib import Path

from graph_builder.models import Document


class MineruPdfParser:
    """Parser for .pdf files using MinerU.

    MinerU provides high-quality PDF extraction with support for complex
    layouts, tables, and formulas. It outputs markdown which is then
    parsed into paragraph metadata.
    """

    SUPPORTED_EXTENSIONS = {".pdf"}
    SECTION_NUMBER_PATTERN = re.compile(r"^(\d+(?:\.\d+)*\.?)\s+")

    # Markdown heading pattern (e.g., "# Heading", "## Subheading")
    HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$")

    def __init__(self, method: str = "auto", lang: str = "en") -> None:
        """Initialize the parser.

        Args:
            method: Parsing method - "auto", "ocr", or "txt".
            lang: Language for OCR - "en" for English, "ch" for Chinese.
        """
        self._mineru = None
        self.method = method
        self.lang = lang

    @property
    def mineru(self):
        """Lazy-load mineru module."""
        if self._mineru is None:
            try:
                from mineru.cli.common import do_parse

                self._mineru = {"do_parse": do_parse}
            except ImportError as e:
                raise ImportError(
                    "MinerU is required for MinerU PDF parsing. "
                    "Install it with: uv pip install -U 'mineru[all]'"
                ) from e
        return self._mineru

    def supports(self, file_path: Path) -> bool:
        """Check if this parser supports the given file type."""
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def parse(self, file_path: Path) -> Document:
        """Parse a .pdf file using MinerU and return a Document model.

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

        # Read PDF bytes
        pdf_bytes = file_path.read_bytes()

        # Extract markdown content using MinerU
        md_content = self._extract_with_mineru(pdf_bytes, file_path.name)

        # Parse markdown into paragraphs
        paragraphs_data, content_parts = self._parse_markdown(md_content)

        full_content = "\n".join(content_parts)

        return Document(
            content=full_content,
            source=str(file_path),
            metadata={
                "file_type": "pdf",
                "file_name": file_path.name,
                "parser": "mineru",
                "paragraphs": paragraphs_data,
                "paragraph_count": len(paragraphs_data),
            },
        )

    def _extract_with_mineru(self, pdf_bytes: bytes, filename: str) -> str:
        """Extract markdown content from PDF using MinerU.

        Args:
            pdf_bytes: Raw PDF file bytes.
            filename: Original filename for reference.

        Returns:
            Extracted markdown content.
        """
        do_parse = self.mineru["do_parse"]

        # Create temporary directory for output
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Run MinerU parsing
            do_parse(
                output_dir=str(temp_path),
                pdf_file_names=[filename],
                pdf_bytes_list=[pdf_bytes],
                p_lang_list=[self.lang],
                backend="pipeline",
                parse_method=self.method,
                formula_enable=True,
                table_enable=True,
                f_draw_layout_bbox=False,
                f_draw_span_bbox=False,
                f_dump_md=True,
                f_dump_middle_json=False,
                f_dump_model_output=False,
                f_dump_orig_pdf=False,
                f_dump_content_list=False,
            )

            # Find the generated markdown file
            # MinerU outputs to output_dir/filename_without_ext/filename_without_ext.md
            base_name = Path(filename).stem
            md_file = temp_path / base_name / f"{base_name}.md"

            if md_file.exists():
                return md_file.read_text(encoding="utf-8")

            # Try alternative location
            for md_path in temp_path.rglob("*.md"):
                return md_path.read_text(encoding="utf-8")

            return ""

    def _parse_markdown(self, md_content: str) -> tuple[list[dict], list[str]]:
        """Parse markdown content into paragraph metadata.

        Args:
            md_content: Markdown content from MinerU.

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

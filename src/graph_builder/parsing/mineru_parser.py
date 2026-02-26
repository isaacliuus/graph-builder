"""Parser for PDF files using MinerU."""

import tempfile
from pathlib import Path

from graph_builder.models import Document
from graph_builder.parsing.utils import MARKDOWN_HEADING_PATTERN as _MARKDOWN_HEADING_PATTERN
from graph_builder.parsing.utils import SECTION_NUMBER_PATTERN as _SECTION_NUMBER_PATTERN
from graph_builder.parsing.utils import parse_markdown, validate_file


class MineruPdfParser:
    """Parser for .pdf files using MinerU.

    MinerU provides high-quality PDF extraction with support for complex
    layouts, tables, and formulas. It outputs markdown which is then
    parsed into paragraph metadata.
    """

    SUPPORTED_EXTENSIONS = {".pdf"}
    SECTION_NUMBER_PATTERN = _SECTION_NUMBER_PATTERN
    HEADING_PATTERN = _MARKDOWN_HEADING_PATTERN

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
        file_path = validate_file(Path(file_path), self.SUPPORTED_EXTENSIONS)

        # Read PDF bytes
        pdf_bytes = file_path.read_bytes()

        # Extract markdown content using MinerU
        md_content = self._extract_with_mineru(pdf_bytes, file_path.name)

        # Parse markdown into paragraphs
        paragraphs_data, content_parts = parse_markdown(md_content)

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

    def _parse_markdown(self, md_content: str) -> tuple[list[dict], list[str]]:
        """Parse markdown content into paragraph metadata (delegates to utils)."""
        return parse_markdown(md_content)

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

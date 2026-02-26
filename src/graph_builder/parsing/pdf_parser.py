"""Parser for PDF files."""

from pathlib import Path

from graph_builder.models import Document
from graph_builder.parsing.utils import SECTION_NUMBER_PATTERN as _SECTION_NUMBER_PATTERN
from graph_builder.parsing.utils import validate_file


class PdfParser:
    """Parser for .pdf files using PyMuPDF."""

    SUPPORTED_EXTENSIONS = {".pdf"}
    SECTION_NUMBER_PATTERN = _SECTION_NUMBER_PATTERN

    # Font size threshold for heading detection (relative to median font size)
    HEADING_SIZE_RATIO = 1.2

    def __init__(self) -> None:
        """Initialize the parser, lazily loading PyMuPDF."""
        self._fitz_module = None

    @property
    def fitz(self):
        """Lazy-load PyMuPDF (fitz) module."""
        if self._fitz_module is None:
            try:
                import fitz

                self._fitz_module = fitz
            except ImportError as e:
                raise ImportError(
                    "PyMuPDF is required for .pdf parsing. "
                    "Install it with: uv sync --extra contracts"
                ) from e
        return self._fitz_module

    def supports(self, file_path: Path) -> bool:
        """Check if this parser supports the given file type."""
        return file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS

    def parse(self, file_path: Path) -> Document:
        """Parse a .pdf file and return a Document model.

        Args:
            file_path: Path to the .pdf file.

        Returns:
            Document with content and paragraph metadata.

        Raises:
            ValueError: If file type is not supported.
            FileNotFoundError: If file does not exist.
        """
        file_path = validate_file(Path(file_path), self.SUPPORTED_EXTENSIONS)

        pdf = self.fitz.open(file_path)
        all_blocks, font_sizes = self._collect_blocks(pdf)
        pdf.close()

        # Calculate median font size for heading detection
        if font_sizes:
            sorted_sizes = sorted(font_sizes)
            mid = len(sorted_sizes) // 2
            median_size = (
                sorted_sizes[mid]
                if len(sorted_sizes) % 2
                else (sorted_sizes[mid - 1] + sorted_sizes[mid]) / 2
            )
        else:
            median_size = 12

        heading_threshold = median_size * self.HEADING_SIZE_RATIO
        paragraphs_data, content_parts = self._build_paragraphs(all_blocks, heading_threshold)

        full_content = "\n".join(content_parts)

        return Document(
            content=full_content,
            source=str(file_path),
            metadata={
                "file_type": "pdf",
                "file_name": file_path.name,
                "paragraphs": paragraphs_data,
                "paragraph_count": len(paragraphs_data),
            },
        )

    def _collect_blocks(self, pdf) -> tuple[list[dict], list[float]]:
        """First pass: collect text spans with font metadata from all pages.

        Args:
            pdf: Open PyMuPDF document.

        Returns:
            Tuple of (all_blocks, font_sizes) where all_blocks is a list of
            dicts with keys "text", "size", "flags", and font_sizes is the
            flat list of all observed font sizes.
        """
        all_blocks: list[dict] = []
        font_sizes: list[float] = []

        for page in pdf:
            blocks = page.get_text("dict", flags=self.fitz.TEXT_PRESERVE_WHITESPACE)["blocks"]
            for block in blocks:
                if block.get("type") != 0:  # Skip non-text blocks (images, etc.)
                    continue
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if text:
                            font_size = span.get("size", 12)
                            font_sizes.append(font_size)
                            all_blocks.append(
                                {
                                    "text": text,
                                    "size": font_size,
                                    "flags": span.get("flags", 0),
                                }
                            )

        return all_blocks, font_sizes

    def _build_paragraphs(
        self, all_blocks: list[dict], heading_threshold: float
    ) -> tuple[list[dict], list[str]]:
        """Second pass: group spans into paragraphs and build metadata.

        Args:
            all_blocks: Collected text spans from _collect_blocks().
            heading_threshold: Font size above which a span is a heading.

        Returns:
            Tuple of (paragraphs_data, content_parts).
        """
        paragraphs_data: list[dict] = []
        content_parts: list[str] = []
        current_char_offset = 0

        current_para_text: list[str] = []
        current_para_is_heading = False
        current_para_max_size = 0.0

        for i, block_info in enumerate(all_blocks):
            text = block_info["text"]
            size = block_info["size"]
            flags = block_info["flags"]

            # Check if this is a heading based on font size or bold flag
            is_bold = flags & 2**4  # Bit 4 indicates bold
            is_heading_span = size >= heading_threshold or is_bold

            current_para_text.append(text)
            if is_heading_span:
                current_para_is_heading = True
            current_para_max_size = max(current_para_max_size, size)

            # End paragraph on certain conditions
            is_last = i == len(all_blocks) - 1
            ends_sentence = text.rstrip().endswith((".", ":", "?", "!"))

            if is_last or ends_sentence or is_heading_span:
                para_text = " ".join(current_para_text).strip()
                if para_text:
                    is_heading = current_para_is_heading

                    section_match = _SECTION_NUMBER_PATTERN.match(para_text)
                    section_number = (
                        section_match.group(1).rstrip(".") if section_match else None
                    )

                    if current_para_max_size >= heading_threshold * 1.3 or is_heading:
                        style = "Heading"
                    else:
                        style = "Normal"

                    para_data = {
                        "index": len(paragraphs_data),
                        "text": para_text,
                        "style": style,
                        "is_heading": is_heading,
                        "section_number": section_number,
                        "start_char": current_char_offset,
                        "end_char": current_char_offset + len(para_text),
                    }
                    paragraphs_data.append(para_data)
                    content_parts.append(para_text)
                    current_char_offset += len(para_text) + 1  # +1 for newline

                # Reset for next paragraph
                current_para_text = []
                current_para_is_heading = False
                current_para_max_size = 0.0

        return paragraphs_data, content_parts

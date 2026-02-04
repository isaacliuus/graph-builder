"""Parser for PDF files."""

import re
from pathlib import Path

from graph_builder.models import Document


class PdfParser:
    """Parser for .pdf files using PyMuPDF."""

    SUPPORTED_EXTENSIONS = {".pdf"}
    SECTION_NUMBER_PATTERN = re.compile(r"^(\d+(?:\.\d+)*\.?)\s+")

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
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not self.supports(file_path):
            raise ValueError(
                f"Unsupported file type: {file_path.suffix}. "
                f"Supported: {self.SUPPORTED_EXTENSIONS}"
            )

        pdf = self.fitz.open(file_path)

        # First pass: collect all text blocks with font info to determine median font size
        all_blocks = []
        font_sizes = []

        for page in pdf:
            blocks = page.get_text("dict", flags=self.fitz.TEXT_PRESERVE_WHITESPACE)[
                "blocks"
            ]
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

        # Second pass: group spans into paragraphs and build metadata
        paragraphs_data = []
        content_parts = []
        current_char_offset = 0

        # Group consecutive spans into paragraphs (simplified: each text block line = paragraph)
        current_para_text = []
        current_para_is_heading = False
        current_para_max_size = 0

        for i, block_info in enumerate(all_blocks):
            text = block_info["text"]
            size = block_info["size"]
            flags = block_info["flags"]

            # Check if this is a heading based on font size or bold flag
            is_bold = flags & 2**4  # Bit 4 indicates bold
            is_heading_span = size >= heading_threshold or is_bold

            # Simple heuristic: if text ends with certain punctuation, it's end of paragraph
            # Otherwise, accumulate spans
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
                    # Determine if heading
                    is_heading = current_para_is_heading

                    # Extract section number
                    section_match = self.SECTION_NUMBER_PATTERN.match(para_text)
                    section_number = (
                        section_match.group(1).rstrip(".") if section_match else None
                    )

                    # Determine style based on font size
                    if current_para_max_size >= heading_threshold * 1.3:
                        style = "Heading"
                    elif is_heading:
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
                current_para_max_size = 0

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

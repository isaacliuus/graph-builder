"""Shared utilities for document parsers."""

import re
from pathlib import Path

SECTION_NUMBER_PATTERN = re.compile(r"^(\d+(?:\.\d+)*\.?)\s+")
MARKDOWN_HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+)$")


def validate_file(file_path: Path, supported_extensions: set[str]) -> Path:
    """Validate that a file exists and has a supported extension."""
    file_path = Path(file_path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if file_path.suffix.lower() not in supported_extensions:
        raise ValueError(
            f"Unsupported file type: {file_path.suffix}. "
            f"Supported: {supported_extensions}"
        )
    return file_path


def create_paragraph_data(
    text: str,
    index: int,
    start_char: int,
    is_heading: bool,
    heading_level: int | None = None,
) -> dict:
    """Create standard paragraph metadata dict used by all parsers."""
    section_match = SECTION_NUMBER_PATTERN.match(text)
    section_number = section_match.group(1).rstrip(".") if section_match else None

    if is_heading:
        style = f"Heading {heading_level}" if heading_level and heading_level <= 2 else "Heading"
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


def parse_markdown(md_content: str) -> tuple[list[dict], list[str]]:
    """Parse markdown content into paragraph metadata.

    Shared by MinerU and Docling parsers which both produce markdown output.

    Args:
        md_content: Markdown content to parse.

    Returns:
        Tuple of (paragraphs_data, content_parts).
    """
    paragraphs_data = []
    content_parts = []
    current_char_offset = 0

    # Split by lines; headings are self-contained, plain text accumulates
    lines = md_content.split("\n")
    current_para: list[str] = []

    for line in lines:
        stripped = line.strip()

        heading_match = MARKDOWN_HEADING_PATTERN.match(stripped)

        if heading_match:
            # Flush any accumulated paragraph first
            if current_para:
                para_text = " ".join(current_para).strip()
                if para_text:
                    para_data = create_paragraph_data(
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
                para_data = create_paragraph_data(
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
            # Empty line — paragraph break
            if current_para:
                para_text = " ".join(current_para).strip()
                if para_text:
                    para_data = create_paragraph_data(
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
            para_data = create_paragraph_data(
                para_text,
                len(paragraphs_data),
                current_char_offset,
                is_heading=False,
            )
            paragraphs_data.append(para_data)
            content_parts.append(para_text)

    return paragraphs_data, content_parts

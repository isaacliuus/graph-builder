# Parsing Module

Document parsing utilities for extracting text and structure from various file formats.

## Files

- `base.py` - `DocumentParser` Protocol defining the parser interface
- `docx_parser.py` - Microsoft Word .docx file parser using python-docx

## Protocol

```python
@runtime_checkable
class DocumentParser(Protocol):
    def parse(self, file_path: Path) -> Document: ...
    def supports(self, file_path: Path) -> bool: ...
```

## DocxParser Features

- Extracts paragraph text with style information (Heading 1, 2, 3, Normal)
- Detects section numbers via regex (e.g., "1.2.3 Title")
- Tracks character offsets for each paragraph
- Stores structured data in `Document.metadata["paragraphs"]`

## Paragraph Metadata Format

```python
{
    "index": 0,                    # Paragraph index in document
    "text": "1.1 Definitions",     # Paragraph text
    "style": "Heading 1",          # Word style name
    "is_heading": True,            # Whether it's a heading style
    "section_number": "1.1",       # Extracted section number (or None)
    "start_char": 0,               # Start character offset
    "end_char": 15,                # End character offset
}
```

## Lazy Loading

The `python-docx` dependency is lazy-loaded to avoid import errors when the `contracts` extra is not installed.

## Installation

```bash
uv sync --extra contracts
```

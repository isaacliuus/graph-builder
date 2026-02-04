# Parsing Module

Document parsing utilities for extracting text and structure from various file formats.

## Files

- `base.py` - `DocumentParser` Protocol defining the parser interface
- `docx_parser.py` - Microsoft Word .docx file parser using python-docx
- `pdf_parser.py` - PDF file parser using PyMuPDF

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

## PdfParser Features

- Extracts text blocks from PDF pages using PyMuPDF (fitz)
- Detects headings via font size (relative to median) and bold flags
- Detects section numbers via regex (same pattern as DocxParser)
- Tracks character offsets for each paragraph
- Stores structured data in same format as DocxParser

## Paragraph Metadata Format

Both parsers produce the same metadata format:

```python
{
    "index": 0,                    # Paragraph index in document
    "text": "1.1 Definitions",     # Paragraph text
    "style": "Heading 1",          # Style name ("Heading" or "Normal" for PDF)
    "is_heading": True,            # Whether it's a heading style
    "section_number": "1.1",       # Extracted section number (or None)
    "start_char": 0,               # Start character offset
    "end_char": 15,                # End character offset
}
```

## Lazy Loading

Both `python-docx` and `PyMuPDF` dependencies are lazy-loaded to avoid import errors when the `contracts` extra is not installed.

## Installation

```bash
uv sync --extra contracts
```

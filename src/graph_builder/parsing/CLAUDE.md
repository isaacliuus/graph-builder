# Parsing Module

Document parsing utilities for extracting text and structure from various file formats.

## Files

- `base.py` - `DocumentParser` Protocol defining the parser interface
- `docx_parser.py` - Microsoft Word .docx file parser using python-docx
- `pdf_parser.py` - PDF file parser using PyMuPDF (fast)
- `mineru_parser.py` - PDF file parser using MinerU (high quality)
- `docling_parser.py` - PDF file parser using Docling (high quality); also contains `DoclingParser` which handles both .pdf and .docx

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

## PdfParser Features (PyMuPDF)

- Extracts text blocks from PDF pages using PyMuPDF (fitz)
- Detects headings via font size (relative to median) and bold flags
- Detects section numbers via regex (same pattern as DocxParser)
- Tracks character offsets for each paragraph
- Fast and lightweight
- Stores structured data in same format as DocxParser

## MineruPdfParser Features (MinerU)

- High-quality PDF extraction using MinerU (magic_pdf)
- Better handling of complex layouts, tables, and formulas
- Outputs markdown which is parsed into paragraph metadata
- Supports OCR for scanned documents
- Configurable parsing method: "auto", "ocr", or "txt"
- Configurable language: "en" (English), "ch" (Chinese)
- Stores structured data in same format as other parsers

## DoclingPdfParser Features (Docling)

- High-quality PDF extraction using Docling (IBM open-source)
- Advanced table, OCR, and formula support
- Outputs markdown which is parsed into paragraph metadata
- Simple API via `DocumentConverter`
- Stores structured data in same format as other parsers

## Paragraph Metadata Format

All parsers produce the same metadata format:

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

All dependencies are lazy-loaded to avoid import errors when optional extras are not installed.

## Installation

```bash
# For PyMuPDF-based parsing (fast)
uv sync --extra contracts

# For MinerU-based parsing (high quality)
uv pip install -U "mineru[all]"

# For Docling-based parsing (high quality)
uv sync --extra docling
```

## DoclingParser Features (Docling, .pdf + .docx)

- Subclass of `DoclingPdfParser` that also supports .docx files
- Docling's `DocumentConverter` handles both formats natively
- Used by `PipelineBuilder.entity_graph()` for contract-aware entity graph pipelines
- Sets `file_type` metadata based on actual file suffix

## Choosing a PDF Parser

| Parser | Speed | Quality | Dependencies |
|--------|-------|---------|--------------|
| PdfParser (PyMuPDF) | Fast | Good | PyMuPDF |
| MineruPdfParser | Slower | Excellent | MinerU (large) |
| DoclingPdfParser | Slower | Excellent | Docling |

Use PyMuPDF for quick processing and MinerU or Docling for complex documents requiring higher accuracy.

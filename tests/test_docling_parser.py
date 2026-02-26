"""Unit tests for Docling PDF parser."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestDoclingPdfParser:
    """Tests for DoclingPdfParser class."""

    def test_supports_pdf(self):
        """Test that parser supports .pdf files."""
        from graph_builder.parsing.docling_parser import DoclingPdfParser

        parser = DoclingPdfParser()
        assert parser.supports(Path("contract.pdf"))
        assert parser.supports(Path("CONTRACT.PDF"))
        assert parser.supports(Path("/path/to/file.pdf"))

    def test_does_not_support_other_formats(self):
        """Test that parser rejects non-.pdf files."""
        from graph_builder.parsing.docling_parser import DoclingPdfParser

        parser = DoclingPdfParser()
        assert not parser.supports(Path("contract.docx"))
        assert not parser.supports(Path("contract.doc"))
        assert not parser.supports(Path("contract.txt"))
        assert not parser.supports(Path("contract.odt"))

    def test_parse_raises_for_unsupported_file(self, tmp_path):
        """Test that parse raises ValueError for unsupported files."""
        from graph_builder.parsing.docling_parser import DoclingPdfParser

        # Create a test file with unsupported extension
        test_file = tmp_path / "contract.docx"
        test_file.touch()

        parser = DoclingPdfParser()
        with pytest.raises(ValueError, match="Unsupported file type"):
            parser.parse(test_file)

    def test_parse_raises_for_missing_file(self):
        """Test that parse raises FileNotFoundError for missing files."""
        from graph_builder.parsing.docling_parser import DoclingPdfParser

        parser = DoclingPdfParser()
        with pytest.raises(FileNotFoundError, match="File not found"):
            parser.parse(Path("nonexistent.pdf"))

    def test_section_number_pattern(self):
        """Test section number regex pattern."""
        from graph_builder.parsing.docling_parser import DoclingPdfParser

        parser = DoclingPdfParser()
        pattern = parser.SECTION_NUMBER_PATTERN

        # Should match
        assert pattern.match("1 Introduction")
        assert pattern.match("1. Introduction")
        assert pattern.match("1.1 Definitions")
        assert pattern.match("1.1. Definitions")
        assert pattern.match("1.2.3 Sub-section")
        assert pattern.match("10.20.30 Deep nesting")

        # Should not match
        assert not pattern.match("Introduction")
        assert not pattern.match("A. Introduction")
        assert not pattern.match("- Item")

    def test_heading_pattern(self):
        """Test markdown heading regex pattern."""
        from graph_builder.parsing.docling_parser import DoclingPdfParser

        parser = DoclingPdfParser()
        pattern = parser.HEADING_PATTERN

        # Should match
        match = pattern.match("# Heading 1")
        assert match
        assert match.group(1) == "#"
        assert match.group(2) == "Heading 1"

        match = pattern.match("## Heading 2")
        assert match
        assert match.group(1) == "##"

        match = pattern.match("### Heading 3")
        assert match
        assert match.group(1) == "###"

        # Should not match
        assert not pattern.match("Regular text")
        assert not pattern.match("  # Indented heading")


class TestDoclingPdfParserIntegration:
    """Integration tests for DoclingPdfParser requiring docling."""

    @pytest.fixture
    def mock_docling(self):
        """Create a mock docling module that returns markdown content."""
        md_content = """# 1. Definitions

The following terms shall have the meanings set forth below.

## 1.1 Agreement

Agreement means this contract between the parties.

# 2. Confidentiality

Each party shall maintain confidential all proprietary information.
"""
        mock_document = MagicMock()
        mock_document.export_to_markdown.return_value = md_content

        mock_result = MagicMock()
        mock_result.document = mock_document

        mock_converter_instance = MagicMock()
        mock_converter_instance.convert.return_value = mock_result

        mock_converter_class = MagicMock(return_value=mock_converter_instance)

        return {"DocumentConverter": mock_converter_class}

    def test_parse_with_mock(self, mock_docling, tmp_path):
        """Test parsing with mocked docling."""
        from graph_builder.parsing.docling_parser import DoclingPdfParser

        # Create a test file
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 test content")

        parser = DoclingPdfParser()
        parser._docling = mock_docling

        doc = parser.parse(test_file)

        assert doc.source == str(test_file)
        assert doc.metadata["file_type"] == "pdf"
        assert doc.metadata["file_name"] == "test.pdf"
        assert doc.metadata["parser"] == "docling"
        assert doc.metadata["paragraph_count"] > 0

        # Check paragraph metadata
        paragraphs = doc.metadata["paragraphs"]
        assert len(paragraphs) > 0

        # First paragraph should be a heading with section number
        assert paragraphs[0]["text"] == "1. Definitions"
        assert paragraphs[0]["is_heading"] is True
        assert paragraphs[0]["section_number"] == "1"

        # Check that content is joined
        assert "1. Definitions" in doc.content
        assert "Confidentiality" in doc.content

    def test_parse_character_offsets(self, mock_docling, tmp_path):
        """Test that character offsets are calculated correctly."""
        from graph_builder.parsing.docling_parser import DoclingPdfParser

        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 test content")

        parser = DoclingPdfParser()
        parser._docling = mock_docling

        doc = parser.parse(test_file)
        paragraphs = doc.metadata["paragraphs"]

        # First paragraph starts at 0
        assert paragraphs[0]["start_char"] == 0
        assert paragraphs[0]["end_char"] == len(paragraphs[0]["text"])

        # Second paragraph starts after first + newline
        if len(paragraphs) > 1:
            expected_start = paragraphs[0]["end_char"] + 1
            assert paragraphs[1]["start_char"] == expected_start

    def test_lazy_import_error(self):
        """Test that ImportError is raised when docling is not installed."""
        from graph_builder.parsing.docling_parser import DoclingPdfParser

        parser = DoclingPdfParser()
        parser._docling = None

        with patch.dict("sys.modules", {"docling": None, "docling.document_converter": None}):
            with patch(
                "builtins.__import__",
                side_effect=ImportError("No module named 'docling'"),
            ):
                with pytest.raises(ImportError, match="Docling"):
                    _ = parser.docling

    def test_parse_markdown_headings(self):
        """Test parsing of markdown headings."""
        from graph_builder.parsing.docling_parser import DoclingPdfParser

        parser = DoclingPdfParser()

        md_content = """# Main Title

Some introduction text.

## 1. First Section

Content of first section.

### 1.1 Subsection

Subsection content.

Regular paragraph without heading.
"""

        paragraphs, content_parts = parser._parse_markdown(md_content)

        # Check headings are detected
        assert paragraphs[0]["text"] == "Main Title"
        assert paragraphs[0]["is_heading"] is True

        # Check section numbers are extracted
        section_para = next(p for p in paragraphs if "First Section" in p["text"])
        assert section_para["section_number"] == "1"

        # Check normal paragraphs
        intro_para = next(p for p in paragraphs if "introduction" in p["text"])
        assert intro_para["is_heading"] is False

    def test_converter_called_with_file_path(self, mock_docling, tmp_path):
        """Test that DocumentConverter is called with the file path."""
        from graph_builder.parsing.docling_parser import DoclingPdfParser

        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 test content")

        parser = DoclingPdfParser()
        parser._docling = mock_docling

        parser.parse(test_file)

        # Verify converter was instantiated and called
        mock_docling["DocumentConverter"].assert_called_once()
        converter_instance = mock_docling["DocumentConverter"].return_value
        converter_instance.convert.assert_called_once_with(str(test_file))

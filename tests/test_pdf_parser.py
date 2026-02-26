"""Unit tests for PDF parser."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestPdfParser:
    """Tests for PdfParser class."""

    def test_supports_pdf(self):
        """Test that parser supports .pdf files."""
        from graph_builder.parsing.pdf_parser import PdfParser

        parser = PdfParser()
        assert parser.supports(Path("contract.pdf"))
        assert parser.supports(Path("CONTRACT.PDF"))
        assert parser.supports(Path("/path/to/file.pdf"))

    def test_does_not_support_other_formats(self):
        """Test that parser rejects non-.pdf files."""
        from graph_builder.parsing.pdf_parser import PdfParser

        parser = PdfParser()
        assert not parser.supports(Path("contract.docx"))
        assert not parser.supports(Path("contract.doc"))
        assert not parser.supports(Path("contract.txt"))
        assert not parser.supports(Path("contract.odt"))

    def test_parse_raises_for_unsupported_file(self, tmp_path):
        """Test that parse raises ValueError for unsupported files."""
        from graph_builder.parsing.pdf_parser import PdfParser

        # Create a test file with unsupported extension
        test_file = tmp_path / "contract.docx"
        test_file.touch()

        parser = PdfParser()
        with pytest.raises(ValueError, match="Unsupported file type"):
            parser.parse(test_file)

    def test_parse_raises_for_missing_file(self):
        """Test that parse raises FileNotFoundError for missing files."""
        from graph_builder.parsing.pdf_parser import PdfParser

        parser = PdfParser()
        with pytest.raises(FileNotFoundError, match="File not found"):
            parser.parse(Path("nonexistent.pdf"))

    def test_section_number_pattern(self):
        """Test section number regex pattern."""
        from graph_builder.parsing.pdf_parser import PdfParser

        parser = PdfParser()
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

    def test_section_number_extraction(self):
        """Test that section numbers are extracted correctly."""
        from graph_builder.parsing.pdf_parser import PdfParser

        parser = PdfParser()
        pattern = parser.SECTION_NUMBER_PATTERN

        match = pattern.match("1.2.3 Title")
        assert match.group(1).rstrip(".") == "1.2.3"

        match = pattern.match("5. Section Five")
        assert match.group(1).rstrip(".") == "5"


class TestPdfParserIntegration:
    """Integration tests for PdfParser requiring PyMuPDF."""

    @pytest.fixture
    def mock_fitz(self):
        """Create a mock fitz (PyMuPDF) module."""
        mock_module = MagicMock()
        mock_module.TEXT_PRESERVE_WHITESPACE = 1

        # Create mock PDF pages with text blocks
        def make_span(text, size=12, flags=0):
            return {"text": text, "size": size, "flags": flags}

        def make_line(spans):
            return {"spans": spans}

        def make_block(lines, block_type=0):
            return {"type": block_type, "lines": lines}

        mock_page = MagicMock()
        mock_page.get_text.return_value = {
            "blocks": [
                make_block(
                    [make_line([make_span("1. Definitions", size=16, flags=16)])]
                ),  # Bold heading
                make_block(
                    [
                        make_line(
                            [
                                make_span(
                                    "The following terms shall have the meanings set forth below."
                                )
                            ]
                        )
                    ]
                ),
                make_block(
                    [make_line([make_span("1.1 Agreement", size=14, flags=16)])]
                ),  # Bold subheading
                make_block(
                    [
                        make_line(
                            [
                                make_span(
                                    "Agreement means this contract between the parties."
                                )
                            ]
                        )
                    ]
                ),
                make_block(
                    [make_line([make_span("2. Confidentiality", size=16, flags=16)])]
                ),  # Bold heading
                make_block(
                    [
                        make_line(
                            [
                                make_span(
                                    "Each party shall maintain confidential all proprietary information."
                                )
                            ]
                        )
                    ]
                ),
            ]
        }

        mock_pdf = MagicMock()
        mock_pdf.__iter__ = lambda self: iter([mock_page])
        mock_module.open.return_value = mock_pdf

        return mock_module

    def test_parse_with_mock(self, mock_fitz, tmp_path):
        """Test parsing with mocked PyMuPDF."""
        from graph_builder.parsing.pdf_parser import PdfParser

        # Create a test file
        test_file = tmp_path / "test.pdf"
        test_file.touch()

        parser = PdfParser()
        parser._fitz_module = mock_fitz

        doc = parser.parse(test_file)

        assert doc.source == str(test_file)
        assert doc.metadata["file_type"] == "pdf"
        assert doc.metadata["file_name"] == "test.pdf"
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

    def test_parse_character_offsets(self, mock_fitz, tmp_path):
        """Test that character offsets are calculated correctly."""
        from graph_builder.parsing.pdf_parser import PdfParser

        test_file = tmp_path / "test.pdf"
        test_file.touch()

        parser = PdfParser()
        parser._fitz_module = mock_fitz

        doc = parser.parse(test_file)
        paragraphs = doc.metadata["paragraphs"]

        # First paragraph starts at 0
        assert paragraphs[0]["start_char"] == 0
        assert paragraphs[0]["end_char"] == len(paragraphs[0]["text"])

        # Second paragraph starts after first + newline
        if len(paragraphs) > 1:
            expected_start = paragraphs[0]["end_char"] + 1
            assert paragraphs[1]["start_char"] == expected_start

    def test_parse_empty_text_skipped(self, tmp_path):
        """Test that empty text blocks are skipped."""
        from graph_builder.parsing.pdf_parser import PdfParser

        mock_module = MagicMock()
        mock_module.TEXT_PRESERVE_WHITESPACE = 1

        def make_span(text, size=12, flags=0):
            return {"text": text, "size": size, "flags": flags}

        def make_line(spans):
            return {"spans": spans}

        def make_block(lines, block_type=0):
            return {"type": block_type, "lines": lines}

        mock_page = MagicMock()
        mock_page.get_text.return_value = {
            "blocks": [
                make_block([make_line([make_span("First paragraph.")])]),
                make_block([make_line([make_span("")])]),  # Empty
                make_block([make_line([make_span("   ")])]),  # Whitespace only
                make_block([make_line([make_span("Second paragraph.")])]),
            ]
        }

        mock_pdf = MagicMock()
        mock_pdf.__iter__ = lambda self: iter([mock_page])
        mock_module.open.return_value = mock_pdf

        test_file = tmp_path / "test.pdf"
        test_file.touch()

        parser = PdfParser()
        parser._fitz_module = mock_module

        doc = parser.parse(test_file)
        paragraphs = doc.metadata["paragraphs"]

        # Should only have 2 paragraphs (empty ones skipped)
        assert len(paragraphs) == 2
        assert paragraphs[0]["text"] == "First paragraph."
        assert paragraphs[1]["text"] == "Second paragraph."

    def test_lazy_import_error(self):
        """Test that ImportError is raised when PyMuPDF is not installed."""
        from graph_builder.parsing.pdf_parser import PdfParser

        parser = PdfParser()
        parser._fitz_module = None

        with patch.dict("sys.modules", {"fitz": None}):
            with patch(
                "builtins.__import__", side_effect=ImportError("No module named 'fitz'")
            ):
                with pytest.raises(ImportError, match="PyMuPDF is required"):
                    _ = parser.fitz

    def test_image_blocks_skipped(self, tmp_path):
        """Test that image blocks (type != 0) are skipped."""
        from graph_builder.parsing.pdf_parser import PdfParser

        mock_module = MagicMock()
        mock_module.TEXT_PRESERVE_WHITESPACE = 1

        def make_span(text, size=12, flags=0):
            return {"text": text, "size": size, "flags": flags}

        def make_line(spans):
            return {"spans": spans}

        def make_block(lines, block_type=0):
            return {"type": block_type, "lines": lines}

        mock_page = MagicMock()
        mock_page.get_text.return_value = {
            "blocks": [
                make_block([make_line([make_span("Text paragraph.")])]),
                make_block([], block_type=1),  # Image block
                make_block([make_line([make_span("Another paragraph.")])]),
            ]
        }

        mock_pdf = MagicMock()
        mock_pdf.__iter__ = lambda self: iter([mock_page])
        mock_module.open.return_value = mock_pdf

        test_file = tmp_path / "test.pdf"
        test_file.touch()

        parser = PdfParser()
        parser._fitz_module = mock_module

        doc = parser.parse(test_file)
        paragraphs = doc.metadata["paragraphs"]

        # Should have 2 paragraphs (image block skipped)
        assert len(paragraphs) == 2
        assert "Text paragraph" in paragraphs[0]["text"]
        assert "Another paragraph" in paragraphs[1]["text"]

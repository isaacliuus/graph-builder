"""Unit tests for docx parser."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestDocxParser:
    """Tests for DocxParser class."""

    def test_supports_docx(self):
        """Test that parser supports .docx files."""
        from graph_builder.parsing.docx_parser import DocxParser

        parser = DocxParser()
        assert parser.supports(Path("contract.docx"))
        assert parser.supports(Path("CONTRACT.DOCX"))
        assert parser.supports(Path("/path/to/file.docx"))

    def test_does_not_support_other_formats(self):
        """Test that parser rejects non-.docx files."""
        from graph_builder.parsing.docx_parser import DocxParser

        parser = DocxParser()
        assert not parser.supports(Path("contract.doc"))
        assert not parser.supports(Path("contract.pdf"))
        assert not parser.supports(Path("contract.txt"))
        assert not parser.supports(Path("contract.odt"))

    def test_parse_raises_for_unsupported_file(self, tmp_path):
        """Test that parse raises ValueError for unsupported files."""
        from graph_builder.parsing.docx_parser import DocxParser

        # Create a test file with unsupported extension
        test_file = tmp_path / "contract.pdf"
        test_file.touch()

        parser = DocxParser()
        with pytest.raises(ValueError, match="Unsupported file type"):
            parser.parse(test_file)

    def test_parse_raises_for_missing_file(self):
        """Test that parse raises FileNotFoundError for missing files."""
        from graph_builder.parsing.docx_parser import DocxParser

        parser = DocxParser()
        with pytest.raises(FileNotFoundError, match="File not found"):
            parser.parse(Path("nonexistent.docx"))

    def test_section_number_pattern(self):
        """Test section number regex pattern."""
        from graph_builder.parsing.docx_parser import DocxParser

        parser = DocxParser()
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
        from graph_builder.parsing.docx_parser import DocxParser

        parser = DocxParser()
        pattern = parser.SECTION_NUMBER_PATTERN

        match = pattern.match("1.2.3 Title")
        assert match.group(1).rstrip(".") == "1.2.3"

        match = pattern.match("5. Section Five")
        assert match.group(1).rstrip(".") == "5"


class TestDocxParserIntegration:
    """Integration tests for DocxParser requiring python-docx."""

    @pytest.fixture
    def mock_docx(self):
        """Create a mock docx module."""
        mock_module = MagicMock()

        # Create mock paragraphs
        def make_para(text, style_name="Normal"):
            para = MagicMock()
            para.text = text
            para.style = MagicMock()
            para.style.name = style_name
            return para

        mock_doc = MagicMock()
        mock_doc.paragraphs = [
            make_para("1. Definitions", "Heading 1"),
            make_para("The following terms shall have the meanings set forth below."),
            make_para("1.1 Agreement", "Heading 2"),
            make_para("Agreement means this contract between the parties."),
            make_para("2. Confidentiality", "Heading 1"),
            make_para("Each party shall maintain confidential all proprietary information."),
        ]
        mock_module.Document.return_value = mock_doc

        return mock_module

    def test_parse_with_mock(self, mock_docx, tmp_path):
        """Test parsing with mocked python-docx."""
        from graph_builder.parsing.docx_parser import DocxParser

        # Create a test file
        test_file = tmp_path / "test.docx"
        test_file.touch()

        parser = DocxParser()
        parser._docx_module = mock_docx

        doc = parser.parse(test_file)

        assert doc.source == str(test_file)
        assert doc.metadata["file_type"] == "docx"
        assert doc.metadata["file_name"] == "test.docx"
        assert doc.metadata["paragraph_count"] == 6

        # Check paragraph metadata
        paragraphs = doc.metadata["paragraphs"]
        assert len(paragraphs) == 6

        # First paragraph should be a heading with section number
        assert paragraphs[0]["text"] == "1. Definitions"
        assert paragraphs[0]["is_heading"] is True
        assert paragraphs[0]["section_number"] == "1"
        assert paragraphs[0]["style"] == "Heading 1"

        # Second paragraph should be normal text
        assert paragraphs[1]["is_heading"] is False
        assert paragraphs[1]["section_number"] is None

        # Check that content is joined
        assert "1. Definitions" in doc.content
        assert "Confidentiality" in doc.content

    def test_parse_character_offsets(self, mock_docx, tmp_path):
        """Test that character offsets are calculated correctly."""
        from graph_builder.parsing.docx_parser import DocxParser

        test_file = tmp_path / "test.docx"
        test_file.touch()

        parser = DocxParser()
        parser._docx_module = mock_docx

        doc = parser.parse(test_file)
        paragraphs = doc.metadata["paragraphs"]

        # First paragraph starts at 0
        assert paragraphs[0]["start_char"] == 0
        assert paragraphs[0]["end_char"] == len("1. Definitions")

        # Second paragraph starts after first + newline
        expected_start = len("1. Definitions") + 1
        assert paragraphs[1]["start_char"] == expected_start

    def test_parse_empty_paragraphs_skipped(self, tmp_path):
        """Test that empty paragraphs are skipped."""
        from graph_builder.parsing.docx_parser import DocxParser

        mock_module = MagicMock()

        def make_para(text, style_name="Normal"):
            para = MagicMock()
            para.text = text
            para.style = MagicMock()
            para.style.name = style_name
            return para

        mock_doc = MagicMock()
        mock_doc.paragraphs = [
            make_para("First paragraph"),
            make_para(""),  # Empty
            make_para("   "),  # Whitespace only
            make_para("Second paragraph"),
        ]
        mock_module.Document.return_value = mock_doc

        test_file = tmp_path / "test.docx"
        test_file.touch()

        parser = DocxParser()
        parser._docx_module = mock_module

        doc = parser.parse(test_file)
        paragraphs = doc.metadata["paragraphs"]

        assert len(paragraphs) == 2
        assert paragraphs[0]["text"] == "First paragraph"
        assert paragraphs[1]["text"] == "Second paragraph"

    def test_lazy_import_error(self):
        """Test that ImportError is raised when python-docx is not installed."""
        from graph_builder.parsing.docx_parser import DocxParser

        parser = DocxParser()
        parser._docx_module = None

        with patch.dict("sys.modules", {"docx": None}):
            with patch("builtins.__import__", side_effect=ImportError("No module named 'docx'")):
                with pytest.raises(ImportError, match="python-docx is required"):
                    _ = parser.docx

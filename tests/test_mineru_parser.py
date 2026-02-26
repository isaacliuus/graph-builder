"""Unit tests for MinerU PDF parser."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch


class TestMineruPdfParser:
    """Tests for MineruPdfParser class."""

    def test_supports_pdf(self):
        """Test that parser supports .pdf files."""
        from graph_builder.parsing.mineru_parser import MineruPdfParser

        parser = MineruPdfParser()
        assert parser.supports(Path("contract.pdf"))
        assert parser.supports(Path("CONTRACT.PDF"))
        assert parser.supports(Path("/path/to/file.pdf"))

    def test_does_not_support_other_formats(self):
        """Test that parser rejects non-.pdf files."""
        from graph_builder.parsing.mineru_parser import MineruPdfParser

        parser = MineruPdfParser()
        assert not parser.supports(Path("contract.docx"))
        assert not parser.supports(Path("contract.doc"))
        assert not parser.supports(Path("contract.txt"))
        assert not parser.supports(Path("contract.odt"))

    def test_parse_raises_for_unsupported_file(self, tmp_path):
        """Test that parse raises ValueError for unsupported files."""
        from graph_builder.parsing.mineru_parser import MineruPdfParser

        # Create a test file with unsupported extension
        test_file = tmp_path / "contract.docx"
        test_file.touch()

        parser = MineruPdfParser()
        with pytest.raises(ValueError, match="Unsupported file type"):
            parser.parse(test_file)

    def test_parse_raises_for_missing_file(self):
        """Test that parse raises FileNotFoundError for missing files."""
        from graph_builder.parsing.mineru_parser import MineruPdfParser

        parser = MineruPdfParser()
        with pytest.raises(FileNotFoundError, match="File not found"):
            parser.parse(Path("nonexistent.pdf"))

    def test_section_number_pattern(self):
        """Test section number regex pattern."""
        from graph_builder.parsing.mineru_parser import MineruPdfParser

        parser = MineruPdfParser()
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
        from graph_builder.parsing.mineru_parser import MineruPdfParser

        parser = MineruPdfParser()
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


class TestMineruPdfParserIntegration:
    """Integration tests for MineruPdfParser requiring mineru."""

    @pytest.fixture
    def mock_mineru(self, tmp_path):
        """Create a mock mineru module that writes a markdown file."""
        md_content = """# 1. Definitions

The following terms shall have the meanings set forth below.

## 1.1 Agreement

Agreement means this contract between the parties.

# 2. Confidentiality

Each party shall maintain confidential all proprietary information.
"""

        def mock_do_parse(output_dir, pdf_file_names, pdf_bytes_list, **kwargs):
            # Create the expected output structure
            for filename in pdf_file_names:
                base_name = Path(filename).stem
                out_dir = Path(output_dir) / base_name
                out_dir.mkdir(parents=True, exist_ok=True)
                md_file = out_dir / f"{base_name}.md"
                md_file.write_text(md_content, encoding="utf-8")

        return {"do_parse": mock_do_parse}

    def test_parse_with_mock(self, mock_mineru, tmp_path):
        """Test parsing with mocked mineru."""
        from graph_builder.parsing.mineru_parser import MineruPdfParser

        # Create a test file
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 test content")

        parser = MineruPdfParser()
        parser._mineru = mock_mineru

        doc = parser.parse(test_file)

        assert doc.source == str(test_file)
        assert doc.metadata["file_type"] == "pdf"
        assert doc.metadata["file_name"] == "test.pdf"
        assert doc.metadata["parser"] == "mineru"
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

    def test_parse_character_offsets(self, mock_mineru, tmp_path):
        """Test that character offsets are calculated correctly."""
        from graph_builder.parsing.mineru_parser import MineruPdfParser

        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 test content")

        parser = MineruPdfParser()
        parser._mineru = mock_mineru

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
        """Test that ImportError is raised when mineru is not installed."""
        from graph_builder.parsing.mineru_parser import MineruPdfParser

        parser = MineruPdfParser()
        parser._mineru = None

        with patch.dict("sys.modules", {"mineru": None, "mineru.cli.common": None}):
            with patch(
                "builtins.__import__",
                side_effect=ImportError("No module named 'mineru'"),
            ):
                with pytest.raises(ImportError, match="MinerU"):
                    _ = parser.mineru

    def test_parse_markdown_headings(self):
        """Test parsing of markdown headings."""
        from graph_builder.parsing.mineru_parser import MineruPdfParser

        parser = MineruPdfParser()

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

    def test_parser_method_selection(self, tmp_path):
        """Test that parser method selection works."""
        from graph_builder.parsing.mineru_parser import MineruPdfParser

        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"%PDF-1.4 test content")

        # Track calls to do_parse
        calls = []

        def mock_do_parse(output_dir, pdf_file_names, pdf_bytes_list, **kwargs):
            calls.append(kwargs.get("parse_method"))
            # Create the expected output structure
            for filename in pdf_file_names:
                base_name = Path(filename).stem
                out_dir = Path(output_dir) / base_name
                out_dir.mkdir(parents=True, exist_ok=True)
                md_file = out_dir / f"{base_name}.md"
                md_file.write_text("# Test", encoding="utf-8")

        mock_mineru = {"do_parse": mock_do_parse}

        # Test OCR method
        parser = MineruPdfParser(method="ocr")
        parser._mineru = mock_mineru
        parser.parse(test_file)
        assert "ocr" in calls

        # Test TXT method
        calls.clear()
        parser = MineruPdfParser(method="txt")
        parser._mineru = mock_mineru
        parser.parse(test_file)
        assert "txt" in calls

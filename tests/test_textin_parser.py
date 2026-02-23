"""Unit tests for Textin xParse parser."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock


MOCK_API_RESPONSE = {
    "code": 200,
    "message": "success",
    "result": {
        "markdown": "# 1. Definitions\n\nThe following terms shall have the meanings.\n\n# 2. Confidentiality\n\nEach party shall maintain confidential information.\n",
        "catalog": {
            "toc": [
                {"title": "1. Definitions", "hierarchy": 1, "page_id": 0, "paragraph_id": 0, "pos": "0"},
                {"title": "2. Confidentiality", "hierarchy": 1, "page_id": 0, "paragraph_id": 2, "pos": "1"},
            ]
        },
        "detail": [
            {
                "page_id": 0,
                "paragraph_id": 0,
                "outline_level": 0,
                "text": "1. Definitions",
                "type": "text",
                "sub_type": "title",
            },
            {
                "page_id": 0,
                "paragraph_id": 1,
                "outline_level": -1,
                "text": "The following terms shall have the meanings.",
                "type": "text",
                "sub_type": "paragraph",
            },
            {
                "page_id": 0,
                "paragraph_id": 2,
                "outline_level": 0,
                "text": "2. Confidentiality",
                "type": "text",
                "sub_type": "title",
            },
            {
                "page_id": 0,
                "paragraph_id": 3,
                "outline_level": -1,
                "text": "Each party shall maintain confidential information.",
                "type": "text",
                "sub_type": "paragraph",
            },
        ],
    },
}


class TestTextinParser:
    """Tests for TextinParser class."""

    def test_supports_pdf(self):
        """Test that parser supports .pdf files."""
        from graph_builder.parsing.textin_parser import TextinParser

        parser = TextinParser(app_id="test", secret_code="test")
        assert parser.supports(Path("contract.pdf"))
        assert parser.supports(Path("CONTRACT.PDF"))

    def test_supports_docx(self):
        """Test that parser supports .docx files."""
        from graph_builder.parsing.textin_parser import TextinParser

        parser = TextinParser(app_id="test", secret_code="test")
        assert parser.supports(Path("contract.docx"))

    def test_supports_multiple_formats(self):
        """Test that parser supports all declared formats."""
        from graph_builder.parsing.textin_parser import TextinParser

        parser = TextinParser(app_id="test", secret_code="test")
        for ext in [".pdf", ".docx", ".doc", ".pptx", ".xlsx", ".html", ".txt"]:
            assert parser.supports(Path(f"file{ext}")), f"Should support {ext}"

    def test_does_not_support_unknown_format(self):
        """Test that parser rejects unsupported formats."""
        from graph_builder.parsing.textin_parser import TextinParser

        parser = TextinParser(app_id="test", secret_code="test")
        assert not parser.supports(Path("file.odt"))
        assert not parser.supports(Path("file.rtf"))

    def test_parse_raises_for_missing_file(self):
        """Test that parse raises FileNotFoundError for missing files."""
        from graph_builder.parsing.textin_parser import TextinParser

        parser = TextinParser(app_id="test", secret_code="test")
        with pytest.raises(FileNotFoundError, match="File not found"):
            parser.parse(Path("nonexistent.pdf"))

    def test_parse_raises_for_unsupported_file(self, tmp_path):
        """Test that parse raises ValueError for unsupported files."""
        from graph_builder.parsing.textin_parser import TextinParser

        test_file = tmp_path / "contract.odt"
        test_file.touch()

        parser = TextinParser(app_id="test", secret_code="test")
        with pytest.raises(ValueError, match="Unsupported file type"):
            parser.parse(test_file)

    def test_parse_produces_correct_document(self, tmp_path):
        """Test that parse produces a Document with correct metadata."""
        from graph_builder.parsing.textin_parser import TextinParser

        test_file = tmp_path / "contract.pdf"
        test_file.write_bytes(b"%PDF-1.4 test")

        parser = TextinParser(app_id="test", secret_code="test")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_API_RESPONSE

        with patch("httpx.post", return_value=mock_response):
            doc = parser.parse(test_file)

        assert doc.source == str(test_file)
        assert doc.metadata["file_type"] == "pdf"
        assert doc.metadata["file_name"] == "contract.pdf"
        assert doc.metadata["parser"] == "textin"
        assert doc.metadata["paragraph_count"] == 4
        assert "Definitions" in doc.content

    def test_detail_to_paragraphs_heading_detection(self, tmp_path):
        """Test that outline_level maps correctly to is_heading and style."""
        from graph_builder.parsing.textin_parser import TextinParser

        test_file = tmp_path / "contract.pdf"
        test_file.write_bytes(b"%PDF-1.4 test")

        parser = TextinParser(app_id="test", secret_code="test")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_API_RESPONSE

        with patch("httpx.post", return_value=mock_response):
            doc = parser.parse(test_file)

        paragraphs = doc.metadata["paragraphs"]

        # outline_level=0 → heading
        assert paragraphs[0]["is_heading"] is True
        assert paragraphs[0]["style"] == "Heading 1"

        # outline_level=-1 → normal text
        assert paragraphs[1]["is_heading"] is False
        assert paragraphs[1]["style"] == "Normal"

    def test_detail_to_paragraphs_section_number(self, tmp_path):
        """Test that section numbers are extracted from paragraph text."""
        from graph_builder.parsing.textin_parser import TextinParser

        test_file = tmp_path / "contract.pdf"
        test_file.write_bytes(b"%PDF-1.4 test")

        parser = TextinParser(app_id="test", secret_code="test")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_API_RESPONSE

        with patch("httpx.post", return_value=mock_response):
            doc = parser.parse(test_file)

        paragraphs = doc.metadata["paragraphs"]

        assert paragraphs[0]["section_number"] == "1"
        assert paragraphs[1]["section_number"] is None
        assert paragraphs[2]["section_number"] == "2"

    def test_catalog_preserved_in_metadata(self, tmp_path):
        """Test that textin_catalog is preserved in document metadata."""
        from graph_builder.parsing.textin_parser import TextinParser

        test_file = tmp_path / "contract.pdf"
        test_file.write_bytes(b"%PDF-1.4 test")

        parser = TextinParser(app_id="test", secret_code="test")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_API_RESPONSE

        with patch("httpx.post", return_value=mock_response):
            doc = parser.parse(test_file)

        toc = doc.metadata["textin_catalog"]
        assert len(toc) == 2
        assert toc[0]["title"] == "1. Definitions"
        assert toc[1]["title"] == "2. Confidentiality"

    def test_detail_preserved_in_metadata(self, tmp_path):
        """Test that textin_detail is preserved in document metadata."""
        from graph_builder.parsing.textin_parser import TextinParser

        test_file = tmp_path / "contract.pdf"
        test_file.write_bytes(b"%PDF-1.4 test")

        parser = TextinParser(app_id="test", secret_code="test")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = MOCK_API_RESPONSE

        with patch("httpx.post", return_value=mock_response):
            doc = parser.parse(test_file)

        detail = doc.metadata["textin_detail"]
        assert len(detail) == 4

    def test_api_error_raises_runtime_error(self, tmp_path):
        """Test that API errors raise RuntimeError."""
        from graph_builder.parsing.textin_parser import TextinParser

        test_file = tmp_path / "contract.pdf"
        test_file.write_bytes(b"%PDF-1.4 test")

        parser = TextinParser(app_id="test", secret_code="test")

        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.post", return_value=mock_response):
            with pytest.raises(RuntimeError, match="status 500"):
                parser.parse(test_file)

    def test_api_error_code_raises_runtime_error(self, tmp_path):
        """Test that non-200 API code raises RuntimeError."""
        from graph_builder.parsing.textin_parser import TextinParser

        test_file = tmp_path / "contract.pdf"
        test_file.write_bytes(b"%PDF-1.4 test")

        parser = TextinParser(app_id="test", secret_code="test")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"code": 401, "message": "Unauthorized"}

        with patch("httpx.post", return_value=mock_response):
            with pytest.raises(RuntimeError, match="error code 401"):
                parser.parse(test_file)

    def test_missing_credentials_raises_runtime_error(self, tmp_path):
        """Test that missing credentials raise RuntimeError."""
        from graph_builder.parsing.textin_parser import TextinParser

        test_file = tmp_path / "contract.pdf"
        test_file.write_bytes(b"%PDF-1.4 test")

        parser = TextinParser(app_id="", secret_code="")
        parser._app_id = ""
        parser._secret_code = ""

        with pytest.raises(RuntimeError, match="Textin credentials required"):
            parser.parse(test_file)

    def test_credentials_from_settings(self):
        """Test that credentials fall back to Settings."""
        from graph_builder.parsing.textin_parser import TextinParser

        with patch("graph_builder.config.settings.Settings") as mock_cls:
            mock_cls.return_value = MagicMock(
                textin_app_id="settings-id",
                textin_secret_code="settings-secret",
            )
            parser = TextinParser()
            assert parser._app_id == "settings-id"
            assert parser._secret_code == "settings-secret"

    def test_outline_level_heading_styles(self):
        """Test that different outline levels produce correct heading styles."""
        from graph_builder.parsing.textin_parser import TextinParser

        parser = TextinParser(app_id="test", secret_code="test")

        detail = [
            {"text": "Title", "outline_level": 0},
            {"text": "Subtitle", "outline_level": 1},
            {"text": "Sub-subtitle", "outline_level": 2},
            {"text": "Body", "outline_level": -1},
        ]
        markdown = "Title\nSubtitle\nSub-subtitle\nBody"

        paragraphs = parser._detail_to_paragraphs(detail, markdown)

        assert paragraphs[0]["style"] == "Heading 1"
        assert paragraphs[1]["style"] == "Heading 2"
        assert paragraphs[2]["style"] == "Heading"  # level 3+
        assert paragraphs[3]["style"] == "Normal"

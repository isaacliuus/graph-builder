"""Unit tests for LLM clause extractor."""

import pytest
from unittest.mock import MagicMock, patch
from uuid import uuid4

from graph_builder.models import Document, ClauseType


class TestLLMClauseExtractor:
    """Tests for LLMClauseExtractor class."""

    @pytest.fixture
    def mock_instructor(self):
        """Mock instructor and OpenAI modules."""
        # Create mocks
        mock_inst = MagicMock()
        mock_openai = MagicMock()
        mock_client = MagicMock()

        mock_inst.from_openai.return_value = mock_client
        mock_openai.return_value = MagicMock()  # OpenAI instance

        # Create mock response
        mock_response = MagicMock()
        mock_response.clauses = [
            MagicMock(
                type=ClauseType.CONFIDENTIALITY,
                section_title="Confidentiality",
                section_number="2",
                content="Section 2: Confidentiality\nAll information shall be kept confidential.",
                confidence=0.95
            ),
            MagicMock(
                type=ClauseType.TERMINATION,
                section_title="Termination",
                section_number="3",
                content="Section 3: Termination\nEither party may terminate with 30 days notice.",
                confidence=0.90
            ),
        ]
        mock_client.chat.completions.create.return_value = mock_response

        # Patch at import time
        import sys
        sys.modules['instructor'] = mock_inst
        sys.modules['openai'] = MagicMock(OpenAI=mock_openai)

        yield mock_inst, mock_openai, mock_client

        # Cleanup
        if 'instructor' in sys.modules:
            del sys.modules['instructor']
        if 'openai' in sys.modules:
            del sys.modules['openai']

    def test_extractor_creation(self):
        """Test creating LLM clause extractor."""
        from graph_builder.clauses.llm_extractor import LLMClauseExtractor

        extractor = LLMClauseExtractor(api_key="test-key", model="gpt-4o")
        assert extractor.api_key == "test-key"
        assert extractor.model == "gpt-4o"
        assert extractor._client is None

    def test_lazy_client_loading(self, mock_instructor):
        """Test that client is lazily loaded."""
        from graph_builder.clauses.llm_extractor import LLMClauseExtractor

        mock_inst, mock_openai, _ = mock_instructor

        extractor = LLMClauseExtractor(api_key="test-key")
        assert extractor._client is None

        # Access client property
        _ = extractor.client

        # Verify OpenAI was initialized
        mock_openai.assert_called_once_with(api_key="test-key")
        mock_inst.from_openai.assert_called_once()

    def test_client_import_error(self):
        """Test that ImportError is raised when dependencies are missing."""
        from graph_builder.clauses.llm_extractor import LLMClauseExtractor

        with patch("builtins.__import__", side_effect=ImportError("No module named 'instructor'")):
            extractor = LLMClauseExtractor(api_key="test-key")
            with pytest.raises(ImportError, match="LLM clause extraction requires"):
                _ = extractor.client

    def test_extract_clauses(self, mock_instructor):
        """Test extracting clauses with LLM."""
        from graph_builder.clauses.llm_extractor import LLMClauseExtractor

        _, _, mock_client = mock_instructor

        doc = Document(
            content="Section 2: Confidentiality\nAll information shall be kept confidential.\n"
                    "Section 3: Termination\nEither party may terminate with 30 days notice.",
            metadata={
                "paragraphs": [
                    {
                        "index": 0,
                        "text": "Section 2: Confidentiality",
                        "section_number": "2",
                        "start_char": 0,
                        "end_char": 26,
                    },
                    {
                        "index": 1,
                        "text": "All information shall be kept confidential.",
                        "section_number": None,
                        "start_char": 27,
                        "end_char": 70,
                    },
                ]
            }
        )

        extractor = LLMClauseExtractor(api_key="test-key")
        clauses = extractor.extract(doc)

        assert len(clauses) == 2
        assert clauses[0].type == ClauseType.CONFIDENTIALITY
        assert clauses[0].location.section_title == "Confidentiality"
        assert clauses[0].confidence == 0.95
        assert clauses[0].metadata["extraction_method"] == "llm"
        assert clauses[0].metadata["model"] == "gpt-4o-mini"

        assert clauses[1].type == ClauseType.TERMINATION
        assert clauses[1].confidence == 0.90

        # Verify LLM was called
        mock_client.chat.completions.create.assert_called_once()

    def test_find_clause_location_by_title(self):
        """Test finding clause location by section title."""
        from graph_builder.clauses.llm_extractor import LLMClauseExtractor

        extractor = LLMClauseExtractor(api_key="test-key")

        paragraphs = [
            {
                "index": 0,
                "text": "1. Definitions",
                "section_number": "1",
                "start_char": 0,
                "end_char": 14,
            },
            {
                "index": 1,
                "text": "2. Confidentiality",
                "section_number": "2",
                "start_char": 15,
                "end_char": 33,
            },
        ]

        location = extractor._find_clause_location(
            "Content here", "Confidentiality", paragraphs
        )

        assert location.paragraph_index == 1
        assert location.section_number == "2"
        assert location.section_title == "Confidentiality"

    def test_find_clause_location_by_content(self):
        """Test finding clause location by content match."""
        from graph_builder.clauses.llm_extractor import LLMClauseExtractor

        extractor = LLMClauseExtractor(api_key="test-key")

        paragraphs = [
            {
                "index": 0,
                "text": "First paragraph content",
                "section_number": None,
                "start_char": 0,
                "end_char": 23,
            },
            {
                "index": 1,
                "text": "This is the content we're looking for",
                "section_number": None,
                "start_char": 24,
                "end_char": 62,
            },
        ]

        location = extractor._find_clause_location(
            "This is the content we're looking for", None, paragraphs
        )

        assert location.paragraph_index == 1

    def test_find_clause_location_fallback(self):
        """Test clause location fallback when no match found."""
        from graph_builder.clauses.llm_extractor import LLMClauseExtractor

        extractor = LLMClauseExtractor(api_key="test-key")

        location = extractor._find_clause_location(
            "Some content", "Unknown Title", []
        )

        assert location.paragraph_index == 0
        assert location.section_number is None
        assert location.section_title == "Unknown Title"
        assert location.start_char == 0

    def test_extract_with_no_paragraphs(self, mock_instructor):
        """Test extraction when document has no paragraph metadata."""
        from graph_builder.clauses.llm_extractor import LLMClauseExtractor

        doc = Document(
            content="Simple contract text without paragraph metadata."
        )

        extractor = LLMClauseExtractor(api_key="test-key")
        clauses = extractor.extract(doc)

        assert len(clauses) == 2
        # Should use fallback location
        assert clauses[0].location.paragraph_index == 0


class TestExtractedClauseModels:
    """Tests for Pydantic models used in LLM extraction."""

    def test_extracted_clause_model(self):
        """Test ExtractedClause Pydantic model."""
        from graph_builder.clauses.llm_extractor import ExtractedClause

        clause = ExtractedClause(
            type=ClauseType.CONFIDENTIALITY,
            section_title="Confidential Information",
            section_number="2.1",
            content="All information must be kept confidential.",
            confidence=0.95
        )

        assert clause.type == ClauseType.CONFIDENTIALITY
        assert clause.section_title == "Confidential Information"
        assert clause.section_number == "2.1"
        assert clause.confidence == 0.95

    def test_extracted_clause_defaults(self):
        """Test ExtractedClause default values."""
        from graph_builder.clauses.llm_extractor import ExtractedClause

        clause = ExtractedClause(
            type=ClauseType.OTHER,
            content="Some content"
        )

        assert clause.section_title is None
        assert clause.section_number is None
        assert clause.confidence == 1.0

    def test_extracted_clauses_container(self):
        """Test ExtractedClauses container model."""
        from graph_builder.clauses.llm_extractor import ExtractedClauses, ExtractedClause

        container = ExtractedClauses(
            clauses=[
                ExtractedClause(
                    type=ClauseType.DEFINITIONS,
                    content="Definitions here"
                ),
                ExtractedClause(
                    type=ClauseType.PAYMENT,
                    content="Payment terms here"
                ),
            ]
        )

        assert len(container.clauses) == 2
        assert container.clauses[0].type == ClauseType.DEFINITIONS
        assert container.clauses[1].type == ClauseType.PAYMENT

    def test_extracted_clauses_empty(self):
        """Test empty ExtractedClauses container."""
        from graph_builder.clauses.llm_extractor import ExtractedClauses

        container = ExtractedClauses()
        assert container.clauses == []

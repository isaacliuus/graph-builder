"""Unit tests for clause extraction."""

import pytest
from uuid import UUID

from graph_builder.models import Document, ClauseType
from graph_builder.clauses.pattern_extractor import (
    PatternClauseExtractor,
    CLAUSE_TYPE_KEYWORDS,
)


class TestPatternClauseExtractor:
    """Tests for PatternClauseExtractor class."""

    @pytest.fixture
    def extractor(self):
        return PatternClauseExtractor()

    @pytest.fixture
    def document_with_paragraphs(self):
        """Create a document with paragraph metadata."""
        return Document(
            content=(
                "1. Definitions\n"
                "The following terms have the following meanings.\n"
                "2. Confidentiality\n"
                "Each party shall keep confidential all proprietary information.\n"
                "3. Termination\n"
                "Either party may terminate this agreement with 30 days notice."
            ),
            metadata={
                "paragraphs": [
                    {
                        "index": 0,
                        "text": "1. Definitions",
                        "style": "Heading 1",
                        "is_heading": True,
                        "section_number": "1",
                        "start_char": 0,
                        "end_char": 14,
                    },
                    {
                        "index": 1,
                        "text": "The following terms have the following meanings.",
                        "style": "Normal",
                        "is_heading": False,
                        "section_number": None,
                        "start_char": 15,
                        "end_char": 63,
                    },
                    {
                        "index": 2,
                        "text": "2. Confidentiality",
                        "style": "Heading 1",
                        "is_heading": True,
                        "section_number": "2",
                        "start_char": 64,
                        "end_char": 82,
                    },
                    {
                        "index": 3,
                        "text": "Each party shall keep confidential all proprietary information.",
                        "style": "Normal",
                        "is_heading": False,
                        "section_number": None,
                        "start_char": 83,
                        "end_char": 146,
                    },
                    {
                        "index": 4,
                        "text": "3. Termination",
                        "style": "Heading 1",
                        "is_heading": True,
                        "section_number": "3",
                        "start_char": 147,
                        "end_char": 161,
                    },
                    {
                        "index": 5,
                        "text": "Either party may terminate this agreement with 30 days notice.",
                        "style": "Normal",
                        "is_heading": False,
                        "section_number": None,
                        "start_char": 162,
                        "end_char": 224,
                    },
                ],
            },
        )

    def test_extract_from_paragraphs(self, extractor, document_with_paragraphs):
        """Test clause extraction from document with paragraph metadata."""
        clauses = extractor.extract(document_with_paragraphs)

        assert len(clauses) == 3

        # First clause - Definitions
        assert clauses[0].type == ClauseType.DEFINITIONS
        assert clauses[0].location.section_number == "1"
        assert clauses[0].location.section_title == "Definitions"
        assert clauses[0].document_id == document_with_paragraphs.id

        # Second clause - Confidentiality
        assert clauses[1].type == ClauseType.CONFIDENTIALITY
        assert clauses[1].location.section_number == "2"

        # Third clause - Termination
        assert clauses[2].type == ClauseType.TERMINATION
        assert clauses[2].location.section_number == "3"

    def test_extract_clause_content(self, extractor, document_with_paragraphs):
        """Test that clause content includes all paragraphs in section."""
        clauses = extractor.extract(document_with_paragraphs)

        # Definitions clause should include both heading and body
        assert "Definitions" in clauses[0].content
        assert "following terms" in clauses[0].content

    def test_extract_clause_location(self, extractor, document_with_paragraphs):
        """Test that clause location information is correct."""
        clauses = extractor.extract(document_with_paragraphs)

        # First clause starts at paragraph 0
        assert clauses[0].location.paragraph_index == 0
        assert clauses[0].location.start_char == 0

    def test_extract_empty_document(self, extractor):
        """Test extraction from empty document."""
        doc = Document(content="", metadata={"paragraphs": []})
        clauses = extractor.extract(doc)
        assert clauses == []

    def test_extract_no_paragraphs_metadata(self, extractor):
        """Test extraction when no paragraph metadata is available."""
        doc = Document(
            content=(
                "1. Definitions\n"
                "The following terms have the following meanings.\n"
                "2. Confidentiality\n"
                "Each party shall keep confidential all proprietary information."
            ),
        )
        clauses = extractor.extract(doc)

        # Should fall back to plain text extraction
        assert len(clauses) == 2

    def test_min_clause_length(self):
        """Test that short clauses are filtered out."""
        extractor = PatternClauseExtractor(min_clause_length=100)
        doc = Document(
            content="1. Short\nToo short.",
            metadata={
                "paragraphs": [
                    {
                        "index": 0,
                        "text": "1. Short",
                        "is_heading": True,
                        "section_number": "1",
                        "start_char": 0,
                        "end_char": 8,
                    },
                    {
                        "index": 1,
                        "text": "Too short.",
                        "is_heading": False,
                        "section_number": None,
                        "start_char": 9,
                        "end_char": 19,
                    },
                ],
            },
        )
        clauses = extractor.extract(doc)
        assert clauses == []


class TestClauseTypeClassification:
    """Tests for clause type classification."""

    @pytest.fixture
    def extractor(self):
        return PatternClauseExtractor()

    def test_classify_definitions(self, extractor):
        """Test classification of definitions clause."""
        clause_type = extractor._classify_clause_type(
            "Definitions", "The following defined terms shall have the meanings below."
        )
        assert clause_type == ClauseType.DEFINITIONS

    def test_classify_confidentiality(self, extractor):
        """Test classification of confidentiality clause."""
        clause_type = extractor._classify_clause_type(
            "Confidentiality",
            "Each party agrees to keep confidential all proprietary information.",
        )
        assert clause_type == ClauseType.CONFIDENTIALITY

    def test_classify_termination(self, extractor):
        """Test classification of termination clause."""
        clause_type = extractor._classify_clause_type(
            "Termination", "Either party may terminate this agreement."
        )
        assert clause_type == ClauseType.TERMINATION

    def test_classify_indemnification(self, extractor):
        """Test classification of indemnification clause."""
        clause_type = extractor._classify_clause_type(
            "Indemnification",
            "Party A shall indemnify and hold harmless Party B.",
        )
        assert clause_type == ClauseType.INDEMNIFICATION

    def test_classify_liability(self, extractor):
        """Test classification of liability clause."""
        clause_type = extractor._classify_clause_type(
            "Limitation of Liability",
            "Neither party shall be liable for consequential damages.",
        )
        assert clause_type == ClauseType.LIABILITY

    def test_classify_governing_law(self, extractor):
        """Test classification of governing law clause."""
        clause_type = extractor._classify_clause_type(
            "Governing Law",
            "This agreement shall be governed by the laws of California.",
        )
        assert clause_type == ClauseType.GOVERNING_LAW

    def test_classify_dispute_resolution(self, extractor):
        """Test classification of dispute resolution clause."""
        clause_type = extractor._classify_clause_type(
            "Dispute Resolution",
            "Any disputes shall be resolved through binding arbitration.",
        )
        assert clause_type == ClauseType.DISPUTE_RESOLUTION

    def test_classify_force_majeure(self, extractor):
        """Test classification of force majeure clause."""
        clause_type = extractor._classify_clause_type(
            "Force Majeure",
            "Neither party shall be liable for delays due to force majeure events.",
        )
        assert clause_type == ClauseType.FORCE_MAJEURE

    def test_classify_payment(self, extractor):
        """Test classification of payment clause."""
        clause_type = extractor._classify_clause_type(
            "Payment Terms",
            "Payment shall be due within 30 days of invoice date.",
        )
        assert clause_type == ClauseType.PAYMENT

    def test_classify_intellectual_property(self, extractor):
        """Test classification of IP clause."""
        clause_type = extractor._classify_clause_type(
            "Intellectual Property Rights",
            "All patents, copyrights, and trademarks shall remain with the owner.",
        )
        assert clause_type == ClauseType.INTELLECTUAL_PROPERTY

    def test_classify_warranties(self, extractor):
        """Test classification of warranties clause."""
        clause_type = extractor._classify_clause_type(
            "Warranties",
            "The supplier warrants that products are free from defects.",
        )
        assert clause_type == ClauseType.WARRANTIES

    def test_classify_notices(self, extractor):
        """Test classification of notices clause."""
        clause_type = extractor._classify_clause_type(
            "Notices",
            "All notices shall be delivered by certified mail.",
        )
        assert clause_type == ClauseType.NOTICES

    def test_classify_other(self, extractor):
        """Test classification of unrecognized clause as OTHER."""
        clause_type = extractor._classify_clause_type(
            "Miscellaneous",
            "This section contains various provisions.",
        )
        assert clause_type == ClauseType.OTHER

    def test_classify_case_insensitive(self, extractor):
        """Test that classification is case-insensitive."""
        clause_type = extractor._classify_clause_type(
            "CONFIDENTIALITY",
            "Keep CONFIDENTIAL all information.",
        )
        assert clause_type == ClauseType.CONFIDENTIALITY


class TestConfidenceCalculation:
    """Tests for confidence score calculation."""

    @pytest.fixture
    def extractor(self):
        return PatternClauseExtractor()

    def test_confidence_other_type(self, extractor):
        """Test that OTHER type gets lower confidence."""
        confidence = extractor._calculate_confidence(
            ClauseType.OTHER, "Some generic content"
        )
        assert confidence == 0.5

    def test_confidence_multiple_keywords(self, extractor):
        """Test confidence increases with more keyword matches."""
        # Multiple keyword matches should give high confidence
        confidence = extractor._calculate_confidence(
            ClauseType.CONFIDENTIALITY,
            "This confidentiality agreement covers all confidential information and trade secrets.",
        )
        assert confidence >= 0.9

    def test_confidence_single_keyword(self, extractor):
        """Test confidence with single keyword match."""
        confidence = extractor._calculate_confidence(
            ClauseType.TERMINATION, "This clause covers termination."
        )
        assert 0.7 <= confidence <= 0.9


class TestSectionTitleExtraction:
    """Tests for section title extraction."""

    @pytest.fixture
    def extractor(self):
        return PatternClauseExtractor()

    def test_extract_title_with_number(self, extractor):
        """Test extracting title from numbered section."""
        title = extractor._extract_section_title("1.2.3 Definitions")
        assert title == "Definitions"

    def test_extract_title_with_trailing_period(self, extractor):
        """Test extracting title with trailing period on number."""
        title = extractor._extract_section_title("1. Introduction")
        assert title == "Introduction"

    def test_extract_title_no_number(self, extractor):
        """Test extracting title without section number."""
        title = extractor._extract_section_title("Introduction")
        assert title == "Introduction"


class TestClauseTypeKeywords:
    """Tests for clause type keywords configuration."""

    def test_all_clause_types_have_keywords(self):
        """Test that all clause types (except OTHER) have keywords defined."""
        for clause_type in ClauseType:
            if clause_type != ClauseType.OTHER:
                assert clause_type in CLAUSE_TYPE_KEYWORDS
                assert len(CLAUSE_TYPE_KEYWORDS[clause_type]) > 0

    def test_keywords_are_lowercase_compatible(self):
        """Test that keywords work with lowercase comparison."""
        for keywords in CLAUSE_TYPE_KEYWORDS.values():
            for keyword in keywords:
                # Keywords should be lowercase or work with .lower()
                assert keyword == keyword.lower()

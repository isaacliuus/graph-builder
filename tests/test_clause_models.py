"""Unit tests for clause models."""

import pytest
from uuid import UUID

from graph_builder.models.clause import Clause, ClauseType, ClauseLocation


class TestClauseType:
    def test_clause_types(self):
        assert ClauseType.DEFINITIONS.value == "DEFINITIONS"
        assert ClauseType.CONFIDENTIALITY.value == "CONFIDENTIALITY"
        assert ClauseType.TERMINATION.value == "TERMINATION"
        assert ClauseType.INDEMNIFICATION.value == "INDEMNIFICATION"
        assert ClauseType.LIABILITY.value == "LIABILITY"
        assert ClauseType.GOVERNING_LAW.value == "GOVERNING_LAW"
        assert ClauseType.DISPUTE_RESOLUTION.value == "DISPUTE_RESOLUTION"
        assert ClauseType.FORCE_MAJEURE.value == "FORCE_MAJEURE"
        assert ClauseType.PAYMENT.value == "PAYMENT"
        assert ClauseType.INTELLECTUAL_PROPERTY.value == "INTELLECTUAL_PROPERTY"
        assert ClauseType.WARRANTIES.value == "WARRANTIES"
        assert ClauseType.REPRESENTATIONS.value == "REPRESENTATIONS"
        assert ClauseType.NOTICES.value == "NOTICES"
        assert ClauseType.TERM_AND_TERMINATION.value == "TERM_AND_TERMINATION"
        assert ClauseType.OTHER.value == "OTHER"

    def test_clause_type_is_string_enum(self):
        assert isinstance(ClauseType.DEFINITIONS, str)
        assert ClauseType.DEFINITIONS == "DEFINITIONS"


class TestClauseLocation:
    def test_location_creation(self):
        location = ClauseLocation(
            paragraph_index=5,
            section_number="3.1",
            section_title="Confidentiality",
            start_char=100,
            end_char=500,
        )
        assert location.paragraph_index == 5
        assert location.section_number == "3.1"
        assert location.section_title == "Confidentiality"
        assert location.start_char == 100
        assert location.end_char == 500

    def test_location_optional_fields(self):
        location = ClauseLocation(
            paragraph_index=0,
            start_char=0,
            end_char=100,
        )
        assert location.section_number is None
        assert location.section_title is None

    def test_location_nested_section_number(self):
        location = ClauseLocation(
            paragraph_index=10,
            section_number="4.2.1",
            start_char=200,
            end_char=400,
        )
        assert location.section_number == "4.2.1"


class TestClause:
    def test_clause_creation(self):
        doc_id = UUID("00000000-0000-0000-0000-000000000001")
        location = ClauseLocation(
            paragraph_index=0,
            section_number="1",
            section_title="Definitions",
            start_char=0,
            end_char=100,
        )
        clause = Clause(
            content="This is a definitions clause.",
            type=ClauseType.DEFINITIONS,
            location=location,
            document_id=doc_id,
        )
        assert clause.content == "This is a definitions clause."
        assert clause.type == ClauseType.DEFINITIONS
        assert clause.location == location
        assert clause.document_id == doc_id
        assert isinstance(clause.id, UUID)
        assert clause.confidence == 1.0
        assert clause.metadata == {}

    def test_clause_with_confidence(self):
        doc_id = UUID("00000000-0000-0000-0000-000000000001")
        location = ClauseLocation(
            paragraph_index=0,
            start_char=0,
            end_char=100,
        )
        clause = Clause(
            content="Content",
            type=ClauseType.OTHER,
            location=location,
            document_id=doc_id,
            confidence=0.85,
        )
        assert clause.confidence == 0.85

    def test_clause_confidence_bounds(self):
        doc_id = UUID("00000000-0000-0000-0000-000000000001")
        location = ClauseLocation(
            paragraph_index=0,
            start_char=0,
            end_char=100,
        )

        # Valid bounds
        clause = Clause(
            content="Content",
            type=ClauseType.OTHER,
            location=location,
            document_id=doc_id,
            confidence=0.0,
        )
        assert clause.confidence == 0.0

        clause = Clause(
            content="Content",
            type=ClauseType.OTHER,
            location=location,
            document_id=doc_id,
            confidence=1.0,
        )
        assert clause.confidence == 1.0

        # Invalid bounds should raise
        with pytest.raises(ValueError):
            Clause(
                content="Content",
                type=ClauseType.OTHER,
                location=location,
                document_id=doc_id,
                confidence=-0.1,
            )

        with pytest.raises(ValueError):
            Clause(
                content="Content",
                type=ClauseType.OTHER,
                location=location,
                document_id=doc_id,
                confidence=1.1,
            )

    def test_clause_with_metadata(self):
        doc_id = UUID("00000000-0000-0000-0000-000000000001")
        location = ClauseLocation(
            paragraph_index=0,
            start_char=0,
            end_char=100,
        )
        clause = Clause(
            content="Content",
            type=ClauseType.CONFIDENTIALITY,
            location=location,
            document_id=doc_id,
            metadata={"key": "value", "nested": {"inner": True}},
        )
        assert clause.metadata == {"key": "value", "nested": {"inner": True}}

    def test_clause_has_unique_id(self):
        doc_id = UUID("00000000-0000-0000-0000-000000000001")
        location = ClauseLocation(
            paragraph_index=0,
            start_char=0,
            end_char=100,
        )
        clause1 = Clause(
            content="Content 1",
            type=ClauseType.OTHER,
            location=location,
            document_id=doc_id,
        )
        clause2 = Clause(
            content="Content 2",
            type=ClauseType.OTHER,
            location=location,
            document_id=doc_id,
        )
        assert clause1.id != clause2.id

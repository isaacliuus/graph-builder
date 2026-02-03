"""Clause models for legal contract processing."""

from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class ClauseType(str, Enum):
    """Types of clauses commonly found in legal contracts."""

    DEFINITIONS = "DEFINITIONS"
    CONFIDENTIALITY = "CONFIDENTIALITY"
    TERMINATION = "TERMINATION"
    INDEMNIFICATION = "INDEMNIFICATION"
    LIABILITY = "LIABILITY"
    GOVERNING_LAW = "GOVERNING_LAW"
    DISPUTE_RESOLUTION = "DISPUTE_RESOLUTION"
    FORCE_MAJEURE = "FORCE_MAJEURE"
    PAYMENT = "PAYMENT"
    INTELLECTUAL_PROPERTY = "INTELLECTUAL_PROPERTY"
    WARRANTIES = "WARRANTIES"
    REPRESENTATIONS = "REPRESENTATIONS"
    NOTICES = "NOTICES"
    TERM_AND_TERMINATION = "TERM_AND_TERMINATION"
    OTHER = "OTHER"


class ClauseLocation(BaseModel):
    """Location information for a clause within a document."""

    paragraph_index: int = Field(description="0-based paragraph index in the document")
    section_number: str | None = Field(
        default=None, description="Section number e.g., '3.1', '4.2.1'"
    )
    section_title: str | None = Field(
        default=None, description="Section heading text"
    )
    start_char: int = Field(description="Start character offset in document")
    end_char: int = Field(description="End character offset in document")


class Clause(BaseModel):
    """A clause extracted from a legal contract."""

    id: UUID = Field(default_factory=uuid4)
    content: str = Field(description="Full text of the clause")
    type: ClauseType = Field(description="Classification of the clause type")
    location: ClauseLocation = Field(description="Location metadata for the clause")
    document_id: UUID = Field(description="ID of the source document")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score for extraction"
    )
    metadata: dict = Field(default_factory=dict)

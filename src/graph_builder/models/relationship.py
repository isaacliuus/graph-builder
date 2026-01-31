"""Relationship models for knowledge graph."""

from enum import Enum
from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class RelationshipType(str, Enum):
    """Types of relationships between entities."""

    WORKS_FOR = "WORKS_FOR"
    LOCATED_IN = "LOCATED_IN"
    FOUNDED = "FOUNDED"
    ACQUIRED = "ACQUIRED"
    PARTNER_OF = "PARTNER_OF"
    SUBSIDIARY_OF = "SUBSIDIARY_OF"
    MEMBER_OF = "MEMBER_OF"
    CREATED = "CREATED"
    RELATED_TO = "RELATED_TO"
    OTHER = "OTHER"


class Relationship(BaseModel):
    """A relationship between two entities."""

    id: UUID = Field(default_factory=uuid4)
    source_id: UUID
    target_id: UUID
    type: RelationshipType
    weight: float = Field(default=1.0, ge=0.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    description: str = ""
    chunk_id: UUID | None = None
    metadata: dict = Field(default_factory=dict)

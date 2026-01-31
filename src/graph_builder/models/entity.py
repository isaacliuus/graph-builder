"""Entity models for knowledge graph."""

from enum import Enum
from uuid import UUID, uuid4
from pydantic import BaseModel, Field, computed_field


class EntityType(str, Enum):
    """Types of entities that can be extracted."""

    PERSON = "PERSON"
    ORGANIZATION = "ORG"
    LOCATION = "LOC"
    DATE = "DATE"
    EVENT = "EVENT"
    PRODUCT = "PRODUCT"
    CONCEPT = "CONCEPT"
    OTHER = "OTHER"


class Entity(BaseModel):
    """An extracted entity."""

    id: UUID = Field(default_factory=uuid4)
    name: str
    type: EntityType
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    chunk_id: UUID | None = None
    metadata: dict = Field(default_factory=dict)

    @computed_field
    @property
    def canonical_name(self) -> str:
        """Lowercase canonical name for deduplication."""
        return self.name.lower().strip()

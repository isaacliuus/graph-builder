"""Document and chunk models."""

from uuid import UUID, uuid4
from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """A chunk of text from a document."""

    id: UUID = Field(default_factory=uuid4)
    content: str
    document_id: UUID
    start_index: int = 0
    end_index: int = 0
    metadata: dict = Field(default_factory=dict)


class Document(BaseModel):
    """A document to be processed."""

    id: UUID = Field(default_factory=uuid4)
    content: str
    source: str = ""
    metadata: dict = Field(default_factory=dict)

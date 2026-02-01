"""Pytest configuration and shared fixtures."""

import pytest
from uuid import UUID

from graph_builder.models.document import Document, Chunk
from graph_builder.models.entity import Entity, EntityType
from graph_builder.models.relationship import Relationship, RelationshipType


@pytest.fixture
def sample_document():
    """A sample document for testing."""
    return Document(
        content="Apple Inc. was founded by Steve Jobs, Steve Wozniak, and Ronald Wayne in Cupertino, California.",
        source="sample.txt",
    )


@pytest.fixture
def sample_chunk(sample_document):
    """A sample chunk for testing."""
    return Chunk(
        content=sample_document.content,
        document_id=sample_document.id,
        start_index=0,
        end_index=len(sample_document.content),
    )


@pytest.fixture
def sample_entities(sample_chunk):
    """Sample entities for testing."""
    return [
        Entity(name="Apple Inc.", type=EntityType.ORGANIZATION, chunk_id=sample_chunk.id),
        Entity(name="Steve Jobs", type=EntityType.PERSON, chunk_id=sample_chunk.id),
        Entity(name="Steve Wozniak", type=EntityType.PERSON, chunk_id=sample_chunk.id),
        Entity(name="Ronald Wayne", type=EntityType.PERSON, chunk_id=sample_chunk.id),
        Entity(name="Cupertino", type=EntityType.LOCATION, chunk_id=sample_chunk.id),
        Entity(name="California", type=EntityType.LOCATION, chunk_id=sample_chunk.id),
    ]


@pytest.fixture
def sample_relationships(sample_entities):
    """Sample relationships for testing."""
    apple = sample_entities[0]
    steve_jobs = sample_entities[1]
    cupertino = sample_entities[4]

    return [
        Relationship(
            source_id=steve_jobs.id,
            target_id=apple.id,
            type=RelationshipType.FOUNDED,
        ),
        Relationship(
            source_id=apple.id,
            target_id=cupertino.id,
            type=RelationshipType.LOCATED_IN,
        ),
    ]

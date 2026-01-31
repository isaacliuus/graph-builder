"""LLM-based entity and relationship extraction using instructor."""

from uuid import UUID
from pydantic import BaseModel, Field

from graph_builder.models.document import Chunk
from graph_builder.models.entity import Entity, EntityType
from graph_builder.models.relationship import Relationship, RelationshipType
from graph_builder.extraction.base import EntityExtractorBase, RelationshipExtractorBase


class ExtractedEntity(BaseModel):
    """Schema for LLM-extracted entities."""

    name: str = Field(description="The entity name as it appears in the text")
    type: EntityType = Field(description="The type of entity")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score"
    )


class ExtractedEntities(BaseModel):
    """Container for extracted entities."""

    entities: list[ExtractedEntity] = Field(
        default_factory=list, description="List of extracted entities"
    )


class ExtractedRelationship(BaseModel):
    """Schema for LLM-extracted relationships."""

    source_name: str = Field(description="Name of the source entity")
    target_name: str = Field(description="Name of the target entity")
    type: RelationshipType = Field(description="The type of relationship")
    description: str = Field(default="", description="Description of the relationship")
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence score"
    )


class ExtractedRelationships(BaseModel):
    """Container for extracted relationships."""

    relationships: list[ExtractedRelationship] = Field(
        default_factory=list, description="List of extracted relationships"
    )


class LLMEntityExtractor(EntityExtractorBase):
    """Entity extractor using LLM with instructor."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self._client = None

    @property
    def client(self):
        """Lazy load the instructor client."""
        if self._client is None:
            try:
                import instructor
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "LLM extraction requires 'openai' and 'instructor' packages. "
                    "Install with: pip install openai instructor"
                )

            openai_client = OpenAI(api_key=self.api_key)
            self._client = instructor.from_openai(openai_client)
        return self._client

    def extract(self, chunks: list[Chunk]) -> list[Entity]:
        """Extract entities from chunks using LLM."""
        entities: list[Entity] = []

        for chunk in chunks:
            prompt = f"""Extract all named entities from the following text.
Identify people, organizations, locations, dates, events, products, and concepts.

Text:
{chunk.content}

Return a list of entities with their names, types, and confidence scores."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_model=ExtractedEntities,
            )

            for extracted in response.entities:
                entity = Entity(
                    name=extracted.name,
                    type=extracted.type,
                    confidence=extracted.confidence,
                    chunk_id=chunk.id,
                    metadata={"extraction_method": "llm", "model": self.model},
                )
                entities.append(entity)

        return entities


class LLMRelationshipExtractor(RelationshipExtractorBase):
    """Relationship extractor using LLM with instructor."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model
        self._client = None

    @property
    def client(self):
        """Lazy load the instructor client."""
        if self._client is None:
            try:
                import instructor
                from openai import OpenAI
            except ImportError:
                raise ImportError(
                    "LLM extraction requires 'openai' and 'instructor' packages. "
                    "Install with: pip install openai instructor"
                )

            openai_client = OpenAI(api_key=self.api_key)
            self._client = instructor.from_openai(openai_client)
        return self._client

    def extract(
        self, chunks: list[Chunk], entities: list[Entity]
    ) -> list[Relationship]:
        """Extract relationships using LLM."""
        relationships: list[Relationship] = []

        # Build entity name to ID mapping
        entity_name_to_id: dict[str, UUID] = {}
        for entity in entities:
            entity_name_to_id[entity.canonical_name] = entity.id

        # Group entities by chunk
        entities_by_chunk: dict[str, list[Entity]] = {}
        for entity in entities:
            if entity.chunk_id:
                chunk_key = str(entity.chunk_id)
                if chunk_key not in entities_by_chunk:
                    entities_by_chunk[chunk_key] = []
                entities_by_chunk[chunk_key].append(entity)

        for chunk in chunks:
            chunk_entities = entities_by_chunk.get(str(chunk.id), [])
            if len(chunk_entities) < 2:
                continue

            entity_names = [e.name for e in chunk_entities]
            prompt = f"""Given the following text and list of entities, extract relationships between the entities.

Text:
{chunk.content}

Entities: {', '.join(entity_names)}

For each relationship, specify:
- source_name: The name of the source entity (must be from the list)
- target_name: The name of the target entity (must be from the list)
- type: One of WORKS_FOR, LOCATED_IN, FOUNDED, ACQUIRED, PARTNER_OF, SUBSIDIARY_OF, MEMBER_OF, CREATED, RELATED_TO, OTHER
- description: A brief description of the relationship
- confidence: How confident you are (0.0 to 1.0)

Only extract relationships that are explicitly stated or strongly implied in the text."""

            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_model=ExtractedRelationships,
            )

            for extracted in response.relationships:
                source_canonical = extracted.source_name.lower().strip()
                target_canonical = extracted.target_name.lower().strip()

                source_id = entity_name_to_id.get(source_canonical)
                target_id = entity_name_to_id.get(target_canonical)

                if source_id and target_id:
                    relationship = Relationship(
                        source_id=source_id,
                        target_id=target_id,
                        type=extracted.type,
                        description=extracted.description,
                        confidence=extracted.confidence,
                        chunk_id=chunk.id,
                        metadata={"extraction_method": "llm", "model": self.model},
                    )
                    relationships.append(relationship)

        return relationships

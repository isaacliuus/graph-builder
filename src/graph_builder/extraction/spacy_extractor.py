"""spaCy-based entity and relationship extraction."""

import spacy
from spacy.language import Language

from graph_builder.models.document import Chunk
from graph_builder.models.entity import Entity, EntityType
from graph_builder.models.relationship import Relationship, RelationshipType
from graph_builder.extraction.base import EntityExtractorBase, RelationshipExtractorBase


# Mapping from spaCy entity labels to our EntityType
SPACY_TO_ENTITY_TYPE: dict[str, EntityType] = {
    "PERSON": EntityType.PERSON,
    "ORG": EntityType.ORGANIZATION,
    "GPE": EntityType.LOCATION,
    "LOC": EntityType.LOCATION,
    "DATE": EntityType.DATE,
    "EVENT": EntityType.EVENT,
    "PRODUCT": EntityType.PRODUCT,
    "WORK_OF_ART": EntityType.CONCEPT,
    "LAW": EntityType.CONCEPT,
    "NORP": EntityType.ORGANIZATION,
    "FAC": EntityType.LOCATION,
}


def get_spacy_model(model_name: str = "en_core_web_sm") -> Language:
    """Load or download spaCy model."""
    try:
        return spacy.load(model_name)
    except OSError:
        from spacy.cli import download

        download(model_name)
        return spacy.load(model_name)


class SpacyEntityExtractor(EntityExtractorBase):
    """Entity extractor using spaCy NER."""

    def __init__(self, model_name: str = "en_core_web_sm"):
        self.model_name = model_name
        self._nlp: Language | None = None

    @property
    def nlp(self) -> Language:
        """Lazy load the spaCy model."""
        if self._nlp is None:
            self._nlp = get_spacy_model(self.model_name)
        return self._nlp

    def extract(self, chunks: list[Chunk]) -> list[Entity]:
        """Extract entities from chunks using spaCy NER."""
        entities: list[Entity] = []

        for chunk in chunks:
            doc = self.nlp(chunk.content)

            for ent in doc.ents:
                entity_type = SPACY_TO_ENTITY_TYPE.get(ent.label_, EntityType.OTHER)
                entity = Entity(
                    name=ent.text,
                    type=entity_type,
                    confidence=1.0,
                    chunk_id=chunk.id,
                    metadata={
                        "spacy_label": ent.label_,
                        "start_char": ent.start_char,
                        "end_char": ent.end_char,
                    },
                )
                entities.append(entity)

        return entities


class SpacyRelationshipExtractor(RelationshipExtractorBase):
    """Relationship extractor using spaCy dependency parsing."""

    def __init__(self, model_name: str = "en_core_web_sm"):
        self.model_name = model_name
        self._nlp: Language | None = None

    @property
    def nlp(self) -> Language:
        """Lazy load the spaCy model."""
        if self._nlp is None:
            self._nlp = get_spacy_model(self.model_name)
        return self._nlp

    def extract(
        self, chunks: list[Chunk], entities: list[Entity]
    ) -> list[Relationship]:
        """Extract relationships using dependency parsing and co-occurrence."""
        relationships: list[Relationship] = []

        # Group entities by chunk
        entities_by_chunk: dict[str, list[Entity]] = {}
        for entity in entities:
            if entity.chunk_id:
                chunk_key = str(entity.chunk_id)
                if chunk_key not in entities_by_chunk:
                    entities_by_chunk[chunk_key] = []
                entities_by_chunk[chunk_key].append(entity)

        # For each chunk, find relationships between co-occurring entities
        for chunk in chunks:
            chunk_entities = entities_by_chunk.get(str(chunk.id), [])
            if len(chunk_entities) < 2:
                continue

            doc = self.nlp(chunk.content)

            # Create relationships based on syntactic proximity and verb connections
            for i, entity1 in enumerate(chunk_entities):
                for entity2 in chunk_entities[i + 1 :]:
                    rel_type = self._infer_relationship_type(
                        doc, entity1.name, entity2.name
                    )
                    if rel_type:
                        relationship = Relationship(
                            source_id=entity1.id,
                            target_id=entity2.id,
                            type=rel_type,
                            confidence=0.7,
                            chunk_id=chunk.id,
                        )
                        relationships.append(relationship)

        return relationships

    def _infer_relationship_type(
        self, doc, entity1_name: str, entity2_name: str
    ) -> RelationshipType | None:
        """Infer relationship type based on connecting verbs."""
        text_lower = doc.text.lower()
        e1_lower = entity1_name.lower()
        e2_lower = entity2_name.lower()

        # Check for common relationship patterns
        if "founded" in text_lower or "started" in text_lower or "created" in text_lower:
            return RelationshipType.FOUNDED
        if "works" in text_lower or "employed" in text_lower or "joined" in text_lower:
            return RelationshipType.WORKS_FOR
        if "located" in text_lower or "based" in text_lower or "in" in text_lower:
            if e1_lower in text_lower and e2_lower in text_lower:
                return RelationshipType.LOCATED_IN
        if "acquired" in text_lower or "bought" in text_lower:
            return RelationshipType.ACQUIRED
        if "partner" in text_lower:
            return RelationshipType.PARTNER_OF
        if "subsidiary" in text_lower:
            return RelationshipType.SUBSIDIARY_OF
        if "member" in text_lower:
            return RelationshipType.MEMBER_OF

        # Default to RELATED_TO for co-occurring entities
        return RelationshipType.RELATED_TO

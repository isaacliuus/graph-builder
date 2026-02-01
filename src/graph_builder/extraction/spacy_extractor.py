"""spaCy-based entity and relationship extraction."""

import spacy
from spacy.language import Language

from graph_builder.models.document import Chunk
from graph_builder.models.entity import Entity, EntityType
from graph_builder.models.relationship import Relationship, RelationshipType
from graph_builder.extraction.base import EntityExtractorBase, RelationshipExtractorBase
from graph_builder.extraction.utils import group_entities_by_chunk


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
            doc = self.nlp(chunk.content)  # pylint: disable=not-callable

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
        entities_by_chunk = group_entities_by_chunk(entities)

        # For each chunk, find relationships between co-occurring entities
        for chunk in chunks:
            chunk_entities = entities_by_chunk.get(str(chunk.id), [])
            if len(chunk_entities) < 2:
                continue

            doc = self.nlp(chunk.content)  # pylint: disable=not-callable

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

        # Keyword to relationship type mapping
        keyword_patterns: dict[RelationshipType, list[str]] = {
            RelationshipType.FOUNDED: ["founded", "started", "created"],
            RelationshipType.WORKS_FOR: ["works", "employed", "joined"],
            RelationshipType.ACQUIRED: ["acquired", "bought"],
            RelationshipType.PARTNER_OF: ["partner"],
            RelationshipType.SUBSIDIARY_OF: ["subsidiary"],
            RelationshipType.MEMBER_OF: ["member"],
        }

        for rel_type, keywords in keyword_patterns.items():
            if any(kw in text_lower for kw in keywords):
                return rel_type

        # Special case for location relationships
        if any(kw in text_lower for kw in ["located", "based", "headquartered"]):
            e1_lower = entity1_name.lower()
            e2_lower = entity2_name.lower()
            if e1_lower in text_lower and e2_lower in text_lower:
                return RelationshipType.LOCATED_IN

        # Default to RELATED_TO for co-occurring entities
        return RelationshipType.RELATED_TO

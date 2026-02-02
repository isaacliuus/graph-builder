"""Main evaluator for extraction quality assessment."""

from dataclasses import dataclass, field
from uuid import uuid4

from graph_builder.extraction.base import EntityExtractorBase, RelationshipExtractorBase
from graph_builder.models.document import Chunk
from graph_builder.models.entity import Entity, EntityType

from .dataset import GroundTruthDocument, GroundTruthEntity, GroundTruthRelationship
from .metrics import f1_score, precision, recall


# Map common entity type strings to EntityType enum
ENTITY_TYPE_MAP: dict[str, EntityType] = {
    "PERSON": EntityType.PERSON,
    "ORG": EntityType.ORGANIZATION,
    "ORGANIZATION": EntityType.ORGANIZATION,
    "LOC": EntityType.LOCATION,
    "LOCATION": EntityType.LOCATION,
    "GPE": EntityType.LOCATION,
    "DATE": EntityType.DATE,
    "EVENT": EntityType.EVENT,
    "PRODUCT": EntityType.PRODUCT,
    "CONCEPT": EntityType.CONCEPT,
    "OTHER": EntityType.OTHER,
}


def normalize_entity_type(type_str: str) -> EntityType:
    """Normalize an entity type string to EntityType enum."""
    return ENTITY_TYPE_MAP.get(type_str.upper(), EntityType.OTHER)


@dataclass
class DocumentResult:  # pylint: disable=too-many-instance-attributes
    """Evaluation results for a single document."""

    document_id: str
    entity_tp: int = 0
    entity_fp: int = 0
    entity_fn: int = 0
    relationship_tp: int = 0
    relationship_fp: int = 0
    relationship_fn: int = 0
    # Debug fields for extracted data
    extracted_entities: list = field(default_factory=list)
    extracted_relationships: list = field(default_factory=list)
    ground_truth_entities: list = field(default_factory=list)
    ground_truth_relationships: list = field(default_factory=list)


@dataclass
class EvaluationResult:
    """Overall evaluation results."""

    entity_precision: float
    entity_recall: float
    entity_f1: float
    relationship_precision: float
    relationship_recall: float
    relationship_f1: float
    details: dict[str, DocumentResult] = field(default_factory=dict)

    def to_dict(self, include_debug: bool = False) -> dict:
        """Convert results to a dictionary.

        Args:
            include_debug: If True, include extracted entities/relationships.
        """
        result = {
            "entity_precision": self.entity_precision,
            "entity_recall": self.entity_recall,
            "entity_f1": self.entity_f1,
            "relationship_precision": self.relationship_precision,
            "relationship_recall": self.relationship_recall,
            "relationship_f1": self.relationship_f1,
            "details": {},
        }

        for doc_id, doc_result in self.details.items():
            doc_dict = {
                "document_id": doc_result.document_id,
                "entity_tp": doc_result.entity_tp,
                "entity_fp": doc_result.entity_fp,
                "entity_fn": doc_result.entity_fn,
                "relationship_tp": doc_result.relationship_tp,
                "relationship_fp": doc_result.relationship_fp,
                "relationship_fn": doc_result.relationship_fn,
            }
            if include_debug:
                doc_dict["extracted_entities"] = doc_result.extracted_entities
                doc_dict["extracted_relationships"] = doc_result.extracted_relationships
                doc_dict["ground_truth_entities"] = doc_result.ground_truth_entities
                doc_dict["ground_truth_relationships"] = doc_result.ground_truth_relationships
            result["details"][doc_id] = doc_dict

        return result


class Evaluator:  # pylint: disable=too-few-public-methods
    """Evaluates extraction quality against ground truth datasets."""

    def __init__(
        self,
        entity_extractor: EntityExtractorBase,
        relationship_extractor: RelationshipExtractorBase,
    ):
        """Initialize the evaluator.

        Args:
            entity_extractor: Entity extractor to evaluate.
            relationship_extractor: Relationship extractor to evaluate.
        """
        self.entity_extractor = entity_extractor
        self.relationship_extractor = relationship_extractor

    def evaluate(  # pylint: disable=too-many-locals
        self, dataset: list[GroundTruthDocument]
    ) -> EvaluationResult:
        """Evaluate extractors against a ground truth dataset.

        Args:
            dataset: List of ground truth documents.

        Returns:
            EvaluationResult with precision, recall, F1 scores.
        """
        total_entity_tp = 0
        total_entity_fp = 0
        total_entity_fn = 0
        total_rel_tp = 0
        total_rel_fp = 0
        total_rel_fn = 0
        details: dict[str, DocumentResult] = {}

        for gt_doc in dataset:
            doc_result = self._evaluate_document(gt_doc)
            details[gt_doc.id] = doc_result

            total_entity_tp += doc_result.entity_tp
            total_entity_fp += doc_result.entity_fp
            total_entity_fn += doc_result.entity_fn
            total_rel_tp += doc_result.relationship_tp
            total_rel_fp += doc_result.relationship_fp
            total_rel_fn += doc_result.relationship_fn

        entity_prec = precision(total_entity_tp, total_entity_fp)
        entity_rec = recall(total_entity_tp, total_entity_fn)
        entity_f1 = f1_score(entity_prec, entity_rec)

        rel_prec = precision(total_rel_tp, total_rel_fp)
        rel_rec = recall(total_rel_tp, total_rel_fn)
        rel_f1 = f1_score(rel_prec, rel_rec)

        return EvaluationResult(
            entity_precision=entity_prec,
            entity_recall=entity_rec,
            entity_f1=entity_f1,
            relationship_precision=rel_prec,
            relationship_recall=rel_rec,
            relationship_f1=rel_f1,
            details=details,
        )

    def _evaluate_document(  # pylint: disable=too-many-locals
        self, gt_doc: GroundTruthDocument
    ) -> DocumentResult:
        """Evaluate extractors on a single document."""
        doc_id = uuid4()
        chunk = Chunk(
            content=gt_doc.content,
            document_id=doc_id,
            start_index=0,
            end_index=len(gt_doc.content),
        )

        # Extract entities
        extracted_entities = self.entity_extractor.extract([chunk])

        # Match entities and build entity map for relationship matching
        entity_tp, entity_fp, entity_fn, entity_map = self._match_entities(
            extracted_entities, gt_doc.entities
        )

        # Extract relationships
        extracted_relationships = self.relationship_extractor.extract(
            [chunk], extracted_entities
        )

        # Match relationships
        rel_tp, rel_fp, rel_fn = self._match_relationships(
            extracted_relationships, gt_doc.relationships, entity_map
        )

        # Build id_to_name map for relationship debug output
        id_to_name: dict[str, str] = {}
        for name, entity in entity_map.items():
            id_to_name[str(entity.id)] = name

        return DocumentResult(
            document_id=gt_doc.id,
            entity_tp=entity_tp,
            entity_fp=entity_fp,
            entity_fn=entity_fn,
            relationship_tp=rel_tp,
            relationship_fp=rel_fp,
            relationship_fn=rel_fn,
            extracted_entities=[
                {"name": e.name, "type": e.type.value, "confidence": e.confidence}
                for e in extracted_entities
            ],
            extracted_relationships=[
                {
                    "source": id_to_name.get(str(r.source_id), "unknown"),
                    "target": id_to_name.get(str(r.target_id), "unknown"),
                    "type": r.type.value,
                    "confidence": r.confidence,
                }
                for r in extracted_relationships
            ],
            ground_truth_entities=[
                {"name": e.name, "type": e.type} for e in gt_doc.entities
            ],
            ground_truth_relationships=[
                {"source": r.source, "target": r.target, "type": r.type}
                for r in gt_doc.relationships
            ],
        )

    def _match_entities(
        self, extracted: list[Entity], ground_truth: list[GroundTruthEntity]
    ) -> tuple[int, int, int, dict[str, Entity]]:
        """Match extracted entities against ground truth.

        Returns:
            Tuple of (true_positives, false_positives, false_negatives, entity_map)
            where entity_map maps canonical names to extracted entities.
        """
        # Build sets for matching
        extracted_set: set[tuple[str, EntityType]] = set()
        entity_map: dict[str, Entity] = {}

        for entity in extracted:
            key = (entity.canonical_name, entity.type)
            extracted_set.add(key)
            entity_map[entity.canonical_name] = entity

        gt_set: set[tuple[str, EntityType]] = set()
        for gt_entity in ground_truth:
            normalized_type = normalize_entity_type(gt_entity.type)
            key = (gt_entity.name.lower().strip(), normalized_type)
            gt_set.add(key)

        # Calculate metrics
        true_positives = len(extracted_set & gt_set)
        false_positives = len(extracted_set - gt_set)
        false_negatives = len(gt_set - extracted_set)

        return true_positives, false_positives, false_negatives, entity_map

    def _match_relationships(  # pylint: disable=too-many-locals
        self,
        extracted: list,
        ground_truth: list[GroundTruthRelationship],
        entity_map: dict[str, Entity],
    ) -> tuple[int, int, int]:
        """Match extracted relationships against ground truth.

        Returns:
            Tuple of (true_positives, false_positives, false_negatives).
        """
        # Build reverse map from entity ID to canonical name
        id_to_name: dict[str, str] = {}
        for name, entity in entity_map.items():
            id_to_name[str(entity.id)] = name

        # Build extracted relationship set
        extracted_set: set[tuple[str, str, str]] = set()
        for rel in extracted:
            source_name = id_to_name.get(str(rel.source_id), "")
            target_name = id_to_name.get(str(rel.target_id), "")
            if source_name and target_name:
                key = (source_name, target_name, rel.type.value)
                extracted_set.add(key)

        # Build ground truth relationship set
        gt_set: set[tuple[str, str, str]] = set()
        for gt_rel in ground_truth:
            key = (
                gt_rel.source.lower().strip(),
                gt_rel.target.lower().strip(),
                gt_rel.type,
            )
            gt_set.add(key)

        # Calculate metrics
        true_positives = len(extracted_set & gt_set)
        false_positives = len(extracted_set - gt_set)
        false_negatives = len(gt_set - extracted_set)

        return true_positives, false_positives, false_negatives

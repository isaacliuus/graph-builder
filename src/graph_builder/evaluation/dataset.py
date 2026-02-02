"""Ground truth dataset models and loading."""

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GroundTruthEntity:
    """A ground truth entity annotation."""

    name: str
    type: str


@dataclass
class GroundTruthRelationship:
    """A ground truth relationship annotation."""

    source: str
    target: str
    type: str


@dataclass
class GroundTruthDocument:
    """A document with ground truth annotations."""

    id: str
    content: str
    entities: list[GroundTruthEntity] = field(default_factory=list)
    relationships: list[GroundTruthRelationship] = field(default_factory=list)


def load_dataset(path: Path | str) -> list[GroundTruthDocument]:
    """Load a ground truth dataset from a JSON file.

    Args:
        path: Path to the JSON dataset file.

    Returns:
        List of GroundTruthDocument objects.

    Raises:
        FileNotFoundError: If the dataset file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
        KeyError: If required fields are missing.
    """
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    documents = []
    for doc_data in data.get("documents", []):
        entities = [
            GroundTruthEntity(name=e["name"], type=e["type"])
            for e in doc_data.get("entities", [])
        ]
        relationships = [
            GroundTruthRelationship(
                source=r["source"], target=r["target"], type=r["type"]
            )
            for r in doc_data.get("relationships", [])
        ]
        documents.append(
            GroundTruthDocument(
                id=doc_data["id"],
                content=doc_data["content"],
                entities=entities,
                relationships=relationships,
            )
        )

    return documents

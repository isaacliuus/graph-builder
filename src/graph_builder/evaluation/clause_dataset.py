"""Ground truth dataset models for clause extraction evaluation."""

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class GroundTruthClause:
    """A ground truth clause annotation."""

    type: str
    section_number: str | None = None
    title: str | None = None
    start_paragraph: int | None = None
    end_paragraph: int | None = None


@dataclass
class GroundTruthContractDocument:
    """A contract document with ground truth clause annotations."""

    id: str
    file: str
    clauses: list[GroundTruthClause] = field(default_factory=list)


def load_clause_dataset(path: Path | str) -> list[GroundTruthContractDocument]:
    """Load a ground truth clause dataset from a JSON file.

    Args:
        path: Path to the JSON dataset file.

    Returns:
        List of GroundTruthContractDocument objects.

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
        clauses = [
            GroundTruthClause(
                type=c["type"],
                section_number=c.get("section_number"),
                title=c.get("title"),
                start_paragraph=c.get("start_paragraph"),
                end_paragraph=c.get("end_paragraph"),
            )
            for c in doc_data.get("clauses", [])
        ]
        documents.append(
            GroundTruthContractDocument(
                id=doc_data["id"],
                file=doc_data["file"],
                clauses=clauses,
            )
        )

    return documents

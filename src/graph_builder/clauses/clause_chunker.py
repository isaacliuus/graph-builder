"""Clause-based chunkers that use clause extraction to split documents."""

from graph_builder.clauses.base import ClauseExtractor
from graph_builder.models.clause import Clause
from graph_builder.models.document import Document, Chunk


def _clause_to_chunk(clause: Clause) -> Chunk:
    """Convert a Clause to a Chunk, preserving clause metadata."""
    return Chunk(
        content=clause.content,
        document_id=clause.document_id,
        start_index=clause.location.start_char,
        end_index=clause.location.end_char,
        metadata={
            "clause_type": clause.type.value,
            "section_number": clause.location.section_number,
            "section_title": clause.location.section_title,
            "clause_id": str(clause.id),
            "confidence": clause.confidence,
        },
    )


class ClauseChunker:
    """Chunker that uses clause extraction to split documents into chunks.

    Each extracted clause becomes a chunk, making the pipeline contract-aware:
    entities are extracted per clause, and co-occurrence means "appears in the
    same clause".
    """

    def __init__(
        self,
        clause_extractor: ClauseExtractor | None = None,
        min_clause_length: int = 50,
    ) -> None:
        if clause_extractor is not None:
            self.clause_extractor = clause_extractor
        else:
            from graph_builder.clauses.pattern_extractor import PatternClauseExtractor

            self.clause_extractor = PatternClauseExtractor(
                min_clause_length=min_clause_length
            )

    def chunk(self, documents: list[Document]) -> list[Chunk]:
        """Split documents into chunks using clause extraction."""
        chunks: list[Chunk] = []

        for document in documents:
            clauses = self.clause_extractor.extract(document)
            chunks.extend(_clause_to_chunk(c) for c in clauses)

        return chunks


class DoclingClauseChunker(ClauseChunker):
    """Clause chunker designed for Docling-parsed documents.

    Expects Documents that were parsed by DoclingParser (with paragraph metadata).
    Uses clause extraction to split each document into clause-based chunks.

    This is the default chunker for the entity graph pipeline when processing
    contract files (.pdf, .docx) parsed with Docling.
    """

    def __init__(
        self,
        clause_extractor: ClauseExtractor | None = None,
        min_clause_length: int = 50,
    ) -> None:
        super().__init__(
            clause_extractor=clause_extractor,
            min_clause_length=min_clause_length,
        )

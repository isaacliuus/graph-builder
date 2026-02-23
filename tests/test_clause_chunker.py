"""Tests for ClauseChunker and DoclingClauseChunker."""

from unittest.mock import MagicMock
from uuid import uuid4

from graph_builder.clauses.clause_chunker import ClauseChunker, DoclingClauseChunker
from graph_builder.models.clause import Clause, ClauseType, ClauseLocation
from graph_builder.models.document import Document


def _make_clause(
    content: str,
    document_id,
    clause_type=ClauseType.CONFIDENTIALITY,
    section_number="1.1",
    section_title="Confidentiality",
    start_char=0,
    end_char=100,
    confidence=0.95,
):
    return Clause(
        content=content,
        type=clause_type,
        location=ClauseLocation(
            paragraph_index=0,
            section_number=section_number,
            section_title=section_title,
            start_char=start_char,
            end_char=end_char,
        ),
        document_id=document_id,
        confidence=confidence,
    )


class TestClauseChunker:
    def test_clause_to_chunk_conversion(self):
        doc_id = uuid4()
        doc = Document(id=doc_id, content="Some contract text.")

        clause = _make_clause(
            content="The parties agree to keep information confidential.",
            document_id=doc_id,
            start_char=10,
            end_char=60,
        )

        extractor = MagicMock()
        extractor.extract.return_value = [clause]

        chunker = ClauseChunker(clause_extractor=extractor)
        chunks = chunker.chunk([doc])

        assert len(chunks) == 1
        chunk = chunks[0]
        assert chunk.content == clause.content
        assert chunk.document_id == doc_id
        assert chunk.start_index == 10
        assert chunk.end_index == 60

    def test_clause_metadata_preserved(self):
        doc_id = uuid4()
        doc = Document(id=doc_id, content="Contract text.")

        clause = _make_clause(
            content="Payment shall be made within 30 days.",
            document_id=doc_id,
            clause_type=ClauseType.PAYMENT,
            section_number="3.2",
            section_title="Payment Terms",
            confidence=0.88,
        )

        extractor = MagicMock()
        extractor.extract.return_value = [clause]

        chunker = ClauseChunker(clause_extractor=extractor)
        chunks = chunker.chunk([doc])

        meta = chunks[0].metadata
        assert meta["clause_type"] == "PAYMENT"
        assert meta["section_number"] == "3.2"
        assert meta["section_title"] == "Payment Terms"
        assert meta["clause_id"] == str(clause.id)
        assert meta["confidence"] == 0.88

    def test_multiple_documents(self):
        doc1_id = uuid4()
        doc2_id = uuid4()
        doc1 = Document(id=doc1_id, content="First contract.")
        doc2 = Document(id=doc2_id, content="Second contract.")

        clause1 = _make_clause(content="Clause from doc 1." * 5, document_id=doc1_id)
        clause2 = _make_clause(
            content="Clause from doc 2." * 5,
            document_id=doc2_id,
            clause_type=ClauseType.TERMINATION,
        )

        extractor = MagicMock()
        extractor.extract.side_effect = [[clause1], [clause2]]

        chunker = ClauseChunker(clause_extractor=extractor)
        chunks = chunker.chunk([doc1, doc2])

        assert len(chunks) == 2
        assert chunks[0].document_id == doc1_id
        assert chunks[1].document_id == doc2_id
        assert chunks[1].metadata["clause_type"] == "TERMINATION"

    def test_empty_clauses_returns_empty(self):
        doc = Document(content="No clauses here.")

        extractor = MagicMock()
        extractor.extract.return_value = []

        chunker = ClauseChunker(clause_extractor=extractor)
        chunks = chunker.chunk([doc])

        assert len(chunks) == 0

    def test_default_extractor_used_when_none_provided(self):
        chunker = ClauseChunker()
        from graph_builder.clauses.pattern_extractor import PatternClauseExtractor

        assert isinstance(chunker.clause_extractor, PatternClauseExtractor)

    def test_section_title_none_preserved(self):
        doc_id = uuid4()
        doc = Document(id=doc_id, content="Text.")

        clause = _make_clause(
            content="Some clause content without title." * 3,
            document_id=doc_id,
            section_title=None,
            section_number=None,
        )

        extractor = MagicMock()
        extractor.extract.return_value = [clause]

        chunker = ClauseChunker(clause_extractor=extractor)
        chunks = chunker.chunk([doc])

        assert chunks[0].metadata["section_title"] is None
        assert chunks[0].metadata["section_number"] is None


class TestDoclingClauseChunker:
    def test_is_subclass_of_clause_chunker(self):
        assert issubclass(DoclingClauseChunker, ClauseChunker)

    def test_default_extractor(self):
        chunker = DoclingClauseChunker()
        from graph_builder.clauses.pattern_extractor import PatternClauseExtractor

        assert isinstance(chunker.clause_extractor, PatternClauseExtractor)

    def test_custom_extractor(self):
        extractor = MagicMock()
        chunker = DoclingClauseChunker(clause_extractor=extractor)
        assert chunker.clause_extractor is extractor

    def test_chunks_docling_parsed_document(self):
        """DoclingClauseChunker works with Docling-parsed documents (with paragraph metadata)."""
        doc_id = uuid4()
        doc = Document(
            id=doc_id,
            content="1.1 Confidentiality\nParties shall keep all information confidential.",
            source="contract.pdf",
            metadata={
                "file_type": "pdf",
                "parser": "docling",
                "paragraphs": [
                    {
                        "index": 0,
                        "text": "1.1 Confidentiality",
                        "style": "Heading 1",
                        "is_heading": True,
                        "section_number": "1.1",
                        "start_char": 0,
                        "end_char": 19,
                    },
                    {
                        "index": 1,
                        "text": "Parties shall keep all information confidential.",
                        "style": "Normal",
                        "is_heading": False,
                        "section_number": None,
                        "start_char": 20,
                        "end_char": 68,
                    },
                ],
            },
        )

        clause = _make_clause(
            content="Parties shall keep all information confidential.",
            document_id=doc_id,
            clause_type=ClauseType.CONFIDENTIALITY,
            section_number="1.1",
            section_title="Confidentiality",
            start_char=20,
            end_char=68,
        )

        extractor = MagicMock()
        extractor.extract.return_value = [clause]

        chunker = DoclingClauseChunker(clause_extractor=extractor)
        chunks = chunker.chunk([doc])

        assert len(chunks) == 1
        assert chunks[0].metadata["clause_type"] == "CONFIDENTIALITY"
        assert chunks[0].start_index == 20
        assert chunks[0].end_index == 68
        extractor.extract.assert_called_once_with(doc)

"""Unit tests for chunking module."""

import pytest

from graph_builder.models.document import Document
from graph_builder.chunking.recursive import RecursiveChunker


class TestRecursiveChunker:
    def test_chunker_creation(self):
        chunker = RecursiveChunker(chunk_size=100, chunk_overlap=20)
        assert chunker.chunk_size == 100
        assert chunker.chunk_overlap == 20

    def test_chunk_short_document(self):
        chunker = RecursiveChunker(chunk_size=1000, chunk_overlap=100)
        doc = Document(content="Short text.", source="test.txt")
        chunks = chunker.chunk([doc])

        assert len(chunks) == 1
        assert chunks[0].content == "Short text."
        assert chunks[0].document_id == doc.id

    def test_chunk_long_document(self):
        chunker = RecursiveChunker(chunk_size=50, chunk_overlap=10)
        content = "This is a longer document. " * 10
        doc = Document(content=content, source="test.txt")
        chunks = chunker.chunk([doc])

        assert len(chunks) > 1
        for chunk in chunks:
            assert chunk.document_id == doc.id
            assert len(chunk.content) <= 50 + 10  # Allow for overlap

    def test_chunk_multiple_documents(self):
        chunker = RecursiveChunker(chunk_size=1000, chunk_overlap=100)
        doc1 = Document(content="First document.", source="doc1.txt")
        doc2 = Document(content="Second document.", source="doc2.txt")
        chunks = chunker.chunk([doc1, doc2])

        assert len(chunks) == 2
        assert chunks[0].document_id == doc1.id
        assert chunks[1].document_id == doc2.id

    def test_chunk_preserves_metadata(self):
        chunker = RecursiveChunker()
        doc = Document(content="Test content", source="test.txt")
        chunks = chunker.chunk([doc])

        assert chunks[0].metadata.get("source") == "test.txt"

    def test_chunk_indices(self):
        chunker = RecursiveChunker(chunk_size=1000)
        doc = Document(content="Hello world", source="test.txt")
        chunks = chunker.chunk([doc])

        assert chunks[0].start_index == 0
        assert chunks[0].end_index == 11

    def test_chunk_empty_document(self):
        chunker = RecursiveChunker()
        doc = Document(content="", source="empty.txt")
        chunks = chunker.chunk([doc])

        assert len(chunks) == 0

    def test_chunk_with_custom_separators(self):
        chunker = RecursiveChunker(
            chunk_size=50,
            chunk_overlap=0,
            separators=["\n\n", "\n", " "],
        )
        content = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        doc = Document(content=content)
        chunks = chunker.chunk([doc])

        assert len(chunks) >= 1
        for chunk in chunks:
            assert chunk.document_id == doc.id

"""Recursive character text splitter implementation."""

from langchain_text_splitters import RecursiveCharacterTextSplitter

from graph_builder.models.document import Document, Chunk
from graph_builder.chunking.base import ChunkerBase


class RecursiveChunker(ChunkerBase):  # pylint: disable=too-few-public-methods
    """Chunker using langchain's RecursiveCharacterTextSplitter."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separators: list[str] | None = None,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.separators = separators or ["\n\n", "\n", ". ", " ", ""]

        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=self.separators,
            length_function=len,
        )

    def chunk(self, documents: list[Document]) -> list[Chunk]:
        """Split documents into chunks."""
        chunks: list[Chunk] = []

        for doc in documents:
            split_texts = self._splitter.split_text(doc.content)

            #TODO: make this more efficient
            current_index = 0
            for text in split_texts:
                start_index = doc.content.find(text, current_index)
                if start_index == -1:
                    start_index = current_index
                end_index = start_index + len(text)

                chunk = Chunk(
                    content=text,
                    document_id=doc.id,
                    start_index=start_index,
                    end_index=end_index,
                    metadata={"source": doc.source},
                )
                chunks.append(chunk)
                current_index = start_index + 1

        return chunks

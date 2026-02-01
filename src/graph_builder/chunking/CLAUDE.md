# Chunking Module

Text chunking implementations for splitting documents.

## Files

- `base.py` - ChunkerBase abstract class
- `recursive.py` - RecursiveChunker wrapping langchain's RecursiveCharacterTextSplitter

## Conventions

- Chunkers implement the `Chunker` protocol from `pipeline.base`
- Default chunk_size=1000, chunk_overlap=200
- Chunks track start_index and end_index for source mapping

# Graph Builder

A modular knowledge graph pipeline that extracts entities and relationships from text. Supports both spaCy (fast/free) and LLM-based (higher quality) extraction.

**Requirements:** Python 3.11+

## Project Structure

```
src/graph_builder/
├── models/       # Pydantic data models (Document, Entity, Relationship, KnowledgeGraph)
├── pipeline/     # Pipeline orchestration and builder API
├── chunking/     # Text chunking (RecursiveCharacterTextSplitter)
├── extraction/   # Entity & relationship extraction (spaCy, LLM)
├── graph/        # Graph building (NetworkX)
└── config/       # Pydantic settings
```

## Installation

```bash
# Install dependencies
uv sync

# Install with LLM support
uv sync --extra llm

# Install with dev dependencies (pytest)
uv sync --extra dev

# Download spaCy model (required)
uv pip install en-core-web-sm@https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl
```

## Usage

### CLI

```bash
# Run with sample text
uv run python main.py

# Run with a file
uv run python main.py your_text_file.txt
```

### Python API

```python
from graph_builder import Document, PipelineBuilder

docs = [Document(content="Apple was founded by Steve Jobs.")]

# Default (spaCy-based)
pipeline = PipelineBuilder.default()
graph = pipeline.run(docs)

# LLM-based (requires openai + instructor)
pipeline = PipelineBuilder.with_llm(api_key="sk-...")
graph = pipeline.run(docs)
```

## Environment Variables

- `GRAPH_BUILDER_USE_LLM` - Enable LLM extraction (default: false)
- `GRAPH_BUILDER_OPENAI_API_KEY` - OpenAI API key
- `GRAPH_BUILDER_LLM_MODEL` - LLM model (default: gpt-4o-mini)

## Architecture

The pipeline has 4 stages:
1. **Chunking** - Split documents into chunks
2. **Entity Extraction** - Extract named entities (PERSON, ORG, LOC, etc.)
3. **Relationship Extraction** - Find relationships between entities
4. **Graph Building** - Build KnowledgeGraph with deduplication

## Testing

```bash
uv run pytest tests/ -v
```

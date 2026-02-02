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
├── evaluation/   # Extraction quality metrics (precision, recall, F1)
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
# Run with sample text (uses spaCy by default)
uv run python main.py

# Run with a file
uv run python main.py your_text_file.txt
```

### Using the LLM Extractor

The LLM extractor provides higher quality extraction than spaCy but requires an OpenAI API key.

**Via environment variables:**
```bash
# Set variables and run
GRAPH_BUILDER_USE_LLM=true GRAPH_BUILDER_OPENAI_API_KEY=sk-... uv run python main.py

# Or export them
export GRAPH_BUILDER_USE_LLM=true
export GRAPH_BUILDER_OPENAI_API_KEY=sk-...
uv run python main.py
```

**Via .env file:**
```bash
# Create .env file
echo "GRAPH_BUILDER_USE_LLM=true" >> .env
echo "GRAPH_BUILDER_OPENAI_API_KEY=sk-..." >> .env

# Run (pydantic-settings loads .env automatically)
uv run python main.py
```

### Python API

```python
from graph_builder import Document, PipelineBuilder

docs = [Document(content="Apple was founded by Steve Jobs.")]

# Default (spaCy-based) - fast and free
pipeline = PipelineBuilder.default()
graph = pipeline.run(docs)

# LLM-based - higher quality extraction
pipeline = PipelineBuilder.with_llm(api_key="sk-...", model="gpt-4o-mini")
graph = pipeline.run(docs)
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GRAPH_BUILDER_USE_LLM` | Enable LLM extraction | `false` |
| `GRAPH_BUILDER_OPENAI_API_KEY` | OpenAI API key | (required for LLM) |
| `GRAPH_BUILDER_LLM_MODEL` | Model to use | `gpt-4o-mini` |

## Architecture

The pipeline has 4 stages:
1. **Chunking** - Split documents into chunks
2. **Entity Extraction** - Extract named entities (PERSON, ORG, LOC, etc.)
3. **Relationship Extraction** - Find relationships between entities
4. **Graph Building** - Build KnowledgeGraph with deduplication

## Evaluation

Measure extraction quality against ground truth datasets using precision, recall, and F1 metrics.

```bash
# Run evaluation with spaCy (default)
uv run python scripts/run_evaluation.py data/ground_truth/sample.json

# Run with LLM extractor
uv run python scripts/run_evaluation.py data/ground_truth/sample.json --extractor llm

# Export debug info to tmp/ folder
uv run python scripts/run_evaluation.py data/ground_truth/sample.json --debug

# Save results to JSON
uv run python scripts/run_evaluation.py data/ground_truth/sample.json --output results.json
```

### Ground Truth Format

```json
{
  "documents": [
    {
      "id": "doc1",
      "content": "Apple Inc. was founded by Steve Jobs.",
      "entities": [
        {"name": "Apple Inc.", "type": "ORG"},
        {"name": "Steve Jobs", "type": "PERSON"}
      ],
      "relationships": [
        {"source": "Steve Jobs", "target": "Apple Inc.", "type": "FOUNDED"}
      ]
    }
  ]
}
```

## Testing

```bash
uv run pytest tests/ -v
```

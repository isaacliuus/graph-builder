# Graph Builder

A modular knowledge graph pipeline that extracts entities and relationships from text, and clauses from legal contracts. Supports both spaCy (fast/free) and LLM-based (higher quality) extraction.

**Requirements:** Python 3.11+

## Project Structure

```
src/graph_builder/
├── models/       # Pydantic data models (Document, Entity, Relationship, KnowledgeGraph, Clause)
├── pipeline/     # Pipeline orchestration and builder API
├── chunking/     # Text chunking (RecursiveCharacterTextSplitter)
├── extraction/   # Entity & relationship extraction (spaCy, LLM)
├── parsing/      # Document parsing (.docx, .pdf)
├── clauses/      # Clause extraction from legal contracts
├── graph/        # Graph building (NetworkX)
├── graphdb/      # Graph database persistence (Memgraph)
├── evaluation/   # Extraction quality metrics (precision, recall, F1)
└── config/       # Pydantic settings
```

## Installation

```bash
# Install dependencies
uv sync

# Install with LLM support
uv sync --extra llm

# Install with Memgraph support
uv sync --extra memgraph

# Install with contract parsing support (.docx, .pdf)
uv sync --extra contracts

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

### Clause Extraction from Legal Contracts

Extract clauses from contract files (.docx or .pdf) with type classification and location tracking.

```bash
# Extract clauses from a contract file (pattern-based, default)
uv run python scripts/extract_clauses.py data/test_contracts/contract.docx

# Extract from PDF
uv run python scripts/extract_clauses.py contract.pdf

# Use LLM for higher quality extraction
uv run python scripts/extract_clauses.py contract.docx --extractor llm --api-key sk-...

# Table format (summary)
uv run python scripts/extract_clauses.py contract.docx --format table

# Save to JSON
uv run python scripts/extract_clauses.py contract.docx --output clauses.json
```

**Python API (Pattern-based):**

```python
from pathlib import Path
from graph_builder.parsing import DocxParser, PdfParser
from graph_builder.clauses import PatternClauseExtractor

# Parse a .docx document
parser = DocxParser()
doc = parser.parse(Path("contract.docx"))

# Or parse a .pdf document
parser = PdfParser()
doc = parser.parse(Path("contract.pdf"))

# Extract clauses
extractor = PatternClauseExtractor()
clauses = extractor.extract(doc)

for clause in clauses:
    print(f"{clause.type.value}: {clause.location.section_title}")
```

**Python API (LLM-based):**

```python
from pathlib import Path
from graph_builder.parsing import DocxParser, PdfParser
from graph_builder.clauses import LLMClauseExtractor

# Parse the document (works with both .docx and .pdf)
parser = PdfParser()
doc = parser.parse(Path("contract.pdf"))

# Extract clauses with LLM (higher quality)
extractor = LLMClauseExtractor(api_key="sk-...", model="gpt-4o-mini")
clauses = extractor.extract(doc)

for clause in clauses:
    print(f"{clause.type.value}: {clause.location.section_title}")
    print(f"Confidence: {clause.confidence}")
```

**Supported Clause Types:**
- DEFINITIONS, CONFIDENTIALITY, TERMINATION, INDEMNIFICATION
- LIABILITY, GOVERNING_LAW, DISPUTE_RESOLUTION, FORCE_MAJEURE
- PAYMENT, INTELLECTUAL_PROPERTY, WARRANTIES, REPRESENTATIONS
- NOTICES, TERM_AND_TERMINATION, OTHER

**Features:**
- Bilingual support (English/Chinese keywords)
- Section number and title detection
- Character offset tracking
- Confidence scores for classifications

### Persisting to Memgraph

The pipeline can automatically persist extracted graphs to a Memgraph database.

```python
from graph_builder import Document, PipelineBuilder
from graph_builder.graphdb.memgraph import MemgraphGraphDB

docs = [Document(content="Apple was founded by Steve Jobs.")]

# Run pipeline and persist to Memgraph
with MemgraphGraphDB(host="localhost", port=7687) as db:
    pipeline = PipelineBuilder.default()
    pipeline.graphdb = db
    graph = pipeline.run(docs)  # Automatically syncs to Memgraph

# Or use the builder API
with MemgraphGraphDB(host="localhost", port=7687) as db:
    from graph_builder.chunking.recursive import RecursiveChunker
    from graph_builder.extraction.spacy_extractor import (
        SpacyEntityExtractor,
        SpacyRelationshipExtractor,
    )
    from graph_builder.graph.networkx_builder import NetworkXGraphBuilder

    pipeline = (
        PipelineBuilder()
        .with_chunker(RecursiveChunker())
        .with_entity_extractor(SpacyEntityExtractor())
        .with_relationship_extractor(SpacyRelationshipExtractor())
        .with_graph_builder(NetworkXGraphBuilder())
        .with_graphdb(db)
        .build()
    )
    graph = pipeline.run(docs)

# Standalone usage (without pipeline)
with MemgraphGraphDB(host="localhost", port=7687) as db:
    db.sync(graph)  # Persist an existing graph
    loaded = db.load_graph()  # Load graph from database
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GRAPH_BUILDER_USE_LLM` | Enable LLM extraction | `false` |
| `GRAPH_BUILDER_OPENAI_API_KEY` | OpenAI API key | (required for LLM) |
| `GRAPH_BUILDER_LLM_MODEL` | Model to use | `gpt-4o-mini` |
| `GRAPH_BUILDER_MEMGRAPH_HOST` | Memgraph server hostname | `localhost` |
| `GRAPH_BUILDER_MEMGRAPH_PORT` | Memgraph Bolt port | `7687` |
| `GRAPH_BUILDER_MEMGRAPH_USERNAME` | Memgraph username | (empty) |
| `GRAPH_BUILDER_MEMGRAPH_PASSWORD` | Memgraph password | (empty) |
| `GRAPH_BUILDER_MEMGRAPH_DATABASE` | Memgraph database name | `memgraph` |
| `GRAPH_BUILDER_USE_GRAPHDB` | Enable graph database persistence | `false` |

## Architecture

The pipeline has 5 stages:
1. **Chunking** - Split documents into chunks
2. **Entity Extraction** - Extract named entities (PERSON, ORG, LOC, etc.)
3. **Relationship Extraction** - Find relationships between entities
4. **Graph Building** - Build KnowledgeGraph with deduplication
5. **Persistence** (optional) - Sync graph to database (Memgraph)

## Evaluation

### Entity & Relationship Extraction

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

**Ground Truth Format:**

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

### Clause Extraction Evaluation

Evaluate clause extraction quality with detection, type classification, and boundary metrics. Supports both .docx and .pdf contract files.

```bash
# Run clause evaluation (pattern-based, default)
uv run python scripts/run_clause_evaluation.py data/ground_truth/contracts/sample.json

# Use LLM extractor for evaluation
uv run python scripts/run_clause_evaluation.py data/ground_truth/contracts/sample.json --extractor llm --api-key sk-...

# With debug output
uv run python scripts/run_clause_evaluation.py data/ground_truth/contracts/sample.json --debug

# Save results
uv run python scripts/run_clause_evaluation.py data/ground_truth/contracts/sample.json --output results.json
```

**Ground Truth Format:**

```json
{
  "documents": [
    {
      "id": "contract1",
      "file": "contract.docx",
      "clauses": [
        {
          "type": "CONFIDENTIALITY",
          "section_number": "2",
          "title": "Confidential Information",
          "start_paragraph": 4,
          "end_paragraph": 8
        }
      ]
    },
    {
      "id": "contract2",
      "file": "contract.pdf",
      "clauses": [...]
    }
  ]
}
```

**Metrics:**
- Detection precision, recall, and F1 score
- Type classification accuracy
- Boundary IoU (Intersection over Union)

## Testing

```bash
uv run pytest tests/ -v
```

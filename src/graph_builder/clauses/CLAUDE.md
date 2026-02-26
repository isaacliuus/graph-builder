# Clauses Module

Clause extraction from legal contracts and documents.

## Files

- `base.py` - `ClauseExtractor` Protocol defining the extractor interface
- `pattern_extractor.py` - Rule-based clause extraction using keyword matching
- `llm_extractor.py` - LLM-based clause extraction using OpenAI + instructor (optional dependency)
- `clause_chunker.py` - `ClauseChunker` adapter that wraps a `ClauseExtractor` to implement the `Chunker` protocol
- `textin_chunker.py` - `TextinClauseChunker` (Chunker protocol) and `TextinClauseExtractor` (ClauseExtractor protocol) using Textin's catalog tree

## Protocol

```python
@runtime_checkable
class ClauseExtractor(Protocol):
    def extract(self, document: Document) -> list[Clause]: ...
```

## PatternClauseExtractor

Rule-based clause extractor that:
1. Identifies clause boundaries using heading styles and section numbers
2. Classifies clause types via keyword matching
3. Extracts content between section boundaries with location metadata

### Clause Types Supported

- DEFINITIONS, CONFIDENTIALITY, TERMINATION, INDEMNIFICATION
- LIABILITY, GOVERNING_LAW, DISPUTE_RESOLUTION, FORCE_MAJEURE
- PAYMENT, INTELLECTUAL_PROPERTY, WARRANTIES, REPRESENTATIONS
- NOTICES, TERM_AND_TERMINATION, OTHER

### Usage

```python
from graph_builder.parsing import DocxParser
from graph_builder.clauses import PatternClauseExtractor

parser = DocxParser()
doc = parser.parse(Path("contract.docx"))

extractor = PatternClauseExtractor()
clauses = extractor.extract(doc)

for clause in clauses:
    print(f"{clause.location.section_number}: {clause.type.value}")
```

### Configuration

- `min_clause_length`: Minimum characters for a valid clause (default: 50)

### Fallback Behavior

If the document lacks paragraph metadata (not parsed by DocxParser), the extractor falls back to plain text extraction using regex-based section detection.

## LLMClauseExtractor

LLM-based clause extractor that uses OpenAI's API with instructor for structured output.

### Usage

```python
from graph_builder.parsing import DocxParser
from graph_builder.clauses import LLMClauseExtractor

parser = DocxParser()
doc = parser.parse(Path("contract.docx"))

extractor = LLMClauseExtractor(api_key="sk-...", model="gpt-4o-mini")
clauses = extractor.extract(doc)

for clause in clauses:
    print(f"{clause.type.value}: {clause.location.section_title}")
    print(f"Confidence: {clause.confidence}")
```

### Features

- Uses instructor for structured output
- Lazy-loads OpenAI client to avoid import errors
- Automatically finds clause locations in parsed documents
- Supports bilingual content (English/Chinese)
- Higher accuracy than pattern-based extraction
- Requires `llm` extra: `uv sync --extra llm`

## ClauseChunker

Base adapter that wraps a `ClauseExtractor` and implements the `Chunker` protocol from the pipeline. Each extracted clause becomes a `Chunk`, preserving clause metadata (type, section number, section title, confidence) in chunk metadata.

## DoclingClauseChunker

Subclass of `ClauseChunker` designed for Docling-parsed documents. This is the default chunker used by `PipelineBuilder.entity_graph()` and `PipelineBuilder.entity_graph_with_llm()`. Expects Documents parsed by `DoclingParser` (with paragraph metadata).

### Usage

```python
from graph_builder.clauses import DoclingClauseChunker

# Default (uses PatternClauseExtractor)
chunker = DoclingClauseChunker()

# With LLM clause extractor
from graph_builder.clauses import LLMClauseExtractor
chunker = DoclingClauseChunker(clause_extractor=LLMClauseExtractor(api_key="sk-..."))

# Use in entity graph pipeline
chunks = chunker.chunk(documents)  # documents should be parsed by DoclingParser
```

## TextinClauseChunker

Chunker that uses Textin's catalog tree (from `TextinParser`) to detect clause boundaries. Uses the `hierarchy` levels from the TOC to build a tree. More reliable than regex-based section detection since it uses Textin's built-in heading analysis.

- Expects documents parsed by `TextinParser` (with `textin_catalog` metadata)
- Builds catalog tree via parent-stack algorithm (`build_catalog_tree()`)
- `clause_level` parameter: level 2 (default) for articles, level 1 for top-level sections
- Classifies clause types using keyword matching by default, or LLM batch classification when `api_key` is provided
- LLM classification: single API call per document via instructor + OpenAI, returns `ClauseClassifications` with per-clause confidence scores
- Falls back to keyword matching (`CLAUSE_TYPE_KEYWORDS`) when no `api_key` or when a title is missing from LLM response
- Fuzzy title matching via `difflib.SequenceMatcher` (threshold 0.7)
- `include_preamble` parameter (default `True`): extracts text before first clause (preamble) and after last clause (postamble) as additional chunks with `chunk_type: "PREAMBLE"/"POSTAMBLE"` metadata (no `clause_type`, so they flow through entity extraction but are skipped by clause-specific logic)
- Stores catalog tree structure in chunk metadata for downstream use
- Selected automatically when `GRAPH_BUILDER_DOCUMENT_PARSER=textin`
- `PipelineBuilder.entity_graph_with_llm()` passes `api_key` and `model` to enable LLM classification

## TextinClauseExtractor

Adapter that wraps `TextinClauseChunker` and implements the `ClauseExtractor` protocol. Converts `Chunk` objects to `Clause` objects, enabling use with `ClauseEvaluator` and the clause evaluation script.

- Used by `scripts/run_clause_evaluation.py --pdf-parser textin`
- Derives `paragraph_index` from `start_char` against paragraph metadata
- Skips preamble/postamble chunks (those without `clause_type` in metadata)

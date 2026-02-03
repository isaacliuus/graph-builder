# Clauses Module

Clause extraction from legal contracts and documents.

## Files

- `base.py` - `ClauseExtractor` Protocol defining the extractor interface
- `pattern_extractor.py` - Rule-based clause extraction using keyword matching

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

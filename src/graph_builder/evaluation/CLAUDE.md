# Evaluation Module

Evaluation tools for measuring extraction quality against ground truth datasets.

## Files

- `metrics.py` - Precision, recall, and F1 score calculation functions
- `dataset.py` - Ground truth data models and JSON loader
- `evaluator.py` - Main Evaluator class that compares extraction results to ground truth

## Usage

```python
from graph_builder.evaluation import Evaluator, load_dataset
from graph_builder.extraction import SpacyEntityExtractor, SpacyRelationshipExtractor

# Load ground truth
dataset = load_dataset("data/ground_truth/sample.json")

# Create extractors
entity_ext = SpacyEntityExtractor()
rel_ext = SpacyRelationshipExtractor()

# Run evaluation
evaluator = Evaluator(entity_ext, rel_ext)
result = evaluator.evaluate(dataset)

print(f"Entity F1: {result.entity_f1}")
print(f"Relationship F1: {result.relationship_f1}")
```

## Ground Truth Format

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

## Matching Logic

- **Entity match**: canonical_name (lowercase, stripped) AND type must match
- **Relationship match**: source name, target name, AND type must all match
- Entity types are normalized (e.g., "ORGANIZATION" -> "ORG", "LOCATION" -> "LOC")

## Standalone Script

```bash
# Run with spaCy (default)
uv run python scripts/run_evaluation.py data/ground_truth/sample.json

# Run with LLM extractor
uv run python scripts/run_evaluation.py data/ground_truth/sample.json --extractor llm

# Save results to file
uv run python scripts/run_evaluation.py data/ground_truth/sample.json --output results.json
```

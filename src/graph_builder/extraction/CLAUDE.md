# Extraction Module

Entity and relationship extraction implementations.

## Files

- `base.py` - EntityExtractorBase and RelationshipExtractorBase abstract classes
- `spacy_extractor.py` - SpaCy-based NER and co-occurrence relationship extraction
- `llm_extractor.py` - LLM-based extraction using OpenAI + instructor (optional dependency)

## Conventions

- Extractors implement protocols from `pipeline.base`
- SpaCy extractors use the `en_core_web_sm` model
- LLM extractors lazy-load the client to avoid import errors when deps missing
- SpaCy relationship extraction uses co-occurrence (entities in same chunk are related)

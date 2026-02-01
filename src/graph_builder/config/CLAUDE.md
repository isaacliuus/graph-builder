# Config Module

Configuration management using pydantic-settings.

## Files

- `settings.py` - Settings class with environment variable support

## Environment Variables

- `GRAPH_BUILDER_USE_LLM` - Enable LLM-based extraction (default: false)
- `GRAPH_BUILDER_OPENAI_API_KEY` - OpenAI API key for LLM extraction
- `GRAPH_BUILDER_LLM_MODEL` - LLM model to use (default: gpt-4o-mini)
- `GRAPH_BUILDER_SPACY_MODEL` - spaCy model to use (default: en_core_web_sm)

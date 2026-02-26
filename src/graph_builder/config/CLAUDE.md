# Config Module

Configuration management using pydantic-settings.

## Files

- `settings.py` - Settings class with environment variable support

## Environment Variables

- `GRAPH_BUILDER_USE_LLM` - Enable LLM-based extraction (default: false)
- `GRAPH_BUILDER_OPENAI_API_KEY` - OpenAI API key for LLM extraction
- `GRAPH_BUILDER_LLM_MODEL` - LLM model to use (default: gpt-4o-mini)
- `GRAPH_BUILDER_SPACY_MODEL` - spaCy model to use (default: en_core_web_sm)
- `GRAPH_BUILDER_MEMGRAPH_HOST` - Memgraph server hostname (default: localhost)
- `GRAPH_BUILDER_MEMGRAPH_PORT` - Memgraph Bolt port (default: 7687)
- `GRAPH_BUILDER_MEMGRAPH_USERNAME` - Memgraph username (default: empty)
- `GRAPH_BUILDER_MEMGRAPH_PASSWORD` - Memgraph password (default: empty)
- `GRAPH_BUILDER_MEMGRAPH_DATABASE` - Memgraph database name (default: memgraph)
- `GRAPH_BUILDER_MEMGRAPH_ENCRYPTED` - Use encrypted connection (default: false)
- `GRAPH_BUILDER_USE_GRAPHDB` - Enable graph database persistence (default: false)
- `GRAPH_BUILDER_TEXTIN_APP_ID` - Textin xParse API app ID (default: empty)
- `GRAPH_BUILDER_TEXTIN_SECRET_CODE` - Textin xParse API secret code (default: empty)
- `GRAPH_BUILDER_DOCUMENT_PARSER` - Document parser to use: "docling" or "textin" (default: docling)

# CLAUDE.md

Project guidance for Claude Code. 

* See @README.md for project overview
* See @.claude/rules/python.mdc for common coding conventions

## Project Rules

### Code Style

- Python 3.11+ with type hints
- Pydantic models for all data structures
- Use `typing.Protocol` for interfaces (duck typing)
- UUIDs for all entity/relationship IDs

### Module Documentation

Each module has its own CLAUDE.md with specific conventions:

- `src/graph_builder/models/CLAUDE.md` - Data model conventions
- `src/graph_builder/pipeline/CLAUDE.md` - Pipeline architecture
- `src/graph_builder/chunking/CLAUDE.md` - Chunking implementation
- `src/graph_builder/extraction/CLAUDE.md` - Extraction strategies
- `src/graph_builder/graph/CLAUDE.md` - Graph building rules
- `src/graph_builder/evaluation/CLAUDE.md` - Evaluation metrics and datasets
- `src/graph_builder/config/CLAUDE.md` - Configuration settings

### Testing

- Tests live in `tests/` directory
- Use pytest with pytest-mock
- Skip tests for optional dependencies with `@pytest.mark.skipif`
- Integration tests use real spaCy model

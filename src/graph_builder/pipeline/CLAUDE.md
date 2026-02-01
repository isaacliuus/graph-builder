# Pipeline Module

Pipeline orchestration for the knowledge graph builder.

## Files

- `base.py` - Protocols (Chunker, EntityExtractor, RelationshipExtractor, GraphBuilder) and PipelineContext dataclass
- `pipeline.py` - Pipeline class that chains the 4 stages together
- `builder.py` - Fluent PipelineBuilder API with `.default()` and `.with_llm()` factory methods

## Conventions

- Use `typing.Protocol` for stage interfaces (duck typing)
- PipelineContext is a dataclass that flows through all stages
- Pipeline.run() returns just the graph; Pipeline.run_with_context() returns full context

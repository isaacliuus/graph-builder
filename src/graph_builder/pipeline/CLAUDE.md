# Pipeline Module

Pipeline orchestration for the knowledge graph builder.

## Files

- `base.py` - Protocols (Chunker, EntityExtractor, EntityMerger, RelationshipExtractor, GraphBuilder, GraphDB) and PipelineContext dataclass
- `pipeline.py` - Pipeline class that chains the 5 stages together (chunking, entity extraction, relationship extraction, graph building, persistence)
- `entity_graph_pipeline.py` - EntityGraphPipeline variant: chunk → extract entities → fuzzy merge → co-occurrence relationships → build graph. Supports `run_from_files()` for parsing contract files directly.
- `builder.py` - Fluent PipelineBuilder API with `.default()`, `.with_llm()`, `.entity_graph()`, and `.entity_graph_with_llm()` factory methods

## Conventions

- Use `typing.Protocol` for stage interfaces (duck typing)
- PipelineContext is a dataclass that flows through all stages
- Pipeline.run() returns just the graph; Pipeline.run_with_context() returns full context
- Optional graphdb parameter enables automatic persistence after graph building
- Use `.with_graphdb(db)` on PipelineBuilder to configure database persistence
- Use `.with_parser(parser)` on PipelineBuilder to enable `run_from_files()`
- `.entity_graph()` and `.entity_graph_with_llm()` use ClauseChunker + DoclingParser by default

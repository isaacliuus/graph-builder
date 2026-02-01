# Graph Module

Graph building implementations.

## Files

- `base.py` - GraphBuilderBase abstract class
- `networkx_builder.py` - NetworkXGraphBuilder that creates KnowledgeGraph and converts to/from NetworkX

## Conventions

- Graph builders implement the `GraphBuilder` protocol from `pipeline.base`
- Deduplication is enabled by default (entities with same canonical_name are merged)
- Relationships are remapped to deduplicated entity IDs
- Invalid relationships (missing source/target) are silently dropped

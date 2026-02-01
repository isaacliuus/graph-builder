# GraphDB Module

Graph database persistence layer for storing and retrieving knowledge graphs.

## Files

- `base.py` - GraphDBBase ABC defining the interface for all graph database implementations
- `memgraph.py` - MemgraphGraphDB implementation using Bolt protocol (neo4j driver)

## Conventions

- All implementations extend `GraphDBBase` ABC
- Use context manager pattern for connection handling (`with db:`)
- Lazy-load database drivers to avoid import errors when deps missing
- Use MERGE (Cypher) for idempotent create/update operations
- Use UNWIND for batch operations
- Nodes labeled `:Entity` with properties: id, name, canonical_name, type, confidence, metadata
- Relationships use dynamic types matching RelationshipType enum values

## Optional Dependency

Memgraph support requires the neo4j driver:

```bash
uv sync --extra memgraph
```

## Usage

```python
from graph_builder.graphdb.memgraph import MemgraphGraphDB

# Using context manager (recommended)
with MemgraphGraphDB(host="localhost", port=7687) as db:
    db.sync(graph)
    loaded = db.load_graph()

# Manual connection management
db = MemgraphGraphDB(host="localhost")
db.connect()
try:
    db.create_node(node)
finally:
    db.close()
```

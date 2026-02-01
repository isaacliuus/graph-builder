# Models Module

Pydantic data models for the knowledge graph pipeline.

## Files

- `document.py` - Document and Chunk models for input text
- `entity.py` - Entity model with EntityType enum for extracted entities
- `relationship.py` - Relationship model with RelationshipType enum
- `graph.py` - KnowledgeGraph, GraphNode, and GraphEdge models

## Conventions

- All models inherit from `pydantic.BaseModel`
- Use UUID for all entity/relationship IDs (auto-generated via `uuid4`)
- Entity canonical names are lowercase/stripped for deduplication
- Confidence scores are floats between 0.0 and 1.0

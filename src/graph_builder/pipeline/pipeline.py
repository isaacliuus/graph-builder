"""Pipeline orchestrator for knowledge graph building."""

from graph_builder.models.document import Document
from graph_builder.models.graph import KnowledgeGraph
from graph_builder.pipeline.base import (
    PipelineContext,
    Chunker,
    EntityExtractor,
    RelationshipExtractor,
    GraphBuilder,
    GraphDB,
)


class Pipeline:
    """Orchestrates the knowledge graph building pipeline."""

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        chunker: Chunker,
        entity_extractor: EntityExtractor,
        relationship_extractor: RelationshipExtractor,
        graph_builder: GraphBuilder,
        graphdb: GraphDB | None = None,
    ):
        self.chunker = chunker
        self.entity_extractor = entity_extractor
        self.relationship_extractor = relationship_extractor
        self.graph_builder = graph_builder
        self.graphdb = graphdb

    def run(self, documents: list[Document]) -> KnowledgeGraph:
        """Run the full pipeline on the given documents."""
        context = PipelineContext(documents=documents)

        # Stage 1: Chunking
        context.chunks = self.chunker.chunk(context.documents)

        # Stage 2: Entity extraction
        context.entities = self.entity_extractor.extract(context.chunks)

        # Stage 3: Relationship extraction
        context.relationships = self.relationship_extractor.extract(
            context.chunks, context.entities
        )

        # Stage 4: Graph building
        context.graph = self.graph_builder.build(
            context.entities, context.relationships
        )

        # Stage 5: Persist to graph database (optional)
        if self.graphdb is not None:
            self.graphdb.sync(context.graph)

        return context.graph

    def run_with_context(self, documents: list[Document]) -> PipelineContext:
        """Run the pipeline and return the full context."""
        context = PipelineContext(documents=documents)

        context.chunks = self.chunker.chunk(context.documents)
        context.entities = self.entity_extractor.extract(context.chunks)
        context.relationships = self.relationship_extractor.extract(
            context.chunks, context.entities
        )
        context.graph = self.graph_builder.build(
            context.entities, context.relationships
        )

        # Persist to graph database (optional)
        if self.graphdb is not None:
            self.graphdb.sync(context.graph)

        return context

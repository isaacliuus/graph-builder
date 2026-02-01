"""Fluent builder API for constructing pipelines."""

from graph_builder.pipeline.base import (
    Chunker,
    EntityExtractor,
    RelationshipExtractor,
    GraphBuilder,
    GraphDB,
)
from graph_builder.pipeline.pipeline import Pipeline


class PipelineBuilder:
    """Fluent builder for constructing pipelines."""

    def __init__(self):
        self._chunker: Chunker | None = None
        self._entity_extractor: EntityExtractor | None = None
        self._relationship_extractor: RelationshipExtractor | None = None
        self._graph_builder: GraphBuilder | None = None
        self._graphdb: GraphDB | None = None

    def with_chunker(self, chunker: Chunker) -> "PipelineBuilder":
        """Set the chunker for the pipeline."""
        self._chunker = chunker
        return self

    def with_entity_extractor(self, extractor: EntityExtractor) -> "PipelineBuilder":
        """Set the entity extractor for the pipeline."""
        self._entity_extractor = extractor
        return self

    def with_relationship_extractor(
        self, extractor: RelationshipExtractor
    ) -> "PipelineBuilder":
        """Set the relationship extractor for the pipeline."""
        self._relationship_extractor = extractor
        return self

    def with_graph_builder(self, builder: GraphBuilder) -> "PipelineBuilder":
        """Set the graph builder for the pipeline."""
        self._graph_builder = builder
        return self

    def with_graphdb(self, graphdb: GraphDB) -> "PipelineBuilder":
        """Set the graph database for persisting the built graph."""
        self._graphdb = graphdb
        return self

    def build(self) -> Pipeline:
        """Build the pipeline with the configured components."""
        if self._chunker is None:
            raise ValueError("Chunker is required")
        if self._entity_extractor is None:
            raise ValueError("Entity extractor is required")
        if self._relationship_extractor is None:
            raise ValueError("Relationship extractor is required")
        if self._graph_builder is None:
            raise ValueError("Graph builder is required")

        return Pipeline(
            chunker=self._chunker,
            entity_extractor=self._entity_extractor,
            relationship_extractor=self._relationship_extractor,
            graph_builder=self._graph_builder,
            graphdb=self._graphdb,
        )

    @classmethod
    def default(cls) -> Pipeline:
        """Create a default pipeline with spaCy-based extraction."""
        from graph_builder.chunking.recursive import RecursiveChunker
        from graph_builder.extraction.spacy_extractor import (
            SpacyEntityExtractor,
            SpacyRelationshipExtractor,
        )
        from graph_builder.graph.networkx_builder import NetworkXGraphBuilder

        return (
            cls()
            .with_chunker(RecursiveChunker())
            .with_entity_extractor(SpacyEntityExtractor())
            .with_relationship_extractor(SpacyRelationshipExtractor())
            .with_graph_builder(NetworkXGraphBuilder())
            .build()
        )

    @classmethod
    def with_llm(cls, api_key: str, model: str = "gpt-4o-mini") -> Pipeline:
        """Create a pipeline with LLM-based extraction."""
        from graph_builder.chunking.recursive import RecursiveChunker
        from graph_builder.extraction.llm_extractor import (
            LLMEntityExtractor,
            LLMRelationshipExtractor,
        )
        from graph_builder.graph.networkx_builder import NetworkXGraphBuilder

        return (
            cls()
            .with_chunker(RecursiveChunker())
            .with_entity_extractor(LLMEntityExtractor(api_key=api_key, model=model))
            .with_relationship_extractor(
                LLMRelationshipExtractor(api_key=api_key, model=model)
            )
            .with_graph_builder(NetworkXGraphBuilder())
            .build()
        )

"""Fluent builder API for constructing pipelines."""

from graph_builder.parsing.base import DocumentParser
from graph_builder.pipeline.base import (
    Chunker,
    EntityExtractor,
    EntityMerger,
    RelationshipExtractor,
    GraphBuilder,
    GraphDB,
)
from graph_builder.pipeline.entity_graph_pipeline import EntityGraphPipeline
from graph_builder.pipeline.pipeline import Pipeline


class PipelineBuilder:
    """Fluent builder for constructing pipelines."""

    def __init__(self):
        self._chunker: Chunker | None = None
        self._entity_extractor: EntityExtractor | None = None
        self._entity_merger: EntityMerger | None = None
        self._relationship_extractor: RelationshipExtractor | None = None
        self._graph_builder: GraphBuilder | None = None
        self._graphdb: GraphDB | None = None
        self._parser: DocumentParser | None = None

    def with_chunker(self, chunker: Chunker) -> "PipelineBuilder":
        """Set the chunker for the pipeline."""
        self._chunker = chunker
        return self

    def with_entity_extractor(self, extractor: EntityExtractor) -> "PipelineBuilder":
        """Set the entity extractor for the pipeline."""
        self._entity_extractor = extractor
        return self

    def with_entity_merger(self, merger: EntityMerger) -> "PipelineBuilder":
        """Set the entity merger for the pipeline."""
        self._entity_merger = merger
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

    def with_parser(self, parser: DocumentParser) -> "PipelineBuilder":
        """Set the document parser for file-based pipeline runs."""
        self._parser = parser
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

    def build_entity_graph(self) -> EntityGraphPipeline:
        """Build an entity graph pipeline with fuzzy merging."""
        if self._chunker is None:
            raise ValueError("Chunker is required")
        if self._entity_extractor is None:
            raise ValueError("Entity extractor is required")
        if self._entity_merger is None:
            raise ValueError("Entity merger is required")
        if self._graph_builder is None:
            raise ValueError("Graph builder is required")

        return EntityGraphPipeline(
            chunker=self._chunker,
            entity_extractor=self._entity_extractor,
            entity_merger=self._entity_merger,
            graph_builder=self._graph_builder,
            graphdb=self._graphdb,
            parser=self._parser,
        )

    @classmethod
    def default(cls) -> Pipeline:
        """Create a default pipeline with spaCy-based extraction.

        If GRAPH_BUILDER_USE_GRAPHDB is enabled, automatically connects to
        the configured Memgraph database for persistence.
        """
        from graph_builder.chunking.recursive import RecursiveChunker
        from graph_builder.extraction.spacy_extractor import (
            SpacyEntityExtractor,
            SpacyRelationshipExtractor,
        )
        from graph_builder.graph.networkx_builder import NetworkXGraphBuilder
        from graph_builder.graphdb.factory import create_graphdb_from_settings

        builder = (
            cls()
            .with_chunker(RecursiveChunker())
            .with_entity_extractor(SpacyEntityExtractor())
            .with_relationship_extractor(SpacyRelationshipExtractor())
            .with_graph_builder(NetworkXGraphBuilder())
        )

        graphdb = create_graphdb_from_settings()
        if graphdb is not None:
            builder = builder.with_graphdb(graphdb)

        return builder.build()

    @classmethod
    def entity_graph(cls, threshold: float = 85.0) -> EntityGraphPipeline:
        """Create an entity graph pipeline with clause chunking, spaCy extraction,
        and fuzzy merging. Uses DoclingParser or TextinParser based on settings.

        If GRAPH_BUILDER_USE_GRAPHDB is enabled, automatically connects to
        the configured Memgraph database for persistence.
        """
        from graph_builder.config.settings import get_settings
        from graph_builder.extraction.spacy_extractor import SpacyEntityExtractor
        from graph_builder.graph.networkx_builder import NetworkXGraphBuilder
        from graph_builder.graphdb.factory import create_graphdb_from_settings
        from graph_builder.merging.fuzzy_merger import FuzzyEntityMerger

        settings = get_settings()

        if settings.document_parser == "textin":
            from graph_builder.clauses.textin_chunker import TextinClauseChunker
            from graph_builder.parsing.textin_parser import TextinParser

            chunker = TextinClauseChunker()
            parser = TextinParser()
        else:
            from graph_builder.clauses.clause_chunker import DoclingClauseChunker
            from graph_builder.parsing.docling_parser import DoclingParser

            chunker = DoclingClauseChunker()
            parser = DoclingParser()

        builder = (
            cls()
            .with_chunker(chunker)
            .with_entity_extractor(SpacyEntityExtractor())
            .with_entity_merger(FuzzyEntityMerger(threshold=threshold))
            .with_graph_builder(NetworkXGraphBuilder(deduplicate=False))
            .with_parser(parser)
        )

        graphdb = create_graphdb_from_settings()
        if graphdb is not None:
            builder = builder.with_graphdb(graphdb)

        return builder.build_entity_graph()

    @classmethod
    def entity_graph_with_llm(
        cls, api_key: str, model: str = "gpt-4o-mini", threshold: float = 85.0
    ) -> EntityGraphPipeline:
        """Create an entity graph pipeline with LLM clause extraction, LLM entity
        extraction, and fuzzy merging. Uses DoclingParser or TextinParser based on settings.

        If GRAPH_BUILDER_USE_GRAPHDB is enabled, automatically connects to
        the configured Memgraph database for persistence.
        """
        from graph_builder.config.settings import get_settings
        from graph_builder.clauses.llm_extractor import LLMClauseExtractor
        from graph_builder.extraction.llm_extractor import LLMEntityExtractor
        from graph_builder.graph.networkx_builder import NetworkXGraphBuilder
        from graph_builder.graphdb.factory import create_graphdb_from_settings
        from graph_builder.merging.fuzzy_merger import FuzzyEntityMerger

        settings = get_settings()

        if settings.document_parser == "textin":
            from graph_builder.clauses.textin_chunker import TextinClauseChunker
            from graph_builder.parsing.textin_parser import TextinParser

            chunker = TextinClauseChunker(api_key=api_key, model=model)
            parser = TextinParser()
        else:
            from graph_builder.clauses.clause_chunker import DoclingClauseChunker
            from graph_builder.parsing.docling_parser import DoclingParser

            chunker = DoclingClauseChunker(
                clause_extractor=LLMClauseExtractor(api_key=api_key, model=model)
            )
            parser = DoclingParser()

        builder = (
            cls()
            .with_chunker(chunker)
            .with_entity_extractor(LLMEntityExtractor(api_key=api_key, model=model))
            .with_entity_merger(FuzzyEntityMerger(threshold=threshold))
            .with_graph_builder(NetworkXGraphBuilder(deduplicate=False))
            .with_parser(parser)
        )

        graphdb = create_graphdb_from_settings()
        if graphdb is not None:
            builder = builder.with_graphdb(graphdb)

        return builder.build_entity_graph()

    @classmethod
    def with_llm(cls, api_key: str, model: str = "gpt-4o-mini") -> Pipeline:
        """Create a pipeline with LLM-based extraction.

        If GRAPH_BUILDER_USE_GRAPHDB is enabled, automatically connects to
        the configured Memgraph database for persistence.
        """
        from graph_builder.chunking.recursive import RecursiveChunker
        from graph_builder.extraction.llm_extractor import (
            LLMEntityExtractor,
            LLMRelationshipExtractor,
        )
        from graph_builder.graph.networkx_builder import NetworkXGraphBuilder
        from graph_builder.graphdb.factory import create_graphdb_from_settings

        builder = (
            cls()
            .with_chunker(RecursiveChunker())
            .with_entity_extractor(LLMEntityExtractor(api_key=api_key, model=model))
            .with_relationship_extractor(
                LLMRelationshipExtractor(api_key=api_key, model=model)
            )
            .with_graph_builder(NetworkXGraphBuilder())
        )

        graphdb = create_graphdb_from_settings()
        if graphdb is not None:
            builder = builder.with_graphdb(graphdb)

        return builder.build()

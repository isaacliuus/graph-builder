"""Entity graph pipeline with fuzzy merging and co-occurrence relationships."""

from collections import Counter
from pathlib import Path

from graph_builder.merging.cooccurrence import create_cooccurrence_relationships
from graph_builder.models.document import Document
from graph_builder.models.graph import KnowledgeGraph
from graph_builder.parsing.base import DocumentParser
from graph_builder.pipeline.base import (
    PipelineContext,
    Chunker,
    EntityExtractor,
    EntityMerger,
    GraphBuilder,
    GraphDB,
)


class EntityGraphPipeline:
    """Pipeline that builds graphs via entity extraction, fuzzy merging,
    and co-occurrence relationships.

    Stages:
    1. Chunk documents (optionally using clause extraction)
    2. Extract entities
    3. Fuzzy merge similar entities
    4. Generate co-occurrence relationships from chunk provenance
    5. Build graph (with deduplicate=False since merging is already done)
    6. Optional persistence to graph database
    """

    def __init__(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        chunker: Chunker,
        entity_extractor: EntityExtractor,
        entity_merger: EntityMerger,
        graph_builder: GraphBuilder,
        graphdb: GraphDB | None = None,
        parser: DocumentParser | None = None,
    ):
        self.chunker = chunker
        self.entity_extractor = entity_extractor
        self.entity_merger = entity_merger
        self.graph_builder = graph_builder
        self.graphdb = graphdb
        self.parser = parser

    def run(self, documents: list[Document]) -> KnowledgeGraph:
        """Run the full pipeline on the given documents."""
        context = self.run_with_context(documents)
        return context.graph

    def run_from_files(self, file_paths: list[Path]) -> KnowledgeGraph:
        """Parse files and run the full pipeline."""
        context = self.run_from_files_with_context(file_paths)
        return context.graph

    def run_from_files_with_context(
        self, file_paths: list[Path]
    ) -> PipelineContext:
        """Parse files, run the pipeline, and return the full context."""
        if self.parser is None:
            raise ValueError(
                "No parser configured. Use with_parser() on PipelineBuilder "
                "or pass a parser to EntityGraphPipeline."
            )

        documents = [self.parser.parse(path) for path in file_paths]
        return self.run_with_context(documents)

    def run_with_context(self, documents: list[Document]) -> PipelineContext:
        """Run the pipeline and return the full context."""
        context = PipelineContext(documents=documents)

        # Stage 1: Chunking
        context.chunks = self.chunker.chunk(context.documents)

        # Stage 2: Entity extraction
        raw_entities = self.entity_extractor.extract(context.chunks)

        # Stage 3: Fuzzy merge
        merged_entities, id_mapping = self.entity_merger.merge(raw_entities)
        context.entities = merged_entities

        # Stage 4: Co-occurrence relationships
        # Remap raw entity IDs to primary IDs so co-occurrence uses merged identities
        # while retaining original chunk_id for provenance
        remapped_entities = [
            e.model_copy(update={"id": id_mapping[e.id]})
            for e in raw_entities
        ]
        context.relationships = create_cooccurrence_relationships(remapped_entities)

        # Stage 5: Graph building
        context.graph = self.graph_builder.build(
            context.entities, context.relationships
        )

        # Store merge stats in metadata
        context.metadata["merge_stats"] = {
            "raw_entity_count": len(raw_entities),
            "merged_entity_count": len(merged_entities),
            "entities_reduced": len(raw_entities) - len(merged_entities),
            "relationship_count": len(context.relationships),
        }

        # Store clause stats if chunks have clause metadata
        clause_types = [
            c.metadata["clause_type"]
            for c in context.chunks
            if "clause_type" in c.metadata
        ]
        if clause_types:
            context.metadata["clause_stats"] = {
                "clause_count": len(clause_types),
                "clause_types": dict(Counter(clause_types)),
            }

        # Stage 6: Persist to graph database (optional)
        if self.graphdb is not None:
            self.graphdb.sync(context.graph)

        return context

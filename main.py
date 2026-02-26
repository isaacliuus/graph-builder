"""Knowledge Graph Builder CLI."""

import sys
from pathlib import Path

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from graph_builder.models.document import Document
from graph_builder.pipeline.builder import PipelineBuilder
from graph_builder.config.settings import get_settings


console = Console()

CONTRACT_EXTENSIONS = {".pdf", ".docx"}


def print_graph_summary(graph, entities, relationships):
    """Print a summary of the extracted graph."""
    console.print()
    console.print(
        Panel.fit(
            f"[bold green]Knowledge Graph Built Successfully[/bold green]\n\n"
            f"Nodes: {graph.node_count}\n"
            f"Edges: {graph.edge_count}",
            title="Summary",
        )
    )

    if graph.node_count > 0:
        console.print()
        entity_table = Table(title="Entities")
        entity_table.add_column("Name", style="cyan")
        entity_table.add_column("Type", style="magenta")
        entity_table.add_column("Confidence", style="green")

        for node in graph.nodes.values():
            entity_table.add_row(
                node.name, node.type.value, f"{node.confidence:.2f}"
            )

        console.print(entity_table)

    if graph.edge_count > 0:
        console.print()
        rel_table = Table(title="Relationships")
        rel_table.add_column("Source", style="cyan")
        rel_table.add_column("Relationship", style="yellow")
        rel_table.add_column("Target", style="cyan")

        for edge in graph.edges:
            source_node = graph.nodes.get(edge.source_id)
            target_node = graph.nodes.get(edge.target_id)
            if source_node and target_node:
                rel_table.add_row(
                    source_node.name, edge.type.value, target_node.name
                )

        console.print(rel_table)


def print_merge_stats(metadata):
    """Print merge statistics from the entity graph pipeline."""
    stats = metadata.get("merge_stats")
    if stats:
        console.print()
        console.print(
            Panel.fit(
                f"[bold yellow]Entity Merging[/bold yellow]\n\n"
                f"Raw entities: {stats['raw_entity_count']}\n"
                f"After merging: {stats['merged_entity_count']}\n"
                f"Entities reduced: {stats['entities_reduced']}\n"
                f"Co-occurrence relationships: {stats['relationship_count']}",
                title="Merge Stats",
            )
        )


def print_clause_stats(metadata):
    """Print clause extraction statistics."""
    stats = metadata.get("clause_stats")
    if stats:
        console.print()
        type_lines = "\n".join(
            f"  {ctype}: {count}" for ctype, count in stats["clause_types"].items()
        )
        console.print(
            Panel.fit(
                f"[bold cyan]Clause Extraction[/bold cyan]\n\n"
                f"Total clauses: {stats['clause_count']}\n"
                f"Clause types:\n{type_lines}",
                title="Clause Stats",
            )
        )


def _is_contract_file(path: Path) -> bool:
    return path.suffix.lower() in CONTRACT_EXTENSIONS


def main():
    """Main entry point for the CLI."""
    settings = get_settings()

    # Parse arguments
    use_entity_graph = "--entity-graph" in sys.argv
    file_args = [a for a in sys.argv[1:] if not a.startswith("--")]

    # Check for input file argument
    if not file_args:
        console.print("[yellow]Usage: python main.py [--entity-graph] <file>[/yellow]")
        console.print()
        console.print("Running with sample text...")
        console.print()

        # Sample text for demonstration
        sample_text = """
        Apple Inc. was founded by Steve Jobs, Steve Wozniak, and Ronald Wayne in Cupertino, California.
        The company is headquartered in Cupertino and is known for products like the iPhone and MacBook.
        Tim Cook became the CEO of Apple in 2011 after Steve Jobs resigned due to health issues.
        Apple acquired Beats Electronics in 2014 for $3 billion.
        """
        sample_text_2 = """
        Microsoft is a global technology giant founded in 1975 by Bill Gates and Paul Allen, renowned for its Windows operating systems, Office productivity suite, Azure cloud platform, and diverse innovations across software, hardware, and AI that shape personal computing, enterprise technology, and digital transformation worldwide.
        """
        sample_text_3 = """
        Elon Musk is the CEO of Tesla and SpaceX. Tesla is headquartered in Austin, Texas.
        """
        documents = [
            Document(content=sample_text, source="sample"),
            Document(content=sample_text_2, source="sample_2"),
            Document(content=sample_text_3, source="sample_3"),
        ]
        file_paths = None
    else:
        file_paths = [Path(a) for a in file_args]
        for fp in file_paths:
            if not fp.exists():
                console.print(f"[red]Error: File '{fp}' not found[/red]")
                sys.exit(1)

        # For non-entity-graph mode with text files, read content directly
        if not use_entity_graph or not all(_is_contract_file(fp) for fp in file_paths):
            content = "\n\n".join(fp.read_text() for fp in file_paths)
            documents = [Document(content=content, source=str(file_paths[0]))]
            file_paths = None
        else:
            documents = None

    console.print("[bold]Knowledge Graph Builder[/bold]")
    console.print()

    # Create pipeline based on settings
    if use_entity_graph:
        if settings.use_llm and settings.openai_api_key:
            console.print("[blue]Using entity graph pipeline with LLM extraction + fuzzy merging...[/blue]")
            pipeline = PipelineBuilder.entity_graph_with_llm(
                api_key=settings.openai_api_key, model=settings.llm_model
            )
        else:
            console.print("[blue]Using entity graph pipeline with spaCy extraction + fuzzy merging...[/blue]")
            pipeline = PipelineBuilder.entity_graph()

        # Use run_from_files for contract files, run for pre-loaded documents
        if file_paths is not None:
            parser_name = settings.document_parser.capitalize()
            console.print(f"[blue]Parsing {len(file_paths)} file(s) with {parser_name}...[/blue]")
            context = pipeline.run_from_files_with_context(file_paths)
        else:
            context = pipeline.run_with_context(documents)

        # Print results
        print_graph_summary(context.graph, context.entities, context.relationships)
        print_clause_stats(context.metadata)
        print_merge_stats(context.metadata)
    else:
        if settings.use_llm and settings.openai_api_key:
            console.print("[blue]Using LLM-based extraction...[/blue]")
            pipeline = PipelineBuilder.with_llm(
                api_key=settings.openai_api_key, model=settings.llm_model
            )
        else:
            console.print("[blue]Using spaCy-based extraction...[/blue]")
            pipeline = PipelineBuilder.default()

        context = pipeline.run_with_context(documents)
        print_graph_summary(context.graph, context.entities, context.relationships)


if __name__ == "__main__":
    main()

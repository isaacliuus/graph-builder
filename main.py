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


def main():
    """Main entry point for the CLI."""
    settings = get_settings()

    # Check for input file argument
    if len(sys.argv) < 2:
        console.print("[yellow]Usage: python main.py <text_file>[/yellow]")
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
    else:
        file_path = Path(sys.argv[1])
        if not file_path.exists():
            console.print(f"[red]Error: File '{file_path}' not found[/red]")
            sys.exit(1)

        content = file_path.read_text()
        documents = [Document(content=content, source=str(file_path))]

    console.print("[bold]Knowledge Graph Builder[/bold]")
    console.print()

    # Create pipeline based on settings
    if settings.use_llm and settings.openai_api_key:
        console.print("[blue]Using LLM-based extraction...[/blue]")
        pipeline = PipelineBuilder.with_llm(
            api_key=settings.openai_api_key, model=settings.llm_model
        )
    else:
        console.print("[blue]Using spaCy-based extraction...[/blue]")
        pipeline = PipelineBuilder.default()

    # Run the pipeline
    context = pipeline.run_with_context(documents)

    # Print results
    print_graph_summary(context.graph, context.entities, context.relationships)


if __name__ == "__main__":
    main()

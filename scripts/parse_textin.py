#!/usr/bin/env python
"""Parse a document using Textin xParse API and output structured results.

Usage:
    uv run python scripts/parse_textin.py data/test_contracts/simple2.pdf
    uv run python scripts/parse_textin.py contract.pdf -o results.json
    uv run python scripts/parse_textin.py contract.docx --format table
    uv run python scripts/parse_textin.py contract.pdf --format catalog
    uv run python scripts/parse_textin.py contract.pdf --format markdown
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path for direct script execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# pylint: disable=wrong-import-position
from graph_builder.parsing.textin_parser import TextinParser


def print_table(doc) -> None:
    """Print paragraphs in a table format."""
    paragraphs = doc.metadata.get("paragraphs", [])
    print(f"\n{'#':<5} {'H':<3} {'Style':<12} {'Section':<10} {'Chars':<14} {'Text'}")
    print("-" * 100)
    for p in paragraphs:
        h = "[H]" if p["is_heading"] else ""
        section = p.get("section_number") or ""
        chars = f"{p['start_char']}-{p['end_char']}"
        text = p["text"][:60]
        if len(p["text"]) > 60:
            text += "..."
        print(f"{p['index']:<5} {h:<3} {p['style']:<12} {section:<10} {chars:<14} {text}")


def print_catalog(doc) -> None:
    """Print catalog tree."""
    from graph_builder.clauses.textin_chunker import TextinClauseChunker

    toc = doc.metadata.get("textin_catalog", [])
    if not toc:
        print("No catalog entries found.")
        return

    tree = TextinClauseChunker.build_catalog_tree(toc)

    def _print_node(node, depth=0):
        indent = "  " * depth
        title = node.get("title", "")
        hierarchy = node.get("hierarchy", "?")
        print(f"{indent}{title}  (level={hierarchy})")
        for child in node.get("children", []):
            _print_node(child, depth + 1)

    print(f"\nCatalog ({len(toc)} entries):")
    print("-" * 60)
    for node in tree:
        _print_node(node)


def print_chunks(doc) -> None:
    """Print each catalog entry with its content (all levels)."""
    from graph_builder.clauses.textin_chunker import TextinClauseChunker

    toc = doc.metadata.get("textin_catalog", [])
    paragraphs = doc.metadata.get("paragraphs", [])
    content = doc.content

    if not toc:
        print("No catalog sections found.")
        return

    # For each TOC entry, extract content from its start to the next entry's start
    print(f"\n{len(toc)} sections:")
    for i, entry in enumerate(toc):
        title = entry.get("title", "")
        hierarchy = entry.get("hierarchy", "?")

        # Find start char for this entry
        start = _find_start(title, paragraphs, content)
        if start is None:
            continue

        # Find start char for next entry (or end of content)
        if i + 1 < len(toc):
            next_title = toc[i + 1].get("title", "")
            end = _find_start(next_title, paragraphs, content)
            if end is None:
                end = len(content)
        else:
            end = len(content)

        section_content = content[start:end].strip()

        # Classify type
        clause_type = TextinClauseChunker._classify_clause_type(title, section_content)

        indent = "  " * (hierarchy - 1)
        print(f"\n{'='*70}")
        print(f"{indent}[{i+1}] Level {hierarchy} | {title}")
        print(f"{indent}Type: {clause_type.value}  |  Chars: {start}-{end}  |  Length: {len(section_content)}")
        print("-" * 70)
        if len(section_content) > 500:
            print(section_content[:500])
            print("... [truncated]")
        else:
            print(section_content)


def _find_start(title: str, paragraphs: list[dict], content: str) -> int | None:
    """Find start char offset for a title."""
    for para in paragraphs:
        if title in para.get("text", ""):
            return para["start_char"]
    pos = content.find(title)
    return pos if pos >= 0 else None


def print_summary(doc) -> None:
    """Print a summary of the parsed document."""
    paragraphs = doc.metadata.get("paragraphs", [])
    toc = doc.metadata.get("textin_catalog", [])
    headings = [p for p in paragraphs if p["is_heading"]]

    print(f"\nSource:          {doc.source}")
    print(f"Content length:  {len(doc.content)} chars")
    print(f"Paragraphs:      {len(paragraphs)}")
    print(f"Headings:        {len(headings)}")
    print(f"Catalog entries: {len(toc)}")


def doc_to_dict(doc) -> dict:
    """Convert parsed document to a serializable dict."""
    return {
        "source": doc.source,
        "content": doc.content,
        "metadata": {
            "file_type": doc.metadata.get("file_type"),
            "file_name": doc.metadata.get("file_name"),
            "parser": doc.metadata.get("parser"),
            "paragraph_count": doc.metadata.get("paragraph_count"),
            "paragraphs": doc.metadata.get("paragraphs", []),
            "textin_catalog": doc.metadata.get("textin_catalog", []),
        },
    }


def main() -> None:
    """Parse a document using Textin xParse API."""
    parser = argparse.ArgumentParser(
        description="Parse a document using Textin xParse API."
    )
    parser.add_argument(
        "file",
        type=Path,
        help="Path to the document file",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output file path for JSON results",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["summary", "table", "catalog", "chunks", "markdown", "json"],
        default="summary",
        help="Output format (default: summary)",
    )
    parser.add_argument(
        "--app-id",
        help="Textin app ID (can also use GRAPH_BUILDER_TEXTIN_APP_ID env var)",
    )
    parser.add_argument(
        "--secret-code",
        help="Textin secret code (can also use GRAPH_BUILDER_TEXTIN_SECRET_CODE env var)",
    )

    args = parser.parse_args()

    if not args.file.exists():
        print(f"Error: File not found: {args.file}")
        sys.exit(1)

    # Initialize parser
    kwargs = {}
    if args.app_id:
        kwargs["app_id"] = args.app_id
    if args.secret_code:
        kwargs["secret_code"] = args.secret_code

    textin_parser = TextinParser(**kwargs)

    if not textin_parser.supports(args.file):
        print(f"Error: Unsupported file type: {args.file.suffix}")
        print(f"Supported: {', '.join(sorted(TextinParser.SUPPORTED_EXTENSIONS))}")
        sys.exit(1)

    # Parse
    print(f"Parsing: {args.file}")
    try:
        doc = textin_parser.parse(args.file)
    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Display
    if args.format == "summary":
        print_summary(doc)
        print_catalog(doc)
    elif args.format == "table":
        print_summary(doc)
        print_table(doc)
    elif args.format == "catalog":
        print_catalog(doc)
    elif args.format == "chunks":
        print_summary(doc)
        print_chunks(doc)
    elif args.format == "markdown":
        print(doc.content)
    elif args.format == "json":
        print(json.dumps(doc_to_dict(doc), indent=2, ensure_ascii=False))

    # Save to file if requested
    if args.output:
        output_data = doc_to_dict(doc)
        with args.output.open("w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()

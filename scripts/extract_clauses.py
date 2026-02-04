#!/usr/bin/env python
"""Script to extract clauses from a contract file (.docx or .pdf).

Usage:
    uv run python scripts/extract_clauses.py data/test_contracts/simple2.docx
    uv run python scripts/extract_clauses.py contract.pdf
    uv run python scripts/extract_clauses.py data/test_contracts/simple2.docx --output clauses.json
    uv run python scripts/extract_clauses.py data/test_contracts/simple2.docx --format table
    uv run python scripts/extract_clauses.py data/test_contracts/simple2.docx --extractor llm --api-key sk-...
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add src to path for direct script execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# pylint: disable=wrong-import-position
from graph_builder.parsing import DocxParser, PdfParser
from graph_builder.clauses import PatternClauseExtractor

SUPPORTED_EXTENSIONS = {".docx", ".pdf"}


def print_clauses_table(clauses: list) -> None:
    """Print clauses in a table format."""
    print(f"\n{'#':<3} {'Type':<25} {'Section':<10} {'Title':<40} {'Conf':<6}")
    print("-" * 90)
    for i, clause in enumerate(clauses, 1):
        title = clause.location.section_title or ""
        if len(title) > 38:
            title = title[:35] + "..."
        section = clause.location.section_number or "-"
        print(f"{i:<3} {clause.type.value:<25} {section:<10} {title:<40} {clause.confidence:.2f}")


def print_clauses_detailed(clauses: list) -> None:
    """Print clauses with full details."""
    for i, clause in enumerate(clauses, 1):
        print(f"\n{'='*60}")
        print(f"Clause {i}")
        print(f"{'='*60}")
        print(f"Type:       {clause.type.value}")
        print(f"Section:    {clause.location.section_number or 'N/A'}")
        print(f"Title:      {clause.location.section_title or 'N/A'}")
        print(f"Confidence: {clause.confidence:.2f}")
        print(f"Location:   paragraph {clause.location.paragraph_index}, "
              f"chars {clause.location.start_char}-{clause.location.end_char}")
        print(f"\nContent:")
        print("-" * 60)
        # Truncate long content
        content = clause.content
        if len(content) > 500:
            content = content[:500] + "\n... [truncated]"
        print(content)


def clauses_to_dict(clauses: list) -> list[dict]:
    """Convert clauses to serializable dictionaries."""
    return [
        {
            "id": str(clause.id),
            "type": clause.type.value,
            "confidence": clause.confidence,
            "location": {
                "paragraph_index": clause.location.paragraph_index,
                "section_number": clause.location.section_number,
                "section_title": clause.location.section_title,
                "start_char": clause.location.start_char,
                "end_char": clause.location.end_char,
            },
            "content": clause.content,
        }
        for clause in clauses
    ]


def get_parser_for_file(file_path: Path):
    """Get the appropriate parser based on file extension."""
    ext = file_path.suffix.lower()
    if ext == ".docx":
        return DocxParser()
    elif ext == ".pdf":
        return PdfParser()
    else:
        raise ValueError(
            f"Unsupported file type: {ext}. Supported: {SUPPORTED_EXTENSIONS}"
        )


def main() -> None:
    """Extract clauses from a contract file."""
    parser = argparse.ArgumentParser(
        description="Extract clauses from a contract file (.docx or .pdf)."
    )
    parser.add_argument(
        "file",
        type=Path,
        help="Path to the contract file (.docx or .pdf)",
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output file for JSON results (optional)",
    )
    parser.add_argument(
        "--format", "-f",
        choices=["table", "detailed", "json"],
        default="detailed",
        help="Output format (default: detailed)",
    )
    parser.add_argument(
        "--min-length",
        type=int,
        default=50,
        help="Minimum clause length in characters (default: 50)",
    )
    parser.add_argument(
        "--extractor",
        choices=["pattern", "llm"],
        default="pattern",
        help="Extractor to use: pattern (default) or llm",
    )
    parser.add_argument(
        "--api-key",
        help="OpenAI API key (for LLM extractor, can also use OPENAI_API_KEY env var)",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="LLM model to use (default: gpt-4o-mini)",
    )

    args = parser.parse_args()

    # Validate file path
    if not args.file.exists():
        print(f"Error: File not found: {args.file}")
        sys.exit(1)

    if args.file.suffix.lower() not in SUPPORTED_EXTENSIONS:
        print(f"Error: Unsupported file type: {args.file.suffix}")
        print(f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
        sys.exit(1)

    # Initialize parser and extractor
    print(f"Parsing: {args.file}")
    try:
        doc_parser = get_parser_for_file(args.file)
        document = doc_parser.parse(args.file)
    except ImportError as e:
        print(f"Error: {e}")
        sys.exit(1)

    print(f"Document has {document.metadata.get('paragraph_count', 0)} paragraphs")

    # Create extractor
    if args.extractor == "pattern":
        print("Using pattern-based extractor...")
        extractor = PatternClauseExtractor(min_clause_length=args.min_length)
    else:
        # LLM extractor
        api_key = args.api_key or os.getenv("OPENAI_API_KEY")
        if not api_key:
            print("Error: OpenAI API key required for LLM extractor.")
            print("Set OPENAI_API_KEY environment variable or use --api-key")
            sys.exit(1)

        print(f"Using LLM extractor (model: {args.model})...")
        try:
            from graph_builder.clauses import LLMClauseExtractor
            extractor = LLMClauseExtractor(api_key=api_key, model=args.model)
        except ImportError as e:
            print(f"Error: {e}")
            print("Install LLM dependencies with: uv sync --extra llm")
            sys.exit(1)

    # Extract clauses
    clauses = extractor.extract(document)

    print(f"Extracted {len(clauses)} clauses")

    # Output results
    if args.format == "table":
        print_clauses_table(clauses)
    elif args.format == "detailed":
        print_clauses_detailed(clauses)
    elif args.format == "json":
        print(json.dumps(clauses_to_dict(clauses), indent=2, ensure_ascii=False))

    # Save to file if requested
    if args.output:
        output_data = {
            "source": str(args.file),
            "paragraph_count": document.metadata.get("paragraph_count", 0),
            "clause_count": len(clauses),
            "clauses": clauses_to_dict(clauses),
        }
        with args.output.open("w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to: {args.output}")


if __name__ == "__main__":
    main()

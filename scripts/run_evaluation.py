#!/usr/bin/env python
"""Standalone script to run extraction evaluation.

Usage:
    uv run python scripts/run_evaluation.py data/ground_truth/sample.json
    uv run python scripts/run_evaluation.py data/ground_truth/sample.json --extractor llm
    uv run python scripts/run_evaluation.py data/ground_truth/sample.json --output results.json
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path for direct script execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from graph_builder.config.settings import get_settings
from graph_builder.evaluation import Evaluator, EvaluationResult, load_dataset
from graph_builder.extraction import SpacyEntityExtractor, SpacyRelationshipExtractor


def create_spacy_extractors() -> tuple:
    """Create spaCy-based extractors."""
    return SpacyEntityExtractor(), SpacyRelationshipExtractor()


def create_llm_extractors(api_key: str, model: str) -> tuple:
    """Create LLM-based extractors."""
    try:
        from graph_builder.extraction.llm_extractor import (
            LLMEntityExtractor,
            LLMRelationshipExtractor,
        )
    except ImportError as e:
        print(f"Error: LLM dependencies not installed. Run: uv sync --extra llm")
        print(f"Details: {e}")
        sys.exit(1)

    return LLMEntityExtractor(api_key=api_key, model=model), LLMRelationshipExtractor(
        api_key=api_key, model=model
    )


def print_results(result: EvaluationResult) -> None:
    """Print evaluation results to stdout."""
    print("\n" + "=" * 50)
    print("EVALUATION RESULTS")
    print("=" * 50)

    print("\nEntity Extraction:")
    print(f"  Precision: {result.entity_precision:.3f}")
    print(f"  Recall:    {result.entity_recall:.3f}")
    print(f"  F1 Score:  {result.entity_f1:.3f}")

    print("\nRelationship Extraction:")
    print(f"  Precision: {result.relationship_precision:.3f}")
    print(f"  Recall:    {result.relationship_recall:.3f}")
    print(f"  F1 Score:  {result.relationship_f1:.3f}")

    print("\nPer-Document Details:")
    for doc_id, detail in result.details.items():
        print(f"\n  {doc_id}:")
        print(f"    Entities:      TP={detail.entity_tp}, FP={detail.entity_fp}, FN={detail.entity_fn}")
        print(f"    Relationships: TP={detail.relationship_tp}, FP={detail.relationship_fp}, FN={detail.relationship_fn}")

    print("\n" + "=" * 50)


def main() -> None:
    """Run evaluation."""
    parser = argparse.ArgumentParser(
        description="Evaluate extraction quality against ground truth dataset."
    )
    parser.add_argument(
        "dataset",
        type=Path,
        help="Path to ground truth dataset JSON file",
    )
    parser.add_argument(
        "--extractor",
        choices=["spacy", "llm"],
        default="spacy",
        help="Extractor to use (default: spacy)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for JSON results (optional)",
    )
    parser.add_argument(
        "--api-key",
        help="OpenAI API key (for LLM extractor, overrides env var)",
    )
    parser.add_argument(
        "--model",
        default="gpt-4o-mini",
        help="LLM model to use (default: gpt-4o-mini)",
    )

    args = parser.parse_args()

    # Validate dataset path
    if not args.dataset.exists():
        print(f"Error: Dataset file not found: {args.dataset}")
        sys.exit(1)

    # Load dataset
    print(f"Loading dataset from {args.dataset}...")
    dataset = load_dataset(args.dataset)
    print(f"Loaded {len(dataset)} documents")

    # Create extractors
    if args.extractor == "spacy":
        print("Using spaCy extractors...")
        entity_extractor, rel_extractor = create_spacy_extractors()
    else:
        settings = get_settings()
        api_key = args.api_key or settings.openai_api_key
        if not api_key:
            print("Error: OpenAI API key required for LLM extractor.")
            print("Set GRAPH_BUILDER_OPENAI_API_KEY or use --api-key")
            sys.exit(1)
        model = args.model or settings.llm_model
        print(f"Using LLM extractors (model: {model})...")
        entity_extractor, rel_extractor = create_llm_extractors(api_key, model)

    # Run evaluation
    print("Running evaluation...")
    evaluator = Evaluator(entity_extractor, rel_extractor)
    result = evaluator.evaluate(dataset)

    # Print results
    print_results(result)

    # Save to file if requested
    if args.output:
        with args.output.open("w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2)
        print(f"\nResults saved to {args.output}")


if __name__ == "__main__":
    main()

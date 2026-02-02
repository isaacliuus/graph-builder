#!/usr/bin/env python
# pylint: disable=duplicate-code
"""Standalone script to run extraction evaluation.

Usage:
    uv run python scripts/run_evaluation.py data/ground_truth/sample.json
    uv run python scripts/run_evaluation.py data/ground_truth/sample.json --extractor llm
    uv run python scripts/run_evaluation.py data/ground_truth/sample.json --output results.json
    uv run python scripts/run_evaluation.py data/ground_truth/sample.json --debug
"""

import argparse
import json
import sys
from pathlib import Path

# Add src to path for direct script execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# pylint: disable=wrong-import-position
from graph_builder.config.settings import get_settings
from graph_builder.evaluation import (
    Evaluator,
    EvaluationResult,
    GroundTruthDocument,
    load_dataset,
)
from graph_builder.extraction import SpacyEntityExtractor, SpacyRelationshipExtractor


def create_spacy_extractors() -> tuple:
    """Create spaCy-based extractors."""
    return SpacyEntityExtractor(), SpacyRelationshipExtractor()


def create_llm_extractors(api_key: str, model: str) -> tuple:
    """Create LLM-based extractors."""
    try:
        # pylint: disable=import-outside-toplevel
        from graph_builder.extraction.llm_extractor import (
            LLMEntityExtractor,
            LLMRelationshipExtractor,
        )
    except ImportError as e:
        print("Error: LLM dependencies not installed. Run: uv sync --extra llm")
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
        print(f"    Entities:      TP={detail.entity_tp}, "
              f"FP={detail.entity_fp}, FN={detail.entity_fn}")
        print(f"    Relationships: TP={detail.relationship_tp}, "
              f"FP={detail.relationship_fp}, FN={detail.relationship_fn}")

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
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Export detailed extraction results to tmp/ folder for debugging",
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

    # Export debug info if requested
    if args.debug:
        export_debug_results(result, dataset)


def export_debug_results(
    result: EvaluationResult, dataset: list[GroundTruthDocument]
) -> None:
    """Export detailed extraction results to tmp folder for debugging."""
    tmp_dir = Path(__file__).parent.parent / "tmp"
    tmp_dir.mkdir(exist_ok=True)

    # Export per-document results
    for gt_doc in dataset:
        doc_id = gt_doc.id
        doc_result = result.details.get(doc_id)
        if not doc_result:
            continue

        doc_debug = {
            "document_id": doc_id,
            "content": gt_doc.content,
            "metrics": {
                "entity_tp": doc_result.entity_tp,
                "entity_fp": doc_result.entity_fp,
                "entity_fn": doc_result.entity_fn,
                "relationship_tp": doc_result.relationship_tp,
                "relationship_fp": doc_result.relationship_fp,
                "relationship_fn": doc_result.relationship_fn,
            },
            "ground_truth": {
                "entities": doc_result.ground_truth_entities,
                "relationships": doc_result.ground_truth_relationships,
            },
            "extracted": {
                "entities": doc_result.extracted_entities,
                "relationships": doc_result.extracted_relationships,
            },
        }

        output_file = tmp_dir / f"{doc_id}_debug.json"
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(doc_debug, f, indent=2)
        print(f"Debug output saved: {output_file}")

    # Export summary with all debug info
    summary_file = tmp_dir / "evaluation_debug_summary.json"
    with summary_file.open("w", encoding="utf-8") as f:
        json.dump(result.to_dict(include_debug=True), f, indent=2)
    print(f"Full debug summary saved: {summary_file}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python
# pylint: disable=duplicate-code
"""Standalone script to run clause extraction evaluation.

Usage:
    uv run python scripts/run_clause_evaluation.py data/ground_truth/contracts/sample.json
    uv run python scripts/run_clause_evaluation.py data/ground_truth/contracts/sample.json --output results.json
    uv run python scripts/run_clause_evaluation.py data/ground_truth/contracts/sample.json --debug
    uv run python scripts/run_clause_evaluation.py data/ground_truth/contracts/sample.json --extractor llm --api-key sk-...
"""

import argparse
import json
import os
import sys
from pathlib import Path

# Add src to path for direct script execution
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# pylint: disable=wrong-import-position
from graph_builder.evaluation import (
    ClauseEvaluator,
    ClauseEvaluationResult,
    GroundTruthContractDocument,
    load_clause_dataset,
)
from graph_builder.parsing import DocxParser
from graph_builder.clauses import PatternClauseExtractor


def print_results(result: ClauseEvaluationResult) -> None:
    """Print evaluation results to stdout."""
    print("\n" + "=" * 50)
    print("CLAUSE EVALUATION RESULTS")
    print("=" * 50)

    print("\nClause Detection:")
    print(f"  Precision: {result.detection_precision:.3f}")
    print(f"  Recall:    {result.detection_recall:.3f}")
    print(f"  F1 Score:  {result.detection_f1:.3f}")

    print("\nType Classification:")
    print(f"  Accuracy:  {result.type_accuracy:.3f}")

    print("\nBoundary Detection:")
    print(f"  Mean IoU:  {result.mean_boundary_iou:.3f}")

    print("\nPer-Document Details:")
    for doc_id, detail in result.details.items():
        print(f"\n  {doc_id}:")
        print(
            f"    Detection: TP={detail.detection_tp}, "
            f"FP={detail.detection_fp}, FN={detail.detection_fn}"
        )
        print(f"    Type Correct: {detail.type_correct}/{detail.type_total}")
        if detail.boundary_ious:
            mean_iou = sum(detail.boundary_ious) / len(detail.boundary_ious)
            print(f"    Mean Boundary IoU: {mean_iou:.3f}")

    print("\n" + "=" * 50)


def main() -> None:
    """Run clause evaluation."""
    parser = argparse.ArgumentParser(
        description="Evaluate clause extraction quality against ground truth dataset."
    )
    parser.add_argument(
        "dataset",
        type=Path,
        help="Path to ground truth clause dataset JSON file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output file for JSON results (optional)",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Export detailed extraction results to tmp/ folder for debugging",
    )
    parser.add_argument(
        "--base-path",
        type=Path,
        help="Base path for resolving document file paths (default: dataset directory)",
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

    # Validate dataset path
    if not args.dataset.exists():
        print(f"Error: Dataset file not found: {args.dataset}")
        sys.exit(1)

    # Load dataset
    print(f"Loading dataset from {args.dataset}...")
    dataset = load_clause_dataset(args.dataset)
    print(f"Loaded {len(dataset)} contract documents")

    # Determine base path for document files
    base_path = args.base_path or args.dataset.parent

    # Create parser and extractor
    print("Initializing parser and extractor...")
    try:
        doc_parser = DocxParser()
        # Test that python-docx is available
        _ = doc_parser.docx
    except ImportError as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Create extractor
    if args.extractor == "pattern":
        print("Using pattern-based extractor...")
        extractor = PatternClauseExtractor()
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

    # Run evaluation
    print("Running evaluation...")
    evaluator = ClauseEvaluator(doc_parser, extractor, base_path=base_path)

    try:
        result = evaluator.evaluate(dataset)
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("Make sure the contract documents referenced in the dataset exist.")
        sys.exit(1)

    # Print results
    print_results(result)

    # Save to file if requested
    if args.output:
        with args.output.open("w", encoding="utf-8") as f:
            json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to {args.output}")

    # Export debug info if requested
    if args.debug:
        export_debug_results(result, dataset)


def export_debug_results(
    result: ClauseEvaluationResult, dataset: list[GroundTruthContractDocument]
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
            "file": gt_doc.file,
            "metrics": {
                "detection_tp": doc_result.detection_tp,
                "detection_fp": doc_result.detection_fp,
                "detection_fn": doc_result.detection_fn,
                "type_correct": doc_result.type_correct,
                "type_total": doc_result.type_total,
                "boundary_ious": doc_result.boundary_ious,
            },
            "ground_truth_clauses": doc_result.ground_truth_clauses,
            "extracted_clauses": doc_result.extracted_clauses,
        }

        output_file = tmp_dir / f"{doc_id}_clause_debug.json"
        with output_file.open("w", encoding="utf-8") as f:
            json.dump(doc_debug, f, indent=2, ensure_ascii=False)
        print(f"Debug output saved: {output_file}")

    # Export summary with all debug info
    summary_file = tmp_dir / "clause_evaluation_debug_summary.json"
    with summary_file.open("w", encoding="utf-8") as f:
        json.dump(result.to_dict(include_debug=True), f, indent=2, ensure_ascii=False)
    print(f"Full debug summary saved: {summary_file}")


if __name__ == "__main__":
    main()

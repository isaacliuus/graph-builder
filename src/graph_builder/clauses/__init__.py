"""Clause extraction module for legal contracts."""

from graph_builder.clauses.base import ClauseExtractor
from graph_builder.clauses.pattern_extractor import PatternClauseExtractor

__all__ = [
    "ClauseExtractor",
    "PatternClauseExtractor",
]

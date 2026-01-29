"""
Evaluation Pipeline for Brain Trust

Provides automated testing for model swaps and agent validation.
"""

from .schema import (
    TestCase,
    TestResult,
    EvaluatorResult,
    EvalRunSummary,
    ModelComparison,
    EvaluatorType,
    load_test_cases,
)

__all__ = [
    "TestCase",
    "TestResult",
    "EvaluatorResult",
    "EvalRunSummary",
    "ModelComparison",
    "EvaluatorType",
    "load_test_cases",
]

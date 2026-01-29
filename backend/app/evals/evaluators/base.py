"""
Base Evaluator Interface

All evaluators inherit from BaseEvaluator and implement the evaluate() method.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, TYPE_CHECKING

if TYPE_CHECKING:
    from ..schema import TestCase, EvaluatorResult


class BaseEvaluator(ABC):
    """
    Abstract base class for all evaluators.

    Evaluators receive the test case, agent output, and execution context,
    then return a score (0.0-1.0) with reasoning.
    """

    name: str = "base"

    @abstractmethod
    def evaluate(
        self,
        test_case: "TestCase",
        agent_output: str,
        tools_called: List[str],
        execution_context: Dict[str, Any],
    ) -> "EvaluatorResult":
        """
        Evaluate the agent's performance.

        Args:
            test_case: The test case being evaluated
            agent_output: The agent's response text
            tools_called: List of tool names the agent called
            execution_context: Additional execution info (model_id, duration, etc.)

        Returns:
            EvaluatorResult with score, passed status, and reasoning
        """
        pass


# Registry of available evaluators
_EVALUATOR_REGISTRY: Dict[str, type] = {}


def register_evaluator(name: str):
    """Decorator to register an evaluator class."""
    def decorator(cls):
        _EVALUATOR_REGISTRY[name] = cls
        cls.name = name
        return cls
    return decorator


def get_evaluator(name: str) -> BaseEvaluator:
    """
    Get an evaluator instance by name.

    Args:
        name: Evaluator name (e.g., "tool_selection", "llm_judge")

    Returns:
        Instantiated evaluator

    Raises:
        ValueError: If evaluator not found
    """
    if name not in _EVALUATOR_REGISTRY:
        available = ", ".join(_EVALUATOR_REGISTRY.keys())
        raise ValueError(f"Unknown evaluator: {name}. Available: {available}")

    return _EVALUATOR_REGISTRY[name]()

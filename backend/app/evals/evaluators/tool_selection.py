"""
Tool Selection Evaluator

Evaluates whether the agent used the expected tools to complete a task.
"""

from typing import Dict, Any, List
from .base import BaseEvaluator, register_evaluator
from ..schema import TestCase, EvaluatorResult


@register_evaluator("tool_selection")
class ToolSelectionEvaluator(BaseEvaluator):
    """
    Evaluates tool selection accuracy.

    Scoring:
    - 1.0: Agent used all expected tools (may use additional tools)
    - 0.5-0.9: Agent used some expected tools
    - 0.0: Agent used none of the expected tools

    Does not penalize for using additional tools beyond expected.
    """

    name = "tool_selection"

    def evaluate(
        self,
        test_case: TestCase,
        agent_output: str,
        tools_called: List[str],
        execution_context: Dict[str, Any],
    ) -> EvaluatorResult:
        """Evaluate tool selection."""

        expected_tools = set(t.lower().strip() for t in test_case.expected_tools)
        actual_tools = set(t.lower().strip() for t in tools_called)

        if not expected_tools:
            # No expected tools specified - pass if agent completed without tools
            # or with any tools (lenient)
            return EvaluatorResult(
                evaluator_name=self.name,
                score=1.0,
                passed=True,
                reasoning="No specific tools expected. Agent free to choose tools.",
                details={
                    "expected_tools": list(test_case.expected_tools),
                    "actual_tools": list(tools_called),
                    "mode": "no_expectation",
                },
            )

        # Calculate overlap
        matched_tools = expected_tools & actual_tools
        missing_tools = expected_tools - actual_tools
        extra_tools = actual_tools - expected_tools

        # Score based on coverage of expected tools
        if len(expected_tools) > 0:
            score = len(matched_tools) / len(expected_tools)
        else:
            score = 1.0

        # Determine pass/fail
        passed = score >= test_case.passing_threshold

        # Build reasoning
        if score == 1.0:
            reasoning = f"Agent used all {len(expected_tools)} expected tools."
            if extra_tools:
                reasoning += f" Also used {len(extra_tools)} additional tools."
        elif score > 0:
            reasoning = f"Agent used {len(matched_tools)}/{len(expected_tools)} expected tools. "
            reasoning += f"Missing: {', '.join(missing_tools)}."
        else:
            reasoning = f"Agent did not use any of the expected tools. "
            reasoning += f"Expected: {', '.join(expected_tools)}. "
            reasoning += f"Used: {', '.join(actual_tools) if actual_tools else 'none'}."

        return EvaluatorResult(
            evaluator_name=self.name,
            score=score,
            passed=passed,
            reasoning=reasoning,
            details={
                "expected_tools": list(test_case.expected_tools),
                "actual_tools": list(tools_called),
                "matched_tools": list(matched_tools),
                "missing_tools": list(missing_tools),
                "extra_tools": list(extra_tools),
            },
        )

"""
Task Completion Evaluator

Evaluates whether the agent's output indicates task completion.
Uses heuristics and expected_output_contains for verification.
"""

from typing import Dict, Any, List
import re
from .base import BaseEvaluator, register_evaluator
from ..schema import TestCase, EvaluatorResult


@register_evaluator("task_completion")
class TaskCompletionEvaluator(BaseEvaluator):
    """
    Evaluates task completion using heuristics and content matching.

    Scoring:
    - Checks for expected content in output
    - Penalizes error indicators
    - Rewards structured/complete responses

    This is a heuristic evaluator. For nuanced evaluation, use llm_judge.
    """

    name = "task_completion"

    # Patterns indicating failure
    FAILURE_PATTERNS = [
        r"i (?:cannot|can't|couldn't|am unable to)",
        r"error:",
        r"exception:",
        r"failed to",
        r"unable to (?:complete|finish|perform)",
        r"i don't (?:know|have|understand)",
        r"not (?:possible|available|supported)",
    ]

    # Patterns indicating success
    SUCCESS_PATTERNS = [
        r"here (?:is|are) the",
        r"i (?:have|'ve) (?:found|completed|finished|created)",
        r"successfully",
        r"the (?:result|answer|output) is",
        r"done[.!]",
        r"completed[.!]",
    ]

    def evaluate(
        self,
        test_case: TestCase,
        agent_output: str,
        tools_called: List[str],
        execution_context: Dict[str, Any],
    ) -> EvaluatorResult:
        """Evaluate task completion."""

        output_lower = agent_output.lower()
        score = 0.5  # Start neutral
        reasons = []

        # Check for expected content
        expected_content = test_case.expected_output_contains
        if expected_content:
            matched_content = []
            missing_content = []

            for expected in expected_content:
                if expected.lower() in output_lower:
                    matched_content.append(expected)
                else:
                    missing_content.append(expected)

            content_score = len(matched_content) / len(expected_content) if expected_content else 1.0
            score = content_score * 0.7 + 0.3  # Weight content matching heavily

            if matched_content:
                reasons.append(f"Found {len(matched_content)}/{len(expected_content)} expected content items")
            if missing_content:
                reasons.append(f"Missing content: {', '.join(missing_content[:3])}")
        else:
            # No specific content expected, use pattern matching
            # Check for failure indicators
            failure_count = sum(1 for pattern in self.FAILURE_PATTERNS if re.search(pattern, output_lower))
            success_count = sum(1 for pattern in self.SUCCESS_PATTERNS if re.search(pattern, output_lower))

            if failure_count > 0:
                score -= 0.2 * min(failure_count, 2)
                reasons.append(f"Found {failure_count} failure indicators")

            if success_count > 0:
                score += 0.2 * min(success_count, 2)
                reasons.append(f"Found {success_count} success indicators")

        # Check output length (very short outputs are suspicious)
        if len(agent_output.strip()) < 20:
            score -= 0.2
            reasons.append("Output very short (< 20 chars)")
        elif len(agent_output.strip()) > 100:
            score += 0.1
            reasons.append("Output substantive (> 100 chars)")

        # Check if tools were used (often indicates real work)
        if tools_called:
            score += 0.1
            reasons.append(f"Used {len(tools_called)} tool(s)")

        # Clamp score to valid range
        score = max(0.0, min(1.0, score))
        passed = score >= test_case.passing_threshold

        reasoning = "; ".join(reasons) if reasons else "Basic completion check passed"

        return EvaluatorResult(
            evaluator_name=self.name,
            score=score,
            passed=passed,
            reasoning=reasoning,
            details={
                "output_length": len(agent_output),
                "tools_used": len(tools_called),
                "expected_content_matched": matched_content if expected_content else None,
            },
        )

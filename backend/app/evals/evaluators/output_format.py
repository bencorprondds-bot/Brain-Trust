"""
Output Format Evaluator

Evaluates whether the agent's output matches the expected format.
"""

from typing import Dict, Any, List
import json
import re
from .base import BaseEvaluator, register_evaluator
from ..schema import TestCase, EvaluatorResult


@register_evaluator("output_format")
class OutputFormatEvaluator(BaseEvaluator):
    """
    Evaluates output format compliance.

    Supported formats:
    - json: Valid JSON output
    - markdown: Contains markdown structure
    - structured: Has clear sections/organization
    - code: Contains code blocks
    - list: Contains bullet or numbered lists

    Scoring based on format compliance.
    """

    name = "output_format"

    def evaluate(
        self,
        test_case: TestCase,
        agent_output: str,
        tools_called: List[str],
        execution_context: Dict[str, Any],
    ) -> EvaluatorResult:
        """Evaluate output format."""

        expected_format = test_case.expected_output_format
        if not expected_format:
            return EvaluatorResult(
                evaluator_name=self.name,
                score=1.0,
                passed=True,
                reasoning="No specific format expected.",
                details={"expected_format": None},
            )

        format_lower = expected_format.lower()

        if format_lower == "json":
            return self._evaluate_json(test_case, agent_output)
        elif format_lower == "markdown":
            return self._evaluate_markdown(test_case, agent_output)
        elif format_lower == "structured":
            return self._evaluate_structured(test_case, agent_output)
        elif format_lower == "code":
            return self._evaluate_code(test_case, agent_output)
        elif format_lower == "list":
            return self._evaluate_list(test_case, agent_output)
        else:
            return EvaluatorResult(
                evaluator_name=self.name,
                score=0.5,
                passed=True,
                reasoning=f"Unknown format '{expected_format}', skipping format check.",
                details={"expected_format": expected_format, "supported": False},
            )

    def _evaluate_json(self, test_case: TestCase, agent_output: str) -> EvaluatorResult:
        """Check for valid JSON in output."""
        # Try to extract JSON from output (may be wrapped in text or code blocks)
        json_patterns = [
            r'```json\s*([\s\S]*?)\s*```',  # Code block
            r'```\s*([\s\S]*?)\s*```',  # Generic code block
            r'(\{[\s\S]*\})',  # Raw JSON object
            r'(\[[\s\S]*\])',  # Raw JSON array
        ]

        for pattern in json_patterns:
            matches = re.findall(pattern, agent_output)
            for match in matches:
                try:
                    json.loads(match.strip())
                    return EvaluatorResult(
                        evaluator_name=self.name,
                        score=1.0,
                        passed=True,
                        reasoning="Valid JSON found in output.",
                        details={"expected_format": "json", "json_valid": True},
                    )
                except json.JSONDecodeError:
                    continue

        # Try the entire output as JSON
        try:
            json.loads(agent_output.strip())
            return EvaluatorResult(
                evaluator_name=self.name,
                score=1.0,
                passed=True,
                reasoning="Entire output is valid JSON.",
                details={"expected_format": "json", "json_valid": True},
            )
        except json.JSONDecodeError:
            pass

        return EvaluatorResult(
            evaluator_name=self.name,
            score=0.0,
            passed=False,
            reasoning="No valid JSON found in output.",
            details={"expected_format": "json", "json_valid": False},
        )

    def _evaluate_markdown(self, test_case: TestCase, agent_output: str) -> EvaluatorResult:
        """Check for markdown structure."""
        score = 0.0
        features_found = []

        # Check for headers
        if re.search(r'^#{1,6}\s+\w', agent_output, re.MULTILINE):
            score += 0.3
            features_found.append("headers")

        # Check for lists
        if re.search(r'^[\s]*[-*+]\s+\w', agent_output, re.MULTILINE):
            score += 0.2
            features_found.append("bullet lists")
        if re.search(r'^[\s]*\d+\.\s+\w', agent_output, re.MULTILINE):
            score += 0.2
            features_found.append("numbered lists")

        # Check for code blocks
        if re.search(r'```[\s\S]*?```', agent_output):
            score += 0.2
            features_found.append("code blocks")

        # Check for links or bold/italic
        if re.search(r'\[.*?\]\(.*?\)', agent_output) or re.search(r'\*\*.*?\*\*', agent_output):
            score += 0.1
            features_found.append("formatting")

        # Minimum score if any features found
        if features_found:
            score = max(score, 0.5)

        passed = score >= test_case.passing_threshold

        return EvaluatorResult(
            evaluator_name=self.name,
            score=score,
            passed=passed,
            reasoning=f"Markdown features found: {', '.join(features_found) or 'none'}.",
            details={"expected_format": "markdown", "features": features_found},
        )

    def _evaluate_structured(self, test_case: TestCase, agent_output: str) -> EvaluatorResult:
        """Check for structured organization."""
        score = 0.0
        features = []

        lines = agent_output.strip().split('\n')

        # Check for multiple distinct sections/paragraphs
        if len(lines) > 5:
            score += 0.3
            features.append(f"{len(lines)} lines")

        # Check for section headers or labels
        if re.search(r'^[A-Z][^.!?]*:\s*$', agent_output, re.MULTILINE):
            score += 0.3
            features.append("section labels")

        # Check for consistent indentation/hierarchy
        indented_lines = sum(1 for line in lines if line.startswith(('  ', '\t')))
        if indented_lines > 2:
            score += 0.2
            features.append("hierarchical structure")

        # Check for separators
        if re.search(r'^[-=]{3,}$', agent_output, re.MULTILINE):
            score += 0.2
            features.append("separators")

        passed = score >= test_case.passing_threshold

        return EvaluatorResult(
            evaluator_name=self.name,
            score=min(score, 1.0),
            passed=passed,
            reasoning=f"Structure features: {', '.join(features) or 'minimal structure'}.",
            details={"expected_format": "structured", "features": features},
        )

    def _evaluate_code(self, test_case: TestCase, agent_output: str) -> EvaluatorResult:
        """Check for code blocks."""
        # Check for fenced code blocks
        fenced_blocks = re.findall(r'```(\w+)?\s*[\s\S]*?```', agent_output)
        if fenced_blocks:
            return EvaluatorResult(
                evaluator_name=self.name,
                score=1.0,
                passed=True,
                reasoning=f"Found {len(fenced_blocks)} fenced code block(s).",
                details={"expected_format": "code", "code_blocks": len(fenced_blocks)},
            )

        # Check for indented code (4+ spaces)
        indented_code = re.findall(r'^(?:    |\t).+$', agent_output, re.MULTILINE)
        if len(indented_code) > 3:
            return EvaluatorResult(
                evaluator_name=self.name,
                score=0.7,
                passed=True,
                reasoning=f"Found {len(indented_code)} lines of indented code.",
                details={"expected_format": "code", "indented_lines": len(indented_code)},
            )

        return EvaluatorResult(
            evaluator_name=self.name,
            score=0.0,
            passed=False,
            reasoning="No code blocks found in output.",
            details={"expected_format": "code", "code_blocks": 0},
        )

    def _evaluate_list(self, test_case: TestCase, agent_output: str) -> EvaluatorResult:
        """Check for list format."""
        bullet_items = re.findall(r'^[\s]*[-*+]\s+.+$', agent_output, re.MULTILINE)
        numbered_items = re.findall(r'^[\s]*\d+[.)]\s+.+$', agent_output, re.MULTILINE)

        total_items = len(bullet_items) + len(numbered_items)

        if total_items >= 3:
            return EvaluatorResult(
                evaluator_name=self.name,
                score=1.0,
                passed=True,
                reasoning=f"Found list with {total_items} items.",
                details={
                    "expected_format": "list",
                    "bullet_items": len(bullet_items),
                    "numbered_items": len(numbered_items),
                },
            )
        elif total_items > 0:
            return EvaluatorResult(
                evaluator_name=self.name,
                score=0.5,
                passed=total_items >= test_case.passing_threshold * 3,
                reasoning=f"Found partial list with {total_items} items.",
                details={
                    "expected_format": "list",
                    "bullet_items": len(bullet_items),
                    "numbered_items": len(numbered_items),
                },
            )

        return EvaluatorResult(
            evaluator_name=self.name,
            score=0.0,
            passed=False,
            reasoning="No list format found in output.",
            details={"expected_format": "list", "items_found": 0},
        )

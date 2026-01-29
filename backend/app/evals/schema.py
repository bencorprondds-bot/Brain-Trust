"""
Evaluation Schema for Brain Trust

Defines the data models for evaluation test cases and results.
Test cases are loaded from YAML files and validated against these schemas.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
import yaml
from pathlib import Path


class EvaluatorType(str, Enum):
    """Available evaluator types."""
    TOOL_SELECTION = "tool_selection"
    OUTPUT_FORMAT = "output_format"
    TASK_COMPLETION = "task_completion"
    LLM_JUDGE = "llm_judge"


@dataclass
class TestCase:
    """
    A single evaluation test case.

    Loaded from YAML files in ~/.pai/evals/ or config/evals/.

    Example YAML:
        id: librarian-find-folder-001
        name: "Find Inbox Folder"
        agent_role: "Librarian"
        agent_goal: "Find and return the ID of the Inbox folder"
        input_prompt: "Find the Inbox folder in our Shared Drive"
        expected_tools:
          - "Google Drive Folder Finder"
        evaluators:
          - tool_selection
          - task_completion
        passing_threshold: 0.8
    """

    # Identity
    id: str
    name: str

    # Agent configuration
    agent_role: str
    agent_goal: str

    # Test input (required, so must be before fields with defaults)
    input_prompt: str

    # Optional agent configuration
    agent_backstory: str = ""
    agent_tools: List[str] = field(default_factory=list)

    # Optional test context
    context: Optional[str] = None

    # Expected behavior
    expected_tools: List[str] = field(default_factory=list)
    expected_output_contains: List[str] = field(default_factory=list)
    expected_output_format: Optional[str] = None  # "json", "markdown", etc.

    # Evaluation configuration
    evaluators: List[str] = field(default_factory=lambda: ["task_completion"])
    passing_threshold: float = 0.8

    # LLM Judge configuration (if using llm_judge evaluator)
    judge_criteria: Optional[str] = None
    judge_rubric: Optional[Dict[str, str]] = None

    # Metadata
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    timeout_seconds: int = 120

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TestCase":
        """Create TestCase from dictionary (parsed YAML)."""
        return cls(
            id=data["id"],
            name=data["name"],
            agent_role=data["agent_role"],
            agent_goal=data["agent_goal"],
            agent_backstory=data.get("agent_backstory", ""),
            agent_tools=data.get("agent_tools", []),
            input_prompt=data["input_prompt"],
            context=data.get("context"),
            expected_tools=data.get("expected_tools", []),
            expected_output_contains=data.get("expected_output_contains", []),
            expected_output_format=data.get("expected_output_format"),
            evaluators=data.get("evaluators", ["task_completion"]),
            passing_threshold=float(data.get("passing_threshold", 0.8)),
            judge_criteria=data.get("judge_criteria"),
            judge_rubric=data.get("judge_rubric"),
            category=data.get("category", "general"),
            tags=data.get("tags", []),
            timeout_seconds=int(data.get("timeout_seconds", 120)),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "agent_role": self.agent_role,
            "agent_goal": self.agent_goal,
            "agent_backstory": self.agent_backstory,
            "agent_tools": self.agent_tools,
            "input_prompt": self.input_prompt,
            "context": self.context,
            "expected_tools": self.expected_tools,
            "expected_output_contains": self.expected_output_contains,
            "expected_output_format": self.expected_output_format,
            "evaluators": self.evaluators,
            "passing_threshold": self.passing_threshold,
            "judge_criteria": self.judge_criteria,
            "judge_rubric": self.judge_rubric,
            "category": self.category,
            "tags": self.tags,
            "timeout_seconds": self.timeout_seconds,
        }


@dataclass
class EvaluatorResult:
    """Result from a single evaluator."""

    evaluator_name: str
    score: float  # 0.0 to 1.0
    passed: bool
    reasoning: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "evaluator_name": self.evaluator_name,
            "score": self.score,
            "passed": self.passed,
            "reasoning": self.reasoning,
            "details": self.details,
        }


@dataclass
class TestResult:
    """Complete result of running a test case."""

    # Test identity
    test_case_id: str
    test_case_name: str

    # Execution details
    model_id: str
    executed_at: datetime
    duration_seconds: float

    # Agent output
    agent_output: str
    tools_called: List[str] = field(default_factory=list)

    # Evaluation results
    evaluator_results: List[EvaluatorResult] = field(default_factory=list)

    # Aggregate score
    overall_score: float = 0.0
    passed: bool = False

    # Error handling
    error: Optional[str] = None

    def calculate_overall_score(self) -> None:
        """Calculate overall score as average of evaluator scores."""
        if not self.evaluator_results:
            self.overall_score = 0.0
            return

        self.overall_score = sum(r.score for r in self.evaluator_results) / len(self.evaluator_results)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_case_id": self.test_case_id,
            "test_case_name": self.test_case_name,
            "model_id": self.model_id,
            "executed_at": self.executed_at.isoformat(),
            "duration_seconds": self.duration_seconds,
            "agent_output": self.agent_output,
            "tools_called": self.tools_called,
            "evaluator_results": [r.to_dict() for r in self.evaluator_results],
            "overall_score": self.overall_score,
            "passed": self.passed,
            "error": self.error,
        }


@dataclass
class EvalRunSummary:
    """Summary of an entire evaluation run (multiple test cases)."""

    run_id: str
    model_id: str
    started_at: datetime
    completed_at: Optional[datetime] = None

    # Results
    test_results: List[TestResult] = field(default_factory=list)

    # Aggregate metrics
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    error_tests: int = 0
    average_score: float = 0.0

    def calculate_summary(self) -> None:
        """Calculate aggregate metrics from test results."""
        self.total_tests = len(self.test_results)
        self.passed_tests = sum(1 for r in self.test_results if r.passed)
        self.failed_tests = sum(1 for r in self.test_results if not r.passed and not r.error)
        self.error_tests = sum(1 for r in self.test_results if r.error)

        scores = [r.overall_score for r in self.test_results if not r.error]
        self.average_score = sum(scores) / len(scores) if scores else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "model_id": self.model_id,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "test_results": [r.to_dict() for r in self.test_results],
            "total_tests": self.total_tests,
            "passed_tests": self.passed_tests,
            "failed_tests": self.failed_tests,
            "error_tests": self.error_tests,
            "average_score": self.average_score,
        }


@dataclass
class ModelComparison:
    """Comparison of two models across evaluation runs."""

    model_a_id: str
    model_b_id: str
    model_a_summary: EvalRunSummary
    model_b_summary: EvalRunSummary

    # Per-test comparison
    test_comparisons: List[Dict[str, Any]] = field(default_factory=list)

    # Winner determination
    winner: Optional[str] = None  # model_a_id, model_b_id, or "tie"
    margin: float = 0.0

    def compare(self) -> None:
        """Compare the two runs and determine winner."""
        score_a = self.model_a_summary.average_score
        score_b = self.model_b_summary.average_score

        self.margin = abs(score_a - score_b)

        if self.margin < 0.05:  # Within 5% is a tie
            self.winner = "tie"
        elif score_a > score_b:
            self.winner = self.model_a_id
        else:
            self.winner = self.model_b_id

        # Build per-test comparisons
        results_a = {r.test_case_id: r for r in self.model_a_summary.test_results}
        results_b = {r.test_case_id: r for r in self.model_b_summary.test_results}

        all_test_ids = set(results_a.keys()) | set(results_b.keys())

        for test_id in sorted(all_test_ids):
            result_a = results_a.get(test_id)
            result_b = results_b.get(test_id)

            self.test_comparisons.append({
                "test_case_id": test_id,
                "model_a_score": result_a.overall_score if result_a else None,
                "model_b_score": result_b.overall_score if result_b else None,
                "model_a_passed": result_a.passed if result_a else None,
                "model_b_passed": result_b.passed if result_b else None,
            })

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_a_id": self.model_a_id,
            "model_b_id": self.model_b_id,
            "model_a_average_score": self.model_a_summary.average_score,
            "model_b_average_score": self.model_b_summary.average_score,
            "winner": self.winner,
            "margin": self.margin,
            "test_comparisons": self.test_comparisons,
        }


def load_test_cases(paths: Optional[List[Path]] = None) -> List[TestCase]:
    """
    Load test cases from YAML files.

    Search order:
    1. Explicit paths if provided
    2. ~/.pai/evals/*.yaml
    3. ./config/evals/*.yaml
    """
    test_cases = []

    if paths:
        search_paths = paths
    else:
        search_paths = [
            Path.home() / ".pai" / "evals",
            Path(__file__).parent.parent.parent.parent / "config" / "evals",
        ]

    for search_path in search_paths:
        if not search_path.exists():
            continue

        yaml_files = list(search_path.glob("*.yaml")) + list(search_path.glob("*.yml"))

        for yaml_file in yaml_files:
            try:
                with open(yaml_file, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)

                # Handle both single test case and list of test cases
                if isinstance(data, list):
                    for item in data:
                        test_cases.append(TestCase.from_dict(item))
                elif isinstance(data, dict):
                    # Could be a single test case or a wrapper with 'tests' key
                    if "tests" in data:
                        for item in data["tests"]:
                            test_cases.append(TestCase.from_dict(item))
                    else:
                        test_cases.append(TestCase.from_dict(data))

            except Exception as e:
                print(f"Warning: Failed to load {yaml_file}: {e}")

    return test_cases

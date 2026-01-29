"""
Simplicity Validator for Brain Trust / Legion

Checks for overcomplexity patterns in code changes.

Based on Karpathy insight: "They will implement 1000 lines where 100 would suffice...
They bloat abstractions, they don't clean up dead code, overcomplicate APIs"
"""

import os
import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ComplexitySignal(str, Enum):
    """Types of complexity signals to detect."""
    UNNECESSARY_ABSTRACTION = "unnecessary_abstraction"
    PREMATURE_GENERALIZATION = "premature_generalization"
    WRAPPER_AROUND_WRAPPER = "wrapper_around_wrapper"
    CONFIG_FOR_HARDCODED = "config_for_hardcoded"
    FACTORY_FOR_SINGLE_IMPL = "factory_for_single_impl"
    EXCESSIVE_PARAMETERS = "excessive_parameters"
    DEEP_NESTING = "deep_nesting"
    DEAD_CODE = "dead_code"
    UNUSED_IMPORTS = "unused_imports"
    OVER_ENGINEERED_SOLUTION = "over_engineered_solution"


@dataclass
class ComplexityIssue:
    """A detected complexity issue."""
    signal: ComplexitySignal
    description: str
    location: Optional[str] = None  # file:line or function name
    severity: str = "medium"  # low, medium, high
    suggestion: Optional[str] = None


@dataclass
class SimplicityReport:
    """Report from simplicity validation."""

    # Code metrics
    lines_added: int = 0
    lines_removed: int = 0
    net_lines: int = 0

    # Abstractions introduced
    new_classes: List[str] = field(default_factory=list)
    new_functions: List[str] = field(default_factory=list)

    # Issues detected
    issues: List[ComplexityIssue] = field(default_factory=list)

    # Overall assessment
    complexity_score: float = 0.0  # 0 = simple, 1 = complex
    simplification_suggested: bool = False
    suggested_approach: Optional[str] = None

    def has_issues(self) -> bool:
        return len(self.issues) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
            "net_lines": self.net_lines,
            "new_classes": self.new_classes,
            "new_functions": self.new_functions,
            "issues": [
                {
                    "signal": i.signal.value,
                    "description": i.description,
                    "location": i.location,
                    "severity": i.severity,
                    "suggestion": i.suggestion,
                }
                for i in self.issues
            ],
            "complexity_score": self.complexity_score,
            "simplification_suggested": self.simplification_suggested,
            "suggested_approach": self.suggested_approach,
        }

    def format_for_user(self) -> str:
        """Format report for display to user."""
        lines = ["## Simplicity Check"]
        lines.append(f"Lines: +{self.lines_added} / -{self.lines_removed} (net: {self.net_lines:+d})")

        if self.new_classes:
            lines.append(f"New classes: {', '.join(self.new_classes)}")
        if self.new_functions:
            lines.append(f"New functions: {', '.join(self.new_functions)}")

        if self.issues:
            lines.append("")
            lines.append("### Issues Detected:")
            for issue in self.issues:
                severity_marker = {"low": "-", "medium": "*", "high": "!"}[issue.severity]
                lines.append(f"  [{severity_marker}] {issue.description}")
                if issue.location:
                    lines.append(f"      at {issue.location}")
                if issue.suggestion:
                    lines.append(f"      Suggestion: {issue.suggestion}")

        if self.simplification_suggested:
            lines.append("")
            lines.append(f"### Simplification Available:")
            lines.append(f"  {self.suggested_approach}")

        return "\n".join(lines)


class SimplicityValidator:
    """
    Validates code changes for unnecessary complexity.

    Inspired by Karpathy: "They will implement 1000 lines where 100 would suffice"
    """

    # Patterns that suggest overcomplexity
    COMPLEXITY_PATTERNS = {
        # Factory patterns for single implementations
        r"class \w+Factory": ComplexitySignal.FACTORY_FOR_SINGLE_IMPL,
        # Abstract base classes with single child
        r"class Abstract\w+": ComplexitySignal.PREMATURE_GENERALIZATION,
        # Config/Settings classes for simple values
        r"class \w+(Config|Settings|Options)": ComplexitySignal.CONFIG_FOR_HARDCODED,
        # Wrapper/Adapter/Proxy without clear need
        r"class \w+(Wrapper|Adapter|Proxy|Delegate)": ComplexitySignal.WRAPPER_AROUND_WRAPPER,
        # Manager/Handler/Controller proliferation
        r"class \w+(Manager|Handler|Controller|Service)": ComplexitySignal.UNNECESSARY_ABSTRACTION,
    }

    # Function parameter count threshold
    MAX_PARAMS = 5

    # Nesting depth threshold
    MAX_NESTING = 4

    # Lines threshold for "this could be simpler"
    LINES_THRESHOLD = 200

    def __init__(self, use_llm: bool = True, model: str = "gemini-2.0-flash"):
        self.use_llm = use_llm
        self.model = model

    def validate(
        self,
        before_code: str,
        after_code: str,
        task_description: str
    ) -> SimplicityReport:
        """
        Compare before/after code and check for overcomplexity.

        Args:
            before_code: Code before changes
            after_code: Code after changes
            task_description: What the task was supposed to do

        Returns:
            SimplicityReport with findings
        """
        report = SimplicityReport()

        # Calculate line changes
        before_lines = before_code.split('\n') if before_code else []
        after_lines = after_code.split('\n') if after_code else []
        report.lines_added = len(after_lines) - len(before_lines) if len(after_lines) > len(before_lines) else sum(1 for line in after_lines if line.strip())
        report.lines_removed = len(before_lines) - len(after_lines) if len(before_lines) > len(after_lines) else 0
        report.net_lines = len(after_lines) - len(before_lines)

        # Extract new classes and functions
        report.new_classes = self._extract_new_definitions(before_code, after_code, r"class (\w+)")
        report.new_functions = self._extract_new_definitions(before_code, after_code, r"def (\w+)")

        # Check for complexity patterns
        self._check_patterns(after_code, report)

        # Check for excessive parameters
        self._check_parameters(after_code, report)

        # Check for deep nesting
        self._check_nesting(after_code, report)

        # Calculate complexity score
        report.complexity_score = self._calculate_complexity_score(report)

        # Check if simplification might be warranted
        if report.net_lines > self.LINES_THRESHOLD or len(report.new_classes) > 2:
            report.simplification_suggested = True
            report.suggested_approach = (
                f"Consider if {len(report.new_classes)} new classes are necessary. "
                f"Could this be done with ~{report.net_lines // 5} lines instead?"
            )

        # Use LLM for deeper analysis if enabled
        if self.use_llm and (report.net_lines > 100 or report.has_issues()):
            llm_analysis = self._analyze_with_llm(after_code, task_description, report)
            if llm_analysis:
                report.suggested_approach = llm_analysis

        return report

    def _extract_new_definitions(
        self,
        before: str,
        after: str,
        pattern: str
    ) -> List[str]:
        """Extract new class/function definitions."""
        before_matches = set(re.findall(pattern, before)) if before else set()
        after_matches = set(re.findall(pattern, after)) if after else set()
        return list(after_matches - before_matches)

    def _check_patterns(self, code: str, report: SimplicityReport) -> None:
        """Check for complexity anti-patterns."""
        for pattern, signal in self.COMPLEXITY_PATTERNS.items():
            matches = re.findall(pattern, code)
            for match in matches:
                # Get the class/function name
                name_match = re.search(r"class (\w+)|def (\w+)", match) if isinstance(match, str) else None
                name = match if isinstance(match, str) else (name_match.group(1) or name_match.group(2) if name_match else "unknown")

                report.issues.append(ComplexityIssue(
                    signal=signal,
                    description=f"Potential {signal.value.replace('_', ' ')}: {name}",
                    location=name,
                    severity="medium",
                    suggestion=self._get_suggestion_for_signal(signal),
                ))

    def _check_parameters(self, code: str, report: SimplicityReport) -> None:
        """Check for functions with too many parameters."""
        # Match function definitions with parameters
        func_pattern = r"def (\w+)\(([^)]*)\)"
        for match in re.finditer(func_pattern, code):
            func_name = match.group(1)
            params = match.group(2)
            # Count parameters (rough, doesn't handle all edge cases)
            param_count = len([p for p in params.split(',') if p.strip() and p.strip() != 'self'])

            if param_count > self.MAX_PARAMS:
                report.issues.append(ComplexityIssue(
                    signal=ComplexitySignal.EXCESSIVE_PARAMETERS,
                    description=f"Function '{func_name}' has {param_count} parameters (max recommended: {self.MAX_PARAMS})",
                    location=func_name,
                    severity="low",
                    suggestion="Consider using a dataclass or config object to group related parameters",
                ))

    def _check_nesting(self, code: str, report: SimplicityReport) -> None:
        """Check for deeply nested code."""
        lines = code.split('\n')
        for i, line in enumerate(lines):
            # Count leading spaces (rough nesting detection)
            stripped = line.lstrip()
            if stripped and not stripped.startswith('#'):
                indent = len(line) - len(stripped)
                nesting_level = indent // 4  # Assume 4-space indents

                if nesting_level > self.MAX_NESTING:
                    report.issues.append(ComplexityIssue(
                        signal=ComplexitySignal.DEEP_NESTING,
                        description=f"Deep nesting detected (level {nesting_level})",
                        location=f"line {i + 1}",
                        severity="medium",
                        suggestion="Consider extracting nested logic into separate functions",
                    ))
                    break  # Only report once

    def _calculate_complexity_score(self, report: SimplicityReport) -> float:
        """Calculate overall complexity score (0-1)."""
        score = 0.0

        # Lines factor
        if report.net_lines > 0:
            score += min(report.net_lines / 500, 0.3)  # Max 0.3 for lines

        # New abstractions factor
        score += len(report.new_classes) * 0.1  # 0.1 per new class
        score += len(report.new_functions) * 0.02  # 0.02 per new function

        # Issues factor
        severity_weights = {"low": 0.05, "medium": 0.1, "high": 0.2}
        for issue in report.issues:
            score += severity_weights.get(issue.severity, 0.1)

        return min(score, 1.0)

    def _get_suggestion_for_signal(self, signal: ComplexitySignal) -> str:
        """Get improvement suggestion for a complexity signal."""
        suggestions = {
            ComplexitySignal.FACTORY_FOR_SINGLE_IMPL: "If there's only one implementation, instantiate it directly",
            ComplexitySignal.PREMATURE_GENERALIZATION: "Start concrete, abstract only when you have 3+ similar implementations",
            ComplexitySignal.WRAPPER_AROUND_WRAPPER: "Check if the wrapper adds value or just passes through",
            ComplexitySignal.CONFIG_FOR_HARDCODED: "For single-use configs, consider simple constants or defaults",
            ComplexitySignal.UNNECESSARY_ABSTRACTION: "Ask: would removing this class make the code harder to understand?",
        }
        return suggestions.get(signal, "Consider if this complexity is necessary")

    def _analyze_with_llm(
        self,
        code: str,
        task: str,
        report: SimplicityReport
    ) -> Optional[str]:
        """Use LLM to suggest simplifications."""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm = ChatGoogleGenerativeAI(
                model=self.model,
                google_api_key=os.getenv("GEMINI_API_KEY"),
                temperature=0.3,
            )

            prompt = f"""Analyze this code change for unnecessary complexity.

Task that was requested: {task}

Code added ({report.net_lines} lines, {len(report.new_classes)} new classes):
```
{code[:3000]}  # Truncate for context limits
```

Current issues detected: {[i.description for i in report.issues]}

Question: Could this task be accomplished with significantly less code or fewer abstractions?

If yes, briefly describe the simpler approach (1-2 sentences).
If the complexity is justified, respond with "COMPLEXITY_JUSTIFIED: <reason>".

Response:"""

            response = llm.invoke(prompt)
            content = response.content.strip()

            if content.startswith("COMPLEXITY_JUSTIFIED"):
                return None

            return content

        except Exception as e:
            logger.warning(f"LLM simplicity analysis failed: {e}")
            return None


def validate_simplicity(
    before_code: str,
    after_code: str,
    task_description: str
) -> SimplicityReport:
    """Convenience function to validate code simplicity."""
    validator = SimplicityValidator()
    return validator.validate(before_code, after_code, task_description)

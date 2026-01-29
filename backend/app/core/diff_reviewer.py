"""
Diff Reviewer for Brain Trust / Legion

Reviews code changes to detect unintended side effects.

Based on Karpathy insight: "They still sometimes change/remove comments and code
they don't like or don't sufficiently understand as side effects, even if it is
orthogonal to the task at hand."
"""

import os
import re
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Set
from enum import Enum

logger = logging.getLogger(__name__)


class SideEffectType(str, Enum):
    """Types of unintended side effects."""
    REMOVED_COMMENT = "removed_comment"
    REMOVED_CODE = "removed_code"
    MODIFIED_UNRELATED_FILE = "modified_unrelated_file"
    CHANGED_FORMATTING = "changed_formatting"
    REMOVED_IMPORT = "removed_import"
    ADDED_UNUSED_CODE = "added_unused_code"
    CHANGED_UNRELATED_FUNCTION = "changed_unrelated_function"


@dataclass
class SideEffect:
    """A detected unintended side effect."""
    effect_type: SideEffectType
    description: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    original_content: Optional[str] = None
    can_revert: bool = True


@dataclass
class DiffReviewReport:
    """Report from diff review."""

    # Files analyzed
    files_changed: List[str] = field(default_factory=list)

    # Changes outside task scope
    unrelated_file_changes: List[str] = field(default_factory=list)

    # Detected side effects
    side_effects: List[SideEffect] = field(default_factory=list)

    # Specific categories
    removed_comments: List[SideEffect] = field(default_factory=list)
    removed_code: List[SideEffect] = field(default_factory=list)
    formatting_changes: List[SideEffect] = field(default_factory=list)

    # Recommendations
    suggested_reverts: List[str] = field(default_factory=list)

    # Summary
    has_concerning_changes: bool = False

    def has_issues(self) -> bool:
        return bool(
            self.unrelated_file_changes or
            self.removed_comments or
            self.removed_code or
            self.side_effects
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "files_changed": self.files_changed,
            "unrelated_file_changes": self.unrelated_file_changes,
            "side_effects": [
                {
                    "type": se.effect_type.value,
                    "description": se.description,
                    "file_path": se.file_path,
                    "line_number": se.line_number,
                    "can_revert": se.can_revert,
                }
                for se in self.side_effects
            ],
            "removed_comments_count": len(self.removed_comments),
            "removed_code_count": len(self.removed_code),
            "suggested_reverts": self.suggested_reverts,
            "has_concerning_changes": self.has_concerning_changes,
        }

    def format_for_user(self) -> str:
        """Format report for display to user."""
        if not self.has_issues():
            return "## Diff Review: No concerning side effects detected"

        lines = ["## Diff Review: Side Effects Detected"]

        if self.unrelated_file_changes:
            lines.append("")
            lines.append("### Unrelated Files Modified:")
            for f in self.unrelated_file_changes:
                lines.append(f"  - {f}")

        if self.removed_comments:
            lines.append("")
            lines.append(f"### Comments Removed ({len(self.removed_comments)}):")
            for se in self.removed_comments[:5]:  # Show first 5
                lines.append(f"  - {se.description}")
                if se.original_content:
                    lines.append(f"    Was: {se.original_content[:60]}...")
            if len(self.removed_comments) > 5:
                lines.append(f"  ... and {len(self.removed_comments) - 5} more")

        if self.removed_code:
            lines.append("")
            lines.append(f"### Code Removed ({len(self.removed_code)}):")
            for se in self.removed_code[:5]:
                lines.append(f"  - {se.description}")
            if len(self.removed_code) > 5:
                lines.append(f"  ... and {len(self.removed_code) - 5} more")

        if self.suggested_reverts:
            lines.append("")
            lines.append("### Suggested Reverts:")
            for revert in self.suggested_reverts:
                lines.append(f"  - {revert}")

        lines.append("")
        lines.append("Would you like to revert these side effects? [Yes] [No] [Review Each]")

        return "\n".join(lines)


class DiffReviewer:
    """
    Reviews diffs to detect unintended changes.

    Catches things agents shouldn't have changed:
    - Comments unrelated to the task
    - Code that was working fine
    - Files not mentioned in the task
    """

    def __init__(self, task_description: str, target_files: List[str] = None):
        """
        Initialize the diff reviewer.

        Args:
            task_description: What the task was supposed to accomplish
            target_files: Files that should have been changed (optional)
        """
        self.task_description = task_description
        self.target_files = set(target_files) if target_files else set()
        self._extract_task_keywords()

    def _extract_task_keywords(self) -> None:
        """Extract keywords from task description for relevance checking."""
        # Extract likely relevant terms from the task
        words = re.findall(r'\b\w+\b', self.task_description.lower())
        # Filter out common words
        stopwords = {'the', 'a', 'an', 'to', 'for', 'in', 'on', 'at', 'and', 'or', 'is', 'it', 'this', 'that'}
        self.task_keywords = set(w for w in words if w not in stopwords and len(w) > 2)

    def review_changes(
        self,
        file_changes: Dict[str, Dict[str, str]]
    ) -> DiffReviewReport:
        """
        Review a set of file changes for side effects.

        Args:
            file_changes: Dict of {filepath: {"before": str, "after": str}}

        Returns:
            DiffReviewReport with findings
        """
        report = DiffReviewReport()
        report.files_changed = list(file_changes.keys())

        for filepath, changes in file_changes.items():
            before = changes.get("before", "")
            after = changes.get("after", "")

            # Check if this file was expected to change
            if self.target_files and filepath not in self.target_files:
                if not self._is_file_related_to_task(filepath):
                    report.unrelated_file_changes.append(filepath)

            # Check for removed comments
            self._check_removed_comments(filepath, before, after, report)

            # Check for removed code
            self._check_removed_code(filepath, before, after, report)

            # Check for formatting-only changes
            self._check_formatting_changes(filepath, before, after, report)

        # Generate suggested reverts
        self._generate_revert_suggestions(report)

        # Determine if changes are concerning
        report.has_concerning_changes = (
            len(report.removed_comments) > 2 or
            len(report.removed_code) > 0 or
            len(report.unrelated_file_changes) > 0
        )

        return report

    def _is_file_related_to_task(self, filepath: str) -> bool:
        """Check if a file seems related to the task."""
        filepath_lower = filepath.lower()
        return any(keyword in filepath_lower for keyword in self.task_keywords)

    def _check_removed_comments(
        self,
        filepath: str,
        before: str,
        after: str,
        report: DiffReviewReport
    ) -> None:
        """Check for comments that were removed."""
        # Extract comments from before
        before_comments = self._extract_comments(before)
        after_comments = self._extract_comments(after)

        # Find removed comments
        removed = before_comments - after_comments

        for comment in removed:
            # Check if removal seems related to task
            comment_lower = comment.lower()
            is_related = any(kw in comment_lower for kw in self.task_keywords)

            if not is_related:
                effect = SideEffect(
                    effect_type=SideEffectType.REMOVED_COMMENT,
                    description=f"Comment removed from {filepath}",
                    file_path=filepath,
                    original_content=comment[:100],
                    can_revert=True,
                )
                report.removed_comments.append(effect)
                report.side_effects.append(effect)

    def _check_removed_code(
        self,
        filepath: str,
        before: str,
        after: str,
        report: DiffReviewReport
    ) -> None:
        """Check for functions/classes that were removed."""
        # Extract function/class definitions
        before_defs = self._extract_definitions(before)
        after_defs = self._extract_definitions(after)

        # Find removed definitions
        removed = before_defs - after_defs

        for definition in removed:
            # Check if removal seems related to task
            def_lower = definition.lower()
            is_related = any(kw in def_lower for kw in self.task_keywords)

            if not is_related:
                effect = SideEffect(
                    effect_type=SideEffectType.REMOVED_CODE,
                    description=f"Definition '{definition}' removed from {filepath}",
                    file_path=filepath,
                    original_content=definition,
                    can_revert=True,
                )
                report.removed_code.append(effect)
                report.side_effects.append(effect)

    def _check_formatting_changes(
        self,
        filepath: str,
        before: str,
        after: str,
        report: DiffReviewReport
    ) -> None:
        """Check for formatting-only changes (whitespace, line breaks)."""
        # Normalize whitespace and compare
        before_normalized = re.sub(r'\s+', ' ', before.strip())
        after_normalized = re.sub(r'\s+', ' ', after.strip())

        # If content is same but file changed, it's formatting only
        if before_normalized == after_normalized and before != after:
            effect = SideEffect(
                effect_type=SideEffectType.CHANGED_FORMATTING,
                description=f"Formatting-only changes in {filepath}",
                file_path=filepath,
                can_revert=True,
            )
            report.formatting_changes.append(effect)
            report.side_effects.append(effect)

    def _extract_comments(self, code: str) -> Set[str]:
        """Extract all comments from code."""
        comments = set()

        # Single-line comments (Python/JS style)
        for match in re.finditer(r'#\s*(.+?)$', code, re.MULTILINE):
            comments.add(match.group(1).strip())

        # Single-line comments (// style)
        for match in re.finditer(r'//\s*(.+?)$', code, re.MULTILINE):
            comments.add(match.group(1).strip())

        # Multi-line docstrings
        for match in re.finditer(r'"""(.+?)"""', code, re.DOTALL):
            comments.add(match.group(1).strip()[:100])  # Truncate long docstrings

        return comments

    def _extract_definitions(self, code: str) -> Set[str]:
        """Extract function and class definitions."""
        definitions = set()

        # Python functions
        for match in re.finditer(r'def\s+(\w+)\s*\(', code):
            definitions.add(f"def {match.group(1)}")

        # Python classes
        for match in re.finditer(r'class\s+(\w+)\s*[:\(]', code):
            definitions.add(f"class {match.group(1)}")

        # JS/TS functions
        for match in re.finditer(r'function\s+(\w+)\s*\(', code):
            definitions.add(f"function {match.group(1)}")

        return definitions

    def _generate_revert_suggestions(self, report: DiffReviewReport) -> None:
        """Generate suggestions for what to revert."""
        if report.unrelated_file_changes:
            report.suggested_reverts.append(
                f"Revert all changes to: {', '.join(report.unrelated_file_changes)}"
            )

        if len(report.removed_comments) > 2:
            report.suggested_reverts.append(
                f"Restore {len(report.removed_comments)} removed comments"
            )

        if report.removed_code:
            for se in report.removed_code:
                report.suggested_reverts.append(
                    f"Restore removed definition: {se.original_content}"
                )


def review_diff(
    task_description: str,
    file_changes: Dict[str, Dict[str, str]],
    target_files: List[str] = None
) -> DiffReviewReport:
    """Convenience function to review a diff."""
    reviewer = DiffReviewer(task_description, target_files)
    return reviewer.review_changes(file_changes)

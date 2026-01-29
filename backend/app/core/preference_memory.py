"""
Preference Memory for Brain Trust / Legion

Remembers what shipped, what was approved, and why — informing future decisions.

This system captures:
- Approved outputs and their characteristics
- Execution patterns that work vs. don't work
- User preferences and taste decisions
- Daily escalation summaries
"""

import uuid
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime, date
from pathlib import Path
import sqlite3

logger = logging.getLogger(__name__)


@dataclass
class ApprovedOutput:
    """Record of an approved/shipped output."""

    id: str
    project: str  # "life_with_ai", "coloring_book", etc.
    output_type: str  # "story", "code", "coloring_page"
    output_reference: Optional[str] = None  # Drive ID, GitHub commit, file path
    content_summary: Optional[str] = None  # Brief summary of content

    # Approval info
    approved_at: datetime = field(default_factory=datetime.now)
    approval_notes: Optional[str] = None
    approved_by: str = "user"

    # Execution context
    agents_involved: List[str] = field(default_factory=list)
    workflow_snapshot: Optional[Dict[str, Any]] = None
    execution_duration_seconds: float = 0.0

    # Quality signals
    quality_rating: Optional[int] = None  # 1-5 if rated
    revision_count: int = 0  # How many revisions before approval

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "project": self.project,
            "output_type": self.output_type,
            "output_reference": self.output_reference,
            "content_summary": self.content_summary,
            "approved_at": self.approved_at.isoformat(),
            "approval_notes": self.approval_notes,
            "approved_by": self.approved_by,
            "agents_involved": self.agents_involved,
            "workflow_snapshot": self.workflow_snapshot,
            "execution_duration_seconds": self.execution_duration_seconds,
            "quality_rating": self.quality_rating,
            "revision_count": self.revision_count,
        }


@dataclass
class ExecutionPattern:
    """A pattern of execution that has been observed to work (or not)."""

    id: str
    intent_category: str  # "create_story", "edit_chapter", "find_files"
    successful_approach: Dict[str, Any]  # The approach that worked

    # Metrics
    success_count: int = 1
    failure_count: int = 0

    # Learnings
    user_feedback: List[str] = field(default_factory=list)
    contraindications: List[str] = field(default_factory=list)  # When NOT to use

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    @property
    def success_rate(self) -> float:
        total = self.success_count + self.failure_count
        return self.success_count / total if total > 0 else 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "intent_category": self.intent_category,
            "successful_approach": self.successful_approach,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": self.success_rate,
            "user_feedback": self.user_feedback,
            "contraindications": self.contraindications,
        }


@dataclass
class DailyDigest:
    """Summary of a day's escalations and decisions."""

    id: str
    digest_date: date

    # Content
    escalation_requests: List[Dict[str, Any]] = field(default_factory=list)
    decisions_made: List[Dict[str, Any]] = field(default_factory=list)
    user_actions_needed: List[Dict[str, Any]] = field(default_factory=list)
    outputs_delivered: List[str] = field(default_factory=list)

    # Delivery
    delivered_at: Optional[datetime] = None
    delivery_channel: Optional[str] = None  # "discord", "email"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "digest_date": self.digest_date.isoformat(),
            "escalation_requests": self.escalation_requests,
            "decisions_made": self.decisions_made,
            "user_actions_needed": self.user_actions_needed,
            "outputs_delivered": self.outputs_delivered,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "delivery_channel": self.delivery_channel,
        }


class PreferenceMemory:
    """
    Preference Memory System.

    Stores and retrieves:
    - Approved outputs (what shipped)
    - Execution patterns (what approaches work)
    - Daily digests (escalation summaries)

    Used by Willow to make informed decisions based on past approvals.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, db_path: Optional[Path] = None):
        if self._initialized:
            return

        self.db_path = db_path or Path.home() / ".pai" / "preference_memory.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self._init_db()
        self._initialized = True

    def _init_db(self) -> None:
        """Initialize the SQLite database."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Approved outputs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS approved_outputs (
                id TEXT PRIMARY KEY,
                project TEXT NOT NULL,
                output_type TEXT NOT NULL,
                output_reference TEXT,
                content_summary TEXT,
                approved_at TEXT NOT NULL,
                approval_notes TEXT,
                approved_by TEXT DEFAULT 'user',
                agents_involved TEXT,
                workflow_snapshot TEXT,
                execution_duration_seconds REAL DEFAULT 0,
                quality_rating INTEGER,
                revision_count INTEGER DEFAULT 0
            )
        """)

        # Execution patterns table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS execution_patterns (
                id TEXT PRIMARY KEY,
                intent_category TEXT NOT NULL,
                successful_approach TEXT NOT NULL,
                success_count INTEGER DEFAULT 1,
                failure_count INTEGER DEFAULT 0,
                user_feedback TEXT,
                contraindications TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Daily digests table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_digests (
                id TEXT PRIMARY KEY,
                digest_date TEXT NOT NULL UNIQUE,
                escalation_requests TEXT,
                decisions_made TEXT,
                user_actions_needed TEXT,
                outputs_delivered TEXT,
                delivered_at TEXT,
                delivery_channel TEXT
            )
        """)

        conn.commit()
        conn.close()
        logger.info(f"Preference memory initialized at {self.db_path}")

    # Approved Outputs Methods

    def record_approval(
        self,
        project: str,
        output_type: str,
        output_reference: Optional[str] = None,
        content_summary: Optional[str] = None,
        approval_notes: Optional[str] = None,
        agents_involved: Optional[List[str]] = None,
        workflow_snapshot: Optional[Dict[str, Any]] = None,
        execution_duration_seconds: float = 0.0,
    ) -> ApprovedOutput:
        """Record a new approved output."""
        output = ApprovedOutput(
            id=str(uuid.uuid4())[:8],
            project=project,
            output_type=output_type,
            output_reference=output_reference,
            content_summary=content_summary,
            approval_notes=approval_notes,
            agents_involved=agents_involved or [],
            workflow_snapshot=workflow_snapshot,
            execution_duration_seconds=execution_duration_seconds,
        )

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO approved_outputs
            (id, project, output_type, output_reference, content_summary,
             approved_at, approval_notes, approved_by, agents_involved,
             workflow_snapshot, execution_duration_seconds, quality_rating, revision_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            output.id,
            output.project,
            output.output_type,
            output.output_reference,
            output.content_summary,
            output.approved_at.isoformat(),
            output.approval_notes,
            output.approved_by,
            json.dumps(output.agents_involved),
            json.dumps(output.workflow_snapshot) if output.workflow_snapshot else None,
            output.execution_duration_seconds,
            output.quality_rating,
            output.revision_count,
        ))

        conn.commit()
        conn.close()

        logger.info(f"Recorded approved output: {output.id} ({output.output_type})")
        return output

    def get_approvals_for_project(self, project: str, limit: int = 20) -> List[ApprovedOutput]:
        """Get recent approved outputs for a project."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM approved_outputs
            WHERE project = ?
            ORDER BY approved_at DESC
            LIMIT ?
        """, (project, limit))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_approved_output(row) for row in rows]

    def get_approvals_by_type(self, output_type: str, limit: int = 20) -> List[ApprovedOutput]:
        """Get recent approved outputs of a specific type."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM approved_outputs
            WHERE output_type = ?
            ORDER BY approved_at DESC
            LIMIT ?
        """, (output_type, limit))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_approved_output(row) for row in rows]

    def _row_to_approved_output(self, row: tuple) -> ApprovedOutput:
        """Convert a database row to ApprovedOutput."""
        return ApprovedOutput(
            id=row[0],
            project=row[1],
            output_type=row[2],
            output_reference=row[3],
            content_summary=row[4],
            approved_at=datetime.fromisoformat(row[5]),
            approval_notes=row[6],
            approved_by=row[7],
            agents_involved=json.loads(row[8]) if row[8] else [],
            workflow_snapshot=json.loads(row[9]) if row[9] else None,
            execution_duration_seconds=row[10] or 0.0,
            quality_rating=row[11],
            revision_count=row[12] or 0,
        )

    # Execution Patterns Methods

    def record_pattern(
        self,
        intent_category: str,
        approach: Dict[str, Any],
        success: bool,
        feedback: Optional[str] = None,
    ) -> ExecutionPattern:
        """Record or update an execution pattern."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        # Check if pattern exists for this intent/approach
        approach_json = json.dumps(approach, sort_keys=True)

        cursor.execute("""
            SELECT id, success_count, failure_count, user_feedback
            FROM execution_patterns
            WHERE intent_category = ? AND successful_approach = ?
        """, (intent_category, approach_json))

        existing = cursor.fetchone()

        if existing:
            # Update existing pattern
            pattern_id = existing[0]
            success_count = existing[1] + (1 if success else 0)
            failure_count = existing[2] + (0 if success else 1)
            user_feedback = json.loads(existing[3]) if existing[3] else []

            if feedback:
                user_feedback.append(feedback)

            cursor.execute("""
                UPDATE execution_patterns
                SET success_count = ?, failure_count = ?, user_feedback = ?,
                    updated_at = ?
                WHERE id = ?
            """, (
                success_count,
                failure_count,
                json.dumps(user_feedback),
                datetime.now().isoformat(),
                pattern_id,
            ))

            pattern = ExecutionPattern(
                id=pattern_id,
                intent_category=intent_category,
                successful_approach=approach,
                success_count=success_count,
                failure_count=failure_count,
                user_feedback=user_feedback,
            )
        else:
            # Create new pattern
            pattern = ExecutionPattern(
                id=str(uuid.uuid4())[:8],
                intent_category=intent_category,
                successful_approach=approach,
                success_count=1 if success else 0,
                failure_count=0 if success else 1,
                user_feedback=[feedback] if feedback else [],
            )

            cursor.execute("""
                INSERT INTO execution_patterns
                (id, intent_category, successful_approach, success_count, failure_count,
                 user_feedback, contraindications, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pattern.id,
                pattern.intent_category,
                approach_json,
                pattern.success_count,
                pattern.failure_count,
                json.dumps(pattern.user_feedback),
                json.dumps(pattern.contraindications),
                pattern.created_at.isoformat(),
                pattern.updated_at.isoformat(),
            ))

        conn.commit()
        conn.close()

        return pattern

    def get_patterns_for_intent(self, intent_category: str) -> List[ExecutionPattern]:
        """Get execution patterns for an intent category."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM execution_patterns
            WHERE intent_category = ?
            ORDER BY success_count DESC
        """, (intent_category,))

        rows = cursor.fetchall()
        conn.close()

        return [self._row_to_pattern(row) for row in rows]

    def get_best_pattern(self, intent_category: str) -> Optional[ExecutionPattern]:
        """Get the most successful pattern for an intent."""
        patterns = self.get_patterns_for_intent(intent_category)
        if not patterns:
            return None

        # Sort by success rate, then by total executions
        patterns.sort(
            key=lambda p: (p.success_rate, p.success_count + p.failure_count),
            reverse=True,
        )
        return patterns[0] if patterns[0].success_rate > 0.5 else None

    def _row_to_pattern(self, row: tuple) -> ExecutionPattern:
        """Convert a database row to ExecutionPattern."""
        return ExecutionPattern(
            id=row[0],
            intent_category=row[1],
            successful_approach=json.loads(row[2]),
            success_count=row[3],
            failure_count=row[4],
            user_feedback=json.loads(row[5]) if row[5] else [],
            contraindications=json.loads(row[6]) if row[6] else [],
            created_at=datetime.fromisoformat(row[7]),
            updated_at=datetime.fromisoformat(row[8]),
        )

    # Daily Digest Methods

    def create_or_update_digest(
        self,
        digest_date: Optional[date] = None,
        escalation: Optional[Dict[str, Any]] = None,
        decision: Optional[Dict[str, Any]] = None,
        action_needed: Optional[Dict[str, Any]] = None,
        output_delivered: Optional[str] = None,
    ) -> DailyDigest:
        """Create or update today's digest."""
        digest_date = digest_date or date.today()

        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM daily_digests WHERE digest_date = ?
        """, (digest_date.isoformat(),))

        existing = cursor.fetchone()

        if existing:
            digest = self._row_to_digest(existing)
        else:
            digest = DailyDigest(
                id=str(uuid.uuid4())[:8],
                digest_date=digest_date,
            )

        # Add new items
        if escalation:
            digest.escalation_requests.append(escalation)
        if decision:
            digest.decisions_made.append(decision)
        if action_needed:
            digest.user_actions_needed.append(action_needed)
        if output_delivered:
            digest.outputs_delivered.append(output_delivered)

        # Save
        cursor.execute("""
            INSERT OR REPLACE INTO daily_digests
            (id, digest_date, escalation_requests, decisions_made,
             user_actions_needed, outputs_delivered, delivered_at, delivery_channel)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            digest.id,
            digest.digest_date.isoformat(),
            json.dumps(digest.escalation_requests),
            json.dumps(digest.decisions_made),
            json.dumps(digest.user_actions_needed),
            json.dumps(digest.outputs_delivered),
            digest.delivered_at.isoformat() if digest.delivered_at else None,
            digest.delivery_channel,
        ))

        conn.commit()
        conn.close()

        return digest

    def get_digest(self, digest_date: date) -> Optional[DailyDigest]:
        """Get digest for a specific date."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            SELECT * FROM daily_digests WHERE digest_date = ?
        """, (digest_date.isoformat(),))

        row = cursor.fetchone()
        conn.close()

        return self._row_to_digest(row) if row else None

    def mark_digest_delivered(
        self,
        digest_date: date,
        channel: str = "discord"
    ) -> bool:
        """Mark a digest as delivered."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE daily_digests
            SET delivered_at = ?, delivery_channel = ?
            WHERE digest_date = ?
        """, (datetime.now().isoformat(), channel, digest_date.isoformat()))

        conn.commit()
        affected = cursor.rowcount
        conn.close()

        return affected > 0

    def _row_to_digest(self, row: tuple) -> DailyDigest:
        """Convert a database row to DailyDigest."""
        return DailyDigest(
            id=row[0],
            digest_date=date.fromisoformat(row[1]),
            escalation_requests=json.loads(row[2]) if row[2] else [],
            decisions_made=json.loads(row[3]) if row[3] else [],
            user_actions_needed=json.loads(row[4]) if row[4] else [],
            outputs_delivered=json.loads(row[5]) if row[5] else [],
            delivered_at=datetime.fromisoformat(row[6]) if row[6] else None,
            delivery_channel=row[7],
        )

    # Context Generation for Willow

    def get_preference_context(self, project: Optional[str] = None) -> str:
        """Generate context string about preferences for Willow."""
        lines = ["# Preference Memory Context\n"]

        # Recent approvals
        if project:
            approvals = self.get_approvals_for_project(project, limit=5)
            lines.append(f"\n## Recent Approvals for {project}")
        else:
            # Get from all projects
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM approved_outputs
                ORDER BY approved_at DESC
                LIMIT 5
            """)
            rows = cursor.fetchall()
            conn.close()
            approvals = [self._row_to_approved_output(row) for row in rows]
            lines.append("\n## Recent Approvals")

        for approval in approvals:
            lines.append(f"- [{approval.output_type}] {approval.content_summary or 'No summary'}")
            if approval.approval_notes:
                lines.append(f"  Note: {approval.approval_notes}")

        # Successful patterns
        lines.append("\n## Successful Patterns")
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM execution_patterns
            WHERE success_count > failure_count
            ORDER BY success_count DESC
            LIMIT 5
        """)
        rows = cursor.fetchall()
        conn.close()

        patterns = [self._row_to_pattern(row) for row in rows]
        for pattern in patterns:
            lines.append(
                f"- {pattern.intent_category}: {pattern.success_rate:.0%} success "
                f"({pattern.success_count} successes)"
            )

        return "\n".join(lines)


def get_preference_memory() -> PreferenceMemory:
    """Get the singleton preference memory instance."""
    return PreferenceMemory()

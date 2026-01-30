"""
Plan Proposer for Brain Trust / Legion

Generates execution plans from parsed intents.
Works with Willow to propose how to accomplish the user's goals.
"""

import os
import json
import uuid
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

from .intent_parser import ParsedIntent, IntentType, ProjectScope
from .capability_registry import get_capability_registry, Capability

logger = logging.getLogger(__name__)


class PlanStatus(str, Enum):
    """Status of a plan."""
    DRAFT = "draft"
    PROPOSED = "proposed"
    APPROVED = "approved"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PlanStep:
    """
    A single step in an execution plan.

    Each step is assigned to an agent with specific instructions.
    """

    id: str
    order: int
    description: str
    agent_role: str
    capability_id: Optional[str] = None
    agent_id: Optional[str] = None  # Specific agent config key (e.g., "line_editor")

    # Dependencies
    depends_on: List[str] = field(default_factory=list)  # Step IDs

    # Execution
    status: str = "pending"  # pending, in_progress, completed, failed
    output: Optional[str] = None
    error: Optional[str] = None

    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "order": self.order,
            "description": self.description,
            "agent_role": self.agent_role,
            "capability_id": self.capability_id,
            "agent_id": self.agent_id,
            "depends_on": self.depends_on,
            "status": self.status,
            "output": self.output,
            "error": self.error,
        }


@dataclass
class ExecutionPlan:
    """
    A complete execution plan for accomplishing user intent.

    This is what Willow proposes to the user for approval.
    """

    id: str
    intent_summary: str
    project: ProjectScope

    # Steps
    steps: List[PlanStep] = field(default_factory=list)

    # Status
    status: PlanStatus = PlanStatus.DRAFT

    # Context
    context_files: List[str] = field(default_factory=list)  # Files to load
    constraints: List[str] = field(default_factory=list)

    # Timing
    created_at: datetime = field(default_factory=datetime.now)
    approved_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # User interaction
    requires_approval: bool = True
    approval_notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "intent_summary": self.intent_summary,
            "project": self.project.value,
            "steps": [s.to_dict() for s in self.steps],
            "status": self.status.value,
            "context_files": self.context_files,
            "constraints": self.constraints,
            "created_at": self.created_at.isoformat(),
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "requires_approval": self.requires_approval,
        }

    def to_display_string(self) -> str:
        """Generate a human-readable plan summary."""
        lines = [
            f"# Execution Plan: {self.intent_summary}",
            f"Project: {self.project.value}",
            f"Status: {self.status.value}",
            "",
            "## Steps:",
        ]

        for step in self.steps:
            # Use ASCII-safe status indicators for Windows compatibility
            import sys
            if sys.platform == "win32":
                status_emoji = {
                    "pending": "[...]",
                    "in_progress": "[>>]",
                    "completed": "[OK]",
                    "failed": "[ERR]",
                }.get(step.status, "[...]")
            else:
                status_emoji = {
                    "pending": "⏳",
                    "in_progress": "🔄",
                    "completed": "✅",
                    "failed": "❌",
                }.get(step.status, "⏳")

            deps = ""
            if step.depends_on:
                deps = f" (after step {', '.join(step.depends_on)})"

            lines.append(f"{status_emoji} {step.order}. [{step.agent_role}] {step.description}{deps}")

        if self.constraints:
            lines.append("")
            lines.append(f"Constraints: {', '.join(self.constraints)}")

        return "\n".join(lines)


class PlanProposer:
    """
    Generates execution plans from parsed intents.

    Uses:
    - Capability registry to find appropriate agents
    - Intent context to determine order of operations
    - LLM for complex plan generation
    """

    def __init__(self, use_llm: bool = True, model: str = "gemini-2.0-flash"):
        self.use_llm = use_llm
        self.model = model
        self.registry = get_capability_registry()

    def propose(self, intent: ParsedIntent) -> ExecutionPlan:
        """
        Generate an execution plan for the given intent.

        Args:
            intent: Parsed user intent

        Returns:
            ExecutionPlan ready for approval
        """
        plan_id = str(uuid.uuid4())[:8]

        # Try LLM-based planning for complex intents
        if self.use_llm and intent.intent_type not in [IntentType.STATUS, IntentType.APPROVE]:
            try:
                plan = self._plan_with_llm(intent, plan_id)
                if plan:
                    return plan
            except Exception as e:
                logger.warning(f"LLM planning failed: {e}")

        # Fallback to template-based planning
        return self._plan_with_templates(intent, plan_id)

    def _plan_with_templates(self, intent: ParsedIntent, plan_id: str) -> ExecutionPlan:
        """
        Generate plan using predefined templates.

        PRINCIPLE: Do LESS not MORE.
        - FIND/STATUS: ONLY Librarian, no additional agents
        - Don't auto-add review steps unless explicitly requested
        - Single agent for simple tasks
        """

        steps = []
        step_order = 1

        # FIND and STATUS: ONLY Librarian, nothing else
        if intent.intent_type in [IntentType.FIND, IntentType.STATUS]:
            steps.append(PlanStep(
                id=f"step-{step_order}",
                order=step_order,
                description=f"{'Find' if intent.intent_type == IntentType.FIND else 'Check status'}: {intent.summary}",
                agent_role="Librarian",
                capability_id="find-drive-files",
            ))
            # Return immediately - no additional steps for find/status
            return ExecutionPlan(
                id=plan_id,
                intent_summary=intent.summary,
                project=intent.project,
                steps=steps,
                status=PlanStatus.PROPOSED,
                context_files=intent.context_needed,
                constraints=intent.constraints,
            )

        # For other intents, add context gathering only if explicitly needed
        if intent.context_needed:
            steps.append(PlanStep(
                id=f"step-{step_order}",
                order=step_order,
                description=f"Gather context: {', '.join(intent.context_needed)}",
                agent_role="Librarian",
                capability_id="find-drive-files",
            ))
            step_order += 1

        # Intent-specific steps - minimal agents
        if intent.intent_type == IntentType.CREATE:
            steps.append(PlanStep(
                id=f"step-{step_order}",
                order=step_order,
                description=f"Create content: {intent.summary}",
                agent_role="Writer",
                capability_id="write-short-fiction",
                depends_on=[s.id for s in steps],
            ))
            # NOTE: Removed auto-add of Editor review step
            # Only add review if user explicitly requests it

        elif intent.intent_type == IntentType.EDIT:
            steps.append(PlanStep(
                id=f"step-{step_order}",
                order=step_order,
                description=f"Edit content: {intent.summary}",
                agent_role="Editor",
                capability_id="edit-prose",
                depends_on=[s.id for s in steps],
            ))

        elif intent.intent_type == IntentType.REVIEW:
            steps.append(PlanStep(
                id=f"step-{step_order}",
                order=step_order,
                description=f"Review: {intent.summary}",
                agent_role="Editor",
                capability_id="review-consistency",
                depends_on=[s.id for s in steps],
            ))

        elif intent.intent_type == IntentType.ORGANIZE:
            steps.append(PlanStep(
                id=f"step-{step_order}",
                order=step_order,
                description=f"Organize: {intent.summary}",
                agent_role="Librarian",
                capability_id="find-drive-files",
            ))

        elif intent.intent_type == IntentType.ANALYZE:
            steps.append(PlanStep(
                id=f"step-{step_order}",
                order=step_order,
                description=f"Analyze: {intent.summary}",
                agent_role="Researcher",
                depends_on=[s.id for s in steps],
            ))

        # Default if no steps generated - use first suggested agent
        if not steps:
            steps.append(PlanStep(
                id="step-1",
                order=1,
                description=intent.summary,
                agent_role=intent.suggested_agents[0] if intent.suggested_agents else "Librarian",
            ))

        return ExecutionPlan(
            id=plan_id,
            intent_summary=intent.summary,
            project=intent.project,
            steps=steps,
            status=PlanStatus.PROPOSED,
            context_files=intent.context_needed,
            constraints=intent.constraints,
        )

    def _plan_with_llm(self, intent: ParsedIntent, plan_id: str) -> Optional[ExecutionPlan]:
        """Generate plan using LLM for complex reasoning."""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm = ChatGoogleGenerativeAI(
                model=self.model,
                google_api_key=os.getenv("GEMINI_API_KEY"),
                temperature=0.3,
            )

            # Get capability context
            capability_context = self.registry.to_context_string()

            prompt = f"""You are planning an execution for a creative AI team (the Legion).

User Intent:
- Type: {intent.intent_type.value}
- Summary: {intent.summary}
- Project: {intent.project.value}
- Target: {intent.target_artifact or 'Not specified'}
- Constraints: {', '.join(intent.constraints) or 'None'}

{capability_context}

PLANNING RULES:
1. If user EXPLICITLY mentions multiple agents (Librarian, Writer, Editor), include ALL of them in the plan.
2. For simple "find" or "status" queries with no other work: Use only Librarian.
3. For creative workflows (write + edit): Include the full pipeline the user requests.
4. Each step should do ONE thing. Chain steps with depends_on for sequential work.
5. Librarian gathers context/creates files FIRST, then Writer drafts, then Editor polishes.

Available roles: Librarian (file ops, search, create docs), Writer (creative drafting), Editor (review/polish), Developer (code), Artist (visuals)

Respond with JSON only:
{{
    "steps": [
        {{
            "order": 1,
            "description": "<what this step does>",
            "agent_role": "<role name>",
            "depends_on": []
        }}
    ],
    "context_files": [],
    "requires_approval": true
}}

Match the complexity of the plan to what the user asked for. Output only valid JSON."""

            response = llm.invoke(prompt)
            content = response.content.strip()

            # Parse JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            data = json.loads(content.strip())

            # Convert to ExecutionPlan
            steps = []
            for step_data in data.get("steps", []):
                step_id = f"step-{step_data['order']}"
                depends_on = [f"step-{d}" for d in step_data.get("depends_on", [])]

                steps.append(PlanStep(
                    id=step_id,
                    order=step_data["order"],
                    description=step_data["description"],
                    agent_role=step_data["agent_role"],
                    depends_on=depends_on,
                ))

            return ExecutionPlan(
                id=plan_id,
                intent_summary=intent.summary,
                project=intent.project,
                steps=steps,
                status=PlanStatus.PROPOSED,
                context_files=data.get("context_files", []),
                constraints=intent.constraints,
                requires_approval=data.get("requires_approval", True),
            )

        except Exception as e:
            logger.error(f"LLM plan generation failed: {e}")
            return None


def propose_plan(intent: ParsedIntent) -> ExecutionPlan:
    """Convenience function to generate a plan."""
    proposer = PlanProposer()
    return proposer.propose(intent)

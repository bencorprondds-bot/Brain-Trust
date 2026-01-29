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

from .intent_parser import ParsedIntent, IntentType, ProjectScope, Assumption
from .capability_registry import get_capability_registry, Capability

logger = logging.getLogger(__name__)


class VerificationMethod(str, Enum):
    """How to verify success criteria."""
    TEST = "test"              # Run automated tests
    LLM_JUDGE = "llm_judge"    # Use LLM to evaluate
    USER_APPROVAL = "user_approval"  # Requires human sign-off
    METRIC = "metric"          # Check a measurable value
    FILE_EXISTS = "file_exists"  # Verify output file exists


@dataclass
class SuccessCriteria:
    """
    Defines what "done" looks like for a plan.

    Based on Karpathy insight: "Give success criteria, not step-by-step instructions"
    """

    id: str
    description: str
    verification_method: VerificationMethod

    # For test-based verification
    test_command: Optional[str] = None

    # For metric-based verification
    target_metric: Optional[float] = None
    metric_name: Optional[str] = None

    # For LLM judge verification
    judge_prompt: Optional[str] = None

    # Status
    verified: bool = False
    verification_result: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "verification_method": self.verification_method.value,
            "test_command": self.test_command,
            "target_metric": self.target_metric,
            "metric_name": self.metric_name,
            "judge_prompt": self.judge_prompt,
            "verified": self.verified,
            "verification_result": self.verification_result,
        }


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

    # Success criteria (Karpathy insight: declarative goals, not just steps)
    success_criteria: List[SuccessCriteria] = field(default_factory=list)
    max_iterations: int = 5  # How many times to loop before giving up
    allow_self_correction: bool = True  # Let agent retry on failure

    # Assumptions carried from intent parsing
    assumptions: List[Assumption] = field(default_factory=list)

    # Pushback/concerns (Karpathy insight: agents should push back)
    concerns: List[str] = field(default_factory=list)
    alternative_suggestions: List[str] = field(default_factory=list)
    disagrees_with_approach: bool = False
    disagreement_reason: Optional[str] = None
    recommended_alternative: Optional[str] = None

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
            "success_criteria": [sc.to_dict() for sc in self.success_criteria],
            "max_iterations": self.max_iterations,
            "allow_self_correction": self.allow_self_correction,
            "assumptions": [
                {"description": a.description, "confidence": a.confidence, "category": a.category}
                for a in self.assumptions
            ],
            "concerns": self.concerns,
            "alternative_suggestions": self.alternative_suggestions,
            "disagrees_with_approach": self.disagrees_with_approach,
            "disagreement_reason": self.disagreement_reason,
            "recommended_alternative": self.recommended_alternative,
        }

    def to_display_string(self, use_ascii: bool = False) -> str:
        """Generate a human-readable plan summary."""
        # Use ASCII indicators for Windows compatibility
        if use_ascii:
            status_indicators = {
                "pending": "[ ]",
                "in_progress": "[~]",
                "completed": "[x]",
                "failed": "[!]",
            }
        else:
            status_indicators = {
                "pending": "[ ]",
                "in_progress": "[~]",
                "completed": "[x]",
                "failed": "[!]",
            }

        lines = [
            f"# Execution Plan: {self.intent_summary}",
            f"Project: {self.project.value}",
            f"Status: {self.status.value}",
        ]

        # Show concerns/pushback if any (Karpathy insight: agents should push back)
        if self.concerns or self.disagrees_with_approach:
            lines.append("")
            lines.append("## Concerns:")
            if self.disagrees_with_approach:
                lines.append(f"  WARNING: {self.disagreement_reason}")
                if self.recommended_alternative:
                    lines.append(f"  Recommended: {self.recommended_alternative}")
            for concern in self.concerns:
                lines.append(f"  - {concern}")

        # Show assumptions if any
        if self.assumptions:
            lines.append("")
            lines.append("## Assumptions:")
            for a in self.assumptions:
                confidence_label = "High" if a.confidence >= 0.8 else "Med" if a.confidence >= 0.5 else "Low"
                lines.append(f"  [{confidence_label}] {a.description}")

        # Show success criteria (Karpathy insight: declarative goals)
        if self.success_criteria:
            lines.append("")
            lines.append("## Success Criteria:")
            for sc in self.success_criteria:
                verified = "[x]" if sc.verified else "[ ]"
                lines.append(f"  {verified} {sc.description}")
                if sc.test_command:
                    lines.append(f"      Verify: {sc.test_command}")
            lines.append(f"  (Will iterate up to {self.max_iterations} times until criteria met)")

        # Show steps
        lines.append("")
        lines.append("## Steps:")
        for step in self.steps:
            indicator = status_indicators.get(step.status, "[ ]")
            deps = ""
            if step.depends_on:
                deps = f" (after {', '.join(step.depends_on)})"
            lines.append(f"  {indicator} {step.order}. [{step.agent_role}] {step.description}{deps}")

        if self.constraints:
            lines.append("")
            lines.append(f"Constraints: {', '.join(self.constraints)}")

        # Show alternatives if suggested
        if self.alternative_suggestions:
            lines.append("")
            lines.append("## Alternatives Considered:")
            for alt in self.alternative_suggestions:
                lines.append(f"  - {alt}")

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
        """Generate plan using predefined templates."""

        steps = []
        step_order = 1

        # Common pattern: if we need context, start with Librarian
        if intent.context_needed or intent.intent_type == IntentType.FIND:
            steps.append(PlanStep(
                id=f"step-{step_order}",
                order=step_order,
                description=f"Gather context: {', '.join(intent.context_needed) or 'relevant files'}",
                agent_role="Librarian",
                capability_id="find-drive-files",
            ))
            step_order += 1

        # Intent-specific steps
        if intent.intent_type == IntentType.CREATE:
            steps.append(PlanStep(
                id=f"step-{step_order}",
                order=step_order,
                description=f"Create content: {intent.summary}",
                agent_role="Writer",
                capability_id="write-short-fiction",
                depends_on=[s.id for s in steps],
            ))
            step_order += 1

            # Add review step
            steps.append(PlanStep(
                id=f"step-{step_order}",
                order=step_order,
                description="Review and polish the created content",
                agent_role="Editor",
                capability_id="edit-prose",
                depends_on=[f"step-{step_order - 1}"],
            ))

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

        elif intent.intent_type == IntentType.FIND:
            if not steps:  # If we didn't already add Librarian
                steps.append(PlanStep(
                    id=f"step-{step_order}",
                    order=step_order,
                    description=f"Find: {intent.summary}",
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

        # Default if no steps generated
        if not steps:
            steps.append(PlanStep(
                id="step-1",
                order=1,
                description=intent.summary,
                agent_role=intent.suggested_agents[0] if intent.suggested_agents else "Writer",
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

Create an execution plan with ordered steps. Each step should be assigned to ONE agent.
Available roles: Librarian (file ops), Writer (creative), Editor (review/polish), Developer (code), Artist (visuals)

Respond with JSON only:
{{
    "steps": [
        {{
            "order": 1,
            "description": "<what this step does>",
            "agent_role": "<role name>",
            "depends_on": []
        }},
        {{
            "order": 2,
            "description": "<what this step does>",
            "agent_role": "<role name>",
            "depends_on": [1]
        }}
    ],
    "context_files": ["<files to load>"],
    "requires_approval": true
}}

Keep plans focused: 2-4 steps typically. Output only valid JSON."""

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

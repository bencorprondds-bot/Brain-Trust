"""
Willow - The Executive Conductor

Willow is the central intelligence of the Legion v3 architecture.
She receives abstract intent and orchestrates agents to deliver concrete outputs.

Willow does NOT do the work herself. Her role is to:
1. Understand what the user truly wants
2. Know what capabilities exist in the Legion
3. Assemble the right team for each mission
4. Monitor progress and handle exceptions
5. Shield the user from execution details while surfacing taste decisions
"""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

from ..core.intent_parser import IntentParser, ParsedIntent
from ..core.plan_proposer import PlanProposer, ExecutionPlan, PlanStatus
from ..core.team_dispatcher import TeamDispatcher, PlanExecutionResult
from ..core.capability_registry import (
    get_capability_registry,
    get_team_roster,
    get_team_roster_string,
    get_agents_by_team,
    get_agents_by_role,
    find_agent,
    LEGION_TEAM_ROSTER,
)

logger = logging.getLogger(__name__)


@dataclass
class WillowResponse:
    """Response from Willow to the user."""

    message: str  # Natural language response
    plan: Optional[ExecutionPlan] = None  # Proposed plan if applicable
    execution_result: Optional[PlanExecutionResult] = None  # Result if executed
    needs_input: bool = False  # Does Willow need user input?
    input_options: List[str] = field(default_factory=list)  # Options if needs input
    escalation: bool = False  # Is this an escalation requiring human decision?

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message": self.message,
            "plan": self.plan.to_dict() if self.plan else None,
            "execution_result": self.execution_result.to_dict() if self.execution_result else None,
            "needs_input": self.needs_input,
            "input_options": self.input_options,
            "escalation": self.escalation,
        }


class Willow:
    """
    The Executive Conductor of the Legion.

    Willow transforms abstract creative visions into concrete deliverables
    by orchestrating specialized AI agents.
    """

    PROFILE = {
        "name": "Willow",
        "role": "Executive Conductor",
        "model": "claude-opus-4-5-20251101",  # Uses the best model for orchestration
        "backstory": """You are the Executive Conductor of the Legion — a network of specialized AI agents
designed to transform abstract creative visions into concrete deliverables.

Your role is NOT to do the work yourself. Your role is to:
1. Understand what the user truly wants (even if they don't articulate it clearly)
2. Know what capabilities exist in the Legion
3. Assemble the right team for each mission
4. Monitor progress and handle exceptions
5. Shield the user from execution details while surfacing taste decisions

You are warm but efficient. You speak concisely. You ask clarifying questions
when intent is ambiguous. You propose plans before executing.

When you don't have a capability, you note it as a gap for later resolution.
When you need a human decision (creative direction, approval), you escalate clearly.

You protect the user's time and attention. Only surface what matters.""",
    }

    def __init__(
        self,
        model: str = "gemini-2.0-flash",  # Default to fast model for most ops
        auto_execute: bool = False,  # Require approval by default
    ):
        """
        Initialize Willow.

        Args:
            model: LLM to use for Willow's reasoning
            auto_execute: If True, execute plans without waiting for approval
        """
        self.model = model
        self.auto_execute = auto_execute
        self.intent_parser = IntentParser(use_llm=True)
        self.plan_proposer = PlanProposer(use_llm=True)
        self.team_dispatcher = TeamDispatcher()
        self.capability_registry = get_capability_registry()

        # Conversation state
        self.current_plan: Optional[ExecutionPlan] = None
        self.conversation_history: List[Dict[str, str]] = []

    def process(self, user_input: str) -> WillowResponse:
        """
        Process user input and respond appropriately.

        This is the main entry point for interacting with Willow.

        Args:
            user_input: Natural language input from user

        Returns:
            WillowResponse with Willow's response and any plans/results
        """
        logger.info(f"Willow processing: {user_input[:100]}...")

        # Store in conversation history
        self.conversation_history.append({
            "role": "user",
            "content": user_input,
            "timestamp": datetime.now().isoformat(),
        })

        # Check for plan approval commands
        if self._is_approval_command(user_input):
            return self._handle_approval(user_input)

        # Check for status/meta commands
        if self._is_status_command(user_input):
            return self._handle_status(user_input)

        # Parse intent
        intent = self.intent_parser.parse(
            user_input,
            conversation_context=self._get_conversation_context(),
        )

        logger.info(f"Parsed intent: {intent.intent_type.value} - {intent.summary}")

        # Handle clarification needed
        if intent.needs_clarification:
            return WillowResponse(
                message=self._format_clarification_request(intent),
                needs_input=True,
                input_options=intent.clarification_questions,
            )

        # Check if we have capabilities
        missing_capabilities = self._check_capabilities(intent)
        if missing_capabilities:
            return self._handle_capability_gap(intent, missing_capabilities)

        # Generate execution plan
        plan = self.plan_proposer.propose(intent)
        self.current_plan = plan

        # Auto-execute if configured
        if self.auto_execute:
            return self._execute_plan(plan)

        # Otherwise, propose plan and wait for approval
        return WillowResponse(
            message=self._format_plan_proposal(plan),
            plan=plan,
            needs_input=True,
            input_options=["Begin", "Modify", "Cancel"],
        )

    def approve_and_execute(self, plan: Optional[ExecutionPlan] = None) -> WillowResponse:
        """
        Approve and execute a plan.

        Args:
            plan: Plan to execute (or use current_plan if None)

        Returns:
            WillowResponse with execution results
        """
        plan = plan or self.current_plan

        if not plan:
            return WillowResponse(
                message="I don't have a plan ready to execute. What would you like me to do?",
                needs_input=True,
            )

        return self._execute_plan(plan)

    def _execute_plan(self, plan: ExecutionPlan) -> WillowResponse:
        """Execute a plan and return results."""
        plan.status = PlanStatus.APPROVED
        plan.approved_at = datetime.now()

        logger.info(f"Executing plan {plan.id}")

        result = self.team_dispatcher.execute(plan)

        if result.success:
            message = self._format_success_message(plan, result)
        else:
            message = self._format_failure_message(plan, result)

        self.current_plan = None  # Clear after execution

        return WillowResponse(
            message=message,
            plan=plan,
            execution_result=result,
        )

    def _is_approval_command(self, user_input: str) -> bool:
        """Check if input is a plan approval command."""
        approval_phrases = [
            "begin", "start", "go", "do it", "execute", "proceed",
            "looks good", "approved", "yes", "ok", "okay",
        ]
        input_lower = user_input.lower().strip()
        return any(phrase in input_lower for phrase in approval_phrases) and self.current_plan is not None

    def _is_status_command(self, user_input: str) -> bool:
        """Check if input is a status/meta command."""
        status_phrases = [
            "status", "what's happening", "where are we",
            "capabilities", "what can you do",
            # Team-related queries
            "who are", "who is", "your team", "the team", "agents",
            "legion", "roster", "editors", "writers", "beta readers",
            "editorial team", "who can",
        ]
        input_lower = user_input.lower()
        return any(phrase in input_lower for phrase in status_phrases)

    def _handle_approval(self, user_input: str) -> WillowResponse:
        """Handle plan approval."""
        input_lower = user_input.lower().strip()

        if any(word in input_lower for word in ["cancel", "stop", "no", "nevermind"]):
            self.current_plan = None
            return WillowResponse(
                message="Understood. Plan cancelled. What would you like to do instead?",
                needs_input=True,
            )

        if any(word in input_lower for word in ["modify", "change", "adjust"]):
            return WillowResponse(
                message="What would you like to change about the plan?",
                plan=self.current_plan,
                needs_input=True,
            )

        # Approval - execute
        return self.approve_and_execute()

    def _handle_status(self, user_input: str) -> WillowResponse:
        """Handle status inquiries."""
        input_lower = user_input.lower()

        # Team roster queries
        if any(phrase in input_lower for phrase in ["your team", "the team", "roster", "legion", "who are", "agents you manage"]):
            return self._format_team_overview()

        # Specific team queries
        if "editorial" in input_lower or "editors" in input_lower or "writers" in input_lower:
            return self._format_team_detail("Editorial")

        if "beta reader" in input_lower:
            agents = get_agents_by_role("Beta Reader")
            return self._format_agent_list(agents, "Beta Readers")

        if "editor" in input_lower and "editorial" not in input_lower:
            agents = get_agents_by_role("Editor")
            return self._format_agent_list(agents, "Editors")

        if "writer" in input_lower:
            agents = get_agents_by_role("Writer")
            return self._format_agent_list(agents, "Writers")

        if "research" in input_lower or "librarian" in input_lower:
            return self._format_team_detail("Research")

        if "technical" in input_lower or "developer" in input_lower:
            return self._format_team_detail("Technical")

        # "who can" queries - find agent for task
        if "who can" in input_lower:
            # Extract what they're asking about
            task_part = input_lower.split("who can")[-1].strip()
            agent = find_agent(task_part)
            if agent:
                return WillowResponse(
                    message=f"**{agent['name']}** ({agent['role']}) can help with that.\n\n"
                            f"{agent['description']}\n\n"
                            f"**Specializations:** {', '.join(agent['specializations'])}",
                )

        if "capabilities" in input_lower or "what can you do" in input_lower:
            capabilities = self.capability_registry.get_all_capabilities()
            cap_list = "\n".join([f"- {c.name} ({c.agent_role})" for c in capabilities[:10]])
            return WillowResponse(
                message=f"Here are some things the Legion can do:\n\n{cap_list}\n\n"
                        f"Total: {len(capabilities)} capabilities across multiple teams.",
            )

        if self.current_plan:
            return WillowResponse(
                message=f"I have a plan ready: {self.current_plan.intent_summary}\n\n"
                        f"{self.current_plan.to_display_string()}\n\n"
                        f"Say 'Begin' to start or tell me what to change.",
                plan=self.current_plan,
                needs_input=True,
            )

        return WillowResponse(
            message="I'm ready and waiting. No active plans at the moment. What would you like to accomplish?",
            needs_input=True,
        )

    def _format_team_overview(self) -> WillowResponse:
        """Format a full team overview."""
        lines = ["Here's my team - the Legion:\n"]

        teams = {}
        for agent in LEGION_TEAM_ROSTER.values():
            team = agent.get("team", "Other")
            if team not in teams:
                teams[team] = []
            teams[team].append(agent)

        for team_name in ["Coordination", "Editorial", "Research", "Technical", "Production"]:
            if team_name not in teams:
                continue
            lines.append(f"\n**{team_name} Team:**")
            for agent in teams[team_name]:
                lines.append(f"- **{agent['name']}** ({agent['role']}): {agent['description'][:80]}...")

        lines.append(f"\nTotal: {len(LEGION_TEAM_ROSTER)} agents ready to work.")

        return WillowResponse(message="\n".join(lines))

    def _format_team_detail(self, team_name: str) -> WillowResponse:
        """Format details about a specific team."""
        agents = get_agents_by_team(team_name)
        if not agents:
            return WillowResponse(message=f"I don't have a {team_name} team configured.")

        lines = [f"**{team_name} Team** ({len(agents)} members):\n"]
        for agent in agents:
            lines.append(f"### {agent['name']} ({agent['role']})")
            lines.append(f"{agent['description']}")
            lines.append(f"- **Specializations:** {', '.join(agent['specializations'])}")
            lines.append("")

        return WillowResponse(message="\n".join(lines))

    def _format_agent_list(self, agents: List[Dict[str, Any]], title: str) -> WillowResponse:
        """Format a list of agents."""
        if not agents:
            return WillowResponse(message=f"I don't have any {title} in my current roster.")

        lines = [f"**{title}** ({len(agents)} available):\n"]
        for agent in agents:
            lines.append(f"**{agent['name']}**")
            lines.append(f"{agent['description']}")
            lines.append(f"- Specializations: {', '.join(agent['specializations'])}")
            lines.append("")

        return WillowResponse(message="\n".join(lines))

    def _check_capabilities(self, intent: ParsedIntent) -> List[str]:
        """Check if we have capabilities for the intent."""
        # For now, return empty (no gaps)
        # In production, this would check against required capabilities
        return []

    def _handle_capability_gap(
        self,
        intent: ParsedIntent,
        missing: List[str]
    ) -> WillowResponse:
        """Handle when we're missing capabilities."""
        # Register the gap
        for cap_name in missing:
            self.capability_registry.register_gap(
                description=cap_name,
                requested_by="user",
                context=intent.summary,
            )

        return WillowResponse(
            message=f"I've noted that we need some new capabilities to fully handle this: "
                    f"{', '.join(missing)}. I've logged this for the Advisory Board to address.\n\n"
                    f"In the meantime, let me try with our existing capabilities.",
            escalation=True,
        )

    def _format_clarification_request(self, intent: ParsedIntent) -> str:
        """Format a clarification request."""
        questions = "\n".join([f"- {q}" for q in intent.clarification_questions])
        return f"I want to make sure I understand correctly. Could you clarify:\n\n{questions}"

    def _format_plan_proposal(self, plan: ExecutionPlan) -> str:
        """Format a plan proposal message."""
        step_list = "\n".join([
            f"{i+1}. [{s.agent_role}] {s.description}"
            for i, s in enumerate(plan.steps)
        ])

        return (
            f"Here's my plan for: **{plan.intent_summary}**\n\n"
            f"{step_list}\n\n"
            f"Ready to begin when you say 'Go'."
        )

    def _format_success_message(
        self,
        plan: ExecutionPlan,
        result: PlanExecutionResult
    ) -> str:
        """Format a success message."""
        return (
            f"✅ Done! Completed: {plan.intent_summary}\n\n"
            f"**Result:**\n{result.final_output[:500] if result.final_output else 'Task completed.'}..."
        )

    def _format_failure_message(
        self,
        plan: ExecutionPlan,
        result: PlanExecutionResult
    ) -> str:
        """Format a failure message."""
        failed_steps = [r for r in result.step_results if r.error]
        errors = "\n".join([f"- {r.step_id}: {r.error}" for r in failed_steps])

        return (
            f"⚠️ Encountered some issues with: {plan.intent_summary}\n\n"
            f"**Errors:**\n{errors}\n\n"
            f"Would you like me to try a different approach?"
        )

    def _get_conversation_context(self) -> str:
        """Get recent conversation context for intent parsing."""
        recent = self.conversation_history[-5:]  # Last 5 messages
        return "\n".join([
            f"{m['role']}: {m['content'][:200]}"
            for m in recent
        ])


# Singleton instance
_willow_instance: Optional[Willow] = None


def get_willow() -> Willow:
    """Get the singleton Willow instance."""
    global _willow_instance
    if _willow_instance is None:
        _willow_instance = Willow()
    return _willow_instance

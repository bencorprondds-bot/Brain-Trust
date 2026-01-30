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
from ..core.state.memory import LongTermMemory, get_memory
from ..core.preference_memory import PreferenceMemory, get_preference_memory
from ..core.context_loader import ContextLoader

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
        model: str = "claude-sonnet-4-20250514",  # Strong reasoning model for orchestration
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

        # Memory systems
        self.long_term_memory = get_memory()
        self.preference_memory = get_preference_memory()
        self.context_loader = ContextLoader()

        # Conversation state
        self.current_plan: Optional[ExecutionPlan] = None
        self.conversation_history: List[Dict[str, str]] = []
        self.session_learnings: List[Dict[str, Any]] = []  # Track learnings for commit

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

        # Check for corrections and learn from them
        if self._is_correction(user_input):
            self._record_correction(user_input)

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

        # Parse intent with memory context
        memory_context = self._get_memory_context()
        conversation_context = self._get_conversation_context()
        full_context = f"{memory_context}\n\n{conversation_context}" if memory_context else conversation_context

        intent = self.intent_parser.parse(
            user_input,
            conversation_context=full_context,
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
        """Check if input is a status/meta command (NOT an action request)."""
        input_lower = user_input.lower()

        # If it looks like an action request, NOT a status query
        action_indicators = [
            "can you", "please", "could you", "would you",
            "ask the", "have the", "get the", "tell the",
            "bring up", "find", "search", "look for", "fetch",
            "create", "write", "edit", "review",
        ]
        if any(phrase in input_lower for phrase in action_indicators):
            return False

        status_phrases = [
            "status", "what's happening", "where are we",
            "what are we working on", "what are we doing",
            "what's going on", "current project", "active project",
            "capabilities", "what can you do",
            # Team-related queries - only when genuinely asking about the team
            "who are the", "who is the", "your team", "the team",
            "tell me about the legion", "show me the roster",
            "list the agents", "what agents", "which agents",
            "who can help with",
        ]
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

        # Project status queries - use TELOS context
        if any(phrase in input_lower for phrase in [
            "what are we working on", "what are we doing", "current project",
            "active project", "what's going on", "where did we leave off"
        ]):
            try:
                telos = self.context_loader.load_context()
                return WillowResponse(
                    message=f"Here's what we're working on:\n\n{telos.goals}\n\n"
                            f"**Mission:** {telos.mission[:200]}..."
                            if len(telos.mission) > 200 else
                            f"Here's what we're working on:\n\n{telos.goals}\n\n"
                            f"**Mission:** {telos.mission}",
                )
            except FileNotFoundError:
                return WillowResponse(
                    message="I don't have context loaded yet. You can set up your goals in ~/.pai/context/GOALS.md",
                    needs_input=True,
                )

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

        if ("research team" in input_lower or "about the librarian" in input_lower or
            "who is the librarian" in input_lower or "tell me about librarian" in input_lower):
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
            f"[OK] Done! Completed: {plan.intent_summary}\n\n"
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
            f"[WARN] Encountered some issues with: {plan.intent_summary}\n\n"
            f"**Errors:**\n{errors}\n\n"
            f"Would you like me to try a different approach?"
        )

    def _is_correction(self, user_input: str) -> bool:
        """Detect if user is correcting Willow's behavior."""
        correction_phrases = [
            "no", "that's not", "that is not", "wrong", "incorrect",
            "not what i", "not what I", "i didn't", "I didn't",
            "i don't want", "I don't want", "don't do", "stop",
            "that's wrong", "you misunderstood", "no i meant",
            "no I meant", "actually i want", "actually I want",
            "just the", "only the", "just use", "only use",
        ]
        input_lower = user_input.lower()
        return any(phrase.lower() in input_lower for phrase in correction_phrases)

    def _record_correction(self, user_input: str) -> None:
        """
        Record a correction for learning.

        Captures what Willow did wrong so it can improve.
        """
        # Get the last assistant response to understand what was corrected
        last_response = None
        for msg in reversed(self.conversation_history):
            if msg.get("role") == "assistant":
                last_response = msg.get("content", "")[:300]
                break

        correction_record = {
            "type": "correction",
            "content": f"User correction: {user_input}\nPrevious response: {last_response or 'N/A'}",
            "metadata": {
                "correction_text": user_input,
                "corrected_response": last_response,
                "timestamp": datetime.now().isoformat(),
            }
        }

        # Add to session learnings for commit
        self.session_learnings.append(correction_record)

        # Also record to preference memory as a failed pattern
        if last_response and self.current_plan:
            try:
                self.preference_memory.record_pattern(
                    intent_category=self.current_plan.intent_summary[:50],
                    approach={"plan": self.current_plan.to_dict()},
                    success=False,
                    feedback=user_input,
                )
            except Exception as e:
                logger.warning(f"Could not record correction pattern: {e}")

        logger.info(f"Recorded correction: {user_input[:50]}...")

    def _get_conversation_context(self) -> str:
        """Get recent conversation context for intent parsing."""
        recent = self.conversation_history[-5:]  # Last 5 messages
        return "\n".join([
            f"{m['role']}: {m['content'][:200]}"
            for m in recent
        ])

    def _get_memory_context(self, intent_summary: Optional[str] = None) -> str:
        """
        Build context from memory systems for better decision-making.

        Includes:
        - TELOS context (mission, goals, identity)
        - Relevant past memories
        - Preference patterns
        """
        context_parts = []

        # Load TELOS context
        try:
            telos = self.context_loader.load_context()
            context_parts.append(f"# Mission\n{telos.mission[:500]}")
            context_parts.append(f"# Current Goals\n{telos.goals[:500]}")
        except FileNotFoundError:
            logger.warning("TELOS context not found - run with default context")

        # Get preference context
        try:
            pref_context = self.preference_memory.get_preference_context()
            if pref_context:
                context_parts.append(pref_context)
        except Exception as e:
            logger.warning(f"Could not load preference context: {e}")

        # Recall relevant memories if we have an intent
        if intent_summary:
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                memories = loop.run_until_complete(
                    self.long_term_memory.recall(intent_summary, limit=3)
                )
                if memories:
                    memory_text = "\n".join([
                        f"- {m['content'][:200]}" for m in memories
                    ])
                    context_parts.append(f"# Relevant Past Experiences\n{memory_text}")
            except Exception as e:
                logger.warning(f"Could not recall memories: {e}")

        return "\n\n".join(context_parts) if context_parts else ""

    async def commit_session_memory(self) -> Dict[str, Any]:
        """
        Commit session learnings to long-term memory.

        Called when user runs /remember or at session end.
        Stores successful patterns, corrections, and user preferences.

        Returns:
            Dict with commit statistics
        """
        committed_count = 0
        errors = []

        # Commit session learnings
        for learning in self.session_learnings:
            try:
                await self.long_term_memory.remember(
                    agent_id="willow",
                    content=learning.get("content", ""),
                    memory_type=learning.get("type", "learning"),
                    metadata=learning.get("metadata", {}),
                )
                committed_count += 1
            except Exception as e:
                errors.append(str(e))
                logger.error(f"Failed to commit learning: {e}")

        # Extract patterns from conversation history
        if len(self.conversation_history) >= 2:
            # Look for successful completions
            for i, msg in enumerate(self.conversation_history):
                if msg.get("role") == "assistant" and i > 0:
                    prev_msg = self.conversation_history[i - 1]
                    if prev_msg.get("role") == "user":
                        # Store interaction pattern
                        pattern_content = f"User: {prev_msg['content'][:200]}\nResponse: {msg['content'][:200]}"
                        try:
                            await self.long_term_memory.remember(
                                agent_id="willow",
                                content=pattern_content,
                                memory_type="experience",
                                metadata={"session_commit": True},
                            )
                            committed_count += 1
                        except Exception as e:
                            errors.append(str(e))

        # Clear session learnings after commit
        self.session_learnings.clear()

        logger.info(f"Committed {committed_count} memories to long-term storage")

        return {
            "committed": committed_count,
            "errors": errors,
            "success": len(errors) == 0,
        }


# Singleton instance
_willow_instance: Optional[Willow] = None


def get_willow() -> Willow:
    """Get the singleton Willow instance."""
    global _willow_instance
    if _willow_instance is None:
        _willow_instance = Willow()
    return _willow_instance

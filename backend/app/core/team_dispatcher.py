"""
Team Dispatcher for Brain Trust / Legion

Executes approved plans by dispatching work to appropriate agents.
Tracks progress and handles failures.
"""

import os
import logging
import time
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from enum import Enum

from crewai import Agent, Task, Crew, Process

from .plan_proposer import ExecutionPlan, PlanStep, PlanStatus
from .capability_registry import get_capability_registry

logger = logging.getLogger(__name__)

# LLM retry configuration
LLM_MAX_RETRIES = 3
LLM_INITIAL_BACKOFF = 2  # seconds
LLM_BACKOFF_MULTIPLIER = 2  # exponential backoff


class DispatchResult(str, Enum):
    """Result of dispatching a step."""
    SUCCESS = "success"
    FAILURE = "failure"
    BLOCKED = "blocked"
    TIMEOUT = "timeout"


@dataclass
class StepResult:
    """Result of executing a single plan step."""

    step_id: str
    result: DispatchResult
    output: Optional[str] = None
    error: Optional[str] = None
    duration_seconds: float = 0.0
    tools_called: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "result": self.result.value,
            "output": self.output,
            "error": self.error,
            "duration_seconds": self.duration_seconds,
            "tools_called": self.tools_called,
        }


@dataclass
class PlanExecutionResult:
    """Result of executing an entire plan."""

    plan_id: str
    status: PlanStatus
    step_results: List[StepResult] = field(default_factory=list)
    final_output: Optional[str] = None
    total_duration_seconds: float = 0.0

    @property
    def success(self) -> bool:
        return self.status == PlanStatus.COMPLETED

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "status": self.status.value,
            "step_results": [r.to_dict() for r in self.step_results],
            "final_output": self.final_output,
            "total_duration_seconds": self.total_duration_seconds,
            "success": self.success,
        }


class TeamDispatcher:
    """
    Dispatches work to agents according to execution plans.

    Features:
    - Sequential and parallel step execution
    - Dependency handling
    - Progress callbacks
    - Failure recovery
    """

    def __init__(
        self,
        default_model: str = "gemini-2.0-flash",
        on_step_start: Optional[Callable[[PlanStep], None]] = None,
        on_step_complete: Optional[Callable[[PlanStep, StepResult], None]] = None,
    ):
        """
        Initialize the dispatcher.

        Args:
            default_model: Default LLM for agents
            on_step_start: Callback when step starts
            on_step_complete: Callback when step completes
        """
        self.default_model = default_model
        self.on_step_start = on_step_start
        self.on_step_complete = on_step_complete
        self.capability_registry = get_capability_registry()

    def execute(self, plan: ExecutionPlan, context: Optional[str] = None) -> PlanExecutionResult:
        """
        Execute an approved plan.

        Args:
            plan: The execution plan to run
            context: Optional context from previous steps or files

        Returns:
            PlanExecutionResult with all step outputs
        """
        if plan.status not in [PlanStatus.APPROVED, PlanStatus.IN_PROGRESS]:
            logger.warning(f"Plan {plan.id} not approved. Status: {plan.status}")
            return PlanExecutionResult(
                plan_id=plan.id,
                status=plan.status,
            )

        logger.info(f"Executing plan {plan.id}: {plan.intent_summary}")
        plan.status = PlanStatus.IN_PROGRESS
        start_time = time.time()

        result = PlanExecutionResult(
            plan_id=plan.id,
            status=PlanStatus.IN_PROGRESS,
        )

        # Track completed steps and their outputs
        completed_steps: Dict[str, str] = {}

        # Execute steps in order, respecting dependencies
        for step in sorted(plan.steps, key=lambda s: s.order):
            # Check dependencies
            if not self._dependencies_met(step, completed_steps):
                logger.warning(f"Step {step.id} blocked by unmet dependencies")
                step_result = StepResult(
                    step_id=step.id,
                    result=DispatchResult.BLOCKED,
                    error="Dependencies not met",
                )
                result.step_results.append(step_result)
                continue

            # Execute step
            step_result = self._execute_step(step, context, completed_steps, plan.constraints)
            result.step_results.append(step_result)

            if step_result.result == DispatchResult.SUCCESS:
                completed_steps[step.id] = step_result.output or ""
                step.status = "completed"
                step.output = step_result.output
            else:
                step.status = "failed"
                step.error = step_result.error
                # Continue with other steps that don't depend on this one

        # Determine final status
        all_success = all(r.result == DispatchResult.SUCCESS for r in result.step_results)
        any_success = any(r.result == DispatchResult.SUCCESS for r in result.step_results)

        if all_success:
            result.status = PlanStatus.COMPLETED
            plan.status = PlanStatus.COMPLETED
        elif any_success:
            result.status = PlanStatus.COMPLETED  # Partial success
            plan.status = PlanStatus.COMPLETED
        else:
            result.status = PlanStatus.FAILED
            plan.status = PlanStatus.FAILED

        # Set final output to last successful step's output
        for step_result in reversed(result.step_results):
            if step_result.output:
                result.final_output = step_result.output
                break

        result.total_duration_seconds = time.time() - start_time
        plan.completed_at = datetime.now()

        logger.info(
            f"Plan {plan.id} {'completed' if result.success else 'failed'} "
            f"in {result.total_duration_seconds:.1f}s"
        )

        return result

    def _dependencies_met(self, step: PlanStep, completed_steps: Dict[str, str]) -> bool:
        """Check if all dependencies for a step are met."""
        if not step.depends_on:
            return True
        return all(dep in completed_steps for dep in step.depends_on)

    def _execute_step(
        self,
        step: PlanStep,
        base_context: Optional[str],
        previous_outputs: Dict[str, str],
        constraints: List[str],
    ) -> StepResult:
        """Execute a single plan step."""

        logger.info(f"Executing step {step.id}: {step.description}")
        step.status = "in_progress"
        step.started_at = datetime.now()

        if self.on_step_start:
            self.on_step_start(step)

        start_time = time.time()

        try:
            # Build context from dependencies
            context_parts = []
            if base_context:
                context_parts.append(base_context)

            for dep_id in step.depends_on:
                if dep_id in previous_outputs:
                    context_parts.append(f"Previous step output:\n{previous_outputs[dep_id]}")

            full_context = "\n\n".join(context_parts) if context_parts else None

            # Create and run agent
            output = self._run_agent(step, full_context, constraints)

            step.completed_at = datetime.now()
            duration = time.time() - start_time

            result = StepResult(
                step_id=step.id,
                result=DispatchResult.SUCCESS,
                output=output,
                duration_seconds=duration,
            )

            # Update capability metrics
            if step.capability_id:
                self.capability_registry.update_metrics(
                    step.capability_id,
                    success=True,
                    duration_seconds=int(duration),
                )

        except Exception as e:
            logger.error(f"Step {step.id} failed: {e}")
            step.completed_at = datetime.now()
            duration = time.time() - start_time

            result = StepResult(
                step_id=step.id,
                result=DispatchResult.FAILURE,
                error=str(e),
                duration_seconds=duration,
            )

            if step.capability_id:
                self.capability_registry.update_metrics(
                    step.capability_id,
                    success=False,
                    duration_seconds=int(duration),
                )

        if self.on_step_complete:
            self.on_step_complete(step, result)

        return result

    def _run_agent(
        self,
        step: PlanStep,
        context: Optional[str],
        constraints: List[str],
    ) -> str:
        """Create and run an agent for a step with retry logic."""

        from app.tools import get_registry

        # Get tools for role
        tool_registry = get_registry()
        tools = tool_registry.get_for_adapter("crewai", role=step.agent_role)

        # Build goal/backstory
        goal = step.description
        backstory = f"You are the {step.agent_role} in the Legion, a team of AI agents."

        if constraints:
            backstory += f"\n\nConstraints to follow: {', '.join(constraints)}"

        # Build task description
        task_description = step.description
        if context:
            task_description = f"Context:\n{context}\n\nTask:\n{step.description}"

        # Retry loop with exponential backoff
        last_error = None
        models_to_try = [self.default_model]

        # Add fallback models if primary is Gemini
        if 'gemini' in self.default_model.lower():
            models_to_try.append("claude-sonnet-4-20250514")  # Fallback to Claude

        for model_name in models_to_try:
            for attempt in range(LLM_MAX_RETRIES):
                try:
                    # Create LLM (fresh instance for each attempt)
                    llm = self._create_llm(model_name)

                    # Create agent
                    agent = Agent(
                        role=step.agent_role,
                        goal=goal,
                        backstory=backstory,
                        allow_delegation=False,
                        tools=tools,
                        verbose=False,
                        llm=llm,
                        max_iter=10,
                    )

                    # Create and execute task
                    task = Task(
                        description=task_description,
                        agent=agent,
                        expected_output="Complete the assigned task.",
                    )

                    result = agent.execute_task(task)

                    # Validate result - check for None or empty
                    if result is None or (isinstance(result, str) and not result.strip()):
                        raise ValueError("Invalid response from LLM call - None or empty")

                    return str(result)

                except Exception as e:
                    last_error = e
                    error_str = str(e).lower()

                    # Check if it's a retryable error
                    retryable = any(term in error_str for term in [
                        'rate limit', 'quota', 'timeout', '429', '503', '500',
                        'none or empty', 'invalid response', 'connection'
                    ])

                    if retryable and attempt < LLM_MAX_RETRIES - 1:
                        # Calculate backoff with jitter
                        backoff = LLM_INITIAL_BACKOFF * (LLM_BACKOFF_MULTIPLIER ** attempt)
                        jitter = random.uniform(0, backoff * 0.1)
                        wait_time = backoff + jitter

                        logger.warning(
                            f"Step {step.id} LLM call failed (attempt {attempt + 1}/{LLM_MAX_RETRIES}): {e}. "
                            f"Retrying in {wait_time:.1f}s with model {model_name}..."
                        )
                        time.sleep(wait_time)
                    elif attempt == LLM_MAX_RETRIES - 1 and model_name != models_to_try[-1]:
                        logger.warning(
                            f"Step {step.id} exhausted retries with {model_name}, "
                            f"trying fallback model..."
                        )
                        break  # Try next model
                    else:
                        raise

        # If we get here, all retries and fallbacks failed
        raise last_error or Exception("All LLM retry attempts failed")

    def _create_llm(self, model_name: str):
        """Create LLM instance."""
        model_lower = model_name.lower()

        if 'gemini' in model_lower:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=os.getenv("GEMINI_API_KEY"),
                temperature=0.7,
            )

        elif 'claude' in model_lower or 'sonnet' in model_lower or 'opus' in model_lower:
            from langchain_anthropic import ChatAnthropic

            if "sonnet" in model_lower and "4" not in model_lower:
                ant_model = "claude-sonnet-4-20250514"
            elif "opus" in model_lower and "4" not in model_lower:
                ant_model = "claude-opus-4-20250514"
            else:
                ant_model = model_name

            return ChatAnthropic(
                model_name=ant_model,
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                temperature=0.7,
            )

        else:
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(
                model="gemini-2.0-flash",
                google_api_key=os.getenv("GEMINI_API_KEY"),
                temperature=0.7,
            )


def dispatch_plan(plan: ExecutionPlan, context: Optional[str] = None) -> PlanExecutionResult:
    """Convenience function to execute a plan."""
    dispatcher = TeamDispatcher()
    return dispatcher.execute(plan, context)

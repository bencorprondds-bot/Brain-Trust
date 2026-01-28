"""
State Schema for Brain Trust

Defines model-agnostic state that persists across model swaps ("brain transplants").

Design Philosophy:
- State is separate from intelligence
- If we swap from a 2M context model to an 8k specialist, state survives
- Agents learn from past executions via long-term memory
- Context windowing adapts state to target model's capacity

Key Structures:
- StepRecord: Individual execution step with tool calls
- AgentState: Complete agent state at a point in time
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
import json
import hashlib


class StepStatus(str, Enum):
    """Status of an execution step."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class StepRecord:
    """
    Record of a single execution step.

    Captures everything needed to understand what happened:
    - What was attempted
    - What tools were used
    - What was the result
    - How long it took
    """
    step_id: str
    description: str
    status: StepStatus = StepStatus.PENDING

    # Timing
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Tool execution
    tool_used: Optional[str] = None
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[str] = None

    # Results
    reasoning: Optional[str] = None
    error: Optional[str] = None
    retry_count: int = 0

    # Metadata
    tokens_used: int = 0
    cost_usd: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "step_id": self.step_id,
            "description": self.description,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "tool_used": self.tool_used,
            "tool_input": self.tool_input,
            "tool_output": self.tool_output,
            "reasoning": self.reasoning,
            "error": self.error,
            "retry_count": self.retry_count,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StepRecord":
        """Create from dictionary."""
        return cls(
            step_id=data["step_id"],
            description=data["description"],
            status=StepStatus(data.get("status", "pending")),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            started_at=datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            tool_used=data.get("tool_used"),
            tool_input=data.get("tool_input"),
            tool_output=data.get("tool_output"),
            reasoning=data.get("reasoning"),
            error=data.get("error"),
            retry_count=data.get("retry_count", 0),
            tokens_used=data.get("tokens_used", 0),
            cost_usd=data.get("cost_usd", 0.0),
        )

    def duration_ms(self) -> Optional[int]:
        """Calculate step duration in milliseconds."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() * 1000)
        return None


@dataclass
class AgentState:
    """
    Model-agnostic agent state that survives brain transplants.

    This is the "soul" of the agent - everything it knows and has done,
    separate from the "brain" (the LLM that processes it).

    The state can be serialized to JSON and loaded by any model,
    allowing seamless model swaps without losing context.
    """

    # Identity
    agent_id: str
    workflow_id: str
    name: str = ""
    role: str = ""

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Task tracking
    current_goal: str = ""
    original_prompt: str = ""
    completed_steps: List[StepRecord] = field(default_factory=list)
    pending_steps: List[StepRecord] = field(default_factory=list)

    # Working memory (key-value pairs extracted during execution)
    variables: Dict[str, Any] = field(default_factory=dict)

    # Tool results cache (avoid re-running expensive tools)
    tool_results_cache: Dict[str, str] = field(default_factory=dict)

    # Context from upstream agents
    upstream_context: Dict[str, str] = field(default_factory=dict)

    # Error handling
    error_history: List[Dict[str, Any]] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 3

    # Metadata
    model_used: Optional[str] = None
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0

    # Final output
    final_output: Optional[str] = None
    success: bool = False

    def state_hash(self) -> str:
        """Generate hash of current state for change detection."""
        content = json.dumps({
            "agent_id": self.agent_id,
            "current_goal": self.current_goal,
            "completed_steps": [s.step_id for s in self.completed_steps],
            "variables": self.variables,
        }, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def add_step(self, description: str) -> StepRecord:
        """Add a new pending step."""
        step = StepRecord(
            step_id=f"{self.agent_id}-step-{len(self.completed_steps) + len(self.pending_steps) + 1}",
            description=description,
            status=StepStatus.PENDING,
        )
        self.pending_steps.append(step)
        self.updated_at = datetime.utcnow()
        return step

    def start_step(self, step_id: str) -> Optional[StepRecord]:
        """Mark a step as in progress."""
        for step in self.pending_steps:
            if step.step_id == step_id:
                step.status = StepStatus.IN_PROGRESS
                step.started_at = datetime.utcnow()
                self.updated_at = datetime.utcnow()
                return step
        return None

    def complete_step(
        self,
        step_id: str,
        tool_output: Optional[str] = None,
        reasoning: Optional[str] = None,
        tokens_used: int = 0,
        cost_usd: float = 0.0,
    ) -> Optional[StepRecord]:
        """Mark a step as completed and move to completed list."""
        for i, step in enumerate(self.pending_steps):
            if step.step_id == step_id:
                step.status = StepStatus.COMPLETED
                step.completed_at = datetime.utcnow()
                step.tool_output = tool_output
                step.reasoning = reasoning
                step.tokens_used = tokens_used
                step.cost_usd = cost_usd

                # Move to completed
                self.pending_steps.pop(i)
                self.completed_steps.append(step)

                # Update totals
                self.total_tokens_used += tokens_used
                self.total_cost_usd += cost_usd
                self.updated_at = datetime.utcnow()

                return step
        return None

    def fail_step(self, step_id: str, error: str) -> Optional[StepRecord]:
        """Mark a step as failed."""
        for step in self.pending_steps:
            if step.step_id == step_id:
                step.status = StepStatus.FAILED
                step.error = error
                step.completed_at = datetime.utcnow()

                # Record in error history
                self.error_history.append({
                    "step_id": step_id,
                    "error": error,
                    "timestamp": datetime.utcnow().isoformat(),
                })

                self.updated_at = datetime.utcnow()
                return step
        return None

    def set_variable(self, key: str, value: Any) -> None:
        """Set a working memory variable."""
        self.variables[key] = value
        self.updated_at = datetime.utcnow()

    def get_variable(self, key: str, default: Any = None) -> Any:
        """Get a working memory variable."""
        return self.variables.get(key, default)

    def cache_tool_result(self, tool_call_hash: str, result: str) -> None:
        """Cache a tool result to avoid re-execution."""
        self.tool_results_cache[tool_call_hash] = result
        self.updated_at = datetime.utcnow()

    def get_cached_result(self, tool_call_hash: str) -> Optional[str]:
        """Get a cached tool result."""
        return self.tool_results_cache.get(tool_call_hash)

    def to_json(self) -> str:
        """Serialize state to JSON for persistence."""
        return json.dumps(self.to_dict(), indent=2, default=str)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "agent_id": self.agent_id,
            "workflow_id": self.workflow_id,
            "name": self.name,
            "role": self.role,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "current_goal": self.current_goal,
            "original_prompt": self.original_prompt,
            "completed_steps": [s.to_dict() for s in self.completed_steps],
            "pending_steps": [s.to_dict() for s in self.pending_steps],
            "variables": self.variables,
            "tool_results_cache": self.tool_results_cache,
            "upstream_context": self.upstream_context,
            "error_history": self.error_history,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "model_used": self.model_used,
            "total_tokens_used": self.total_tokens_used,
            "total_cost_usd": self.total_cost_usd,
            "final_output": self.final_output,
            "success": self.success,
        }

    @classmethod
    def from_json(cls, data: str) -> "AgentState":
        """Deserialize state from JSON."""
        return cls.from_dict(json.loads(data))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentState":
        """Create from dictionary."""
        state = cls(
            agent_id=data["agent_id"],
            workflow_id=data["workflow_id"],
            name=data.get("name", ""),
            role=data.get("role", ""),
        )

        # Parse timestamps
        if data.get("created_at"):
            state.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("updated_at"):
            state.updated_at = datetime.fromisoformat(data["updated_at"])

        # Task tracking
        state.current_goal = data.get("current_goal", "")
        state.original_prompt = data.get("original_prompt", "")
        state.completed_steps = [StepRecord.from_dict(s) for s in data.get("completed_steps", [])]
        state.pending_steps = [StepRecord.from_dict(s) for s in data.get("pending_steps", [])]

        # Memory
        state.variables = data.get("variables", {})
        state.tool_results_cache = data.get("tool_results_cache", {})
        state.upstream_context = data.get("upstream_context", {})

        # Error handling
        state.error_history = data.get("error_history", [])
        state.retry_count = data.get("retry_count", 0)
        state.max_retries = data.get("max_retries", 3)

        # Metadata
        state.model_used = data.get("model_used")
        state.total_tokens_used = data.get("total_tokens_used", 0)
        state.total_cost_usd = data.get("total_cost_usd", 0.0)

        # Output
        state.final_output = data.get("final_output")
        state.success = data.get("success", False)

        return state

    def to_context_prompt(self, max_tokens: int = 4000) -> str:
        """
        Generate context prompt for LLM consumption.

        Automatically truncates to fit context window budget.
        Priority order:
        1. Current goal (always)
        2. Recent completed steps (last 3-5)
        3. Key variables
        4. Upstream context summary
        """
        lines = []

        # Always include goal
        lines.append(f"## Current Goal\n{self.current_goal}\n")

        # Include recent completed steps
        if self.completed_steps:
            lines.append("## Recent Progress")
            recent = self.completed_steps[-5:]  # Last 5 steps
            for step in recent:
                status_icon = "✓" if step.status == StepStatus.COMPLETED else "✗"
                lines.append(f"- {status_icon} {step.description}")
                if step.tool_used:
                    lines.append(f"  Tool: {step.tool_used}")
                if step.tool_output and len(step.tool_output) < 200:
                    lines.append(f"  Result: {step.tool_output[:200]}")
            lines.append("")

        # Include key variables
        if self.variables:
            lines.append("## Working Memory")
            for key, value in list(self.variables.items())[:10]:
                value_str = str(value)[:100]
                lines.append(f"- {key}: {value_str}")
            lines.append("")

        # Include upstream context summary
        if self.upstream_context:
            lines.append("## Context from Previous Agents")
            for agent_name, context in self.upstream_context.items():
                summary = context[:500] + "..." if len(context) > 500 else context
                lines.append(f"### From {agent_name}")
                lines.append(summary)
                lines.append("")

        # Pending steps
        if self.pending_steps:
            lines.append("## Pending Steps")
            for step in self.pending_steps[:5]:
                lines.append(f"- [ ] {step.description}")
            lines.append("")

        context = "\n".join(lines)

        # Simple token estimation (4 chars ≈ 1 token)
        estimated_tokens = len(context) // 4
        if estimated_tokens > max_tokens:
            # Truncate to fit
            max_chars = max_tokens * 4
            context = context[:max_chars] + "\n[Context truncated to fit model limits]"

        return context

    def summary(self) -> str:
        """Generate a one-line summary of current state."""
        completed = len(self.completed_steps)
        pending = len(self.pending_steps)
        status = "✓ Complete" if self.success else "In Progress" if pending else "Idle"
        return f"[{self.agent_id}] {status} | {completed} done, {pending} pending | {self.total_tokens_used} tokens | ${self.total_cost_usd:.4f}"

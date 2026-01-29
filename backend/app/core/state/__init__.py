"""
Brain Trust State Persistence Layer

Model-agnostic agent state that survives "brain transplants" (model swaps).

The state system provides:
1. Short-term state: Current task, pending steps, variables
2. Long-term memory: Vector embeddings for semantic retrieval
3. Context windowing: Automatic truncation to fit model limits
4. Learning: Extract patterns from successful executions

Usage:
    from app.core.state import StateManager, AgentState

    # Save state after execution
    state = AgentState(agent_id="librarian-001", workflow_id="wf-123")
    state.current_goal = "Find project files"
    await manager.save(state)

    # Load state for continuation
    state = await manager.load("librarian-001")
"""

from app.core.state.schema import (
    AgentState,
    StepRecord,
    StepStatus,
)
from app.core.state.manager import (
    StateManager,
    get_state_manager,
)
from app.core.state.memory import (
    LongTermMemory,
    MemoryEntry,
    get_memory,
)
from app.core.state.context import (
    ContextWindowManager,
    ContextBudget,
    ContextSection,
    get_context_manager,
)

__all__ = [
    "AgentState",
    "StepRecord",
    "StepStatus",
    "StateManager",
    "get_state_manager",
    "LongTermMemory",
    "MemoryEntry",
    "get_memory",
    "ContextWindowManager",
    "ContextBudget",
    "ContextSection",
    "get_context_manager",
]

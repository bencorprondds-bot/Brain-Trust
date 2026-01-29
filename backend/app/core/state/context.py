"""
Context Window Manager for Brain Trust

Manages context window allocation across model swaps.

When the "brain" (LLM) changes, the context window size changes.
This component ensures the "soul" (state) fits the new brain:
- Prioritizes critical information
- Truncates gracefully
- Preserves semantic coherence

Priority Order:
1. Current goal and pending steps (always included)
2. Recent completed steps (last 3-5)
3. Key variables from working memory
4. Relevant memories from long-term storage
5. Upstream agent context
6. TELOS context (truncated if needed)
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from app.core.state.schema import AgentState, StepRecord
from app.core.model_registry import ModelRegistry, get_registry

logger = logging.getLogger(__name__)


@dataclass
class ContextBudget:
    """Token budget allocation for context sections."""
    total_tokens: int
    reserved_for_output: int
    reserved_for_system: int

    # Minimum allocations (these MUST fit)
    min_goal: int = 200
    min_steps: int = 300

    # Flexible allocations (can be reduced)
    max_variables: int = 500
    max_memories: int = 1000
    max_upstream: int = 1500
    max_telos: int = 2000

    @property
    def available(self) -> int:
        """Available tokens for context."""
        return self.total_tokens - self.reserved_for_output - self.reserved_for_system


@dataclass
class ContextSection:
    """A section of context with its token usage."""
    name: str
    content: str
    tokens: int
    priority: int  # 1 = highest (must include), 5 = lowest (can drop)
    truncatable: bool = True


class ContextWindowManager:
    """
    Manages context window allocation across model swaps.

    Ensures agent context fits the target model's window while
    preserving the most important information.
    """

    def __init__(self, model_registry: Optional[ModelRegistry] = None):
        """
        Initialize the context window manager.

        Args:
            model_registry: Model registry for context window lookup
        """
        self.registry = model_registry or get_registry()

    def prepare_context(
        self,
        state: AgentState,
        model_id: str,
        memories: Optional[List[Dict[str, Any]]] = None,
        telos_context: Optional[str] = None,
    ) -> str:
        """
        Prepare context that fits the target model's window.

        Args:
            state: Current agent state
            model_id: Target model identifier
            memories: Relevant memories from long-term storage
            telos_context: User context from TELOS layer

        Returns:
            Formatted context string that fits the model's window
        """
        # Get model capabilities
        model = self.registry.get_model(model_id)
        if model is None:
            # Fallback to reasonable defaults
            context_window = 128000
            max_output = 4096
        else:
            context_window = model.context_window
            max_output = model.max_output

        # Calculate budget
        budget = ContextBudget(
            total_tokens=context_window,
            reserved_for_output=max_output,
            reserved_for_system=1000,  # System prompt buffer
        )

        # Build context sections with priorities
        sections = self._build_sections(state, memories, telos_context)

        # Fit sections to budget
        fitted = self._fit_to_budget(sections, budget)

        # Format final context
        return self._format_context(fitted)

    def _build_sections(
        self,
        state: AgentState,
        memories: Optional[List[Dict[str, Any]]],
        telos_context: Optional[str],
    ) -> List[ContextSection]:
        """Build context sections with priorities."""
        sections = []

        # Priority 1: Current goal (always included)
        goal_content = f"## Current Goal\n{state.current_goal}\n"
        if state.original_prompt:
            goal_content += f"\n### Original Request\n{state.original_prompt}\n"
        sections.append(ContextSection(
            name="goal",
            content=goal_content,
            tokens=self._estimate_tokens(goal_content),
            priority=1,
            truncatable=False,
        ))

        # Priority 1: Pending steps (always included)
        if state.pending_steps:
            pending_content = "## Next Steps\n"
            for step in state.pending_steps[:5]:
                pending_content += f"- [ ] {step.description}\n"
            sections.append(ContextSection(
                name="pending",
                content=pending_content,
                tokens=self._estimate_tokens(pending_content),
                priority=1,
                truncatable=False,
            ))

        # Priority 2: Recent completed steps
        if state.completed_steps:
            steps_content = "## Recent Progress\n"
            recent = state.completed_steps[-5:]
            for step in recent:
                status = "✓" if step.status.value == "completed" else "✗"
                steps_content += f"- {status} {step.description}\n"
                if step.tool_used:
                    steps_content += f"  Tool: {step.tool_used}\n"
                if step.tool_output and len(step.tool_output) < 300:
                    steps_content += f"  Result: {step.tool_output[:300]}\n"
                elif step.tool_output:
                    steps_content += f"  Result: {step.tool_output[:200]}... [truncated]\n"
            sections.append(ContextSection(
                name="completed",
                content=steps_content,
                tokens=self._estimate_tokens(steps_content),
                priority=2,
                truncatable=True,
            ))

        # Priority 3: Working memory variables
        if state.variables:
            vars_content = "## Working Memory\n"
            for key, value in list(state.variables.items())[:10]:
                value_str = str(value)[:200]
                vars_content += f"- **{key}**: {value_str}\n"
            sections.append(ContextSection(
                name="variables",
                content=vars_content,
                tokens=self._estimate_tokens(vars_content),
                priority=3,
                truncatable=True,
            ))

        # Priority 3: Relevant memories
        if memories:
            mem_content = "## Relevant Past Experiences\n"
            for mem in memories[:5]:
                mem_content += f"- {mem['content'][:200]}\n"
            sections.append(ContextSection(
                name="memories",
                content=mem_content,
                tokens=self._estimate_tokens(mem_content),
                priority=3,
                truncatable=True,
            ))

        # Priority 4: Upstream context
        if state.upstream_context:
            upstream_content = "## Context from Previous Agents\n"
            for agent_name, context in state.upstream_context.items():
                summary = context[:800] + "..." if len(context) > 800 else context
                upstream_content += f"### From {agent_name}\n{summary}\n\n"
            sections.append(ContextSection(
                name="upstream",
                content=upstream_content,
                tokens=self._estimate_tokens(upstream_content),
                priority=4,
                truncatable=True,
            ))

        # Priority 5: TELOS context
        if telos_context:
            sections.append(ContextSection(
                name="telos",
                content=f"## User Context (TELOS)\n{telos_context}\n",
                tokens=self._estimate_tokens(telos_context),
                priority=5,
                truncatable=True,
            ))

        return sections

    def _fit_to_budget(
        self,
        sections: List[ContextSection],
        budget: ContextBudget,
    ) -> List[ContextSection]:
        """Fit sections to available token budget."""
        available = budget.available
        result = []

        # Sort by priority (lower number = higher priority)
        sections = sorted(sections, key=lambda s: s.priority)

        # First pass: include non-truncatable sections
        for section in sections:
            if not section.truncatable:
                if section.tokens <= available:
                    result.append(section)
                    available -= section.tokens
                else:
                    # Even must-include sections might need truncation in extreme cases
                    truncated = self._truncate_section(section, available)
                    result.append(truncated)
                    available -= truncated.tokens

        # Second pass: add truncatable sections by priority
        for section in sections:
            if section.truncatable:
                if section.tokens <= available:
                    result.append(section)
                    available -= section.tokens
                elif available > 100:  # Only include if reasonable space
                    truncated = self._truncate_section(section, available)
                    result.append(truncated)
                    available -= truncated.tokens
                # If no space, skip this section entirely

        return result

    def _truncate_section(
        self,
        section: ContextSection,
        max_tokens: int,
    ) -> ContextSection:
        """Truncate a section to fit token budget."""
        if section.tokens <= max_tokens:
            return section

        # Estimate character limit (4 chars ≈ 1 token)
        max_chars = max_tokens * 4

        # Truncate content
        truncated_content = section.content[:max_chars]

        # Try to break at a sensible point
        last_newline = truncated_content.rfind("\n")
        if last_newline > max_chars * 0.5:  # If we can keep at least half
            truncated_content = truncated_content[:last_newline]

        truncated_content += "\n[Content truncated to fit context window]\n"

        return ContextSection(
            name=section.name,
            content=truncated_content,
            tokens=self._estimate_tokens(truncated_content),
            priority=section.priority,
            truncatable=section.truncatable,
        )

    def _format_context(self, sections: List[ContextSection]) -> str:
        """Format sections into final context string."""
        # Sort by section order (goal, pending, completed, variables, memories, upstream, telos)
        section_order = ["goal", "pending", "completed", "variables", "memories", "upstream", "telos"]

        ordered = sorted(
            sections,
            key=lambda s: section_order.index(s.name) if s.name in section_order else 99
        )

        return "\n".join(s.content for s in ordered)

    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (4 chars ≈ 1 token)."""
        return len(text) // 4

    def get_context_summary(
        self,
        state: AgentState,
        model_id: str,
    ) -> Dict[str, Any]:
        """
        Get a summary of context allocation for debugging.

        Returns token usage by section and remaining capacity.
        """
        model = self.registry.get_model(model_id)
        context_window = model.context_window if model else 128000

        sections = self._build_sections(state, None, None)

        total_used = sum(s.tokens for s in sections)
        by_section = {s.name: s.tokens for s in sections}

        return {
            "model_id": model_id,
            "context_window": context_window,
            "total_used": total_used,
            "remaining": context_window - total_used,
            "utilization_pct": (total_used / context_window) * 100,
            "by_section": by_section,
        }


# Singleton instance
_context_manager: Optional[ContextWindowManager] = None


def get_context_manager() -> ContextWindowManager:
    """Get the singleton context manager instance."""
    global _context_manager
    if _context_manager is None:
        _context_manager = ContextWindowManager()
    return _context_manager

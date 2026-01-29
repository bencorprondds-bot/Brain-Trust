"""
Semantic Router for Brain Trust

Routes tasks to optimal models based on:
- Task complexity and domain
- Model capabilities and costs
- Budget constraints
- Performance requirements

This removes humans from the model selection loop while preserving
the ability to override when needed.

Design Philosophy:
- Intelligent defaults, manual overrides
- Cost-aware routing
- Graceful fallbacks
- Observable decisions (logging)
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional, List, Dict, Any

from app.core.model_registry import ModelRegistry, ModelCapability, get_registry
from app.core.task_classifier import TaskClassifier, TaskProfile, TaskDomain

logger = logging.getLogger(__name__)


@dataclass
class RoutingDecision:
    """Record of a routing decision for observability."""
    model_id: str
    reason: str
    task_profile: Optional[TaskProfile] = None
    candidates_considered: int = 0
    cost_estimate: float = 0.0
    was_override: bool = False


class SemanticRouter:
    """
    Routes tasks to optimal models based on requirements and constraints.

    Usage:
        router = SemanticRouter()

        # Automatic routing
        decision = router.route(
            task="Write a Python function to parse JSON",
            agent_config={"role": "Developer"}
        )
        model_id = decision.model_id

        # With budget constraint
        decision = router.route(
            task="Analyze this document",
            max_cost_per_1k=0.005
        )

        # Manual override
        decision = router.route(
            task="Any task",
            force_model="claude-opus-4-20250514"
        )
    """

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        classifier: Optional[TaskClassifier] = None,
        default_model: str = "gemini-2.0-flash",
        use_llm_classifier: bool = False,
    ):
        """
        Initialize the router.

        Args:
            registry: Model registry (uses singleton if not provided)
            classifier: Task classifier (creates new if not provided)
            default_model: Fallback model if routing fails
            use_llm_classifier: Use LLM for task classification (more accurate, costs tokens)
        """
        self.registry = registry or get_registry()
        self.classifier = classifier or TaskClassifier(use_llm=use_llm_classifier)
        self.default_model = default_model

        # Track decisions for analysis
        self._decision_history: List[RoutingDecision] = []

    def route(
        self,
        task: str,
        agent_config: Optional[Dict[str, Any]] = None,
        max_cost_per_1k: Optional[float] = None,
        prefer_fast: bool = False,
        force_model: Optional[str] = None,
        min_context: int = 0,
    ) -> RoutingDecision:
        """
        Determine optimal model for a task.

        Args:
            task: The task description/goal
            agent_config: Agent configuration dict with role, goal, etc.
            max_cost_per_1k: Maximum cost per 1k output tokens
            prefer_fast: Prioritize faster models
            force_model: Override to use specific model
            min_context: Minimum context window required

        Returns:
            RoutingDecision with model_id and reasoning
        """
        agent_config = agent_config or {}

        # Handle manual override
        if force_model:
            model = self.registry.get_model(force_model)
            if model and model.available:
                decision = RoutingDecision(
                    model_id=force_model,
                    reason=f"Manual override to {force_model}",
                    was_override=True,
                )
                self._record_decision(decision)
                return decision
            else:
                logger.warning(f"Forced model {force_model} not available, falling back to routing")

        # Classify the task
        role = agent_config.get("role", "")
        profile = self.classifier.classify(task, role)

        # Map task domain to capability
        domain_to_capability = {
            TaskDomain.CODE: "code",
            TaskDomain.CREATIVE: "creative",
            TaskDomain.REASONING: "reasoning",
            TaskDomain.FACTUAL: "factual",
            TaskDomain.TOOL_USE: "tool_use",
            TaskDomain.MULTIMODAL: "vision",
        }
        primary_capability = domain_to_capability.get(profile.primary_domain, "factual")

        # Get suitable models
        candidates = self.registry.get_models_for_task(
            task_type=primary_capability,
            complexity=profile.complexity_score,
            max_cost=max_cost_per_1k,
            require_tools=profile.requires_tools,
            min_context=min_context,
            prefer_fast=prefer_fast,
        )

        if not candidates:
            # No suitable models found - use default
            decision = RoutingDecision(
                model_id=self.default_model,
                reason=f"No models matched requirements, using default ({self.default_model})",
                task_profile=profile,
                candidates_considered=0,
            )
            self._record_decision(decision)
            return decision

        # Select best candidate
        best = candidates[0]

        # Estimate cost
        cost_estimate = best.estimated_cost(
            input_tokens=profile.estimated_input_tokens,
            output_tokens=profile.estimated_output_tokens
        )

        # Build decision record
        decision = RoutingDecision(
            model_id=best.model_id,
            reason=self._build_reason(profile, best, len(candidates)),
            task_profile=profile,
            candidates_considered=len(candidates),
            cost_estimate=cost_estimate,
        )

        self._record_decision(decision)
        logger.info(f"Routed task to {best.model_id}: {decision.reason}")

        return decision

    def route_for_role(
        self,
        role: str,
        task: Optional[str] = None,
        **kwargs
    ) -> RoutingDecision:
        """
        Route based on agent role with sensible defaults.

        Common roles have pre-configured routing preferences:
        - Librarian: Tool-use focused, fast models
        - Writer: Creative-focused, quality models
        - Editor: Reasoning-focused, quality models
        """
        role_lower = role.lower()

        # Role-specific defaults
        role_preferences = {
            "librarian": {
                "prefer_fast": True,
                "primary_capability": "tool_use",
            },
            "writer": {
                "prefer_fast": False,
                "primary_capability": "creative",
            },
            "editor": {
                "prefer_fast": False,
                "primary_capability": "reasoning",
            },
            "developer": {
                "prefer_fast": False,
                "primary_capability": "code",
            },
            "researcher": {
                "prefer_fast": False,
                "primary_capability": "factual",
            },
        }

        prefs = {}
        for key, value in role_preferences.items():
            if key in role_lower:
                prefs = value
                break

        # Merge with kwargs
        merged_kwargs = {**prefs, **kwargs}

        return self.route(
            task=task or f"Perform {role} duties",
            agent_config={"role": role},
            **merged_kwargs
        )

    def get_cheapest_capable_model(
        self,
        capability: str,
        min_score: float = 0.7
    ) -> Optional[str]:
        """Get the cheapest model that meets capability threshold."""
        candidates = []

        for model in self.registry.get_available_models():
            if model.supports(capability, min_score):
                candidates.append(model)

        if not candidates:
            return None

        # Sort by output cost (primary cost driver)
        candidates.sort(key=lambda m: m.cost_per_1k_output)
        return candidates[0].model_id

    def get_fastest_capable_model(
        self,
        capability: str,
        min_score: float = 0.6
    ) -> Optional[str]:
        """Get the fastest model that meets capability threshold."""
        from app.core.model_registry import LatencyTier

        candidates = []

        for model in self.registry.get_available_models():
            if model.supports(capability, min_score):
                candidates.append(model)

        if not candidates:
            return None

        # Sort by latency tier, then cost
        tier_order = {LatencyTier.FAST: 0, LatencyTier.MEDIUM: 1, LatencyTier.SLOW: 2}
        candidates.sort(key=lambda m: (tier_order[m.latency_tier], m.cost_per_1k_output))

        return candidates[0].model_id

    def _build_reason(
        self,
        profile: TaskProfile,
        model: ModelCapability,
        candidate_count: int
    ) -> str:
        """Build human-readable routing reason."""
        parts = [
            f"Task classified as {profile.primary_domain.value}",
            f"complexity {profile.complexity_score}/10",
        ]

        if profile.requires_tools:
            parts.append("requires tools")

        parts.append(f"selected {model.display_name}")
        parts.append(f"from {candidate_count} candidates")

        capability_score = model.capabilities.get(profile.primary_domain.value, 0)
        parts.append(f"({capability_score:.0%} capability)")

        return ", ".join(parts)

    def _record_decision(self, decision: RoutingDecision) -> None:
        """Record decision for analysis."""
        self._decision_history.append(decision)

        # Keep last 100 decisions
        if len(self._decision_history) > 100:
            self._decision_history = self._decision_history[-100:]

    def get_decision_history(self) -> List[RoutingDecision]:
        """Get recent routing decisions."""
        return self._decision_history.copy()

    def get_routing_stats(self) -> Dict[str, Any]:
        """Get statistics about routing decisions."""
        if not self._decision_history:
            return {"total_decisions": 0}

        model_counts: Dict[str, int] = {}
        total_cost = 0.0
        override_count = 0

        for decision in self._decision_history:
            model_counts[decision.model_id] = model_counts.get(decision.model_id, 0) + 1
            total_cost += decision.cost_estimate
            if decision.was_override:
                override_count += 1

        return {
            "total_decisions": len(self._decision_history),
            "model_distribution": model_counts,
            "total_estimated_cost": total_cost,
            "override_rate": override_count / len(self._decision_history),
        }


# Convenience functions
_router: Optional[SemanticRouter] = None


def get_router() -> SemanticRouter:
    """Get the singleton router instance."""
    global _router
    if _router is None:
        _router = SemanticRouter()
    return _router


def route_task(
    task: str,
    role: Optional[str] = None,
    **kwargs
) -> str:
    """
    Quick routing function - returns just the model ID.

    Args:
        task: Task description
        role: Optional agent role
        **kwargs: Additional routing parameters

    Returns:
        model_id string
    """
    router = get_router()
    agent_config = {"role": role} if role else None
    decision = router.route(task, agent_config=agent_config, **kwargs)
    return decision.model_id

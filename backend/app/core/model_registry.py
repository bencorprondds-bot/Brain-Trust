"""
Model Registry for Brain Trust

Provides a centralized database of available LLM models with their capabilities,
costs, and constraints. Enables intelligent model selection based on task requirements.

Design Philosophy:
- Model capabilities are stored in user-configurable YAML
- Runtime availability checks against provider APIs
- Cost-aware routing for budget optimization
- Capability matching for quality optimization
"""

import os
import yaml
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class LatencyTier(str, Enum):
    """Model response latency classification."""
    FAST = "fast"        # < 2s typical
    MEDIUM = "medium"    # 2-10s typical
    SLOW = "slow"        # > 10s typical


class Capability(str, Enum):
    """Model capability categories."""
    CODE = "code"               # Code generation and analysis
    CREATIVE = "creative"       # Creative writing, storytelling
    REASONING = "reasoning"     # Complex logic, math
    FACTUAL = "factual"         # Factual recall, QA
    VISION = "vision"           # Image understanding
    TOOL_USE = "tool_use"       # Function/tool calling
    LONG_CONTEXT = "long_context"  # 100k+ token context


@dataclass
class ModelCapability:
    """Complete specification of a model's capabilities and constraints."""

    # Identity
    model_id: str                    # e.g., "claude-sonnet-4-20250514"
    provider: str                    # "anthropic", "google", "openai"
    display_name: str                # Human-friendly name

    # Costs (USD per 1k tokens)
    cost_per_1k_input: float
    cost_per_1k_output: float

    # Context limits
    context_window: int              # Max input tokens
    max_output: int                  # Max output tokens

    # Performance
    latency_tier: LatencyTier

    # Capabilities (0.0-1.0 quality scores)
    capabilities: Dict[str, float] = field(default_factory=dict)

    # Runtime state
    available: bool = True
    deprecated: bool = False
    notes: str = ""

    def supports(self, capability: str, min_score: float = 0.5) -> bool:
        """Check if model supports a capability above threshold."""
        return self.capabilities.get(capability, 0.0) >= min_score

    def estimated_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Estimate total cost for a request."""
        input_cost = (input_tokens / 1000) * self.cost_per_1k_input
        output_cost = (output_tokens / 1000) * self.cost_per_1k_output
        return input_cost + output_cost

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "model_id": self.model_id,
            "provider": self.provider,
            "display_name": self.display_name,
            "cost_per_1k_input": self.cost_per_1k_input,
            "cost_per_1k_output": self.cost_per_1k_output,
            "context_window": self.context_window,
            "max_output": self.max_output,
            "latency_tier": self.latency_tier.value,
            "capabilities": self.capabilities,
            "available": self.available,
            "deprecated": self.deprecated,
            "notes": self.notes,
        }


class ModelRegistry:
    """
    Central registry for available LLM models.

    Loads model definitions from YAML config and provides query methods
    for finding suitable models based on task requirements.

    Usage:
        registry = ModelRegistry()
        models = registry.get_models_for_task(
            task_type="code",
            complexity=7,
            max_cost=0.01,
            require_tools=True
        )
        best_model = models[0].model_id
    """

    _instance = None
    _DEFAULT_CONFIG = "models.yaml"

    def __new__(cls):
        """Singleton pattern for shared registry access."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.models: Dict[str, ModelCapability] = {}
        self._config_path: Optional[Path] = None

        # Try to load config from multiple locations
        self._load_config()
        self._initialized = True

    def _load_config(self) -> None:
        """Load model configuration from YAML file."""
        # Search order:
        # 1. ~/.pai/models.yaml (user config)
        # 2. ./config/models.yaml (project config)
        # 3. Built-in defaults

        search_paths = [
            Path.home() / ".pai" / "models.yaml",
            Path(__file__).parent.parent.parent.parent / "config" / "models.yaml",
        ]

        for config_path in search_paths:
            if config_path.exists():
                self._config_path = config_path
                self._parse_yaml(config_path)
                logger.info(f"Loaded model registry from {config_path}")
                return

        # No config found - use built-in defaults
        logger.warning("No models.yaml found, using built-in defaults")
        self._load_defaults()

    def _parse_yaml(self, config_path: Path) -> None:
        """Parse YAML config into ModelCapability objects."""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            for model_data in config.get("models", []):
                model = ModelCapability(
                    model_id=model_data["model_id"],
                    provider=model_data["provider"],
                    display_name=model_data.get("display_name", model_data["model_id"]),
                    cost_per_1k_input=float(model_data.get("cost_per_1k_input", 0.0)),
                    cost_per_1k_output=float(model_data.get("cost_per_1k_output", 0.0)),
                    context_window=int(model_data.get("context_window", 8000)),
                    max_output=int(model_data.get("max_output", 4000)),
                    latency_tier=LatencyTier(model_data.get("latency_tier", "medium")),
                    capabilities=model_data.get("capabilities", {}),
                    available=model_data.get("available", True),
                    deprecated=model_data.get("deprecated", False),
                    notes=model_data.get("notes", ""),
                )
                self.models[model.model_id] = model

            logger.info(f"Loaded {len(self.models)} models from config")

        except Exception as e:
            logger.error(f"Failed to parse models.yaml: {e}")
            self._load_defaults()

    def _load_defaults(self) -> None:
        """Load built-in default model configurations."""
        defaults = [
            ModelCapability(
                model_id="claude-sonnet-4-20250514",
                provider="anthropic",
                display_name="Claude Sonnet 4",
                cost_per_1k_input=0.003,
                cost_per_1k_output=0.015,
                context_window=200000,
                max_output=8192,
                latency_tier=LatencyTier.MEDIUM,
                capabilities={
                    "code": 0.95,
                    "creative": 0.90,
                    "reasoning": 0.90,
                    "factual": 0.85,
                    "tool_use": 0.95,
                    "long_context": 0.90,
                },
            ),
            ModelCapability(
                model_id="claude-opus-4-20250514",
                provider="anthropic",
                display_name="Claude Opus 4",
                cost_per_1k_input=0.015,
                cost_per_1k_output=0.075,
                context_window=200000,
                max_output=8192,
                latency_tier=LatencyTier.SLOW,
                capabilities={
                    "code": 0.98,
                    "creative": 0.95,
                    "reasoning": 0.98,
                    "factual": 0.90,
                    "tool_use": 0.95,
                    "long_context": 0.95,
                },
            ),
            ModelCapability(
                model_id="gemini-2.0-flash",
                provider="google",
                display_name="Gemini 2.0 Flash",
                cost_per_1k_input=0.00035,
                cost_per_1k_output=0.0015,
                context_window=1000000,
                max_output=8192,
                latency_tier=LatencyTier.FAST,
                capabilities={
                    "code": 0.85,
                    "creative": 0.80,
                    "reasoning": 0.80,
                    "factual": 0.85,
                    "tool_use": 0.85,
                    "long_context": 0.95,
                    "vision": 0.85,
                },
            ),
            ModelCapability(
                model_id="gpt-4o",
                provider="openai",
                display_name="GPT-4o",
                cost_per_1k_input=0.005,
                cost_per_1k_output=0.015,
                context_window=128000,
                max_output=4096,
                latency_tier=LatencyTier.MEDIUM,
                capabilities={
                    "code": 0.90,
                    "creative": 0.85,
                    "reasoning": 0.90,
                    "factual": 0.90,
                    "tool_use": 0.90,
                    "vision": 0.90,
                },
            ),
            ModelCapability(
                model_id="gpt-4o-mini",
                provider="openai",
                display_name="GPT-4o Mini",
                cost_per_1k_input=0.00015,
                cost_per_1k_output=0.0006,
                context_window=128000,
                max_output=4096,
                latency_tier=LatencyTier.FAST,
                capabilities={
                    "code": 0.75,
                    "creative": 0.70,
                    "reasoning": 0.70,
                    "factual": 0.80,
                    "tool_use": 0.80,
                    "vision": 0.75,
                },
            ),
        ]

        for model in defaults:
            self.models[model.model_id] = model

    def get_model(self, model_id: str) -> Optional[ModelCapability]:
        """Get a specific model by ID."""
        return self.models.get(model_id)

    def get_all_models(self) -> List[ModelCapability]:
        """Get all registered models."""
        return list(self.models.values())

    def get_available_models(self) -> List[ModelCapability]:
        """Get only available (non-deprecated) models."""
        return [m for m in self.models.values() if m.available and not m.deprecated]

    def get_models_by_provider(self, provider: str) -> List[ModelCapability]:
        """Get all models from a specific provider."""
        return [m for m in self.models.values() if m.provider == provider]

    def get_models_for_task(
        self,
        task_type: str,
        complexity: int = 5,
        max_cost: Optional[float] = None,
        require_tools: bool = False,
        min_context: int = 0,
        prefer_fast: bool = False,
    ) -> List[ModelCapability]:
        """
        Get models suitable for a task, ranked by fit.

        Args:
            task_type: Primary capability needed ("code", "creative", etc.)
            complexity: Task complexity 1-10 (higher = need better model)
            max_cost: Maximum cost per 1k output tokens (None = no limit)
            require_tools: Must support tool/function calling
            min_context: Minimum context window required
            prefer_fast: Prioritize faster models over quality

        Returns:
            List of ModelCapability objects, ranked by suitability
        """
        candidates = []

        # Minimum capability score based on complexity
        min_score = 0.5 + (complexity / 20)  # 5 -> 0.75, 10 -> 1.0

        for model in self.get_available_models():
            # Filter: Must support task type at required level
            if not model.supports(task_type, min_score):
                continue

            # Filter: Must support tools if required
            if require_tools and not model.supports("tool_use", 0.7):
                continue

            # Filter: Must have sufficient context window
            if model.context_window < min_context:
                continue

            # Filter: Must be within budget
            if max_cost is not None and model.cost_per_1k_output > max_cost:
                continue

            candidates.append(model)

        # Sort by suitability
        def score_model(m: ModelCapability) -> float:
            """Higher score = better fit."""
            score = m.capabilities.get(task_type, 0.0) * 100

            # Bonus for fast models if preferred
            if prefer_fast:
                if m.latency_tier == LatencyTier.FAST:
                    score += 20
                elif m.latency_tier == LatencyTier.MEDIUM:
                    score += 10

            # Penalty for cost (inverted - lower cost = higher score)
            # Normalize: $0.001 = 10 points, $0.01 = 1 point, $0.1 = 0.1 points
            cost_score = 10 / (m.cost_per_1k_output * 100 + 1)
            score += cost_score

            return score

        candidates.sort(key=score_model, reverse=True)
        return candidates

    def check_availability(self, model_id: str) -> bool:
        """
        Runtime check if model is available from provider.

        TODO: Implement actual API health checks for each provider.
        For now, returns the static 'available' flag.
        """
        model = self.get_model(model_id)
        if not model:
            return False

        # TODO: Add actual API ping
        # Example for Anthropic:
        # try:
        #     response = anthropic.models.retrieve(model_id)
        #     return response.status == "available"
        # except:
        #     return False

        return model.available

    def reload(self) -> None:
        """Reload configuration from disk."""
        self.models.clear()
        self._load_config()


# Module-level convenience function
def get_registry() -> ModelRegistry:
    """Get the singleton registry instance."""
    return ModelRegistry()

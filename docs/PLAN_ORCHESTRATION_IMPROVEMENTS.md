# Plan: Orchestration Improvements for Future-Proofing Brain Trust

**Date:** January 2026
**Status:** Planning Phase
**Horizon:** 5-10 Year Architecture Resilience

---

## Executive Summary

This document outlines a comprehensive plan to evolve Brain Trust from a "manual model selection" system to an **algorithmically orchestrated, model-agnostic platform**. Based on analysis of current architecture and strategic planning discussions, four major architectural improvements are proposed:

1. **Semantic Router Layer** - Remove humans from model selection loop
2. **Tool Protocol Abstraction** - Decouple tools from model-specific schemas
3. **State Persistence Layer** - Isolate memory for "brain transplant" resilience
4. **Evaluation Pipeline** - Automated regression testing for model swaps

The core thesis: **The value is not in the intelligence (which will become commodity), but in the architecture of control.**

---

## Current State Analysis

### What We Have

| Component | Current Implementation | Location |
|-----------|----------------------|----------|
| Model Selection | Hardcoded string mapping in `workflow_parser.py` | Lines 121-144 |
| Tool Assignment | Role-based, priority-ordered via CrewAI BaseTool | Lines 146-172 |
| User Context | File-based TELOS layer with 60s cache | `context_loader.py` |
| Execution Logging | Dual persistence (Markdown + Supabase) | `journaling.py` |
| Agent Memory | **None** - no long-term memory | N/A |
| Testing | Pytest with markers, integration-heavy | `conftest.py` |

### Critical Gaps

1. **Model Selection is Manual** - Dropdown in UI, no cost/capability awareness
2. **Tools Tightly Coupled** - CrewAI-specific schemas, no abstraction layer
3. **No Long-Term Memory** - Agents don't learn from past executions
4. **No Output Evaluation** - Tests check HTTP codes, not response quality
5. **Sequential Only** - No parallel execution or hierarchical delegation

---

## Phase 1: Semantic Router Layer

### Problem Statement

Current model selection assumes humans will always be the decision engine. In 5 years, the number of specialized models will exceed cognitive tracking capacity. A dropdown becomes cognitive load, not a feature.

### Architecture Design

```
┌─────────────────────────────────────────────────────────────┐
│                     INCOMING TASK                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    ROUTER NODE                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  1. Task Classifier (lightweight model)              │   │
│  │     - Complexity scoring (1-10)                      │   │
│  │     - Domain detection (code, creative, factual)     │   │
│  │     - Tool requirements prediction                   │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  2. Model Registry Lookup                            │   │
│  │     - Cost per token                                 │   │
│  │     - Latency characteristics                        │   │
│  │     - Capability matrix                              │   │
│  │     - Context window size                            │   │
│  └─────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  3. Routing Decision                                 │   │
│  │     - Match task requirements to model capabilities  │   │
│  │     - Apply cost constraints                         │   │
│  │     - Return optimal model ID                        │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              SELECTED MODEL EXECUTES TASK                   │
└─────────────────────────────────────────────────────────────┘
```

### Implementation Components

#### 1.1 Model Registry (`backend/app/core/model_registry.py`)

```python
# Proposed schema
@dataclass
class ModelCapability:
    model_id: str                    # e.g., "claude-sonnet-4-20250514"
    provider: str                    # "anthropic", "google", "openai"
    cost_per_1k_input: float         # USD
    cost_per_1k_output: float        # USD
    context_window: int              # tokens
    max_output: int                  # tokens
    latency_tier: str                # "fast", "medium", "slow"
    capabilities: List[str]          # ["code", "creative", "reasoning", "vision"]
    tool_use_quality: float          # 0.0-1.0 score
    availability: bool               # runtime check

class ModelRegistry:
    def __init__(self, config_path: str = "~/.pai/models.yaml"):
        self.models: Dict[str, ModelCapability] = {}
        self._load_config(config_path)

    def get_models_for_task(
        self,
        task_type: str,
        complexity: int,
        max_cost: Optional[float] = None,
        require_tools: bool = False
    ) -> List[ModelCapability]:
        """Return ranked list of suitable models."""
        pass

    def check_availability(self, model_id: str) -> bool:
        """Runtime API check for model availability."""
        pass
```

#### 1.2 Task Classifier (`backend/app/core/task_classifier.py`)

```python
class TaskClassifier:
    """Lightweight classifier to analyze incoming tasks."""

    def __init__(self, classifier_model: str = "gemini-2.0-flash"):
        # Use cheap, fast model for classification
        self.model = classifier_model

    def classify(self, task_description: str) -> TaskProfile:
        """
        Analyze task and return profile.

        Returns:
            TaskProfile with:
            - complexity_score: 1-10
            - domain: "code" | "creative" | "factual" | "reasoning" | "multimodal"
            - estimated_tokens: int
            - requires_tools: bool
            - tool_types: List[str]
        """
        pass
```

#### 1.3 Router Logic (`backend/app/core/semantic_router.py`)

```python
class SemanticRouter:
    """Routes tasks to optimal models based on requirements and constraints."""

    def __init__(
        self,
        registry: ModelRegistry,
        classifier: TaskClassifier,
        cost_budget: Optional[float] = None
    ):
        self.registry = registry
        self.classifier = classifier
        self.cost_budget = cost_budget

    def route(self, task: str, agent_config: dict) -> str:
        """
        Determine optimal model for task.

        Strategy:
        1. Classify task complexity and domain
        2. Query registry for capable models
        3. Apply cost constraints
        4. Return model_id

        Fallback: If routing fails, use agent's configured default.
        """
        profile = self.classifier.classify(task)

        candidates = self.registry.get_models_for_task(
            task_type=profile.domain,
            complexity=profile.complexity_score,
            max_cost=self.cost_budget,
            require_tools=profile.requires_tools
        )

        if not candidates:
            return agent_config.get('model', 'claude-sonnet-4-20250514')

        # Return best match (first in ranked list)
        return candidates[0].model_id
```

### Migration Path

1. **Phase 1a:** Create model registry with static YAML config
2. **Phase 1b:** Implement task classifier using flash model
3. **Phase 1c:** Add router as optional feature (UI toggle: "Auto-select model")
4. **Phase 1d:** Collect routing decisions for evaluation
5. **Phase 1e:** Make auto-routing the default, manual override available

### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `backend/app/core/model_registry.py` | Create | Model capability database |
| `backend/app/core/task_classifier.py` | Create | Lightweight task analysis |
| `backend/app/core/semantic_router.py` | Create | Routing decision logic |
| `backend/app/core/workflow_parser.py` | Modify | Integrate router at model resolution |
| `~/.pai/models.yaml` | Create | User-configurable model registry |
| `frontend/app/page.tsx` | Modify | Add auto-route toggle to agent nodes |

---

## Phase 2: Tool Protocol Abstraction (MCP-Inspired)

### Problem Statement

Tools are currently defined using CrewAI-specific schemas (`BaseTool`, Pydantic `args_schema`). If model providers change their tool calling interfaces, or we want to swap CrewAI for another framework, all tools break.

### The MCP Approach

The Model Context Protocol (MCP) provides a standard for tool connectivity. We should build an **Internal Interface Definition Language (IDL)** that:

1. Defines tools in a provider-agnostic format
2. Uses adapters to translate to model-specific schemas
3. Allows tool swapping without touching agent code

### Architecture Design

```
┌─────────────────────────────────────────────────────────────┐
│                    BRAIN TRUST IDL                          │
│                 (Internal Tool Definition)                   │
│                                                             │
│  {                                                          │
│    "tool_id": "drive_list",                                 │
│    "name": "Google Drive Lister",                           │
│    "description": "Lists files in a Drive folder",          │
│    "parameters": {                                          │
│      "folder_id": {"type": "string", "required": true}      │
│    },                                                       │
│    "returns": {"type": "string"},                           │
│    "executor": "backend.app.tools.drive_tool:DriveListTool" │
│  }                                                          │
└─────────────────────────────────────────────────────────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ▼                 ▼                 ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│  CrewAI Adapter   │ │  OpenAI Adapter   │ │  Anthropic Adapter│
│                   │ │                   │ │                   │
│  Converts to      │ │  Converts to      │ │  Converts to      │
│  BaseTool schema  │ │  function calling │ │  tool_use schema  │
└───────────────────┘ └───────────────────┘ └───────────────────┘
```

### Implementation Components

#### 2.1 Tool Definition Schema (`backend/app/tools/schema.py`)

```python
from typing import Any, Dict, List, Optional, Callable
from pydantic import BaseModel
from enum import Enum

class ParameterType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"

class ToolParameter(BaseModel):
    name: str
    type: ParameterType
    description: str
    required: bool = True
    default: Optional[Any] = None
    enum: Optional[List[str]] = None

class ToolDefinition(BaseModel):
    """Provider-agnostic tool definition."""
    tool_id: str
    name: str
    description: str
    parameters: List[ToolParameter]
    returns: ParameterType
    executor: str  # Module path to implementation
    version: str = "1.0.0"

    # Metadata for routing
    category: str = "general"  # "file", "search", "code", "api"
    requires_auth: bool = False
    estimated_latency_ms: int = 1000
```

#### 2.2 Tool Registry (`backend/app/tools/registry.py`)

```python
class ToolRegistry:
    """Central registry for all available tools."""

    def __init__(self, tools_dir: str = "~/.pai/tools"):
        self.tools: Dict[str, ToolDefinition] = {}
        self._load_builtin_tools()
        self._load_user_tools(tools_dir)

    def register(self, definition: ToolDefinition):
        """Register a tool definition."""
        self.tools[definition.tool_id] = definition

    def get_for_adapter(
        self,
        adapter_type: str,
        tool_ids: Optional[List[str]] = None
    ) -> List[Any]:
        """
        Get tools converted for specific adapter.

        adapter_type: "crewai" | "openai" | "anthropic" | "mcp"
        """
        adapter = self._get_adapter(adapter_type)
        tools = tool_ids or list(self.tools.keys())
        return [adapter.convert(self.tools[tid]) for tid in tools]
```

#### 2.3 Adapter Interface (`backend/app/tools/adapters/base.py`)

```python
from abc import ABC, abstractmethod

class ToolAdapter(ABC):
    """Base class for tool format adapters."""

    @abstractmethod
    def convert(self, definition: ToolDefinition) -> Any:
        """Convert IDL definition to provider-specific format."""
        pass

    @abstractmethod
    def execute(self, tool_id: str, parameters: dict) -> Any:
        """Execute tool and return result."""
        pass
```

#### 2.4 CrewAI Adapter (`backend/app/tools/adapters/crewai_adapter.py`)

```python
from crewai.tools import BaseTool
from pydantic import BaseModel, create_model

class CrewAIAdapter(ToolAdapter):
    """Converts Brain Trust IDL to CrewAI BaseTool."""

    def convert(self, definition: ToolDefinition) -> BaseTool:
        # Dynamically create Pydantic schema from parameters
        fields = {}
        for param in definition.parameters:
            python_type = self._map_type(param.type)
            fields[param.name] = (python_type, param.default)

        ArgsSchema = create_model(
            f"{definition.tool_id}Input",
            **fields
        )

        # Create BaseTool subclass
        executor = self._load_executor(definition.executor)

        class DynamicTool(BaseTool):
            name: str = definition.name
            description: str = definition.description
            args_schema = ArgsSchema

            def _run(self, **kwargs):
                return executor(**kwargs)

        return DynamicTool()
```

### Tool Definition Files

Tools would be defined in YAML for easy editing:

```yaml
# ~/.pai/tools/drive_tools.yaml
tools:
  - tool_id: drive_list
    name: "Google Drive Lister"
    description: "Lists files and folders in a Google Drive folder"
    parameters:
      - name: folder_id
        type: string
        description: "The ID of the folder to list"
        required: true
    returns: string
    executor: "backend.app.tools.drive_tool:drive_list_impl"
    category: file
    requires_auth: true

  - tool_id: drive_read
    name: "Google Doc Reader"
    description: "Reads text content from a Google Doc"
    parameters:
      - name: file_id
        type: string
        description: "The ID of the document to read"
        required: true
    returns: string
    executor: "backend.app.tools.drive_tool:drive_read_impl"
    category: file
    requires_auth: true
```

### Migration Path

1. **Phase 2a:** Define IDL schema and create tool definition files for existing tools
2. **Phase 2b:** Implement CrewAI adapter (maintains current functionality)
3. **Phase 2c:** Refactor `workflow_parser.py` to use registry + adapter
4. **Phase 2d:** Add OpenAI/Anthropic adapters for direct API usage
5. **Phase 2e:** Implement MCP adapter for future compatibility

### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `backend/app/tools/schema.py` | Create | IDL schema definitions |
| `backend/app/tools/registry.py` | Create | Central tool registry |
| `backend/app/tools/adapters/` | Create | Adapter implementations |
| `~/.pai/tools/*.yaml` | Create | Tool definition files |
| `backend/app/core/workflow_parser.py` | Modify | Use registry instead of hardcoded tools |
| `backend/app/tools/drive_tool.py` | Modify | Extract pure functions from BaseTool classes |

---

## Phase 3: State Persistence Layer

### Problem Statement

Current architecture couples the "Brain" (LLM) with the "Soul" (Memory). If we swap from a 2M token context model to an 8k specialist, the agent gets lobotomized. Furthermore, agents don't learn from past executions.

### Architecture Design

```
┌─────────────────────────────────────────────────────────────┐
│                      AGENT STATE                            │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                 STATE OBJECT (JSON)                    │ │
│  │                                                        │ │
│  │  {                                                     │ │
│  │    "agent_id": "librarian-001",                       │ │
│  │    "workflow_id": "wf-abc123",                        │ │
│  │    "created_at": "2026-01-28T10:00:00Z",             │ │
│  │    "current_goal": "Find project files",              │ │
│  │    "completed_steps": [...],                          │ │
│  │    "pending_steps": [...],                            │ │
│  │    "variables": {"target_folder": "inbox"},           │ │
│  │    "tool_results_cache": {...},                       │ │
│  │    "error_history": [...],                            │ │
│  │    "metadata": {...}                                  │ │
│  │  }                                                     │ │
│  └───────────────────────────────────────────────────────┘ │
│                           │                                 │
│              ┌────────────┴────────────┐                   │
│              ▼                         ▼                   │
│  ┌─────────────────────┐   ┌─────────────────────┐        │
│  │   SHORT-TERM        │   │   LONG-TERM          │        │
│  │   (Context Window)  │   │   (Persistent Store) │        │
│  │                     │   │                      │        │
│  │   - Current task    │   │   - Vector embeddings│        │
│  │   - Recent steps    │   │   - Execution history│        │
│  │   - Active vars     │   │   - Learned patterns │        │
│  └─────────────────────┘   └─────────────────────┘        │
└─────────────────────────────────────────────────────────────┘
```

### Implementation Components

#### 3.1 State Schema (`backend/app/core/state/schema.py`)

```python
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional
import json

@dataclass
class StepRecord:
    step_id: str
    description: str
    status: str  # "pending", "in_progress", "completed", "failed"
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    tool_used: Optional[str] = None
    tool_input: Optional[Dict] = None
    tool_output: Optional[str] = None
    error: Optional[str] = None

@dataclass
class AgentState:
    """Model-agnostic agent state that survives brain transplants."""

    # Identity
    agent_id: str
    workflow_id: str
    name: str
    role: str

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    # Task tracking
    current_goal: str = ""
    completed_steps: List[StepRecord] = field(default_factory=list)
    pending_steps: List[StepRecord] = field(default_factory=list)

    # Working memory
    variables: Dict[str, Any] = field(default_factory=dict)
    tool_results_cache: Dict[str, str] = field(default_factory=dict)

    # Error handling
    error_history: List[Dict] = field(default_factory=list)
    retry_count: int = 0

    # Metadata
    model_used: Optional[str] = None
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0

    def to_json(self) -> str:
        """Serialize state for persistence."""
        return json.dumps(self.__dict__, default=str, indent=2)

    @classmethod
    def from_json(cls, data: str) -> "AgentState":
        """Deserialize state from persistence."""
        return cls(**json.loads(data))

    def to_context_prompt(self, max_tokens: int = 4000) -> str:
        """
        Generate context prompt for LLM consumption.
        Automatically truncates to fit context window.
        """
        pass
```

#### 3.2 State Manager (`backend/app/core/state/manager.py`)

```python
class StateManager:
    """Manages agent state persistence and retrieval."""

    def __init__(
        self,
        storage_backend: str = "sqlite",  # or "supabase", "redis"
        db_path: str = "~/.pai/state.db"
    ):
        self.backend = self._init_backend(storage_backend, db_path)

    async def save(self, state: AgentState) -> None:
        """Persist agent state."""
        state.updated_at = datetime.utcnow()
        await self.backend.upsert(state.agent_id, state.to_json())

    async def load(self, agent_id: str) -> Optional[AgentState]:
        """Load agent state."""
        data = await self.backend.get(agent_id)
        return AgentState.from_json(data) if data else None

    async def get_history(
        self,
        agent_id: str,
        limit: int = 10
    ) -> List[AgentState]:
        """Get historical states for learning."""
        pass
```

#### 3.3 Long-Term Memory (`backend/app/core/state/memory.py`)

```python
class LongTermMemory:
    """Vector-based long-term memory for semantic retrieval."""

    def __init__(
        self,
        embedding_model: str = "text-embedding-3-small",
        vector_store: str = "chromadb"  # or "pinecone", "qdrant"
    ):
        self.embedder = self._init_embedder(embedding_model)
        self.store = self._init_store(vector_store)

    async def remember(
        self,
        agent_id: str,
        content: str,
        metadata: Dict[str, Any]
    ) -> None:
        """Store memory with embedding."""
        embedding = await self.embedder.embed(content)
        await self.store.insert(
            id=f"{agent_id}:{uuid4()}",
            embedding=embedding,
            content=content,
            metadata=metadata
        )

    async def recall(
        self,
        agent_id: str,
        query: str,
        limit: int = 5
    ) -> List[Dict]:
        """Retrieve relevant memories."""
        query_embedding = await self.embedder.embed(query)
        return await self.store.search(
            embedding=query_embedding,
            filter={"agent_id": agent_id},
            limit=limit
        )

    async def learn_from_execution(
        self,
        state: AgentState,
        final_output: str,
        success: bool
    ) -> None:
        """
        Extract learnings from completed execution.
        Store patterns for future retrieval.
        """
        # Extract key decisions and outcomes
        learnings = self._extract_learnings(state, final_output, success)

        for learning in learnings:
            await self.remember(
                agent_id=state.agent_id,
                content=learning["content"],
                metadata={
                    "type": "learning",
                    "success": success,
                    "workflow_id": state.workflow_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
```

#### 3.4 Context Windowing (`backend/app/core/state/context.py`)

```python
class ContextWindowManager:
    """Manages context window allocation across model swaps."""

    def __init__(self, model_registry: ModelRegistry):
        self.registry = model_registry

    def prepare_context(
        self,
        state: AgentState,
        model_id: str,
        memories: List[Dict]
    ) -> str:
        """
        Prepare context that fits target model's window.

        Priority order:
        1. Current goal and pending steps (always included)
        2. Recent completed steps (last 3-5)
        3. Relevant memories (semantic search results)
        4. Variable state
        5. TELOS context (truncated if needed)
        """
        model = self.registry.get_model(model_id)
        max_context = model.context_window - model.max_output - 1000  # buffer

        context_parts = []
        tokens_used = 0

        # Priority 1: Current task (always)
        task_context = self._format_current_task(state)
        context_parts.append(task_context)
        tokens_used += self._count_tokens(task_context)

        # Priority 2-5: Add until budget exhausted
        # ... (implementation details)

        return "\n\n".join(context_parts)
```

### Migration Path

1. **Phase 3a:** Define state schema and implement basic persistence (SQLite)
2. **Phase 3b:** Integrate state manager into workflow execution
3. **Phase 3c:** Add vector store for long-term memory (ChromaDB)
4. **Phase 3d:** Implement context windowing for model swaps
5. **Phase 3e:** Add learning extraction from completed executions

### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `backend/app/core/state/schema.py` | Create | State data structures |
| `backend/app/core/state/manager.py` | Create | Persistence layer |
| `backend/app/core/state/memory.py` | Create | Long-term memory |
| `backend/app/core/state/context.py` | Create | Context window management |
| `backend/app/core/workflow_parser.py` | Modify | Integrate state management |
| `backend/app/api/routes.py` | Modify | Save state after execution |
| `~/.pai/state.db` | Create | SQLite state database |

---

## Phase 4: Evaluation Pipeline

### Problem Statement

Current tests check HTTP response codes, not LLM output quality. Without automated metrics, model swaps cause silent degradation. You cannot claim "future-proof" without mathematical proof that Model B outperforms Model A for your use cases.

### Architecture Design

```
┌─────────────────────────────────────────────────────────────┐
│                    EVAL PIPELINE                            │
│                                                             │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                  TEST SUITE                            │ │
│  │                                                        │ │
│  │  test_cases/                                           │ │
│  │  ├── librarian/                                        │ │
│  │  │   ├── find_folder.yaml                             │ │
│  │  │   ├── read_document.yaml                           │ │
│  │  │   └── create_document.yaml                         │ │
│  │  ├── writer/                                           │ │
│  │  │   ├── blog_post.yaml                               │ │
│  │  │   └── summary.yaml                                 │ │
│  │  └── general/                                          │ │
│  │      ├── tool_selection.yaml                          │ │
│  │      └── reasoning.yaml                               │ │
│  └───────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           ▼                                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                  EVAL RUNNER                           │ │
│  │                                                        │ │
│  │  For each test case:                                   │ │
│  │  1. Execute with Model A                               │ │
│  │  2. Execute with Model B                               │ │
│  │  3. Apply evaluators                                   │ │
│  │  4. Compare scores                                     │ │
│  │  5. Generate report                                    │ │
│  └───────────────────────────────────────────────────────┘ │
│                           │                                 │
│                           ▼                                 │
│  ┌───────────────────────────────────────────────────────┐ │
│  │                  EVALUATORS                            │ │
│  │                                                        │ │
│  │  - ToolSelectionEvaluator: Did it pick the right tool?│ │
│  │  - OutputFormatEvaluator: Is output valid JSON/etc?   │ │
│  │  - FactualAccuracyEvaluator: Are facts correct?       │ │
│  │  - TaskCompletionEvaluator: Did it achieve the goal?  │ │
│  │  - LLMJudgeEvaluator: GPT-4 judges quality            │ │
│  └───────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Implementation Components

#### 4.1 Test Case Schema (`backend/app/evals/schema.py`)

```python
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class TestCase(BaseModel):
    """Single evaluation test case."""
    id: str
    name: str
    description: str

    # Input
    agent_role: str
    agent_goal: str
    input_prompt: str

    # Expected behavior
    expected_tools: Optional[List[str]] = None  # Tools that should be called
    expected_output_contains: Optional[List[str]] = None  # Keywords
    expected_output_format: Optional[str] = None  # "json", "markdown", etc.
    expected_facts: Optional[List[str]] = None  # Verifiable facts

    # Evaluator config
    evaluators: List[str] = ["task_completion"]
    passing_threshold: float = 0.7  # 0.0-1.0

    # Metadata
    tags: List[str] = []
    timeout_seconds: int = 60

class EvalResult(BaseModel):
    """Result of running a test case."""
    test_case_id: str
    model_id: str

    # Scores
    scores: Dict[str, float]  # evaluator_name -> score
    overall_score: float
    passed: bool

    # Debug info
    raw_output: str
    tools_called: List[str]
    tokens_used: int
    latency_ms: int
    cost_usd: float
    error: Optional[str] = None
```

#### 4.2 Test Case YAML Format

```yaml
# ~/.pai/evals/librarian/find_folder.yaml
id: librarian-find-folder-001
name: "Find Inbox Folder"
description: "Librarian should find the Inbox folder in Shared Drive"

agent_role: "Librarian"
agent_goal: "Find and return the ID of the Inbox folder"
input_prompt: "Find the Inbox folder in our Shared Drive"

expected_tools:
  - "Google Drive Folder Finder"

expected_output_contains:
  - "inbox"
  - "folder"
  - "ID"

evaluators:
  - tool_selection
  - output_format
  - task_completion

passing_threshold: 0.8

tags:
  - drive
  - librarian
  - folder
```

#### 4.3 Evaluators (`backend/app/evals/evaluators/`)

```python
# base.py
class BaseEvaluator(ABC):
    @abstractmethod
    def evaluate(
        self,
        test_case: TestCase,
        output: str,
        tools_called: List[str]
    ) -> float:
        """Return score 0.0-1.0"""
        pass

# tool_selection.py
class ToolSelectionEvaluator(BaseEvaluator):
    """Evaluates if correct tools were selected."""

    def evaluate(self, test_case, output, tools_called) -> float:
        if not test_case.expected_tools:
            return 1.0  # No expectation = pass

        expected = set(test_case.expected_tools)
        actual = set(tools_called)

        # Jaccard similarity
        intersection = len(expected & actual)
        union = len(expected | actual)

        return intersection / union if union > 0 else 0.0

# output_format.py
class OutputFormatEvaluator(BaseEvaluator):
    """Evaluates if output matches expected format."""

    def evaluate(self, test_case, output, tools_called) -> float:
        if not test_case.expected_output_format:
            return 1.0

        if test_case.expected_output_format == "json":
            try:
                json.loads(output)
                return 1.0
            except:
                return 0.0

        # ... other format checks

# llm_judge.py
class LLMJudgeEvaluator(BaseEvaluator):
    """Uses a separate LLM to judge output quality."""

    def __init__(self, judge_model: str = "gpt-4o"):
        self.judge = judge_model

    def evaluate(self, test_case, output, tools_called) -> float:
        prompt = f"""
        Task: {test_case.input_prompt}
        Expected goal: {test_case.agent_goal}

        Agent output:
        {output}

        Rate the output quality from 0 to 10:
        - Did it complete the task?
        - Is the output accurate?
        - Is it well-formatted?

        Return only a number 0-10.
        """

        score = self._call_judge(prompt)
        return score / 10.0
```

#### 4.4 Eval Runner (`backend/app/evals/runner.py`)

```python
class EvalRunner:
    """Runs evaluation suite across models."""

    def __init__(
        self,
        test_dir: str = "~/.pai/evals",
        output_dir: str = "~/.pai/eval_results"
    ):
        self.test_dir = Path(test_dir).expanduser()
        self.output_dir = Path(output_dir).expanduser()
        self.evaluators = self._load_evaluators()

    async def run_comparison(
        self,
        model_a: str,
        model_b: str,
        test_filter: Optional[str] = None  # e.g., "librarian/*"
    ) -> ComparisonReport:
        """
        Run all matching tests on both models.
        Return comparison report.
        """
        test_cases = self._load_test_cases(test_filter)
        results_a = []
        results_b = []

        for test_case in test_cases:
            result_a = await self._run_single(test_case, model_a)
            result_b = await self._run_single(test_case, model_b)
            results_a.append(result_a)
            results_b.append(result_b)

        return self._generate_comparison(results_a, results_b)

    async def run_regression(
        self,
        model_id: str,
        baseline_results: str  # path to previous results
    ) -> RegressionReport:
        """
        Compare current model against historical baseline.
        Flag any regressions.
        """
        pass
```

#### 4.5 CLI Interface

```bash
# Run full eval suite
brain-trust eval run --model claude-sonnet-4-20250514

# Compare two models
brain-trust eval compare \
    --model-a claude-sonnet-4-20250514 \
    --model-b gemini-2.0-flash \
    --filter "librarian/*"

# Check for regressions
brain-trust eval regression \
    --model claude-sonnet-4-20250514 \
    --baseline ~/.pai/eval_results/2026-01-01.json
```

### Migration Path

1. **Phase 4a:** Define test case schema and create initial test cases
2. **Phase 4b:** Implement basic evaluators (tool selection, output format)
3. **Phase 4c:** Build eval runner with single-model execution
4. **Phase 4d:** Add model comparison functionality
5. **Phase 4e:** Implement LLM judge evaluator
6. **Phase 4f:** Add regression detection and CI integration

### Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `backend/app/evals/schema.py` | Create | Test case and result schemas |
| `backend/app/evals/runner.py` | Create | Evaluation execution engine |
| `backend/app/evals/evaluators/` | Create | Evaluator implementations |
| `backend/app/evals/cli.py` | Create | CLI commands |
| `~/.pai/evals/` | Create | Test case directory |
| `pyproject.toml` or `setup.py` | Modify | Add CLI entry point |

---

## Implementation Roadmap

### Priority Order

Based on impact and dependency analysis:

```
Phase 1: Semantic Router ─────────────────────────────────────┐
  - Highest immediate value                                   │
  - Reduces costs immediately                                 │
  - Foundation for other phases                               │
                                                              │
Phase 2: Tool Abstraction ────────────────────────────────────┤
  - Required before major framework changes                   │  PARALLEL
  - Enables model flexibility                                 │  WORK
  - Medium complexity                                         │  POSSIBLE
                                                              │
Phase 3: State Persistence ───────────────────────────────────┤
  - Enables long-term learning                                │
  - Required for production reliability                       │
  - Higher complexity                                         │
                                                              │
Phase 4: Eval Pipeline ───────────────────────────────────────┘
  - Required before any model swaps
  - Validates all other phases
  - Should run continuously
```

### Suggested Timeline

| Phase | Component | Estimated Effort | Dependencies |
|-------|-----------|------------------|--------------|
| 1a | Model Registry | 1-2 days | None |
| 1b | Task Classifier | 2-3 days | 1a |
| 1c | Semantic Router | 2-3 days | 1a, 1b |
| 2a | Tool IDL Schema | 1 day | None |
| 2b | CrewAI Adapter | 2-3 days | 2a |
| 2c | Registry Integration | 1-2 days | 2b |
| 3a | State Schema | 1 day | None |
| 3b | State Manager | 2-3 days | 3a |
| 3c | Long-Term Memory | 3-4 days | 3b |
| 4a | Test Case Schema | 1 day | None |
| 4b | Basic Evaluators | 2-3 days | 4a |
| 4c | Eval Runner | 2-3 days | 4b |

### Quick Wins (Implement First)

1. **Model Registry YAML** - Can be created immediately, no code changes
2. **Basic Cost Tracking** - Add token counting to workflow execution
3. **Test Case Definitions** - Document expected behaviors

---

## Risk Analysis

### Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Router overhead adds latency | Medium | Low | Use flash model, cache decisions |
| Tool abstraction breaks existing agents | Medium | High | Feature flag, gradual rollout |
| State persistence adds complexity | High | Medium | Start with SQLite, simple schema |
| Eval suite maintenance burden | Medium | Medium | Generate tests from production logs |

### Strategic Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| MCP standard changes significantly | Medium | Medium | Own IDL with MCP adapter |
| Model providers change APIs | High | High | Adapter pattern isolates changes |
| ChromaDB/vector store lock-in | Low | Medium | Abstract vector store interface |

---

## Success Metrics

### Phase 1: Router
- **Metric:** Cost reduction percentage
- **Target:** 30% reduction in inference costs
- **Measurement:** Compare monthly spending before/after

### Phase 2: Tools
- **Metric:** Time to add new tool
- **Target:** < 30 minutes (currently ~2 hours)
- **Measurement:** Track from request to deployment

### Phase 3: State
- **Metric:** Agent success rate on repeated tasks
- **Target:** 20% improvement from learning
- **Measurement:** A/B test with/without memory

### Phase 4: Evals
- **Metric:** Time to validate model swap
- **Target:** < 1 hour (currently manual/undefined)
- **Measurement:** CI pipeline duration

---

## Appendix: Key Quotes from Strategic Discussion

> "The benefit is not in the intelligence (which will become a commodity), but in the architecture of control."

> "If you don't own the orchestration layer, you are merely a tenant in someone else's digital ecosystem."

> "The skill being learned isn't syntax; it's systems engineering. Understanding how to decompose a complex goal into atomic steps for an agent is a skill that persists even if the coding itself disappears."

> "You cannot claim to be 'future-proof' if you cannot mathematically prove that Model B is better than Model A for your specific use case."

---

## Next Steps

1. Review this plan and prioritize phases
2. Create feature branches for parallel development
3. Set up basic model registry YAML (immediate, no-code)
4. Define first batch of eval test cases
5. Prototype semantic router with existing flash model

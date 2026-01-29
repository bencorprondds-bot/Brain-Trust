# Brain Trust / Legion v3 - Unified Implementation Plan

**Date:** January 2026
**Status:** Active Development
**Vision:** Transform Brain Trust from a workflow builder into an intelligent Execution Engine

---

## Executive Summary

This document unifies two strategic initiatives:

1. **Orchestration Improvements** (Phases 1-3 complete) - Future-proofing the architecture
2. **Legion v3 Architecture** - Pivoting to an execution-focused platform with Willow (Executive AI)

The core thesis remains: **The value is not in the intelligence (which will become commodity), but in the architecture of control.**

---

## Completed Phases (1-3)

### Phase 1: Semantic Router Layer [COMPLETE]
- Model Registry with capability matrix
- Task Classifier for complexity/domain detection
- Cost-aware routing decisions
- Auto-select model toggle

### Phase 2: Tool Protocol Abstraction [COMPLETE]
- Provider-agnostic tool definitions (IDL)
- CrewAI adapter implementation
- Tool registry with YAML definitions
- Decoupled from model-specific schemas

### Phase 3: State Persistence Layer [COMPLETE]
- Agent state schema
- SQLite persistence
- Long-term memory (vector store)
- Context window management for model swaps

---

## Completed Phases (4-8) - January 27, 2026

### Phase 4: Evaluation Pipeline [COMPLETE]

**Status:** COMPLETE
**Priority:** High (validates all other work)

#### Objective
Automated testing for model swaps. You cannot claim "future-proof" without mathematical proof that Model B outperforms Model A for your use cases.

#### Components

| Component | Description | Location |
|-----------|-------------|----------|
| Test Case Schema | YAML-defined evaluation cases | `~/.pai/evals/*.yaml` |
| Evaluators | Tool selection, output format, LLM judge | `backend/app/evals/evaluators/` |
| Eval Runner | Execution engine for test suites | `backend/app/evals/runner.py` |
| CLI Commands | `legion eval run`, `legion eval compare` | `cli/commands/eval.py` |

#### Test Case Format
```yaml
id: librarian-find-folder-001
name: "Find Inbox Folder"
agent_role: "Librarian"
agent_goal: "Find and return the ID of the Inbox folder"
input_prompt: "Find the Inbox folder in our Shared Drive"

expected_tools:
  - "Google Drive Folder Finder"

evaluators:
  - tool_selection
  - task_completion

passing_threshold: 0.8
```

#### Tasks
- [x] Define test case schema - `backend/app/evals/schema.py`
- [x] Create initial test cases for Librarian, Writer, Editor - `config/evals/*.yaml`
- [x] Implement basic evaluators (tool selection, output format) - `backend/app/evals/evaluators/`
- [x] Build eval runner - `backend/app/evals/runner.py`
- [x] Add LLM judge evaluator - `backend/app/evals/evaluators/llm_judge.py`
- [x] Integrate with CLI (`legion eval`) - `cli/commands/eval_cmd.py`
- [x] Add API endpoints - `backend/app/api/eval_routes.py`

---

### Phase 5: Willow - Executive AI [COMPLETE]

**Status:** COMPLETE
**Priority:** Critical (core of Legion v3)

#### Objective
Create the Executive Conductor - an AI that receives abstract intent and orchestrates the Legion to deliver concrete outputs.

#### Willow Profile
```yaml
name: Willow
role: Executive Conductor
model: claude-opus-4-5-20251101

backstory: |
  You are the Executive Conductor of the Legion — a network of specialized AI agents
  designed to transform abstract creative visions into concrete deliverables.

  Your role is NOT to do the work yourself. Your role is to:
  1. Understand what the user truly wants
  2. Know what capabilities exist in the Legion
  3. Assemble the right team for each mission
  4. Monitor progress and handle exceptions
  5. Shield the user from execution details while surfacing taste decisions

tools:
  - CapabilityRegistryQuery
  - TeamLeadDispatch
  - PreferenceMemoryQuery
  - EscalationLogger
  - UserNotification (Discord MCP)
  - AdvisoryBoardConvene
```

#### Components

| Component | Description | Location |
|-----------|-------------|----------|
| Willow Agent Profile | Executive AI definition | `backend/app/agents/willow.py` |
| Capability Registry | What the Legion can do | `backend/app/core/capability_registry.py` |
| Intent Parser | Convert abstract input to actionable plan | `backend/app/core/intent_parser.py` |
| Plan Proposer | Generate execution plans | `backend/app/core/plan_proposer.py` |
| Team Dispatcher | Route work to Team Leads | `backend/app/core/team_dispatcher.py` |

#### Database Schema
```sql
-- Capability Registry
create table capabilities (
  id uuid primary key,
  name text not null,
  description text not null,
  category text not null,  -- "editorial", "technical", "production"
  agent_id uuid references agents(id),
  team text,
  required_tools text[],
  success_rate decimal,
  avg_duration_seconds integer
);

-- Capability Gaps
create table capability_gaps (
  id uuid primary key,
  identified_at timestamptz default now(),
  description text not null,
  requested_by text,
  priority text default 'medium',
  status text default 'open',
  resolution_notes text
);
```

#### Tasks
- [x] Create Willow agent profile - `backend/app/agents/willow.py`
- [x] Implement Capability Registry schema + seed data - `backend/app/core/capability_registry.py`
- [x] Build intent parsing logic - `backend/app/core/intent_parser.py`
- [x] Implement plan proposal generation - `backend/app/core/plan_proposer.py`
- [x] Create Team Lead dispatch system - `backend/app/core/team_dispatcher.py`
- [x] Add `/api/v2/intent` endpoint - `backend/app/api/v2/routes.py`

---

### Phase 6: Preference Memory [COMPLETE]

**Status:** COMPLETE
**Priority:** High (enables learning)

#### Objective
Remember what shipped, what was approved, and why — informing future decisions.

#### Components

| Component | Description | Location |
|-----------|-------------|----------|
| Approved Outputs | What shipped and why | `approved_outputs` table |
| Execution Patterns | What approaches work | `execution_patterns` table |
| Daily Digests | Escalation summaries | `daily_digests` table |
| Preference Query | Willow queries past approvals | `backend/app/core/preference_memory.py` |

#### Database Schema
```sql
-- Approved Outputs
create table approved_outputs (
  id uuid primary key,
  project text not null,  -- "life_with_ai", "coloring_book", etc.
  output_type text not null,  -- "story", "code", "coloring_page"
  output_reference text,  -- Drive ID, GitHub commit, etc.
  approved_at timestamptz,
  approval_notes text,
  agents_involved text[],
  workflow_snapshot jsonb
);

-- Execution Patterns
create table execution_patterns (
  id uuid primary key,
  intent_category text not null,
  successful_approach jsonb not null,
  success_count integer default 1,
  failure_count integer default 0,
  user_feedback text[],
  contraindications text[]
);

-- Daily Digests
create table daily_digests (
  id uuid primary key,
  digest_date date not null unique,
  escalation_requests jsonb not null,
  decisions_made jsonb,
  user_actions_needed jsonb,
  delivered_at timestamptz,
  delivery_channel text  -- "discord"
);
```

#### Tasks
- [x] Create database migration for new tables - SQLite in `~/.pai/preference_memory.db`
- [x] Implement PreferenceMemory class - `backend/app/core/preference_memory.py`
- [x] Build approval capture workflow
- [x] Pattern extraction from successful runs
- [x] Inject preferences into Willow's context

---

### Phase 7: Legion CLI [COMPLETE]

**Status:** COMPLETE
**Priority:** High (user requested)

#### Objective
Command-line interface for interacting with Willow and the Legion.

#### Command Structure
```bash
# Interactive session
legion

# With initial intent
legion "I want to finish editing chapter 3"

# Status and management
legion status
legion status --project life_with_ai
legion approve
legion approve --id <output_id>
legion logs
legion logs --today

# Capability management
legion capabilities
legion gaps
legion agents

# Project context
legion projects
legion project life_with_ai

# Configuration
legion config
legion config discord.channel <id>

# Evaluation (Phase 4)
legion eval run --model claude-sonnet-4-20250514
legion eval compare --model-a claude-sonnet --model-b gemini-flash
```

#### Components

| Component | Description | Location |
|-----------|-------------|----------|
| CLI Entry Point | Main legion command | `cli/__init__.py` |
| Interactive Mode | Chat with Willow | `cli/interactive.py` |
| Status Commands | Project/execution status | `cli/commands/status.py` |
| Approve Commands | Approval workflow | `cli/commands/approve.py` |
| Eval Commands | Evaluation pipeline | `cli/commands/eval.py` |
| Config Commands | Configuration management | `cli/commands/config.py` |

#### Package Structure
```
cli/
├── __init__.py          # Entry point, Typer app
├── interactive.py       # Interactive Willow session
├── config.py           # Configuration loader
├── commands/
│   ├── __init__.py
│   ├── status.py       # legion status
│   ├── approve.py      # legion approve
│   ├── logs.py         # legion logs
│   ├── projects.py     # legion projects
│   ├── capabilities.py # legion capabilities/gaps/agents
│   ├── eval.py         # legion eval
│   └── config.py       # legion config
└── utils/
    ├── display.py      # Rich console output
    └── api.py          # Backend API client
```

#### Tasks
- [x] Set up CLI package with Typer - `cli/__init__.py`
- [x] Implement basic `legion` command (interactive mode) - `cli/interactive.py`
- [x] Add `legion status` command - `cli/commands/status.py`
- [x] Add `legion approve` command - `cli/commands/approve.py`
- [x] Add `legion logs` command - `cli/commands/logs.py`
- [x] Add `legion projects` command - `cli/commands/projects.py`
- [x] Add `legion capabilities/gaps/agents` commands - `cli/commands/capabilities.py`
- [x] Integrate eval commands (Phase 4) - `cli/commands/eval_cmd.py`
- [x] Add pyproject.toml entry point - `pyproject.toml`

---

### Phase 8: Advisory Board [COMPLETE]

**Status:** COMPLETE
**Priority:** Medium (for gap resolution)

#### Objective
When Willow identifies a capability gap, convene frontier models to design a solution.

#### Process
1. Gap identified by Willow
2. Board convened (Claude Opus, Gemini Pro, GPT-4)
3. Each model proposes solution
4. Structured debate (2 rounds)
5. Vote with reasoning
6. Present recommendation to user
7. User approves → agent built

#### Components

| Component | Description | Location |
|-----------|-------------|----------|
| Board Convener | Orchestrates multi-model discussion | `backend/app/core/advisory_board.py` |
| Proposal Schema | Structured agent design proposals | `backend/app/core/proposal_schema.py` |
| Voting Logic | Synthesize and vote | `backend/app/core/voting.py` |
| Agent Builder | Create agent from approved proposal | `backend/app/core/agent_builder.py` |

#### Tasks
- [x] Define proposal schema - `backend/app/core/proposal_schema.py`
- [x] Implement board convener - `backend/app/core/advisory_board.py`
- [x] Build multi-model discussion orchestration
- [x] Add voting and synthesis logic (integrated in advisory_board.py)
- [x] Create agent builder pipeline - `backend/app/core/agent_builder.py`
- [x] Add API endpoints - `backend/app/api/v2/routes.py`

---

### Phase 9: Discord Integration

**Status:** Blocked (awaiting Discord setup)
**Priority:** Medium (external notifications)

#### Objective
Willow can reach user outside the app via Discord.

#### Required Capabilities
- Send messages to user
- Receive responses from user
- Support approval/rejection workflows (reactions or replies)
- Status update requests

#### Notification Types

| Type | Urgency | Example |
|------|---------|---------|
| Approval Needed | Medium | "Story ready for review" |
| Blocker | High | "Can't proceed without direction on X" |
| Daily Digest | Low | "Today's escalation summary" |
| Completion | Low | "Coloring book pages ready" |
| Status Response | On-demand | Response to "What's the status?" |

#### Tasks
- [ ] Research Discord MCP servers
- [ ] Set up Discord bot/webhook
- [ ] Implement DiscordNotifier class
- [ ] Add to Willow's tool set
- [ ] Test bidirectional communication

---

### Phase 10: UI Transformation

**Status:** Planned
**Priority:** Low (CLI first)

#### Objective
Simplify the web UI - chat becomes primary, ReactFlow becomes debug view.

#### Primary View: Command Interface
- Simple chat with Willow
- Plan proposals with [Begin] [Modify] [Show Details] buttons
- Approval workflows

#### Secondary View: Debug/Expert Panel
- ReactFlow canvas (demoted from primary)
- Execution logs
- Issues & fixes catalogue
- Active agent status

#### Tasks
- [ ] Build new Command Interface component
- [ ] Create toggle between views
- [ ] Move ReactFlow to debug panel
- [ ] Implement approval UI
- [ ] Add issues/fixes display

---

## Project Scopes

Defined concrete outputs per project:

| Project | Outputs | Team | Quality Gate |
|---------|---------|------|--------------|
| Life with AI | Stories, scripts, world-building | Editorial | Pipeline approval |
| Coloring Book | Coloring pages, PDFs, sales | Production + Art Gen | Daughter approval (via user) |
| Diamond Age Primer | Interactive code | Technical | Daughter engagement (via user) |
| Life with AI Idle Game | Game code | Technical | Playability, code review |

---

## Implementation Order

```
Phase 4: Evaluation Pipeline ──────────────────────────────────┐
  - Validates all other work                                   │
  - Required before model swaps                                │
                                                               │
Phase 5: Willow (Executive AI) ───────────────────────────────┤
  - Core of Legion v3                                          │
  - Enables intelligent orchestration                          │  SEQUENTIAL
                                                               │  (dependencies)
Phase 6: Preference Memory ───────────────────────────────────┤
  - Enables learning from approvals                            │
  - Feeds into Willow's decisions                              │
                                                               │
Phase 7: Legion CLI ──────────────────────────────────────────┤
  - User-facing interface                                      │
  - Can start before Phase 5 complete                          │
                                                               │
Phase 8: Advisory Board ──────────────────────────────────────┤
  - Gap resolution                                             │
  - Requires Willow                                            │
                                                               │
Phase 9: Discord Integration ─────────────────────────────────┤
  - External notifications                                     │
  - Blocked on Discord setup                                   │
                                                               │
Phase 10: UI Transformation ──────────────────────────────────┘
  - Last priority (CLI first)
  - Can be incremental
```

---

## Resolved Decisions

| Decision | Resolution | Date |
|----------|------------|------|
| Executive AI Name | **Willow** | Jan 2026 |
| Daughter Feedback | Relayed through user; Willow logs patterns | Jan 2026 |
| Notification Channel | **Discord** (primary, bidirectional) | Jan 2026 |
| Legacy Workflows | None — clean slate, full retooling | Jan 2026 |
| CLI Framework | Typer (Python) | Jan 2026 |

---

## Open Questions

1. **Multi-project Context**: How does Willow handle concurrent projects?
2. **Discord MCP Setup**: Which Discord MCP server? Configuration?
3. **Parallel Claude Instance**: Coordination strategy for concurrent development?

---

## File Structure (New Additions)

```
Brain-Trust/
├── cli/                          # NEW: Legion CLI
│   ├── __init__.py
│   ├── interactive.py
│   ├── config.py
│   └── commands/
│       ├── status.py
│       ├── approve.py
│       ├── logs.py
│       ├── projects.py
│       ├── capabilities.py
│       ├── eval.py
│       └── config.py
│
├── backend/
│   └── app/
│       ├── agents/               # NEW: Agent profiles
│       │   ├── willow.py
│       │   └── team_leads.py
│       ├── core/
│       │   ├── capability_registry.py   # NEW
│       │   ├── preference_memory.py     # NEW
│       │   ├── intent_parser.py         # NEW
│       │   ├── plan_proposer.py         # NEW
│       │   ├── team_dispatcher.py       # NEW
│       │   ├── advisory_board.py        # NEW
│       │   └── discord_notifier.py      # NEW
│       ├── evals/                # NEW: Evaluation pipeline
│       │   ├── schema.py
│       │   ├── runner.py
│       │   └── evaluators/
│       │       ├── tool_selection.py
│       │       ├── output_format.py
│       │       └── llm_judge.py
│       └── api/
│           └── v2/               # NEW: Legion v3 endpoints
│               └── routes.py
│
├── design_specs/
│   └── legion_architecture_v3.md # Reference architecture
│
└── docs/
    └── IMPLEMENTATION_PLAN.md    # This file
```

---

## Success Metrics

| Phase | Metric | Target |
|-------|--------|--------|
| Phase 4 | Time to validate model swap | < 1 hour |
| Phase 5 | Task completion without manual agent selection | 80% |
| Phase 6 | Preference-informed decisions | 50% of plans |
| Phase 7 | CLI adoption for daily work | Primary interface |
| Phase 8 | Time from gap to new agent | < 1 day |
| Phase 9 | Response time to Discord notifications | < 5 min |

---

## Summary

Legion v3 transforms Brain Trust from a tool you operate into a system that operates for you. You bring vision and taste; the Legion brings execution and delivery.

Willow is your single point of contact — a conductor who knows what the orchestra can play, assembles the right musicians, and only interrupts your listening when a decision about the music itself is needed.

*"Abstract inputs. Concrete outputs. The Legion delivers."*

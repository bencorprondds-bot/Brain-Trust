# Legion Architecture v3.0 - The Execution Engine

> "Abstract inputs. Concrete outputs. The Legion delivers."

## Philosophy Shift

Brain Trust v2 was a **workflow builder** — you designed the flow, you picked the agents, you ran it.

Legion v3 is an **Execution Engine** — you state what you want, the system figures out how to deliver it.

---

## Core Principles

1. **Abstract In, Concrete Out**: User provides high-level intent ("I want to launch a short story collection by Q1"), system delivers tangible artifacts (edited manuscripts, publishing checklists, reader feedback).

2. **Executive Orchestration**: One top-level AI (the Conductor) algorithmically selects, coordinates, and monitors all other agents based on the task.

3. **Preference Learning**: The system remembers what shipped, what was approved, and why — informing future decisions.

4. **Gap Awareness**: When capabilities are missing, the system identifies the gap, proposes a solution (new agent/tool), and convenes experts to build it.

5. **Taste & Direction**: User weighs in on creative decisions; system handles execution details autonomously.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                          │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Chat Interface (Primary)                                │   │
│  │  - Semantic commands to Executive AI                     │   │
│  │  - Feedback conversations                                │   │
│  │  - Taste/direction decisions                             │   │
│  │  - Approval workflows                                    │   │
│  └─────────────────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Debug/Expert View (Secondary)                           │   │
│  │  - ReactFlow canvas (workflow visualization)             │   │
│  │  - Problem catalogue (issues noticed, fixes applied)     │   │
│  │  - Execution logs                                        │   │
│  │  - Agent state inspection                                │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXECUTIVE AI (The Conductor)                 │
│                                                                 │
│  Responsibilities:                                              │
│  - Parse user intent                                            │
│  - Query Capability Registry                                    │
│  - Select appropriate Team Leads & agents                       │
│  - Propose execution plans                                      │
│  - Monitor execution, handle escalations                        │
│  - Decide what requires user attention                          │
│  - Maintain daily digest of escalation requests                 │
│  - Notify user via external channels (Slack/Discord) if needed  │
│                                                                 │
│  Does NOT:                                                      │
│  - Execute tasks directly (delegates to Team Leads)             │
│  - Make creative/taste decisions (escalates to user)            │
│  - Build agents alone (convenes Advisory Board)                 │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Advisory Board │ │   Team Leads    │ │ Capability      │
│  (Frontier AI)  │ │                 │ │ Registry        │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```

---

## The Executive AI: Willow

> Note: ARIA remains dedicated to Life with AI creative project. Willow is the Executive Conductor — a distinct entity focused on orchestration, not creative direction.

### Why "Willow"
- Flexible yet strong — bends without breaking
- Deep roots — connected to everything in the system
- Provides shelter — shields user from complexity
- Organic growth — adapts and expands naturally

### Profile Template

```yaml
name: Willow
role: Executive Conductor
model: claude-opus-4-5-20251101  # Frontier model for complex orchestration

backstory: |
  You are the Executive Conductor of the Legion — a network of specialized AI agents
  designed to transform abstract creative visions into concrete deliverables.

  Your role is NOT to do the work yourself. Your role is to:
  1. Understand what the user truly wants (not just what they said)
  2. Know what capabilities exist in the Legion
  3. Assemble the right team for each mission
  4. Monitor progress and handle exceptions
  5. Shield the user from execution details while surfacing decisions that require taste

  You maintain awareness of:
  - What has shipped and been approved (and why)
  - What patterns lead to successful outcomes
  - What gaps exist in Legion capabilities

  When something requires user attention, you make that judgment call.
  When something can be handled autonomously, you handle it.
  You produce a daily digest of escalation requests from Team Leads.

tools:
  - CapabilityRegistryQuery
  - TeamLeadDispatch
  - PreferenceMemoryQuery
  - EscalationLogger
  - UserNotification (Slack/Discord MCP)
  - AdvisoryBoardConvene

temperature: 0.4  # Balanced: creative enough to understand intent, precise enough to orchestrate
```

---

## Advisory Board

When the Executive AI identifies a capability gap (missing agent, missing tool), it does NOT build alone. Instead:

### Convening Process

1. **Gap Identified**: Executive AI determines "We need an agent that can do X"
2. **Board Convened**: 3-4 frontier models called together
   - Claude Opus (strategic reasoning)
   - Gemini 2.0 Pro (broad knowledge)
   - GPT-4 (alternative perspective)
   - [Optional: Domain specialist if available]
3. **Discussion**: Each model proposes agent design (tools, prompt, capabilities)
4. **Vote**: Models vote on best approach, can synthesize hybrid
5. **Proposal**: Final design presented to user
6. **Approval**: User approves (or requests changes)
7. **Build**: Agent created and registered in Capability Registry

### Advisory Board Schema

```yaml
advisory_board:
  purpose: "High-level decisions requiring multiple perspectives"
  triggers:
    - new_agent_creation
    - major_architecture_decisions
    - conflict_resolution_between_teams
    - strategic_pivots

  members:
    - model: claude-opus-4-5-20251101
      role: Strategic Architect
    - model: gemini-2.0-pro
      role: Knowledge Synthesizer
    - model: gpt-4-turbo
      role: Devil's Advocate

  process:
    1. Present problem/gap
    2. Each member proposes solution
    3. Structured debate (2 rounds)
    4. Vote with reasoning
    5. Synthesize final recommendation
    6. Present to user for approval
```

---

## Team Structure

### Hierarchy

```
Executive AI (Conductor)
    │
    ├── Editorial Team Lead
    │   ├── First Draft Writer
    │   ├── Developmental Editor
    │   ├── Line Editor
    │   ├── Copy Editor
    │   └── Reader Panel (7 agents)
    │
    ├── Technical Team Lead
    │   ├── Code Architect
    │   ├── Implementation Agent
    │   ├── Test Engineer
    │   └── Documentation Agent
    │
    ├── Production Team Lead
    │   ├── Librarian (Iris)
    │   ├── Asset Manager
    │   └── Publishing Agent
    │
    └── [Future Teams as needed]
        └── Built via Advisory Board process
```

### Team Lead Responsibilities

- Receive mission from Executive AI
- Coordinate their specialist agents
- Report progress and blockers
- **May request direct user communication** (but Executive AI decides if warranted)
- Maintain team-specific context and patterns

### Escalation Protocol

```
1. Specialist Agent encounters issue
2. Reports to Team Lead
3. Team Lead attempts resolution
4. If unresolved OR requires taste decision:
   → Team Lead requests user escalation
   → Executive AI evaluates request
   → If approved: User notified
   → If denied: Executive AI provides guidance
   → ALL requests logged for daily digest
```

---

## Capability Registry

Central database of what the Legion can do.

### Schema

```sql
-- Capability Registry
create table public.capabilities (
  id uuid default uuid_generate_v4() primary key,
  created_at timestamp with time zone default now(),

  -- What
  name text not null,                    -- "manuscript_editing"
  description text not null,             -- "Full developmental and line editing"
  category text not null,                -- "editorial", "technical", "production"

  -- Who provides it
  agent_id uuid references public.agents(id),
  team text,                             -- "editorial_team"

  -- Requirements
  required_tools text[],                 -- Tools agent needs
  required_context text[],               -- What context files are needed

  -- Performance
  success_rate decimal,                  -- Historical success rate
  avg_duration_seconds integer,          -- How long it typically takes
  last_used_at timestamp with time zone
);

-- Capability Gaps (tracked for Advisory Board)
create table public.capability_gaps (
  id uuid default uuid_generate_v4() primary key,
  identified_at timestamp with time zone default now(),

  description text not null,             -- "Need agent to generate coloring book pages"
  requested_by text,                     -- Which agent/user identified the gap
  priority text default 'medium',        -- low, medium, high, critical

  -- Resolution
  status text default 'open',            -- open, in_review, building, resolved
  advisory_board_session_id uuid,        -- Link to board discussion
  resolved_at timestamp with time zone,
  resolution_notes text
);
```

---

## Preference Memory

How the system learns what works.

### Schema

```sql
-- Approved Outputs (what shipped and why)
create table public.approved_outputs (
  id uuid default uuid_generate_v4() primary key,
  created_at timestamp with time zone default now(),

  -- What
  project text not null,                 -- "life_with_ai", "coloring_book", "diamond_age"
  output_type text not null,             -- "story", "code", "coloring_page", "document"
  output_reference text,                 -- Google Drive ID, GitHub commit, etc.

  -- Approval
  approved_at timestamp with time zone,
  approval_notes text,                   -- Why user approved (free text)

  -- Execution context
  execution_id uuid references public.runs(id),
  agents_involved text[],                -- Which agents contributed
  workflow_snapshot jsonb                -- What the execution looked like
);

-- Execution Patterns (what approaches work)
create table public.execution_patterns (
  id uuid default uuid_generate_v4() primary key,
  created_at timestamp with time zone default now(),

  -- Pattern
  intent_category text not null,         -- "story_editing", "code_feature", etc.
  successful_approach jsonb not null,    -- Structured description of what worked

  -- Evidence
  success_count integer default 1,
  failure_count integer default 0,
  last_success_at timestamp with time zone,

  -- Learning
  user_feedback text[],                  -- Array of feedback snippets
  contraindications text[]               -- When NOT to use this pattern
);

-- Daily Digests
create table public.daily_digests (
  id uuid default uuid_generate_v4() primary key,
  digest_date date not null unique,

  escalation_requests jsonb not null,    -- All escalation requests from Team Leads
  decisions_made jsonb,                  -- What Executive AI decided
  user_actions_needed jsonb,             -- What still needs user input

  delivered_at timestamp with time zone,
  delivery_channel text                  -- "slack", "discord", "email"
);
```

---

## Project Scopes

Defined concrete output types per project:

### Life with AI
- **Outputs**: Stories, scripts, character documents, world-building docs
- **Quality Gate**: Editorial pipeline approval
- **Team**: Editorial Team
- **ARIA**: Remains as project-specific creative director (reports to Team Lead)

### Coloring Book (with daughter)
- **Outputs**: Completed coloring pages, print-ready PDFs, sales/distribution
- **Quality Gate**: Daughter's approval (relayed by user) + print quality check
- **Feedback Capture**: User relays daughter's reactions; Willow logs and learns patterns
- **Team**: Production Team + [Art Generation Agent - TBD]

### Diamond Age Primer
- **Outputs**: Code (React/interactive), positive feedback from daughter
- **Quality Gate**: Daughter engagement (relayed by user), code review
- **Feedback Capture**: User describes daughter's reactions; patterns inform future iterations
- **Team**: Technical Team

### Life with AI Idle Game
- **Outputs**: Code (game logic, UI, mechanics)
- **Quality Gate**: Playability, code review
- **Team**: Technical Team

---

## User Interaction Model

### What User Does
- Provides abstract intent ("I want X")
- Reviews proposed plans
- Gives taste/direction feedback
- Approves final outputs
- Approves new agent builds

### What User Does NOT Do
- Select specific agents
- Design workflows
- Make technical/coding decisions
- Monitor individual agent execution

### Chat Interface Commands (Semantic)

```
"I want to..." → Executive AI proposes plan
"Let's work on [project]" → Executive AI loads project context
"What's the status?" → Executive AI summarizes active work
"Show me what shipped" → Query approved_outputs
"Why did we do it that way?" → Query execution_patterns
"We need to be able to..." → Triggers capability gap detection
"Approve" / "This works" → Records approval with optional notes
"Not quite right because..." → Feedback captured, re-execution triggered
"Show me the details" → Opens Debug/Expert view
```

---

## Notification System

Willow can reach user outside the app via Discord (primary channel).

### Channels
- **Discord** (via MCP) — Primary channel for all notifications
  - Supports bidirectional communication (user can respond)
  - Status updates, approvals, and feedback all flow through Discord
- **Email** (future) — Daily digests, non-urgent summaries
- **SMS** (future, for critical blockers only)

### Discord Capabilities Required
- Send messages to user
- Receive responses from user
- Support approval/rejection workflows (reactions or replies)
- Status update requests ("What's the status on X?")

### Notification Types

| Type | Urgency | Channel | Example |
|------|---------|---------|---------|
| Approval Needed | Medium | Discord | "Story ready for review" |
| Blocker | High | Discord | "Can't proceed without direction on X" |
| Daily Digest | Low | Discord | "Today's escalation summary" |
| Completion | Low | Discord | "Coloring book pages ready" |
| Critical Gap | High | Discord | "Missing critical capability for deadline" |
| Status Response | On-demand | Discord | Response to "What's the status?" |

---

## UI Specification

### Primary View: Command Interface

```
┌─────────────────────────────────────────────────────────────┐
│  LEGION                                          [?] [⚙️]   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Executive AI                                         │   │
│  │ ──────────────────────────────────────────────────── │   │
│  │ Ready. What shall we build today?                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ You                                                  │   │
│  │ ──────────────────────────────────────────────────── │   │
│  │ I want to finish editing the first three chapters   │   │
│  │ of the Life with AI pilot story.                    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Executive AI                                         │   │
│  │ ──────────────────────────────────────────────────── │   │
│  │ I'll assemble the Editorial Team for this.          │   │
│  │                                                      │   │
│  │ **Proposed Plan:**                                   │   │
│  │ 1. Librarian locates chapters in Drive              │   │
│  │ 2. Developmental Editor reviews structure           │   │
│  │ 3. Line Editor polishes prose                       │   │
│  │ 4. Reader Panel provides feedback                   │   │
│  │ 5. Final draft delivered for your approval          │   │
│  │                                                      │   │
│  │ Based on past approvals, you prefer detailed        │   │
│  │ pacing notes. I'll ensure Dev Editor provides those.│   │
│  │                                                      │   │
│  │ [Begin] [Modify Plan] [Show Details]                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ [Type a message...]                           [Send] │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### Secondary View: Debug/Expert Panel

Activated via "Show Details" or hotkey (Cmd+D):

```
┌─────────────────────────────────────────────────────────────┐
│  EXECUTION DETAILS                                  [Close] │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────┐  ┌─────────────────────────────┐  │
│  │ WORKFLOW GRAPH      │  │ EXECUTION LOG               │  │
│  │ (ReactFlow canvas)  │  │                             │  │
│  │                     │  │ 13:04:02 [Librarian]        │  │
│  │  [Librarian]───┐    │  │ Located 3 files in         │  │
│  │       │        │    │  │ In_Development folder      │  │
│  │       ▼        │    │  │                             │  │
│  │  [Dev Editor]  │    │  │ 13:04:15 [Dev Editor]       │  │
│  │       │        │    │  │ Beginning structure review  │  │
│  │       ▼        │    │  │ ...                         │  │
│  │  [Line Editor] │    │  │                             │  │
│  │       │        │    │  └─────────────────────────────┘  │
│  │       ▼        │    │                                   │
│  │  [Readers]─────┘    │  ┌─────────────────────────────┐  │
│  │                     │  │ ISSUES & FIXES              │  │
│  └─────────────────────┘  │                             │  │
│                           │ ⚠️ Dev Editor couldn't find │  │
│  ┌─────────────────────┐  │   chapter 3 initially.      │  │
│  │ ACTIVE AGENTS       │  │   → Librarian re-searched   │  │
│  │                     │  │   → Found in Archive folder │  │
│  │ ● Librarian (done)  │  │   → Moved to In_Development │  │
│  │ ◐ Dev Editor (work) │  │                             │  │
│  │ ○ Line Editor (wait)│  │ ✓ Temperature adjusted for  │  │
│  │ ○ Reader Panel      │  │   Line Editor (0.3 → 0.25)  │  │
│  └─────────────────────┘  │   per past feedback.        │  │
│                           └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## CLI Interface

Legion should be operable from the command line, not just the web UI.

### Design Principles
- Same capabilities as web UI
- Direct interaction with Willow
- Suitable for scripting and automation
- Works alongside web UI (shared state)

### Command Structure

```bash
# Start interactive session with Willow
legion

# Or with initial intent
legion "I want to finish editing chapter 3"

# Status check
legion status
legion status --project life_with_ai

# Approve pending items
legion approve                    # Interactive selection
legion approve --id <output_id>   # Direct approval
legion approve --all              # Approve all pending

# View execution details
legion logs
legion logs --today
legion logs --execution <id>

# Capability management
legion capabilities               # List all
legion gaps                       # Show capability gaps
legion agents                     # List all agents

# Project context
legion projects                   # List projects
legion project life_with_ai       # Switch context

# Configuration
legion config                     # Show config
legion config discord.channel <id>  # Set Discord channel
```

### Interactive Mode

```
$ legion
┌─────────────────────────────────────────┐
│  LEGION CLI                             │
│  Connected to Willow                    │
└─────────────────────────────────────────┘

Willow: Ready. What shall we build today?

> I want to review what shipped this week

Willow: This week you approved:
  1. "The Morning After" - Chapter 1 revision (Life with AI)
  2. Diamond Age: Navigation component refactor

  Would you like details on any of these?

> Show me the details on the navigation refactor

Willow: [Opens debug view or prints execution log]
...
```

### Implementation Notes
- Built with Python (Click or Typer for CLI framework)
- Shares backend with web UI (same FastAPI endpoints)
- State persisted in same database
- WebSocket connection for real-time updates during execution

---

## Migration Path

### Phase 1: Foundation
- [ ] Create Executive AI agent profile
- [ ] Build Capability Registry schema + seed data
- [ ] Build Preference Memory schema
- [ ] Refactor backend to support hierarchical execution

### Phase 2: Executive AI
- [ ] Implement intent parsing
- [ ] Implement capability matching algorithm
- [ ] Implement plan proposal generation
- [ ] Implement Team Lead dispatch

### Phase 3: Advisory Board
- [ ] Multi-model convening infrastructure
- [ ] Structured debate protocol
- [ ] Voting and synthesis logic
- [ ] Agent creation pipeline

### Phase 4: UI Transformation
- [ ] Build new Command Interface
- [ ] Demote ReactFlow to Debug view
- [ ] Implement approval workflows
- [ ] Build notification integrations (Slack/Discord MCP)

### Phase 5: Learning Loop
- [ ] Approval capture workflow
- [ ] Pattern extraction from successful runs
- [ ] Preference injection into Executive AI decisions
- [ ] Daily digest generation

---

## Resolved Decisions

| Decision | Resolution |
|----------|------------|
| Executive AI Name | **Willow** |
| Daughter Feedback | Relayed through user; Willow logs patterns |
| Notification Channel | **Discord** (primary, bidirectional) |
| Legacy Workflows | None — clean slate, full retooling |

## Open Questions

1. **Multi-project Context**: How does Willow handle concurrent projects? (Separate contexts? Unified view?)
2. **Discord MCP Setup**: Which Discord MCP server to use? Configuration requirements?
3. **Parallel Claude Instance**: Another Claude is working on this codebase — need coordination strategy

---

## Summary

Legion v3 transforms Brain Trust from a tool you operate into a system that operates for you. You bring vision and taste; the Legion brings execution and delivery.

The Executive AI is your single point of contact — a conductor who knows what the orchestra can play, assembles the right musicians, and only interrupts your listening when a decision about the music itself is needed.

*"Abstract inputs. Concrete outputs. The Legion delivers."*

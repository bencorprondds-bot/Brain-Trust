# Next Steps: Make Willow a Learning Executive

## Problem
Willow currently:
1. Starts fresh every session with no memory of past interactions
2. Uses `gemini-2.0-flash` (fast but less capable) instead of stronger reasoning model
3. Over-interprets requests (adds Writers when you just want file retrieval)
4. Doesn't learn from corrections or successful patterns

## Key Discovery
Memory systems already exist but aren't wired up:
- `LongTermMemory` (memory.py) - Vector-based semantic memory
- `PreferenceMemory` (preference_memory.py) - Approved outputs & patterns
- `TELOS Context` (context_loader.py) - User mission/goals
- `Journaling` (journaling.py) - Execution logs

## Implementation Tasks

### 1. Upgrade Willow's Model
**File:** `backend/app/agents/willow.py`
**Change:** Line 93: `model: str = "gemini-2.0-flash"` → `model: str = "claude-sonnet-4-20250514"`

### 2. Wire Up Memory Systems
**File:** `backend/app/agents/willow.py`
Add to `__init__`:
- Initialize `LongTermMemory`, `PreferenceMemory`, `ContextLoader`
- Add `_get_memory_context()` method to load relevant memories for each request

### 3. Add Session Memory Commit
**File:** `backend/app/agents/willow.py`
Add `commit_session_memory()` method that:
- Extracts learnings from conversation history
- Stores in long-term memory
- Updates preference patterns

**File:** `backend/app/api/v2/routes.py`
Add `/session/commit` endpoint

### 4. Fix Intent Parser
**File:** `backend/app/core/intent_parser.py`
- Add status inquiry patterns ("what are we working on", "where are we", etc.)
- Make FIND intent more literal (only Librarian, no Writer/Editor)

### 5. Fix Plan Proposer
**File:** `backend/app/core/plan_proposer.py`
- Constrain templates: FIND/STATUS → only Librarian
- Add explicit rules to LLM prompt: "do LESS not MORE"

### 6. Create TELOS Context Files
**Location:** `~/.pai/context/`
- MISSION.md
- GOALS.md
- IDENTITY.md

### 7. Add Correction Tracking
**File:** `backend/app/agents/willow.py`
Detect corrections ("no", "that's not", "wrong") and record them

## Verification
1. Ask "What are we working on?" → Should use only Librarian
2. Ask "Find Arun's files" → Should use only Librarian, return file IDs
3. Complete a task, run `/remember`, restart, verify context is retained

## Full Plan
See: `~/.claude/plans/silly-percolating-wolf.md`

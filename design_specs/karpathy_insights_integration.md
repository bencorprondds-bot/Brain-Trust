# Karpathy Insights Integration

> Encoding lessons from high-velocity AI-assisted development into Brain Trust / Legion v3

## Source Insights (Karpathy, December 2025)

1. **Wrong Assumptions**: Models make wrong assumptions and run with them without checking
2. **No Clarification Seeking**: Don't manage confusion, don't surface inconsistencies
3. **Sycophancy**: Don't push back when they should, too agreeable
4. **Overcomplexity**: Bloat abstractions, don't clean up dead code, overcomplicate APIs
5. **Scope Creep**: Will implement 1000 lines where 100 would suffice
6. **Side Effects**: Change/remove comments and code orthogonal to the task
7. **Leverage Through Loops**: Give success criteria, not step-by-step instructions
8. **Tenacity Value**: Agents never tire - let them loop until success
9. **Parallelism Needs Isolation**: Multiple agents need non-overlapping work areas

---

## Integration Design

### 1. Assumption Surfacing Protocol

**Problem**: Agents make assumptions silently and proceed.

**Solution**: Add explicit assumption tracking to `ParsedIntent` and `ExecutionPlan`.

```python
# Add to ParsedIntent
@dataclass
class ParsedIntent:
    # ... existing fields ...

    # NEW: Assumption tracking
    assumptions_made: List[str] = field(default_factory=list)
    assumption_confidence: Dict[str, float] = field(default_factory=dict)

    # NEW: Require confirmation for low-confidence assumptions
    requires_assumption_confirmation: bool = False
```

**Willow Behavior Change**:
- Before executing, list assumptions explicitly
- Ask user to confirm assumptions with confidence < 0.7
- Log which assumptions proved correct/incorrect for learning

**Example Output**:
```
I'm assuming:
- [High confidence] You want to edit the existing Chapter 3, not create a new one
- [Medium confidence] "polish the prose" means line editing, not developmental changes
- [Low confidence] The chapter is in the Life with AI project

Should I proceed with these assumptions, or would you like to clarify?
```

### 2. Success Criteria Schema

**Problem**: Imperative instructions ("do X, then Y") vs declarative goals.

**Solution**: Add success criteria to `ExecutionPlan`.

```python
@dataclass
class SuccessCriteria:
    """Defines what "done" looks like."""

    id: str
    description: str
    verification_method: str  # "test", "llm_judge", "user_approval", "metric"
    target_metric: Optional[float] = None  # e.g., test pass rate

    # For test-based verification
    test_command: Optional[str] = None

    # For LLM judge verification
    judge_prompt: Optional[str] = None


@dataclass
class ExecutionPlan:
    # ... existing fields ...

    # NEW: Success criteria (declarative goals)
    success_criteria: List[SuccessCriteria] = field(default_factory=list)

    # NEW: Let agent loop until criteria met
    max_iterations: int = 5
    allow_self_correction: bool = True
```

**Workflow Change**:
```
User: "Make the tests pass for the auth module"

Willow proposes:
  Success Criteria:
  - [ ] All tests in tests/auth/ pass (verification: pytest)
  - [ ] No new lint errors introduced (verification: ruff)

  The agent will iterate until these criteria are met (max 5 iterations).

  [Begin] [Modify Criteria]
```

### 3. Simplicity Validator

**Problem**: Agents overcomplicate solutions, bloat abstractions.

**Solution**: Add a simplicity check phase to plan execution.

```python
class SimplicityValidator:
    """
    Checks for overcomplexity patterns.

    Inspired by: "They will implement 1000 lines where 100 would suffice"
    """

    COMPLEXITY_SIGNALS = [
        "unnecessary abstraction",
        "premature generalization",
        "feature flags for single use case",
        "wrapper around wrapper",
        "configuration for hardcoded values",
        "factory pattern for single implementation",
    ]

    def validate(self, before_code: str, after_code: str, task_description: str) -> SimplicityReport:
        """
        Compare before/after and flag if complexity increased disproportionately.

        Returns suggestions for simplification if warranted.
        """
        pass

    def suggest_simplification(self, code: str, task: str) -> Optional[str]:
        """
        Ask: "Couldn't you just do X instead?"

        Returns a simpler approach if one exists.
        """
        pass
```

**Integration Point**: Run after agent completes work, before user approval.

```
[Agent completes task]

Simplicity Check:
- Lines added: 847
- New abstractions: 3 (ConfigManager, SettingsFactory, PreferenceAdapter)
- Suggestion: This could be simplified to ~120 lines by using a single
  dataclass with default values. Want me to try the simpler approach?

  [Accept Current] [Try Simpler] [Show Comparison]
```

### 4. Anti-Bloat Review Checklist

**Problem**: Dead code, orphaned comments, unnecessary changes.

**Solution**: Post-execution diff review focused on unintended changes.

```python
@dataclass
class DiffReviewReport:
    """Review of changes for unintended side effects."""

    # Changes outside task scope
    unrelated_file_changes: List[str]
    removed_comments: List[str]  # Comments deleted that weren't part of task
    removed_code: List[str]      # Code deleted that wasn't part of task

    # Bloat indicators
    dead_code_introduced: List[str]
    unused_imports_added: List[str]

    # Recommendations
    suggested_reverts: List[str]

    def has_issues(self) -> bool:
        return bool(
            self.unrelated_file_changes or
            self.removed_comments or
            self.removed_code
        )
```

**Automatic Check**:
```
Task: "Fix the login timeout bug"

Diff Review:
- warning: 3 comments removed in auth.py (unrelated to timeout fix)
- warning: helper function `format_date()` deleted (was it unused?)
- warning: Changes made to config.py (not mentioned in task)

Recommend reverting these side effects? [Yes] [No] [Show Details]
```

### 5. Parallel Agent Isolation Protocol

**Problem**: Multiple agents on same codebase cause conflicts.

**Solution**: Explicit work area assignment and conflict detection.

```python
@dataclass
class WorkArea:
    """Defines an agent's exclusive work area."""

    agent_id: str

    # File-level isolation
    owned_files: List[str]        # Exclusive write access
    readable_files: List[str]     # Read-only access

    # Directory-level isolation
    owned_directories: List[str]

    # Conflict detection
    def conflicts_with(self, other: 'WorkArea') -> List[str]:
        """Return list of conflicting files/directories."""
        pass


class ParallelExecutionManager:
    """
    Manages multiple concurrent agent executions.

    Ensures no two agents write to the same files.
    """

    def assign_work_areas(self, plan: ExecutionPlan) -> Dict[str, WorkArea]:
        """
        Analyze plan steps and assign non-overlapping work areas.

        If overlap is unavoidable, serialize those steps.
        """
        pass

    def detect_conflicts(self, executions: List[Execution]) -> List[Conflict]:
        """Real-time conflict detection during execution."""
        pass

    def resolve_conflict(self, conflict: Conflict) -> Resolution:
        """
        Options:
        - Pause one agent
        - Merge changes
        - Escalate to user
        """
        pass
```

**User-Facing**:
```
Parallel Execution Plan:
- Agent A: Working on frontend/ (components, styles)
- Agent B: Working on backend/api/ (routes, handlers)
- Agent C: Working on tests/ (all test files)

Isolation: Full (no overlapping files)
Safe to run in parallel: Yes

[Begin All] [Begin Sequential] [Modify Assignments]
```

### 6. Pushback Protocol

**Problem**: Agents are too sycophantic, don't push back.

**Solution**: Explicit disagreement surfacing in Willow.

```python
@dataclass
class WillowResponse:
    """Willow's response to user intent."""

    # Standard response
    plan: Optional[ExecutionPlan]

    # NEW: Pushback/concerns
    concerns: List[str] = field(default_factory=list)
    alternative_suggestions: List[str] = field(default_factory=list)

    # NEW: Explicit disagreement
    disagrees_with_approach: bool = False
    disagreement_reason: Optional[str] = None
    recommended_alternative: Optional[str] = None
```

**Willow Behavior**:
```
User: "Rewrite the entire authentication system to use my new pattern"

Willow:
I have concerns about this approach:

1. The current auth system has 94% test coverage and no known bugs
2. A full rewrite risks introducing security vulnerabilities
3. The "new pattern" hasn't been tested at scale

Alternative suggestion:
- Refactor incrementally, one component at a time
- Add the new pattern alongside existing code
- Migrate gradually with feature flags

Do you want to proceed with the full rewrite anyway, or try the incremental approach?

[Proceed Anyway] [Try Incremental] [Discuss Further]
```

---

## Implementation Priority

| Feature | Impact | Effort | Priority |
|---------|--------|--------|----------|
| Assumption Surfacing | High | Medium | 1 |
| Success Criteria | High | Medium | 2 |
| Pushback Protocol | High | Low | 3 |
| Simplicity Validator | Medium | Medium | 4 |
| Anti-Bloat Review | Medium | Low | 5 |
| Parallel Isolation | Medium | High | 6 |

---

## Integration Points

### Intent Parser (`intent_parser.py`)
- Add `assumptions_made` field
- Add `assumption_confidence` scoring
- Surface clarification needs more aggressively

### Plan Proposer (`plan_proposer.py`)
- Add `success_criteria` to plans
- Add `concerns` and `alternatives` to proposals
- Implement simplicity pre-check

### Team Dispatcher (`team_dispatcher.py`)
- Add work area assignment
- Add conflict detection
- Support parallel execution with isolation

### Willow Agent (`willow.py`)
- Implement pushback behavior
- Add assumption confirmation flow
- Integrate simplicity validator

### New Modules Needed
- `backend/app/core/simplicity_validator.py`
- `backend/app/core/diff_reviewer.py`
- `backend/app/core/parallel_manager.py`

---

## Success Metrics

How do we know these integrations are working?

1. **Assumption Surfacing**: Track % of plans that required assumption confirmation
2. **Success Criteria**: Track iteration count before criteria met (lower is better)
3. **Pushback Protocol**: Track user acceptance rate of alternatives (higher = useful pushback)
4. **Simplicity Validator**: Track lines of code reduced after simplification suggestions
5. **Anti-Bloat Review**: Track unintended changes caught before approval
6. **Parallel Isolation**: Track conflicts detected and prevented

---

## Philosophical Alignment

These changes align with Legion v3's core principles:

- **"Abstract In, Concrete Out"**: Success criteria make "done" concrete
- **"Taste & Direction"**: User decides on assumptions, not agent
- **"Gap Awareness"**: Pushback surfaces gaps in user's mental model
- **"Preference Learning"**: Learn which assumptions users typically confirm/reject

The goal: Agents that are **capable but humble** - powerful executors that know the limits of their understanding and actively seek alignment rather than assuming it.

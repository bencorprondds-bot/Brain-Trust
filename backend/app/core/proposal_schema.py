"""
Proposal Schema for Advisory Board

Structured agent design proposals for capability gap resolution.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


class ProposalStatus(str, Enum):
    """Status of a proposal."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    IMPLEMENTED = "implemented"


@dataclass
class ToolProposal:
    """Proposed tool for an agent."""

    name: str
    description: str
    parameters: List[Dict[str, str]] = field(default_factory=list)
    implementation_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "implementation_notes": self.implementation_notes,
        }


@dataclass
class AgentProposal:
    """
    A structured proposal for a new agent.

    Submitted by Advisory Board members to fill capability gaps.
    """

    id: str
    gap_id: str  # The capability gap this addresses

    # Agent definition
    role: str
    goal: str
    backstory: str
    team: str  # "Editorial", "Technical", "Production"

    # Capabilities
    capabilities: List[str] = field(default_factory=list)
    tools_needed: List[ToolProposal] = field(default_factory=list)

    # Requirements
    model_requirements: str = ""  # e.g., "Requires vision capability"
    resource_estimate: str = ""  # e.g., "~500 tokens/task"

    # Rationale
    design_rationale: str = ""
    potential_risks: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)

    # Board member info
    proposed_by: str = ""  # Model that proposed this
    proposal_confidence: float = 0.8

    # Status
    status: ProposalStatus = ProposalStatus.DRAFT
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # Voting
    votes_for: List[str] = field(default_factory=list)
    votes_against: List[str] = field(default_factory=list)
    vote_reasoning: Dict[str, str] = field(default_factory=dict)

    @property
    def approval_score(self) -> float:
        """Calculate approval percentage."""
        total_votes = len(self.votes_for) + len(self.votes_against)
        if total_votes == 0:
            return 0.0
        return len(self.votes_for) / total_votes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "gap_id": self.gap_id,
            "role": self.role,
            "goal": self.goal,
            "backstory": self.backstory,
            "team": self.team,
            "capabilities": self.capabilities,
            "tools_needed": [t.to_dict() for t in self.tools_needed],
            "model_requirements": self.model_requirements,
            "resource_estimate": self.resource_estimate,
            "design_rationale": self.design_rationale,
            "potential_risks": self.potential_risks,
            "success_criteria": self.success_criteria,
            "proposed_by": self.proposed_by,
            "proposal_confidence": self.proposal_confidence,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "approval_score": self.approval_score,
            "votes_for": self.votes_for,
            "votes_against": self.votes_against,
        }

    def to_markdown(self) -> str:
        """Generate markdown representation of proposal."""
        tools_md = "\n".join([
            f"- **{t.name}**: {t.description}"
            for t in self.tools_needed
        ]) or "- No new tools required"

        risks_md = "\n".join([f"- {r}" for r in self.potential_risks]) or "- No significant risks identified"
        criteria_md = "\n".join([f"- {c}" for c in self.success_criteria]) or "- TBD"

        return f"""# Agent Proposal: {self.role}

## Summary
**Gap Being Addressed:** {self.gap_id}
**Proposed By:** {self.proposed_by}
**Confidence:** {self.proposal_confidence:.0%}
**Team:** {self.team}

## Agent Definition

**Role:** {self.role}

**Goal:** {self.goal}

**Backstory:**
{self.backstory}

## Capabilities
{chr(10).join([f"- {c}" for c in self.capabilities])}

## Required Tools
{tools_md}

## Design Rationale
{self.design_rationale}

## Potential Risks
{risks_md}

## Success Criteria
{criteria_md}

## Resource Requirements
{self.resource_estimate or "TBD"}

## Model Requirements
{self.model_requirements or "Standard model capabilities sufficient"}
"""


@dataclass
class BoardDebateRound:
    """A single round of debate between board members."""

    round_number: int
    topic: str
    contributions: Dict[str, str] = field(default_factory=dict)  # model -> response
    consensus_points: List[str] = field(default_factory=list)
    disagreements: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "round_number": self.round_number,
            "topic": self.topic,
            "contributions": self.contributions,
            "consensus_points": self.consensus_points,
            "disagreements": self.disagreements,
        }


@dataclass
class BoardSession:
    """A complete Advisory Board session for resolving a capability gap."""

    id: str
    gap_id: str
    gap_description: str

    # Board members
    members: List[str] = field(default_factory=list)  # Model IDs

    # Session flow
    proposals: List[AgentProposal] = field(default_factory=list)
    debate_rounds: List[BoardDebateRound] = field(default_factory=list)

    # Outcome
    final_recommendation: Optional[AgentProposal] = None
    recommendation_rationale: str = ""
    dissenting_opinions: List[str] = field(default_factory=list)

    # Status
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "gap_id": self.gap_id,
            "gap_description": self.gap_description,
            "members": self.members,
            "proposals": [p.to_dict() for p in self.proposals],
            "debate_rounds": [r.to_dict() for r in self.debate_rounds],
            "final_recommendation": self.final_recommendation.to_dict() if self.final_recommendation else None,
            "recommendation_rationale": self.recommendation_rationale,
            "dissenting_opinions": self.dissenting_opinions,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

"""
Advisory Board for Brain Trust / Legion

When Willow identifies a capability gap, the Advisory Board convenes
frontier models to design a solution.

Process:
1. Gap identified by Willow
2. Board convened (Claude Opus, Gemini Pro, GPT-4)
3. Each model proposes a solution
4. Structured debate (2 rounds)
5. Vote with reasoning
6. Present recommendation to user
7. User approves → agent built
"""

import os
import uuid
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from .proposal_schema import (
    AgentProposal,
    ToolProposal,
    BoardSession,
    BoardDebateRound,
    ProposalStatus,
)
from .capability_registry import CapabilityGap

logger = logging.getLogger(__name__)


class AdvisoryBoard:
    """
    The Advisory Board - a council of frontier models.

    Convenes to resolve capability gaps through structured discussion.
    """

    # Default board members (can be configured)
    DEFAULT_MEMBERS = [
        "claude-sonnet-4-20250514",  # Anthropic
        "gemini-2.0-flash",          # Google (fast reasoning)
        "gpt-4o",                    # OpenAI
    ]

    def __init__(
        self,
        members: Optional[List[str]] = None,
        debate_rounds: int = 2,
    ):
        """
        Initialize the Advisory Board.

        Args:
            members: List of model IDs to serve on the board
            debate_rounds: Number of debate rounds before voting
        """
        self.members = members or self.DEFAULT_MEMBERS
        self.debate_rounds = debate_rounds
        self._sessions: Dict[str, BoardSession] = {}

    def convene(self, gap: CapabilityGap) -> BoardSession:
        """
        Convene the board to address a capability gap.

        Args:
            gap: The capability gap to address

        Returns:
            BoardSession with proposals and recommendation
        """
        logger.info(f"Advisory Board convening for gap: {gap.description}")

        session = BoardSession(
            id=str(uuid.uuid4())[:8],
            gap_id=gap.id,
            gap_description=gap.description,
            members=self.members,
        )

        # Phase 1: Initial Proposals
        logger.info("Phase 1: Gathering initial proposals")
        session.proposals = self._gather_proposals(gap, session)

        # Phase 2: Debate Rounds
        logger.info("Phase 2: Structured debate")
        for round_num in range(1, self.debate_rounds + 1):
            debate_round = self._conduct_debate_round(session, round_num)
            session.debate_rounds.append(debate_round)

        # Phase 3: Voting
        logger.info("Phase 3: Final vote")
        self._conduct_vote(session)

        # Phase 4: Final Recommendation
        logger.info("Phase 4: Synthesizing recommendation")
        self._synthesize_recommendation(session)

        session.completed_at = datetime.now()
        self._sessions[session.id] = session

        logger.info(f"Board session {session.id} complete. Recommendation: {session.final_recommendation.role if session.final_recommendation else 'None'}")

        return session

    def _gather_proposals(
        self,
        gap: CapabilityGap,
        session: BoardSession,
    ) -> List[AgentProposal]:
        """Gather proposals from each board member."""
        proposals = []

        for member in self.members:
            try:
                proposal = self._get_proposal_from_model(member, gap, session)
                if proposal:
                    proposals.append(proposal)
            except Exception as e:
                logger.error(f"Failed to get proposal from {member}: {e}")

        return proposals

    def _get_proposal_from_model(
        self,
        model_id: str,
        gap: CapabilityGap,
        session: BoardSession,
    ) -> Optional[AgentProposal]:
        """Get a proposal from a specific model."""

        prompt = f"""You are a member of the Legion Advisory Board.
A capability gap has been identified and you need to propose a solution.

## Capability Gap
**Description:** {gap.description}
**Context:** {gap.context}
**Priority:** {gap.priority}

## Your Task
Design a new agent to fill this capability gap. Respond with JSON only.

{{
    "role": "<agent role name>",
    "goal": "<primary goal of this agent>",
    "backstory": "<2-3 sentence backstory>",
    "team": "<Editorial|Technical|Production|Research>",
    "capabilities": ["<capability1>", "<capability2>"],
    "tools_needed": [
        {{"name": "<tool name>", "description": "<what it does>", "parameters": []}}
    ],
    "model_requirements": "<any special requirements>",
    "resource_estimate": "<estimated tokens/task>",
    "design_rationale": "<why this design>",
    "potential_risks": ["<risk1>", "<risk2>"],
    "success_criteria": ["<criterion1>", "<criterion2>"],
    "confidence": <0.0-1.0>
}}

Output only valid JSON."""

        response = self._call_model(model_id, prompt)
        if not response:
            return None

        try:
            data = self._parse_json(response)

            tools = [
                ToolProposal(
                    name=t["name"],
                    description=t["description"],
                    parameters=t.get("parameters", []),
                )
                for t in data.get("tools_needed", [])
            ]

            return AgentProposal(
                id=str(uuid.uuid4())[:8],
                gap_id=gap.id,
                role=data["role"],
                goal=data["goal"],
                backstory=data["backstory"],
                team=data.get("team", "Editorial"),
                capabilities=data.get("capabilities", []),
                tools_needed=tools,
                model_requirements=data.get("model_requirements", ""),
                resource_estimate=data.get("resource_estimate", ""),
                design_rationale=data.get("design_rationale", ""),
                potential_risks=data.get("potential_risks", []),
                success_criteria=data.get("success_criteria", []),
                proposed_by=model_id,
                proposal_confidence=float(data.get("confidence", 0.7)),
                status=ProposalStatus.SUBMITTED,
            )

        except Exception as e:
            logger.error(f"Failed to parse proposal from {model_id}: {e}")
            return None

    def _conduct_debate_round(
        self,
        session: BoardSession,
        round_num: int,
    ) -> BoardDebateRound:
        """Conduct a single round of debate."""

        # Build context from proposals
        proposals_summary = "\n\n".join([
            f"## Proposal from {p.proposed_by}\n"
            f"**Role:** {p.role}\n"
            f"**Goal:** {p.goal}\n"
            f"**Rationale:** {p.design_rationale}"
            for p in session.proposals
        ])

        # Previous rounds context
        previous_rounds = ""
        if session.debate_rounds:
            previous_rounds = "\n\n## Previous Discussion\n"
            for dr in session.debate_rounds:
                for model, contrib in dr.contributions.items():
                    previous_rounds += f"**{model}:** {contrib[:200]}...\n"

        round = BoardDebateRound(
            round_number=round_num,
            topic=f"Round {round_num}: Evaluate proposals and identify concerns",
        )

        for member in self.members:
            prompt = f"""You are on the Legion Advisory Board, round {round_num} of debate.

## Gap Being Addressed
{session.gap_description}

## Current Proposals
{proposals_summary}

{previous_rounds}

## Your Task (Round {round_num})
Evaluate the proposals. What are the strengths and weaknesses?
What concerns do you have? What would you change?

Be constructive and specific. Keep your response under 200 words."""

            response = self._call_model(member, prompt)
            if response:
                round.contributions[member] = response

        return round

    def _conduct_vote(self, session: BoardSession) -> None:
        """Have board members vote on proposals."""

        proposals_summary = "\n\n".join([
            f"## Proposal {i+1}: {p.role} (by {p.proposed_by})\n"
            f"**Goal:** {p.goal}\n"
            f"**Confidence:** {p.proposal_confidence:.0%}"
            for i, p in enumerate(session.proposals)
        ])

        for member in self.members:
            prompt = f"""You are voting on the Advisory Board.

## Proposals
{proposals_summary}

## Your Task
Vote for ONE proposal. Respond with JSON:
{{
    "vote_for_index": <0-based index of proposal>,
    "reasoning": "<why you chose this proposal>",
    "concerns": "<any remaining concerns>"
}}

Output only valid JSON."""

            response = self._call_model(member, prompt)
            if response:
                try:
                    data = self._parse_json(response)
                    vote_idx = int(data.get("vote_for_index", 0))

                    if 0 <= vote_idx < len(session.proposals):
                        proposal = session.proposals[vote_idx]
                        proposal.votes_for.append(member)
                        proposal.vote_reasoning[member] = data.get("reasoning", "")

                except Exception as e:
                    logger.error(f"Failed to parse vote from {member}: {e}")

    def _synthesize_recommendation(self, session: BoardSession) -> None:
        """Synthesize the final recommendation."""

        if not session.proposals:
            return

        # Find proposal with most votes
        best_proposal = max(
            session.proposals,
            key=lambda p: len(p.votes_for),
        )

        best_proposal.status = ProposalStatus.APPROVED
        session.final_recommendation = best_proposal

        # Build rationale from votes
        vote_reasons = [
            f"- {model}: {reason}"
            for model, reason in best_proposal.vote_reasoning.items()
        ]

        session.recommendation_rationale = (
            f"Selected '{best_proposal.role}' with {len(best_proposal.votes_for)}/{len(self.members)} votes.\n\n"
            f"Voting rationale:\n" + "\n".join(vote_reasons)
        )

        # Note any dissenting opinions
        for proposal in session.proposals:
            if proposal != best_proposal and proposal.votes_for:
                session.dissenting_opinions.append(
                    f"{', '.join(proposal.votes_for)} preferred '{proposal.role}'"
                )

    def _call_model(self, model_id: str, prompt: str) -> Optional[str]:
        """Call a model and return its response."""
        model_lower = model_id.lower()

        try:
            if 'gemini' in model_lower:
                from langchain_google_genai import ChatGoogleGenerativeAI
                llm = ChatGoogleGenerativeAI(
                    model=model_id,
                    google_api_key=os.getenv("GEMINI_API_KEY"),
                    temperature=0.7,
                )
                response = llm.invoke(prompt)
                return response.content

            elif 'claude' in model_lower or 'sonnet' in model_lower or 'opus' in model_lower:
                from langchain_anthropic import ChatAnthropic
                llm = ChatAnthropic(
                    model_name=model_id,
                    api_key=os.getenv("ANTHROPIC_API_KEY"),
                    temperature=0.7,
                )
                response = llm.invoke(prompt)
                return response.content

            elif 'gpt' in model_lower:
                try:
                    from langchain_openai import ChatOpenAI
                    llm = ChatOpenAI(
                        model=model_id,
                        api_key=os.getenv("OPENAI_API_KEY"),
                        temperature=0.7,
                    )
                    response = llm.invoke(prompt)
                    return response.content
                except ImportError:
                    logger.warning(f"OpenAI not available, skipping {model_id}")
                    return None

        except Exception as e:
            logger.error(f"Error calling {model_id}: {e}")
            return None

    def _parse_json(self, text: str) -> Dict[str, Any]:
        """Parse JSON from model response."""
        content = text.strip()

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        return json.loads(content.strip())

    def get_session(self, session_id: str) -> Optional[BoardSession]:
        """Get a specific board session."""
        return self._sessions.get(session_id)

    def list_sessions(self) -> List[BoardSession]:
        """List all board sessions."""
        return list(self._sessions.values())


def convene_advisory_board(gap: CapabilityGap) -> BoardSession:
    """Convenience function to convene the advisory board."""
    board = AdvisoryBoard()
    return board.convene(gap)

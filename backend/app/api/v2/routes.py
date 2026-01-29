"""
API v2 Routes - Legion v3 Endpoints

New architecture endpoints for Willow and intelligent orchestration.
"""

from fastapi import APIRouter, HTTPException, Security
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from app.core.auth import verify_api_key
from app.agents import get_willow
from app.core.intent_parser import parse_intent
from app.core.plan_proposer import propose_plan
from app.core.capability_registry import get_capability_registry
from app.core.team_dispatcher import dispatch_plan

router = APIRouter(prefix="/v2", tags=["legion-v3"])


class IntentRequest(BaseModel):
    """Request to process user intent."""
    message: str
    auto_execute: bool = False  # Execute immediately without approval
    context: Optional[str] = None  # Additional context


class IntentResponse(BaseModel):
    """Response from Willow."""
    message: str
    plan: Optional[Dict[str, Any]] = None
    execution_result: Optional[Dict[str, Any]] = None
    needs_input: bool = False
    input_options: List[str] = []
    escalation: bool = False


class PlanApprovalRequest(BaseModel):
    """Request to approve/modify a plan."""
    plan_id: str
    action: str  # "approve", "modify", "cancel"
    modifications: Optional[str] = None


class CapabilityGapRequest(BaseModel):
    """Request to register a capability gap."""
    description: str
    context: str
    priority: str = "medium"


@router.post("/intent", dependencies=[Security(verify_api_key)])
async def process_intent(request: IntentRequest) -> IntentResponse:
    """
    Main entry point for Legion v3.

    Send natural language intent to Willow, receive plans and results.

    Example:
        POST /api/v2/intent
        {"message": "I want to finish editing chapter 3"}

    Returns proposed plan or execution result.
    """
    willow = get_willow()

    if request.auto_execute:
        willow.auto_execute = True

    response = willow.process(request.message)

    return IntentResponse(
        message=response.message,
        plan=response.plan.to_dict() if response.plan else None,
        execution_result=response.execution_result.to_dict() if response.execution_result else None,
        needs_input=response.needs_input,
        input_options=response.input_options,
        escalation=response.escalation,
    )


@router.post("/intent/approve", dependencies=[Security(verify_api_key)])
async def approve_plan(request: PlanApprovalRequest) -> IntentResponse:
    """
    Approve, modify, or cancel a proposed plan.

    Actions:
    - "approve": Execute the plan
    - "modify": Update the plan (provide modifications)
    - "cancel": Cancel the plan
    """
    willow = get_willow()

    if request.action == "approve":
        response = willow.approve_and_execute()
    elif request.action == "cancel":
        response = willow.process("cancel")
    elif request.action == "modify":
        response = willow.process(f"modify the plan: {request.modifications}")
    else:
        raise HTTPException(status_code=400, detail=f"Unknown action: {request.action}")

    return IntentResponse(
        message=response.message,
        plan=response.plan.to_dict() if response.plan else None,
        execution_result=response.execution_result.to_dict() if response.execution_result else None,
        needs_input=response.needs_input,
        input_options=response.input_options,
        escalation=response.escalation,
    )


@router.get("/capabilities", dependencies=[Security(verify_api_key)])
async def list_capabilities(
    category: Optional[str] = None,
    team: Optional[str] = None,
):
    """
    List available Legion capabilities.

    Filter by category or team.
    """
    registry = get_capability_registry()

    if category:
        from app.core.capability_registry import CapabilityCategory
        try:
            cat_enum = CapabilityCategory(category)
            capabilities = registry.get_by_category(cat_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Unknown category: {category}")
    elif team:
        capabilities = registry.get_by_team(team)
    else:
        capabilities = registry.get_all_capabilities()

    return {
        "count": len(capabilities),
        "capabilities": [c.to_dict() for c in capabilities],
    }


@router.get("/capabilities/{capability_id}", dependencies=[Security(verify_api_key)])
async def get_capability(capability_id: str):
    """Get details of a specific capability."""
    registry = get_capability_registry()
    capability = registry.get_capability(capability_id)

    if not capability:
        raise HTTPException(status_code=404, detail=f"Capability not found: {capability_id}")

    return capability.to_dict()


@router.get("/capabilities/search/{query}", dependencies=[Security(verify_api_key)])
async def search_capabilities(query: str):
    """Search capabilities by keyword."""
    registry = get_capability_registry()
    results = registry.search(query)

    return {
        "query": query,
        "count": len(results),
        "capabilities": [c.to_dict() for c in results],
    }


@router.get("/gaps", dependencies=[Security(verify_api_key)])
async def list_capability_gaps():
    """List open capability gaps."""
    registry = get_capability_registry()
    gaps = registry.get_open_gaps()

    return {
        "count": len(gaps),
        "gaps": [g.to_dict() for g in gaps],
    }


@router.post("/gaps", dependencies=[Security(verify_api_key)])
async def register_gap(request: CapabilityGapRequest):
    """Register a new capability gap."""
    registry = get_capability_registry()
    gap = registry.register_gap(
        description=request.description,
        requested_by="api",
        context=request.context,
        priority=request.priority,
    )

    return gap.to_dict()


@router.post("/gaps/{gap_id}/resolve", dependencies=[Security(verify_api_key)])
async def resolve_gap(gap_id: str, resolution: str):
    """Mark a capability gap as resolved."""
    registry = get_capability_registry()
    success = registry.resolve_gap(gap_id, resolution)

    if not success:
        raise HTTPException(status_code=404, detail=f"Gap not found: {gap_id}")

    return {"status": "resolved", "gap_id": gap_id}


@router.get("/status", dependencies=[Security(verify_api_key)])
async def get_status():
    """Get current Legion status."""
    willow = get_willow()
    registry = get_capability_registry()

    return {
        "willow": {
            "name": willow.PROFILE["name"],
            "role": willow.PROFILE["role"],
            "active_plan": willow.current_plan.to_dict() if willow.current_plan else None,
            "conversation_length": len(willow.conversation_history),
        },
        "capabilities": {
            "total": len(registry.get_all_capabilities()),
            "open_gaps": len(registry.get_open_gaps()),
        },
    }


# ==================== Advisory Board Endpoints ====================

class ConveneRequest(BaseModel):
    """Request to convene the Advisory Board."""
    gap_id: str


class BuildAgentRequest(BaseModel):
    """Request to build an agent from a proposal."""
    proposal_id: str
    session_id: str


@router.post("/board/convene", dependencies=[Security(verify_api_key)])
async def convene_advisory_board(request: ConveneRequest):
    """
    Convene the Advisory Board to address a capability gap.

    This is an expensive operation that calls multiple frontier models.
    The board will propose, debate, and vote on solutions.
    """
    from app.core.advisory_board import AdvisoryBoard
    from app.core.capability_registry import get_capability_registry

    registry = get_capability_registry()

    # Find the gap
    gap = None
    for g in registry.gaps.values():
        if g.id == request.gap_id:
            gap = g
            break

    if not gap:
        raise HTTPException(status_code=404, detail=f"Gap not found: {request.gap_id}")

    # Convene the board
    board = AdvisoryBoard()
    session = board.convene(gap)

    return session.to_dict()


@router.get("/board/sessions", dependencies=[Security(verify_api_key)])
async def list_board_sessions():
    """List all Advisory Board sessions."""
    from app.core.advisory_board import AdvisoryBoard

    board = AdvisoryBoard()
    sessions = board.list_sessions()

    return {
        "count": len(sessions),
        "sessions": [
            {
                "id": s.id,
                "gap_id": s.gap_id,
                "gap_description": s.gap_description,
                "recommendation": s.final_recommendation.role if s.final_recommendation else None,
                "completed": s.completed_at is not None,
            }
            for s in sessions
        ],
    }


@router.get("/board/sessions/{session_id}", dependencies=[Security(verify_api_key)])
async def get_board_session(session_id: str):
    """Get details of a specific board session."""
    from app.core.advisory_board import AdvisoryBoard

    board = AdvisoryBoard()
    session = board.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    return session.to_dict()


@router.post("/board/build", dependencies=[Security(verify_api_key)])
async def build_agent_from_board(request: BuildAgentRequest):
    """
    Build an agent from an approved Advisory Board proposal.

    This creates:
    - Agent configuration file
    - Tool stubs (if needed)
    - Capability registry entries
    """
    from app.core.advisory_board import AdvisoryBoard
    from app.core.agent_builder import AgentBuilder
    from app.core.proposal_schema import ProposalStatus

    board = AdvisoryBoard()
    session = board.get_session(request.session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {request.session_id}")

    # Find the proposal
    proposal = None
    for p in session.proposals:
        if p.id == request.proposal_id:
            proposal = p
            break

    if not proposal:
        raise HTTPException(status_code=404, detail=f"Proposal not found: {request.proposal_id}")

    # Mark as approved if it's the recommendation
    if session.final_recommendation and session.final_recommendation.id == proposal.id:
        proposal.status = ProposalStatus.APPROVED
    else:
        raise HTTPException(
            status_code=400,
            detail="Can only build the recommended proposal. Use a different workflow for alternatives.",
        )

    # Build the agent
    builder = AgentBuilder()
    result = builder.build(proposal)

    return result


@router.get("/board/agents", dependencies=[Security(verify_api_key)])
async def list_built_agents():
    """List all agents built from Advisory Board proposals."""
    from app.core.agent_builder import AgentBuilder

    builder = AgentBuilder()
    agents = builder.list_built_agents()

    return {
        "count": len(agents),
        "agents": agents,
    }

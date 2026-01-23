from fastapi import APIRouter, HTTPException, BackgroundTasks, Security
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from app.core.workflow_parser import WorkflowParser
from app.core.auth import verify_api_key
import time

router = APIRouter()

class WorkflowRequest(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]

@router.post("/run-workflow", dependencies=[Security(verify_api_key)])
async def run_workflow_endpoint(workflow: WorkflowRequest):
    """
    Receives React Flow graph JSON.
    Converts to CrewAI Crew with TELOS context from ~/.pai/
    Kicks off execution with dual-persistence logging.
    
    This is a personal tool - loads YOUR context from YOUR ~/.pai/ directory.
    
    SECURITY: Protected by API key authentication. Required when exposing
    to the internet (Cloudflare Tunnel, Tailscale, cloud hosting).
    
    Args:
        workflow: React Flow graph (nodes + edges)
    
    Headers:
        X-API-Key: Your BRAIN_TRUST_API_KEY from .env
    """
    start_time = time.time()
    
    try:
        # Convert Pydantic model to dict
        workflow_data = workflow.model_dump()
        
        # Initialize Parser
        parser = WorkflowParser(workflow_data)
        
        # Build Crew (with TELOS context and script tools from ~/.pai/)
        crew = parser.parse_graph()
        
        # Execute (Wrapped in Logger for streaming)
        from app.core.logger import StdoutInterceptor
        
        with StdoutInterceptor():
            result = crew.kickoff()
        
        duration = time.time() - start_time
        
        # Dual logging: Database + Markdown
        from app.core.journaling import JournalingProtocol
        journal = JournalingProtocol()
        await journal.log_execution(
            workflow_data=workflow_data,
            result=result,
            agents_count=len(crew.agents),
            duration_seconds=duration
        )
        
        return {
            "status": "success",
            "result": str(result),
            "agent_count": len(crew.agents),
            "task_count": len(crew.tasks),
            "duration": duration
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




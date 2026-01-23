from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from app.core.workflow_parser import WorkflowParser

router = APIRouter()

class WorkflowRequest(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]

@router.post("/run-workflow")
async def run_workflow_endpoint(workflow: WorkflowRequest):
    """
    Receives React Flow graph JSON.
    Converts to CrewAI Crew.
    Kicks off execution.
    """
    try:
        # Convert Pydantic model to dict
        workflow_data = workflow.model_dump()
        
        # Initialize Parser
        parser = WorkflowParser(workflow_data)
        
        # Build Crew
        crew = parser.parse_graph()
        
        # Execute (Wrapped in Logger for streaming)
        from app.core.logger import StdoutInterceptor
        
        with StdoutInterceptor():
            result = crew.kickoff()
        
        # Log to Supabase
        from app.core.db import SupabaseManager
        db = SupabaseManager()
        db.save_execution(
            workflow_data=workflow_data, 
            result=result, 
            agents_count=len(crew.agents)
        )
        
        return {
            "status": "success",
            "result": str(result),
            "agent_count": len(crew.agents),
            "task_count": len(crew.tasks)
        }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

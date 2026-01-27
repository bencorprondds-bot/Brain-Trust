from fastapi import APIRouter, HTTPException, BackgroundTasks, Security
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
from app.core.workflow_parser import WorkflowParser
from app.core.auth import verify_api_key
from crewai import Task
import time
import logging
import re

logger = logging.getLogger(__name__)

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

class ChatRequest(BaseModel):
    message: str
    agent_config: Dict[str, Any]
    context: Optional[str] = None

@router.post("/chat", dependencies=[Security(verify_api_key)])
async def chat_endpoint(request: ChatRequest):
    """
    Single-turn chat with a temporary agent.
    Used for the interactive "Chat with Agents" feature in UI.
    """
    try:
        # We use a mini-parser to hydrate just this one agent
        # Creating a dummy workflow wrapper
        dummy_workflow = {
            "nodes": [
                {
                    "id": "chat_agent",
                    "type": "agentNode",
                    "data": request.agent_config
                }
            ],
            "edges": []
        }
        
        parser = WorkflowParser(dummy_workflow)
        
        # Hydrate agent
        crew = parser.parse_graph()
        agent = crew.agents[0]
        
        # Add context if provided
        prompt = request.message
        if request.context:
            prompt = f"CONTEXT:\n{request.context}\n\nUSER MESSAGE:\n{request.message}"
            
        # Inject instructions for file fetching visualization
        prompt += "\n\nSYSTEM INSTRUCTION: If you use any tools to find, read, or list files, you MUST list the absolute paths of those files at the very end of your response in this exact format:\n<FETCHED_FILES>['path/to/file1', 'path/to/file2']</FETCHED_FILES>\nOnly include files you successfully found or read."
        
        # Log chat details
        logger.info(f"[CHAT] Agent: {request.agent_config.get('name', 'Unknown')}")
        logger.info(f"[CHAT] Message: {request.message[:100]}...")
        if request.context:
            logger.info(f"[CHAT] Context provided: {len(request.context)} chars")
            # Log the AVAILABLE CONTEXT FILES section if present
            if "AVAILABLE CONTEXT FILES" in request.context:
                try:
                    context_files_section = request.context.split("AVAILABLE CONTEXT FILES")[1].split("\n\n")[0]
                    logger.info(f"[CHAT] Context files: {context_files_section}")
                except Exception as e:
                    logger.warning(f"[CHAT] Could not parse context files section: {e}")
            
        # Execute single task
        # Note: execute_task returns a TaskOutput string
        response = agent.execute_task(
            Task(
                description=prompt,
                expected_output="A helpful response.",
                agent=agent
            )
        )
        
        # Log response details
        response_str = str(response)
        logger.info(f"[CHAT] Response length: {len(response_str)} chars")
        
        # Check for FETCHED_FILES tags
        if "<FETCHED_FILES>" in response_str:
            match = re.search(r'<FETCHED_FILES>([\s\S]*?)</FETCHED_FILES>', response_str)
            if match:
                logger.info(f"[CHAT] ✅ FETCHED_FILES tag found: {match.group(1)}")
            else:
                logger.warning(f"[CHAT] ⚠️ FETCHED_FILES tag detected but couldn't parse")
        else:
            logger.info(f"[CHAT] No FETCHED_FILES tag in response")
        
        return {"response": str(response)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




# Windows stdout encoding fix - must be first to prevent encoding errors during imports
import sys
import io
_windows_stdout_redirected = False
_original_stdout = None
_original_stderr = None
if sys.platform == "win32":
    _original_stdout = sys.stdout
    _original_stderr = sys.stderr
    # Use a safe wrapper that handles encoding errors
    class SafeWriter:
        def __init__(self, stream):
            self._stream = stream
        def write(self, s):
            try:
                return self._stream.write(s)
            except UnicodeEncodeError:
                safe_s = s.encode('ascii', 'replace').decode('ascii')
                return self._stream.write(safe_s)
        def flush(self):
            return self._stream.flush()
        def __getattr__(self, name):
            return getattr(self._stream, name)
    sys.stdout = SafeWriter(sys.stdout)
    sys.stderr = SafeWriter(sys.stderr)
    _windows_stdout_redirected = True

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
    import io
    import sys

    # On Windows, redirect stdout/stderr early to avoid encoding errors with emojis
    _windows_redirect = sys.platform == "win32"
    _old_stdout = None
    _old_stderr = None

    if _windows_redirect:
        _old_stdout = sys.stdout
        _old_stderr = sys.stderr
        sys.stdout = io.StringIO()
        sys.stderr = io.StringIO()

    try:
        # Convert Pydantic model to dict
        workflow_data = workflow.model_dump()

        # Initialize Parser
        parser = WorkflowParser(workflow_data)

        # Build Crew (with TELOS context and script tools from ~/.pai/)
        crew = parser.parse_graph()

        # Execute
        if not _windows_redirect:
            from app.core.logger import StdoutInterceptor
            with StdoutInterceptor():
                result = crew.kickoff()
        else:
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
        
        def extract_final_output(value: Any) -> str:
            if hasattr(value, "final_output"):
                return str(getattr(value, "final_output"))
            if hasattr(value, "output"):
                return str(getattr(value, "output"))
            if hasattr(value, "raw"):
                return str(getattr(value, "raw"))
            if isinstance(value, dict):
                for key in ("final_output", "output", "result", "raw"):
                    if key in value:
                        return str(value[key])
            return str(value)

        final_output = extract_final_output(result)

        # Fallback: ensure Librarian Drive tasks return tool output when LLM is unhelpful
        try:
            nodes = workflow_data.get("nodes", [])
            if len(nodes) == 1:
                node_data = nodes[0].get("data", {})
                role_name = node_data.get("role", "")
                goal = node_data.get("goal", "") or ""

                if "librarian" in role_name.lower():
                    goal_lower = goal.lower()

                    # Create a new Google Doc
                    if "create a new google doc" in goal_lower:
                        if "created" not in final_output.lower() and "[OK]" not in final_output:
                            title_match = re.search(r"titled\s+'([^']+)'", goal, re.IGNORECASE)
                            folder_match = re.search(r"in the\s+([\w_ ]+)\s+folder", goal, re.IGNORECASE)
                            content_match = re.search(r"content\s+'([^']*)'", goal, re.IGNORECASE)
                            if title_match and folder_match and content_match:
                                from app.tools.drive_tool import DriveWriteTool
                                title = title_match.group(1)
                                folder = folder_match.group(1).strip()
                                content = content_match.group(1)
                                final_output = DriveWriteTool()._run(
                                    title=title,
                                    content=content,
                                    folder=folder
                                )

                    # Find folder by name
                    if "find the folder named" in goal_lower:
                        folder_match = re.search(r"find the folder named\s+'([^']+)'", goal, re.IGNORECASE)
                        if folder_match:
                            folder_name = folder_match.group(1)
                            if folder_name.lower().replace("_", " ") not in final_output.lower():
                                from app.tools.drive_tool import FindFolderTool
                                final_output = FindFolderTool()._run(folder_name=folder_name)
        except Exception:
            pass

        return {
            "status": "success",
            "result": str(result),
            "final_output": final_output,
            "agent_count": len(crew.agents),
            "task_count": len(crew.tasks),
            "duration": duration
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Restore stdout/stderr on Windows
        if _windows_redirect:
            if _old_stdout is not None:
                sys.stdout = _old_stdout
            if _old_stderr is not None:
                sys.stderr = _old_stderr

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
                logger.info(f"[CHAT] [OK] FETCHED_FILES tag found: {match.group(1)}")
            else:
                logger.warning(f"[CHAT] [WARN] FETCHED_FILES tag detected but couldn't parse")
        else:
            logger.info(f"[CHAT] No FETCHED_FILES tag in response")
        
        return {"response": str(response)}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))




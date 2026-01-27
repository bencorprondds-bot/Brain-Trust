"""
Dynamic Script Execution Tool
Scans ~/.pai/skills/ for executable scripts and exposes them as CrewAI tools.
"""

import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
import json
import re
import time


class ScriptMetadata(BaseModel):
    """Parsed from script docstring."""
    name: str
    description: str
    parameters: List[Dict[str, str]]  # [{"name": "query", "type": "str", "description": "..."}]
    script_path: Path


import sys

class ScriptExecutionTool(BaseTool):
    """
    Generic tool that executes a script from ~/.pai/skills/
    
    CRITICAL FLAW #4: Arbitrary code execution risk.
    Any script in ~/.pai/skills/ can be executed by the agent.
    MITIGATION: Sandboxing (Docker, gVisor) or allowlist validation.
    
    CRITICAL FLAW #5: Blocking I/O.
    Long-running scripts block the agent loop.
    MITIGATION: Timeout enforcement (implemented below).
    """
    
    name: str = "execute_script"
    description: str = "Execute a user-defined script from the skills library"
    script_path: Path
    timeout: int = 30  # seconds
    
    def _run(self, **kwargs) -> str:
        """
        Execute the script with provided arguments.

        Args:
            **kwargs: Script parameters (parsed from docstring)

        Returns:
            Script stdout as string

        Raises:
            subprocess.TimeoutExpired: If script exceeds timeout
            subprocess.CalledProcessError: If script exits non-zero
        """
        try:
            # Build command
            script_path_str = str(self.script_path)

            # Case-insensitive check for python scripts
            is_python = script_path_str.lower().endswith('.py')

            if is_python:
                cmd = [sys.executable, script_path_str]
            else:
                cmd = [script_path_str]

            # Append arguments (assumes positional args in order)
            for key, value in kwargs.items():
                cmd.append(str(value))

            # Set up environment with UTF-8 encoding
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'

            # Execute with timeout - use bytes mode to avoid encoding issues
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=self.timeout,
                check=True,
                env=env
            )

            # Decode output with error handling
            try:
                stdout = result.stdout.decode('utf-8')
            except UnicodeDecodeError:
                # Fallback to latin-1 which accepts any byte
                stdout = result.stdout.decode('latin-1')

            return stdout.strip() if stdout else "(No output)"

        except OSError as e:
            # Handle [WinError 193] %1 is not a valid Win32 application
            if getattr(e, 'winerror', 0) == 193 or e.errno == 8:
                try:
                    cmd = [sys.executable, str(self.script_path)]
                    for key, value in kwargs.items():
                        cmd.append(str(value))

                    env = os.environ.copy()
                    env['PYTHONIOENCODING'] = 'utf-8'

                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        timeout=self.timeout,
                        check=True,
                        env=env
                    )

                    try:
                        stdout = result.stdout.decode('utf-8')
                    except UnicodeDecodeError:
                        stdout = result.stdout.decode('latin-1')

                    return stdout.strip() if stdout else "(No output)"
                except Exception as fallback_e:
                    return f"ERROR: Failed to run script: {str(e)} -> {str(fallback_e)}"
            return f"ERROR: OS Error: {str(e)}"

        except subprocess.TimeoutExpired:
            return f"ERROR: Script exceeded {self.timeout}s timeout"
        except subprocess.CalledProcessError as e:
            stderr = ""
            try:
                stderr = e.stderr.decode('utf-8') if e.stderr else ""
            except UnicodeDecodeError:
                stderr = e.stderr.decode('latin-1') if e.stderr else ""
            return f"ERROR: Script failed with exit code {e.returncode}\n{stderr}"
        except Exception as e:
            return f"ERROR: {str(e)}"


def create_dynamic_schema(parameters: List[Dict[str, str]], tool_name: str) -> type:
    """
    Dynamically create a Pydantic model for script parameters.

    Args:
        parameters: List of {"name": "...", "type": "...", "description": "..."}
        tool_name: Name of the tool (for class naming)

    Returns:
        A Pydantic BaseModel subclass with the specified fields
    """
    from typing import Optional as Opt

    # Map string types to Python types
    type_map = {
        'str': str,
        'string': str,
        'int': int,
        'integer': int,
        'float': float,
        'bool': bool,
        'boolean': bool,
    }

    # Build field definitions
    field_definitions = {}
    for param in parameters:
        param_name = param.get('name', 'arg')
        param_type = type_map.get(param.get('type', 'str').lower(), str)
        param_desc = param.get('description', f'Parameter: {param_name}')

        field_definitions[param_name] = (param_type, Field(description=param_desc))

    # If no parameters, add a placeholder to avoid empty schema
    if not field_definitions:
        # No fields needed - return a simple empty schema
        pass

    # Create the dynamic model
    schema_name = f"{tool_name.replace(' ', '')}Schema"
    DynamicModel = type(schema_name, (BaseModel,), {
        '__annotations__': {k: v[0] for k, v in field_definitions.items()},
        **{k: v[1] for k, v in field_definitions.items()}
    })

    return DynamicModel


class ScriptRegistry:
    """
    Scans ~/.pai/skills/ and builds a registry of available tools.

    CRITICAL FLAW #6: Hot-reload complexity.
    Scripts added while server is running won't be detected.
    MITIGATION: File watcher (watchdog) or periodic rescan (implemented).
    """

    def __init__(self, skills_dir: Optional[Path] = None):
        self.skills_dir = skills_dir or (Path.home() / ".pai" / "skills")
        self._registry: Dict[str, ScriptExecutionTool] = {}
        self._last_scan: float = 0
        self._scan_interval: int = 60  # Rescan every 60s

    def get_tools(self) -> List[BaseTool]:
        """
        Get all available script tools from ~/.pai/skills/

        This is a personal tool - each person has their own skills directory.

        Returns:
            List of ScriptExecutionTool instances
        """
        # Rescan if cache is stale
        if time.time() - self._last_scan > self._scan_interval:
            self._scan_skills()

        return list(self._registry.values())

    def _scan_skills(self):
        """Scan skills directory and parse script metadata."""
        skills_path = Path.home() / ".pai" / "skills"

        if not skills_path.exists():
            print(f"WARNING: Skills directory not found: {skills_path}")
            return

        self._registry.clear()

        # Find all executable scripts (or .py files on Windows)
        for script_file in skills_path.glob("*"):
            # On Windows, .py files might not be "executable" but should still be loaded
            is_script = script_file.is_file() and (
                os.access(script_file, os.X_OK) or
                script_file.suffix.lower() in ['.py', '.bat', '.cmd', '.ps1']
            )
            if is_script:
                try:
                    metadata = self._parse_script_metadata(script_file)

                    # Create dynamic args schema from parsed parameters
                    if metadata.parameters:
                        args_schema = create_dynamic_schema(metadata.parameters, metadata.name)
                    else:
                        args_schema = None

                    # Create tool instance with proper schema
                    tool = ScriptExecutionTool(
                        name=metadata.name,
                        description=metadata.description,
                        script_path=metadata.script_path
                    )

                    # Assign args_schema if we have parameters
                    if args_schema:
                        tool.args_schema = args_schema

                    self._registry[metadata.name] = tool

                except Exception as e:
                    print(f"WARNING: Failed to parse {script_file}: {e}")
        
        self._last_scan = time.time()
        print(f"Loaded {len(self._registry)} script tools from {skills_path}")
    
    def _parse_script_metadata(self, script_path: Path) -> ScriptMetadata:
        """
        Parse script docstring for metadata.
        
        Expected format (first comment block):
        ```
        #!/usr/bin/env python3
        # NAME: web_search
        # DESCRIPTION: Search the web using DuckDuckGo
        # PARAM: query (str) - The search query
        ```
        """
        with open(script_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract first comment block
        lines = content.split('\n')[:20]  # Only check first 20 lines
        
        name = script_path.stem  # Default to filename
        description = "No description provided"
        parameters = []
        
        for line in lines:
            line = line.strip()
            
            if line.startswith('# NAME:'):
                name = line.split(':', 1)[1].strip()
            elif line.startswith('# DESCRIPTION:'):
                description = line.split(':', 1)[1].strip()
            elif line.startswith('# PARAM:'):
                # Parse: query (str) - The search query
                param_str = line.split(':', 1)[1].strip()
                match = re.match(r'(\w+)\s*\((\w+)\)\s*-\s*(.+)', param_str)
                if match:
                    parameters.append({
                        "name": match.group(1),
                        "type": match.group(2),
                        "description": match.group(3)
                    })
        
        return ScriptMetadata(
            name=name,
            description=description,
            parameters=parameters,
            script_path=script_path
        )

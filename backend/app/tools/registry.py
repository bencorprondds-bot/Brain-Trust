"""
Tool Registry for Brain Trust

Central registry for all available tools. Discovers tools from:
1. Built-in tools (drive, script execution)
2. User tools (~/.pai/tools/*.yaml)
3. Dynamically registered tools

The registry provides tools to adapters which translate them
to provider-specific formats (CrewAI, OpenAI, Anthropic, MCP).

Design Philosophy:
- Single source of truth for tool definitions
- Hot-reload of user tools without restart
- Adapter pattern for provider flexibility
"""

import os
import logging
import importlib
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type
from datetime import datetime

from app.tools.schema import ToolDefinition, ToolCategory, ToolExecutionResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central registry for all available tools.

    Usage:
        registry = ToolRegistry()

        # Get tools for CrewAI
        crewai_tools = registry.get_for_adapter("crewai")

        # Get tools by category
        file_tools = registry.get_by_category(ToolCategory.FILE)

        # Execute a tool directly
        result = registry.execute("drive_list", folder_id="root")
    """

    _instance = None
    _BUILTIN_TOOLS_LOADED = False

    def __new__(cls):
        """Singleton pattern for shared registry access."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._tools: Dict[str, ToolDefinition] = {}
        self._executors: Dict[str, Callable] = {}
        self._adapters: Dict[str, Any] = {}
        self._last_user_scan: float = 0
        self._user_scan_interval: int = 60  # seconds

        # Load tools
        self._load_builtin_tools()
        self._load_user_tools()

        self._initialized = True
        logger.info(f"ToolRegistry initialized with {len(self._tools)} tools")

    def _load_builtin_tools(self) -> None:
        """Load built-in tool definitions."""
        if ToolRegistry._BUILTIN_TOOLS_LOADED:
            return

        # Define built-in tools programmatically
        # These match the existing CrewAI tools in drive_tool.py
        builtin_tools = [
            ToolDefinition(
                tool_id="drive_list",
                name="Google Drive Lister",
                description="Lists files and folders in a Google Drive folder. Use 'root' for the root folder or 'all' to list predefined folders.",
                parameters=[
                    {"name": "folder_id", "type": "string", "description": "Folder ID, 'root', or 'all'", "required": True}
                ],
                returns="string",
                executor="app.tools.drive_tool:DriveListTool",
                category="file",
                requires_auth=True,
                estimated_latency_ms=2000,
                tags=["drive", "files", "list"],
            ),
            ToolDefinition(
                tool_id="drive_read",
                name="Google Doc Reader",
                description="Reads the text content of a Google Doc by its file ID.",
                parameters=[
                    {"name": "file_id", "type": "string", "description": "The Google Doc file ID", "required": True}
                ],
                returns="string",
                executor="app.tools.drive_tool:DriveReadTool",
                category="file",
                requires_auth=True,
                estimated_latency_ms=3000,
                tags=["drive", "read", "document"],
            ),
            ToolDefinition(
                tool_id="drive_write",
                name="Google Doc Creator",
                description="Creates a new Google Doc with the specified title and content in a folder.",
                parameters=[
                    {"name": "title", "type": "string", "description": "Document title", "required": True},
                    {"name": "content", "type": "string", "description": "Document content", "required": True},
                    {"name": "folder", "type": "string", "description": "Target folder name", "required": True},
                ],
                returns="string",
                executor="app.tools.drive_tool:DriveWriteTool",
                category="file",
                requires_auth=True,
                estimated_latency_ms=5000,
                tags=["drive", "write", "create"],
            ),
            ToolDefinition(
                tool_id="find_folder",
                name="Google Drive Folder Finder",
                description="Finds a folder by name in Google Drive and returns its ID.",
                parameters=[
                    {"name": "folder_name", "type": "string", "description": "Name of the folder to find", "required": True}
                ],
                returns="string",
                executor="app.tools.drive_tool:FindFolderTool",
                category="file",
                requires_auth=True,
                estimated_latency_ms=2000,
                tags=["drive", "folder", "search"],
            ),
            ToolDefinition(
                tool_id="docs_edit",
                name="Google Docs Editor",
                description="Edits an existing Google Doc by inserting or replacing text.",
                parameters=[
                    {"name": "file_id", "type": "string", "description": "The Google Doc file ID", "required": True},
                    {"name": "insert_text", "type": "string", "description": "Text to insert at the end", "required": False},
                    {"name": "replace_text", "type": "string", "description": "Text to replace entire content with", "required": False},
                ],
                returns="string",
                executor="app.tools.drive_tool:DocsEditTool",
                category="file",
                requires_auth=True,
                estimated_latency_ms=4000,
                tags=["drive", "edit", "document"],
            ),
            ToolDefinition(
                tool_id="word_export",
                name="Word Document Exporter",
                description="Exports a Google Doc to Word format (.docx).",
                parameters=[
                    {"name": "file_id", "type": "string", "description": "The Google Doc file ID", "required": True}
                ],
                returns="string",
                executor="app.tools.drive_tool:WordDocExportTool",
                category="file",
                requires_auth=True,
                estimated_latency_ms=5000,
                tags=["drive", "export", "word"],
            ),
            ToolDefinition(
                tool_id="cached_file_read",
                name="Cached File Reader",
                description="Reads full content from a cached file path (for large documents).",
                parameters=[
                    {"name": "cache_path", "type": "string", "description": "Path to the cached file", "required": True}
                ],
                returns="string",
                executor="app.tools.drive_tool:CachedFileReadTool",
                category="file",
                requires_auth=False,
                estimated_latency_ms=100,
                tags=["cache", "read", "file"],
            ),
        ]

        for tool_data in builtin_tools:
            if isinstance(tool_data, ToolDefinition):
                tool = tool_data
            else:
                tool = ToolDefinition.from_dict(tool_data)
            self._tools[tool.tool_id] = tool

        ToolRegistry._BUILTIN_TOOLS_LOADED = True
        logger.info(f"Loaded {len(builtin_tools)} built-in tools")

    def _load_user_tools(self) -> None:
        """Load user-defined tools from ~/.pai/tools/"""
        import time

        # Rate-limit rescans
        now = time.time()
        if now - self._last_user_scan < self._user_scan_interval:
            return
        self._last_user_scan = now

        user_tools_dir = Path.home() / ".pai" / "tools"
        if not user_tools_dir.exists():
            return

        loaded_count = 0
        for yaml_file in user_tools_dir.glob("*.yaml"):
            try:
                tools = ToolDefinition.from_yaml_file(str(yaml_file))
                for tool in tools:
                    self._tools[tool.tool_id] = tool
                    loaded_count += 1
            except Exception as e:
                logger.warning(f"Failed to load tools from {yaml_file}: {e}")

        if loaded_count > 0:
            logger.info(f"Loaded {loaded_count} user tools from {user_tools_dir}")

    def register(self, tool: ToolDefinition, executor: Optional[Callable] = None) -> None:
        """
        Register a tool definition.

        Args:
            tool: The tool definition
            executor: Optional callable to execute the tool
        """
        self._tools[tool.tool_id] = tool
        if executor:
            self._executors[tool.tool_id] = executor
        logger.debug(f"Registered tool: {tool.tool_id}")

    def unregister(self, tool_id: str) -> None:
        """Remove a tool from the registry."""
        self._tools.pop(tool_id, None)
        self._executors.pop(tool_id, None)

    def get(self, tool_id: str) -> Optional[ToolDefinition]:
        """Get a tool definition by ID."""
        return self._tools.get(tool_id)

    def get_all(self) -> List[ToolDefinition]:
        """Get all registered tools."""
        return list(self._tools.values())

    def get_enabled(self) -> List[ToolDefinition]:
        """Get only enabled (non-deprecated) tools."""
        return [t for t in self._tools.values() if t.enabled and not t.deprecated]

    def get_by_category(self, category: ToolCategory) -> List[ToolDefinition]:
        """Get tools by category."""
        return [t for t in self._tools.values() if t.category == category]

    def get_by_tags(self, tags: List[str]) -> List[ToolDefinition]:
        """Get tools that have any of the specified tags."""
        tag_set = set(tags)
        return [t for t in self._tools.values() if tag_set & set(t.tags)]

    def get_for_role(self, role: str) -> List[ToolDefinition]:
        """
        Get tools suitable for an agent role.

        Role-based tool selection:
        - librarian: file tools
        - writer/editor: document tools
        - developer: code tools
        - researcher: search tools
        """
        role_lower = role.lower()

        if "librarian" in role_lower:
            return self.get_by_category(ToolCategory.FILE)
        elif "writer" in role_lower or "editor" in role_lower:
            # Document manipulation tools
            return [t for t in self._tools.values()
                    if t.category == ToolCategory.FILE and
                    any(tag in t.tags for tag in ["document", "edit", "write"])]
        elif "developer" in role_lower or "coder" in role_lower:
            return self.get_by_category(ToolCategory.CODE)
        elif "researcher" in role_lower:
            return self.get_by_category(ToolCategory.SEARCH)
        else:
            # Return commonly useful tools
            return self.get_enabled()

    def get_for_adapter(
        self,
        adapter_type: str,
        tool_ids: Optional[List[str]] = None,
        role: Optional[str] = None,
    ) -> List[Any]:
        """
        Get tools converted for a specific adapter.

        Args:
            adapter_type: "crewai", "openai", "anthropic", or "mcp"
            tool_ids: Optional list of specific tool IDs to include
            role: Optional agent role for role-based filtering

        Returns:
            List of tools in adapter-specific format
        """
        # Get adapter
        adapter = self._get_adapter(adapter_type)
        if not adapter:
            logger.warning(f"Unknown adapter type: {adapter_type}")
            return []

        # Determine which tools to include
        if tool_ids:
            tools = [self._tools[tid] for tid in tool_ids if tid in self._tools]
        elif role:
            tools = self.get_for_role(role)
        else:
            tools = self.get_enabled()

        # Convert using adapter
        converted = []
        for tool in tools:
            try:
                converted_tool = adapter.convert(tool)
                if converted_tool:
                    converted.append(converted_tool)
            except Exception as e:
                logger.warning(f"Failed to convert tool {tool.tool_id} for {adapter_type}: {e}")

        return converted

    def _get_adapter(self, adapter_type: str):
        """Get or create an adapter instance."""
        if adapter_type in self._adapters:
            return self._adapters[adapter_type]

        # Lazy load adapters
        adapter = None
        if adapter_type == "crewai":
            from app.tools.adapters.crewai_adapter import CrewAIAdapter
            adapter = CrewAIAdapter(self)
        elif adapter_type == "openai":
            # Future: OpenAI function calling adapter
            pass
        elif adapter_type == "anthropic":
            # Future: Anthropic tool_use adapter
            pass
        elif adapter_type == "mcp":
            # Future: Model Context Protocol adapter
            pass

        if adapter:
            self._adapters[adapter_type] = adapter

        return adapter

    def get_executor(self, tool_id: str) -> Optional[Callable]:
        """
        Get the executor for a tool.

        First checks registered executors, then loads from module path.
        """
        # Check registered executors
        if tool_id in self._executors:
            return self._executors[tool_id]

        # Load from tool definition
        tool = self.get(tool_id)
        if not tool:
            return None

        try:
            executor = self._load_executor(tool.executor)
            self._executors[tool_id] = executor
            return executor
        except Exception as e:
            logger.error(f"Failed to load executor for {tool_id}: {e}")
            return None

    def _load_executor(self, executor_path: str) -> Callable:
        """
        Load executor from module path.

        Format: "module.path:ClassName" or "module.path:function_name"
        """
        module_path, name = executor_path.rsplit(":", 1)
        module = importlib.import_module(module_path)
        return getattr(module, name)

    def execute(self, tool_id: str, **kwargs) -> ToolExecutionResult:
        """
        Execute a tool directly.

        Args:
            tool_id: The tool to execute
            **kwargs: Tool parameters

        Returns:
            ToolExecutionResult with output or error
        """
        import time

        start_time = time.time()

        tool = self.get(tool_id)
        if not tool:
            return ToolExecutionResult(
                success=False,
                output=None,
                error=f"Tool not found: {tool_id}",
            )

        executor = self.get_executor(tool_id)
        if not executor:
            return ToolExecutionResult(
                success=False,
                output=None,
                error=f"No executor found for tool: {tool_id}",
            )

        try:
            # Handle both class-based and function-based executors
            if isinstance(executor, type):
                # Class - instantiate and call _run
                instance = executor()
                if hasattr(instance, "_run"):
                    result = instance._run(**kwargs)
                else:
                    result = instance(**kwargs)
            else:
                # Function - call directly
                result = executor(**kwargs)

            return ToolExecutionResult(
                success=True,
                output=result,
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

        except Exception as e:
            return ToolExecutionResult(
                success=False,
                output=None,
                error=str(e),
                execution_time_ms=int((time.time() - start_time) * 1000),
            )

    def reload(self) -> None:
        """Reload all tools."""
        self._tools.clear()
        self._executors.clear()
        ToolRegistry._BUILTIN_TOOLS_LOADED = False
        self._last_user_scan = 0
        self._load_builtin_tools()
        self._load_user_tools()
        logger.info(f"Registry reloaded with {len(self._tools)} tools")

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics."""
        by_category = {}
        for tool in self._tools.values():
            cat = tool.category.value
            by_category[cat] = by_category.get(cat, 0) + 1

        return {
            "total_tools": len(self._tools),
            "enabled_tools": len(self.get_enabled()),
            "by_category": by_category,
            "adapters_loaded": list(self._adapters.keys()),
        }


# Module-level convenience functions
_registry: Optional[ToolRegistry] = None


def get_registry() -> ToolRegistry:
    """Get the singleton registry instance."""
    global _registry
    if _registry is None:
        _registry = ToolRegistry()
    return _registry


def get_tools_for_role(role: str) -> List[ToolDefinition]:
    """Get tools suitable for an agent role."""
    return get_registry().get_for_role(role)

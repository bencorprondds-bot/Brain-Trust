"""
Brain Trust Tool System

Provider-agnostic tool definitions with adapter-based translation.

Usage:
    from app.tools import get_registry, get_tools_for_role

    # Get all tools for the librarian role
    registry = get_registry()
    tools = registry.get_for_adapter("crewai", role="librarian")

    # Execute a tool directly
    result = registry.execute("drive_list", folder_id="root")
"""

from app.tools.registry import get_registry, get_tools_for_role, ToolRegistry
from app.tools.schema import (
    ToolDefinition,
    ToolParameter,
    ToolCategory,
    ParameterType,
    ToolExecutionResult,
)

__all__ = [
    "get_registry",
    "get_tools_for_role",
    "ToolRegistry",
    "ToolDefinition",
    "ToolParameter",
    "ToolCategory",
    "ParameterType",
    "ToolExecutionResult",
]

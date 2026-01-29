"""
CrewAI Adapter for Brain Trust Tool Registry

Converts provider-agnostic ToolDefinitions to CrewAI BaseTool instances.

This adapter handles:
- Dynamic schema generation from ToolParameter definitions
- Executor loading and wiring
- CrewAI-specific metadata mapping
"""

import logging
from typing import Any, Dict, List, Optional, Type, TYPE_CHECKING

from pydantic import BaseModel, Field, create_model
from crewai.tools import BaseTool

from app.tools.schema import ToolDefinition, ToolParameter, ParameterType

if TYPE_CHECKING:
    from app.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class CrewAIAdapter:
    """
    Converts ToolDefinitions to CrewAI BaseTool instances.

    Usage:
        adapter = CrewAIAdapter(registry)
        crewai_tool = adapter.convert(tool_definition)

        # Or get all tools for an agent
        tools = adapter.get_tools_for_role("librarian")
    """

    def __init__(self, registry: "ToolRegistry"):
        self._registry = registry
        self._converted_cache: Dict[str, BaseTool] = {}

    def convert(self, tool: ToolDefinition) -> Optional[BaseTool]:
        """
        Convert a ToolDefinition to a CrewAI BaseTool.

        Args:
            tool: The provider-agnostic tool definition

        Returns:
            A CrewAI BaseTool instance, or None if conversion fails
        """
        # Check cache first
        if tool.tool_id in self._converted_cache:
            return self._converted_cache[tool.tool_id]

        try:
            # Get the executor
            executor = self._registry.get_executor(tool.tool_id)
            if executor is None:
                logger.warning(f"No executor found for tool: {tool.tool_id}")
                return None

            # If executor is already a BaseTool class, just instantiate it
            if isinstance(executor, type) and issubclass(executor, BaseTool):
                instance = executor()
                self._converted_cache[tool.tool_id] = instance
                return instance

            # Otherwise, create a dynamic BaseTool wrapper
            crewai_tool = self._create_dynamic_tool(tool, executor)
            self._converted_cache[tool.tool_id] = crewai_tool
            return crewai_tool

        except Exception as e:
            logger.error(f"Failed to convert tool {tool.tool_id}: {e}")
            return None

    def _create_dynamic_tool(self, tool: ToolDefinition, executor: Any) -> BaseTool:
        """
        Create a dynamic BaseTool class for tools that aren't already BaseTool subclasses.

        This enables YAML-defined tools and function-based tools to work with CrewAI.
        """
        # Create the args schema dynamically from tool parameters
        args_schema = self._create_args_schema(tool)

        # Create the dynamic tool class
        class DynamicTool(BaseTool):
            name: str = tool.name
            description: str = tool.description
            args_schema: Type[BaseModel] = args_schema

            # Store executor reference
            _executor = executor
            _tool_def = tool

            def _run(self, **kwargs) -> str:
                """Execute the tool with the provided arguments."""
                try:
                    # Handle both callable and class-based executors
                    if isinstance(self._executor, type):
                        instance = self._executor()
                        if hasattr(instance, "_run"):
                            result = instance._run(**kwargs)
                        elif hasattr(instance, "__call__"):
                            result = instance(**kwargs)
                        else:
                            raise ValueError(f"Executor class has no _run or __call__ method")
                    else:
                        result = self._executor(**kwargs)

                    # Ensure string output for CrewAI
                    if isinstance(result, str):
                        return result
                    return str(result)

                except Exception as e:
                    return f"Error executing {self._tool_def.tool_id}: {str(e)}"

        # Set the class name for better debugging
        DynamicTool.__name__ = f"Dynamic{tool.tool_id.title().replace('_', '')}Tool"

        return DynamicTool()

    def _create_args_schema(self, tool: ToolDefinition) -> Type[BaseModel]:
        """
        Dynamically create a Pydantic model from tool parameters.

        This converts our ToolParameter list into a Pydantic BaseModel
        that CrewAI can use for argument validation.
        """
        if not tool.parameters:
            # No parameters - return empty schema
            return create_model(f"{tool.tool_id}_Args")

        # Build field definitions
        fields: Dict[str, Any] = {}

        for param in tool.parameters:
            python_type = self._get_python_type(param.type)

            if param.required:
                if param.default is not None:
                    fields[param.name] = (python_type, Field(default=param.default, description=param.description))
                else:
                    fields[param.name] = (python_type, Field(..., description=param.description))
            else:
                default = param.default if param.default is not None else None
                fields[param.name] = (Optional[python_type], Field(default=default, description=param.description))

        # Create the dynamic model
        model_name = f"{tool.tool_id.title().replace('_', '')}Args"
        return create_model(model_name, **fields)

    def _get_python_type(self, param_type: ParameterType) -> type:
        """Map ParameterType to Python type."""
        type_mapping = {
            ParameterType.STRING: str,
            ParameterType.INTEGER: int,
            ParameterType.NUMBER: float,
            ParameterType.BOOLEAN: bool,
            ParameterType.ARRAY: list,
            ParameterType.OBJECT: dict,
        }
        return type_mapping.get(param_type, str)

    def get_tools_for_role(self, role: str) -> List[BaseTool]:
        """
        Get all CrewAI tools suitable for an agent role.

        Args:
            role: Agent role (e.g., "librarian", "writer")

        Returns:
            List of CrewAI BaseTool instances
        """
        tool_defs = self._registry.get_for_role(role)
        tools = []

        for tool_def in tool_defs:
            converted = self.convert(tool_def)
            if converted:
                tools.append(converted)

        return tools

    def get_all_tools(self) -> List[BaseTool]:
        """Get all enabled tools as CrewAI BaseTool instances."""
        tool_defs = self._registry.get_enabled()
        tools = []

        for tool_def in tool_defs:
            converted = self.convert(tool_def)
            if converted:
                tools.append(converted)

        return tools

    def clear_cache(self) -> None:
        """Clear the converted tool cache."""
        self._converted_cache.clear()

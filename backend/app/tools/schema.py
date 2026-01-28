"""
Tool Definition Schema (Internal IDL) for Brain Trust

Provides a provider-agnostic format for defining tools that can be
translated to any model provider's schema (CrewAI, OpenAI, Anthropic, MCP).

Design Philosophy:
- Tools defined once, used everywhere
- YAML-first for easy editing
- Adapters handle provider-specific translation
- Runtime discovery of new tools without code changes

This is the "Internal Interface Definition Language" that decouples
tool definitions from framework-specific implementations.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
import json
import yaml


class ParameterType(str, Enum):
    """Supported parameter types for tool inputs."""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"

    def to_python_type(self) -> type:
        """Convert to Python type for dynamic class creation."""
        mapping = {
            ParameterType.STRING: str,
            ParameterType.INTEGER: int,
            ParameterType.NUMBER: float,
            ParameterType.BOOLEAN: bool,
            ParameterType.ARRAY: list,
            ParameterType.OBJECT: dict,
        }
        return mapping.get(self, str)


class ToolCategory(str, Enum):
    """Tool categories for organization and routing."""
    FILE = "file"           # File system operations
    SEARCH = "search"       # Search and discovery
    CODE = "code"           # Code execution
    API = "api"             # External API calls
    DATA = "data"           # Data processing
    COMMUNICATION = "communication"  # Email, messaging
    GENERAL = "general"     # Uncategorized


class ToolParameter(BaseModel):
    """
    Definition of a single tool parameter.

    Example YAML:
        - name: folder_id
          type: string
          description: "The ID of the Google Drive folder"
          required: true
          default: null
          enum: null
    """
    name: str = Field(..., description="Parameter name (snake_case)")
    type: ParameterType = Field(default=ParameterType.STRING)
    description: str = Field(default="", description="Human-readable description")
    required: bool = Field(default=True)
    default: Optional[Any] = Field(default=None)
    enum: Optional[List[str]] = Field(default=None, description="Allowed values")

    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON Schema format (for OpenAI/Anthropic)."""
        schema: Dict[str, Any] = {
            "type": self.type.value,
            "description": self.description,
        }
        if self.enum:
            schema["enum"] = self.enum
        if self.default is not None:
            schema["default"] = self.default
        return schema


class ToolDefinition(BaseModel):
    """
    Provider-agnostic tool definition.

    This is the core schema that all tools are defined in.
    Adapters translate this to provider-specific formats.

    Example YAML:
        tool_id: drive_list
        name: "Google Drive Lister"
        description: "Lists files and folders in a Google Drive folder"
        parameters:
          - name: folder_id
            type: string
            description: "The ID of the folder to list"
            required: true
        returns: string
        executor: "app.tools.drive_tool:DriveListTool"
        category: file
        requires_auth: true
        estimated_latency_ms: 2000
    """
    # Identity
    tool_id: str = Field(..., description="Unique identifier (snake_case)")
    name: str = Field(..., description="Human-readable name")
    description: str = Field(..., description="What this tool does")

    # Interface
    parameters: List[ToolParameter] = Field(default_factory=list)
    returns: ParameterType = Field(default=ParameterType.STRING)
    returns_description: str = Field(default="Tool output")

    # Implementation
    executor: str = Field(
        ...,
        description="Module path to implementation (module:class or module:function)"
    )

    # Metadata
    version: str = Field(default="1.0.0")
    category: ToolCategory = Field(default=ToolCategory.GENERAL)
    requires_auth: bool = Field(default=False)
    estimated_latency_ms: int = Field(default=1000)
    tags: List[str] = Field(default_factory=list)

    # Runtime
    enabled: bool = Field(default=True)
    deprecated: bool = Field(default=False)
    deprecation_message: str = Field(default="")

    def get_required_params(self) -> List[ToolParameter]:
        """Get list of required parameters."""
        return [p for p in self.parameters if p.required]

    def get_optional_params(self) -> List[ToolParameter]:
        """Get list of optional parameters."""
        return [p for p in self.parameters if not p.required]

    def to_json_schema(self) -> Dict[str, Any]:
        """
        Convert to JSON Schema format for function calling.

        Returns schema compatible with OpenAI/Anthropic function calling.
        """
        properties = {}
        required = []

        for param in self.parameters:
            properties[param.name] = param.to_json_schema()
            if param.required:
                required.append(param.name)

        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }

    def to_openai_function(self) -> Dict[str, Any]:
        """Convert to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.tool_id,
                "description": self.description,
                "parameters": self.to_json_schema(),
            }
        }

    def to_anthropic_tool(self) -> Dict[str, Any]:
        """Convert to Anthropic tool_use format."""
        return {
            "name": self.tool_id,
            "description": self.description,
            "input_schema": self.to_json_schema(),
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "tool_id": self.tool_id,
            "name": self.name,
            "description": self.description,
            "parameters": [
                {
                    "name": p.name,
                    "type": p.type.value,
                    "description": p.description,
                    "required": p.required,
                    "default": p.default,
                    "enum": p.enum,
                }
                for p in self.parameters
            ],
            "returns": self.returns.value,
            "returns_description": self.returns_description,
            "executor": self.executor,
            "version": self.version,
            "category": self.category.value,
            "requires_auth": self.requires_auth,
            "estimated_latency_ms": self.estimated_latency_ms,
            "tags": self.tags,
            "enabled": self.enabled,
            "deprecated": self.deprecated,
        }

    def to_yaml(self) -> str:
        """Convert to YAML string."""
        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ToolDefinition":
        """Create from dictionary."""
        # Convert parameters
        params = []
        for p in data.get("parameters", []):
            params.append(ToolParameter(
                name=p["name"],
                type=ParameterType(p.get("type", "string")),
                description=p.get("description", ""),
                required=p.get("required", True),
                default=p.get("default"),
                enum=p.get("enum"),
            ))

        return cls(
            tool_id=data["tool_id"],
            name=data["name"],
            description=data["description"],
            parameters=params,
            returns=ParameterType(data.get("returns", "string")),
            returns_description=data.get("returns_description", ""),
            executor=data["executor"],
            version=data.get("version", "1.0.0"),
            category=ToolCategory(data.get("category", "general")),
            requires_auth=data.get("requires_auth", False),
            estimated_latency_ms=data.get("estimated_latency_ms", 1000),
            tags=data.get("tags", []),
            enabled=data.get("enabled", True),
            deprecated=data.get("deprecated", False),
            deprecation_message=data.get("deprecation_message", ""),
        )

    @classmethod
    def from_yaml(cls, yaml_str: str) -> "ToolDefinition":
        """Create from YAML string."""
        data = yaml.safe_load(yaml_str)
        return cls.from_dict(data)

    @classmethod
    def from_yaml_file(cls, path: str) -> List["ToolDefinition"]:
        """Load tool definitions from a YAML file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # Handle both single tool and multiple tools
        if "tools" in data:
            return [cls.from_dict(t) for t in data["tools"]]
        else:
            return [cls.from_dict(data)]


@dataclass
class ToolExecutionResult:
    """Result of executing a tool."""
    success: bool
    output: Any
    error: Optional[str] = None
    execution_time_ms: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_string(self) -> str:
        """Convert output to string for LLM consumption."""
        if self.error:
            return f"Error: {self.error}"
        if isinstance(self.output, str):
            return self.output
        return json.dumps(self.output, indent=2, default=str)

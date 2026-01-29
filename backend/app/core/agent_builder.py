"""
Agent Builder for Brain Trust / Legion

Takes approved proposals from the Advisory Board and builds actual agents.
"""

import os
import uuid
import logging
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime

from .proposal_schema import AgentProposal, ProposalStatus
from .capability_registry import get_capability_registry, Capability, CapabilityCategory

logger = logging.getLogger(__name__)


class AgentBuilder:
    """
    Builds agents from approved Advisory Board proposals.

    Generates:
    - Agent configuration files (YAML)
    - Tool stubs (if needed)
    - Capability registry entries
    """

    def __init__(self, config_dir: Optional[Path] = None):
        """
        Initialize the agent builder.

        Args:
            config_dir: Directory for agent configurations
        """
        self.config_dir = config_dir or Path.home() / ".pai" / "agents"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.registry = get_capability_registry()

    def build(self, proposal: AgentProposal) -> Dict[str, Any]:
        """
        Build an agent from an approved proposal.

        Args:
            proposal: The approved agent proposal

        Returns:
            Dictionary with build results and file paths
        """
        if proposal.status != ProposalStatus.APPROVED:
            raise ValueError(f"Proposal must be approved. Current status: {proposal.status}")

        logger.info(f"Building agent from proposal: {proposal.role}")

        result = {
            "agent_id": str(uuid.uuid4())[:8],
            "role": proposal.role,
            "files_created": [],
            "capabilities_added": [],
            "tools_stubbed": [],
        }

        # 1. Generate agent configuration
        config_path = self._generate_agent_config(proposal, result["agent_id"])
        result["files_created"].append(str(config_path))

        # 2. Register capabilities
        for cap_name in proposal.capabilities:
            capability = self._register_capability(
                proposal,
                cap_name,
                result["agent_id"],
            )
            result["capabilities_added"].append(capability.id)

        # 3. Generate tool stubs if needed
        for tool in proposal.tools_needed:
            stub_path = self._generate_tool_stub(tool, result["agent_id"])
            if stub_path:
                result["tools_stubbed"].append(str(stub_path))
                result["files_created"].append(str(stub_path))

        # 4. Update proposal status
        proposal.status = ProposalStatus.IMPLEMENTED

        logger.info(f"Agent {proposal.role} built successfully: {result['agent_id']}")
        return result

    def _generate_agent_config(
        self,
        proposal: AgentProposal,
        agent_id: str,
    ) -> Path:
        """Generate YAML configuration file for the agent."""

        config = {
            "agent": {
                "id": agent_id,
                "role": proposal.role,
                "goal": proposal.goal,
                "backstory": proposal.backstory,
                "team": proposal.team,
                "created_from_proposal": proposal.id,
                "created_at": datetime.now().isoformat(),
            },
            "capabilities": proposal.capabilities,
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                }
                for tool in proposal.tools_needed
            ],
            "model_requirements": proposal.model_requirements,
            "success_criteria": proposal.success_criteria,
            "metadata": {
                "proposed_by": proposal.proposed_by,
                "proposal_confidence": proposal.proposal_confidence,
                "design_rationale": proposal.design_rationale,
            },
        }

        # Generate filename from role
        filename = f"{proposal.role.lower().replace(' ', '_')}_{agent_id}.yaml"
        config_path = self.config_dir / filename

        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        logger.info(f"Generated agent config: {config_path}")
        return config_path

    def _register_capability(
        self,
        proposal: AgentProposal,
        capability_name: str,
        agent_id: str,
    ) -> Capability:
        """Register a capability in the registry."""

        # Determine category from team
        category_map = {
            "Editorial": CapabilityCategory.EDITORIAL,
            "Technical": CapabilityCategory.TECHNICAL,
            "Production": CapabilityCategory.PRODUCTION,
            "Research": CapabilityCategory.RESEARCH,
        }
        category = category_map.get(proposal.team, CapabilityCategory.EDITORIAL)

        # Generate capability ID
        cap_id = f"{proposal.role.lower().replace(' ', '-')}-{capability_name.lower().replace(' ', '-')}"

        capability = Capability(
            id=cap_id,
            name=capability_name,
            description=f"Capability of {proposal.role}: {capability_name}",
            category=category,
            agent_role=proposal.role,
            team=proposal.team,
            required_tools=[t.name for t in proposal.tools_needed],
            success_rate=proposal.proposal_confidence,  # Start with proposal confidence
            avg_duration_seconds=60,  # Default estimate
        )

        self.registry.add_capability(capability)
        logger.info(f"Registered capability: {cap_id}")

        return capability

    def _generate_tool_stub(
        self,
        tool,
        agent_id: str,
    ) -> Optional[Path]:
        """Generate a stub implementation for a new tool."""

        tools_dir = self.config_dir.parent / "tools"
        tools_dir.mkdir(parents=True, exist_ok=True)

        # Generate tool class name
        class_name = "".join(word.title() for word in tool.name.split())
        filename = f"{tool.name.lower().replace(' ', '_')}_tool.py"

        # Generate parameter docs
        params_doc = ""
        if tool.parameters:
            params_doc = "\n    Parameters:\n"
            for param in tool.parameters:
                params_doc += f"        {param.get('name', 'param')}: {param.get('description', 'No description')}\n"

        stub_code = f'''"""
{tool.name} Tool

Auto-generated stub from Advisory Board proposal.
{tool.description}
{params_doc}
"""

from crewai_tools import BaseTool
from typing import Optional


class {class_name}(BaseTool):
    """
    {tool.description}

    This is a stub implementation. Fill in the _run method with actual logic.
    """

    name: str = "{tool.name}"
    description: str = "{tool.description}"

    def _run(self, **kwargs) -> str:
        """
        Execute the tool.

        TODO: Implement actual tool logic here.

        Args:
            **kwargs: Tool parameters

        Returns:
            Tool result as string
        """
        # Stub implementation - replace with actual logic
        return f"[STUB] {{self.name}} called with: {{kwargs}}"


# Register the tool for discovery
def get_tool() -> {class_name}:
    """Get an instance of this tool."""
    return {class_name}()
'''

        stub_path = tools_dir / filename

        # Don't overwrite existing files
        if stub_path.exists():
            logger.warning(f"Tool file already exists, skipping: {stub_path}")
            return None

        with open(stub_path, 'w') as f:
            f.write(stub_code)

        logger.info(f"Generated tool stub: {stub_path}")
        return stub_path

    def load_agent_config(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Load an agent configuration by ID."""

        for config_file in self.config_dir.glob(f"*_{agent_id}.yaml"):
            with open(config_file) as f:
                return yaml.safe_load(f)

        return None

    def list_built_agents(self) -> List[Dict[str, Any]]:
        """List all built agents."""
        agents = []

        for config_file in self.config_dir.glob("*.yaml"):
            try:
                with open(config_file) as f:
                    config = yaml.safe_load(f)
                    if config and "agent" in config:
                        agents.append({
                            "id": config["agent"]["id"],
                            "role": config["agent"]["role"],
                            "team": config["agent"].get("team", "Unknown"),
                            "file": str(config_file),
                        })
            except Exception as e:
                logger.warning(f"Failed to load {config_file}: {e}")

        return agents


def build_agent_from_proposal(proposal: AgentProposal) -> Dict[str, Any]:
    """Convenience function to build an agent from a proposal."""
    builder = AgentBuilder()
    return builder.build(proposal)

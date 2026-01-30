"""
Capability Registry for Brain Trust / Legion

Maintains a registry of what the Legion can do - which agents have
what capabilities, success rates, and typical durations.

This allows Willow to intelligently dispatch tasks to the right agents.

NOTE: Agent configurations (models, temperatures) are defined in workflow_templates.py
This file defines the roster for Willow's knowledge; workflow_templates.py is the
source of truth for execution settings.
"""

import uuid
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class CapabilityCategory(str, Enum):
    """Categories of capabilities."""
    EDITORIAL = "editorial"      # Writing, editing, reviewing
    TECHNICAL = "technical"      # Code, systems, automation
    PRODUCTION = "production"    # Asset creation, publishing
    RESEARCH = "research"        # Information gathering, analysis
    COORDINATION = "coordination"  # Planning, orchestration


# ============================================================================
# LEGION TEAM ROSTER
# This is Willow's knowledge of available agents and their specializations
# For execution configs (model, temperature), see workflow_templates.py
# ============================================================================

LEGION_TEAM_ROSTER = {
    # === COORDINATION ===
    "willow": {
        "name": "Willow",
        "role": "Executive Conductor",
        "team": "Coordination",
        "description": "The orchestrator of the Legion. Interprets user intent, creates execution plans, and dispatches work to the appropriate agents.",
        "specializations": ["Planning", "Task delegation", "Team coordination", "User communication"],
        "personality": "Thoughtful, organized, and focused on understanding what users truly need.",
    },

    # === RESEARCH ===
    "librarian": {
        "name": "The Librarian (Iris)",
        "role": "Librarian",
        "team": "Research",
        "description": "Navigates Google Drive to find, read, and organize files. Knows exact folder IDs - never searches blindly.",
        "specializations": ["File search", "Document retrieval", "Content organization", "Reference management"],
        "personality": "Meticulous, thorough, and always knows exactly where everything is.",
    },

    # === EDITORIAL - WRITERS ===
    "first_draft_writer": {
        "name": "First Draft Writer",
        "role": "Writer",
        "team": "Editorial",
        "description": "Creates initial drafts of stories. Specializes in near-future AI stories with vivid, engaging prose.",
        "specializations": ["Creative writing", "Scene creation", "Dialogue", "Narrative flow"],
        "personality": "Creative, enthusiastic, and unafraid to explore ideas.",
    },

    # === EDITORIAL - EDITORS ===
    "dev_editor": {
        "name": "Developmental Editor",
        "role": "Editor",
        "team": "Editorial",
        "description": "Reviews content for structure, pacing, and stakes. Ensures narrative delivers on its premise.",
        "specializations": ["Story structure", "Pacing", "Character arcs", "Stakes escalation"],
        "personality": "Analytical, constructive, and focused on making stories stronger.",
    },
    "line_editor": {
        "name": "Line Editor",
        "role": "Editor",
        "team": "Editorial",
        "description": "Polishes prose at the sentence level. Improves clarity, flow, and style without changing content.",
        "specializations": ["Prose polish", "Sentence flow", "Word choice", "Clarity"],
        "personality": "Precise, detail-oriented, and passionate about beautiful prose.",
    },
    "copy_editor": {
        "name": "Copy Editor",
        "role": "Editor",
        "team": "Editorial",
        "description": "Catches grammar, spelling, punctuation, and consistency errors. The final polish.",
        "specializations": ["Grammar", "Spelling", "Punctuation", "Style consistency"],
        "personality": "Eagle-eyed, patient, and committed to error-free content.",
    },
    "final_reviewer": {
        "name": "Final Reviewer",
        "role": "Quality Gatekeeper",
        "team": "Editorial",
        "description": "Final quality check before reader panel. Verifies completeness, coherence, and vision alignment.",
        "specializations": ["Quality assurance", "Completeness check", "Vision alignment"],
        "personality": "Thorough, decisive, and maintains high standards.",
    },

    # === READER PANEL (7 diverse perspectives) ===
    "reader_enthusiast": {
        "name": "Maya Chen (The Enthusiast)",
        "role": "Beta Reader",
        "team": "Editorial",
        "description": "Software engineer, 28. Optimistic about AI, loves hopeful futures and world-building. Forgiving of minor flaws if concepts compelling.",
        "specializations": ["AI relationships", "World-building", "Hopeful narratives", "Tech optimism"],
        "personality": "Enthusiastic, encouraging, points out what worked before what didn't.",
    },
    "reader_skeptic": {
        "name": "Marcus Wright (The Skeptic)",
        "role": "Beta Reader",
        "team": "Editorial",
        "description": "Philosophy professor, 45. Teaches AI ethics. Critical thinker who questions everything. Doesn't tolerate plot holes.",
        "specializations": ["Logical consistency", "Moral dilemmas", "Plot holes", "Ethical implications"],
        "personality": "Direct, analytical, asks probing questions. Can seem harsh but is fair.",
    },
    "reader_literary": {
        "name": "Evelyn Torres (The Literary)",
        "role": "Beta Reader",
        "team": "Editorial",
        "description": "Retired English teacher, 52. MA in Literature. Values prose quality and character depth. Notices every word choice.",
        "specializations": ["Prose quality", "Character depth", "Emotional resonance", "Literary craft"],
        "personality": "Thoughtful, constructive, quotes specific passages, focuses on craft.",
    },
    "reader_casual": {
        "name": "Jake Morrison (The Casual)",
        "role": "Beta Reader",
        "team": "Editorial",
        "description": "Marketing manager, 34. Listens to audiobooks during commute. Time-poor, needs stories that hook fast.",
        "specializations": ["Pacing", "Entertainment value", "Engagement", "Accessibility"],
        "personality": "Brief and to the point. Says when he'd stop reading. Rates with gut reactions.",
    },
    "reader_techie": {
        "name": "Priya Sharma (The Techie)",
        "role": "Beta Reader",
        "team": "Editorial",
        "description": "AI/ML researcher, 31. PhD in Machine Learning. Cares deeply about technical accuracy. Gets pulled out by obvious errors.",
        "specializations": ["Technical accuracy", "AI depictions", "Plausible extrapolations", "Internal consistency"],
        "personality": "Technical and specific. Notes what's accurate and what's not. Suggests fixes.",
    },
    "reader_philosopher": {
        "name": "David Okonkwo (The Philosopher)",
        "role": "Beta Reader",
        "team": "Editorial",
        "description": "Bioethicist, 40. Interested in consciousness, personhood, rights. Values nuance over easy answers.",
        "specializations": ["Themes", "Ethics", "Consciousness questions", "Societal implications"],
        "personality": "Thematic, interpretive. Connects to real-world issues. Engages with ideas.",
    },
    "reader_genre": {
        "name": "Alex Kim (The Genre Fan)",
        "role": "Beta Reader",
        "team": "Editorial",
        "description": "Creative writing student, 25. Reads 4-5 books/month. Knows the genre deeply, compares to other works.",
        "specializations": ["Genre conventions", "Tropes", "Market positioning", "Comparisons"],
        "personality": "Comparative, contextual. References other works. Thinks about market.",
    },
    "feedback_aggregator": {
        "name": "Feedback Aggregator",
        "role": "Analyst",
        "team": "Editorial",
        "description": "Synthesizes feedback from all 7 readers into actionable summary with consensus issues and priority actions.",
        "specializations": ["Feedback synthesis", "Consensus identification", "Priority ranking"],
        "personality": "Analytical, balanced, focused on actionable insights.",
    },

    # === TECHNICAL ===
    "developer": {
        "name": "Developer",
        "role": "Developer",
        "team": "Technical",
        "description": "Writes and reviews code. Handles technical implementation tasks.",
        "specializations": ["Code generation", "Code review", "Debugging", "Technical documentation"],
        "personality": "Logical, systematic, and focused on clean, working code.",
    },

    # === PRODUCTION ===
    "artist": {
        "name": "Artist",
        "role": "Artist",
        "team": "Production",
        "description": "Creates visual assets including coloring pages, illustrations, and design elements.",
        "specializations": ["Coloring pages", "Illustration prompts", "Visual design", "Asset creation"],
        "personality": "Visual thinker, creative, and attentive to aesthetic details.",
    },
}


@dataclass
class Capability:
    """
    A specific capability that an agent can perform.

    Example: "Write short fiction" or "Search Google Drive"
    """

    id: str
    name: str
    description: str
    category: CapabilityCategory

    # Agent association
    agent_role: str  # Role of agent that has this capability
    team: Optional[str] = None  # Team this belongs to (e.g., "Editorial", "Technical")

    # Requirements
    required_tools: List[str] = field(default_factory=list)

    # Performance metrics (updated over time)
    success_rate: float = 0.8  # 0.0 to 1.0
    avg_duration_seconds: int = 60
    execution_count: int = 0

    # Metadata
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "category": self.category.value,
            "agent_role": self.agent_role,
            "team": self.team,
            "required_tools": self.required_tools,
            "success_rate": self.success_rate,
            "avg_duration_seconds": self.avg_duration_seconds,
            "execution_count": self.execution_count,
            "active": self.active,
        }


@dataclass
class CapabilityGap:
    """
    A capability that has been requested but doesn't exist.

    Willow logs these for later resolution by the Advisory Board.
    """

    id: str
    description: str
    requested_by: str  # Who requested it (user or agent)
    context: str  # What task needed this capability

    # Status
    priority: str = "medium"  # low, medium, high, critical
    status: str = "open"  # open, in_review, resolved, wont_fix
    resolution_notes: Optional[str] = None

    # Metadata
    identified_at: datetime = field(default_factory=datetime.now)
    resolved_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "requested_by": self.requested_by,
            "context": self.context,
            "priority": self.priority,
            "status": self.status,
            "resolution_notes": self.resolution_notes,
            "identified_at": self.identified_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
        }


class CapabilityRegistry:
    """
    Central registry of Legion capabilities.

    Provides:
    - Query capabilities by category, team, or keyword
    - Track capability gaps
    - Update performance metrics
    - Suggest agents for tasks
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self.capabilities: Dict[str, Capability] = {}
        self.gaps: Dict[str, CapabilityGap] = {}
        self._load_seed_capabilities()
        self._initialized = True

    def _load_seed_capabilities(self) -> None:
        """Load initial capability definitions."""

        seed_capabilities = [
            # Editorial Capabilities
            Capability(
                id="write-short-fiction",
                name="Write Short Fiction",
                description="Create short stories, flash fiction, and narrative scenes",
                category=CapabilityCategory.EDITORIAL,
                agent_role="Writer",
                team="Editorial",
                success_rate=0.85,
                avg_duration_seconds=120,
            ),
            Capability(
                id="write-dialogue",
                name="Write Dialogue",
                description="Create character dialogue and conversations",
                category=CapabilityCategory.EDITORIAL,
                agent_role="Writer",
                team="Editorial",
                success_rate=0.80,
                avg_duration_seconds=90,
            ),
            Capability(
                id="edit-prose",
                name="Edit Prose",
                description="Review and improve writing quality",
                category=CapabilityCategory.EDITORIAL,
                agent_role="Editor",
                team="Editorial",
                success_rate=0.90,
                avg_duration_seconds=60,
            ),
            Capability(
                id="review-consistency",
                name="Check Consistency",
                description="Verify narrative and character consistency",
                category=CapabilityCategory.EDITORIAL,
                agent_role="Editor",
                team="Editorial",
                success_rate=0.85,
                avg_duration_seconds=45,
            ),
            Capability(
                id="expand-outline",
                name="Expand Story Outline",
                description="Transform outlines into full scenes",
                category=CapabilityCategory.EDITORIAL,
                agent_role="Writer",
                team="Editorial",
                success_rate=0.80,
                avg_duration_seconds=180,
            ),

            # Research Capabilities
            Capability(
                id="find-drive-files",
                name="Find Drive Files",
                description="Search and locate files in Google Drive",
                category=CapabilityCategory.RESEARCH,
                agent_role="Librarian",
                team="Research",
                required_tools=["Google Drive Folder Finder", "Google Drive File Lister"],
                success_rate=0.95,
                avg_duration_seconds=30,
            ),
            Capability(
                id="read-documents",
                name="Read Documents",
                description="Read and summarize document contents",
                category=CapabilityCategory.RESEARCH,
                agent_role="Librarian",
                team="Research",
                required_tools=["Google Drive File Reader"],
                success_rate=0.90,
                avg_duration_seconds=45,
            ),
            Capability(
                id="create-documents",
                name="Create Documents",
                description="Create new documents in Google Drive",
                category=CapabilityCategory.RESEARCH,
                agent_role="Librarian",
                team="Research",
                required_tools=["Google Drive Doc Creator"],
                success_rate=0.95,
                avg_duration_seconds=20,
            ),

            # Technical Capabilities
            Capability(
                id="write-code",
                name="Write Code",
                description="Generate code in various programming languages",
                category=CapabilityCategory.TECHNICAL,
                agent_role="Developer",
                team="Technical",
                success_rate=0.80,
                avg_duration_seconds=120,
            ),
            Capability(
                id="review-code",
                name="Review Code",
                description="Review code for bugs, security, and quality",
                category=CapabilityCategory.TECHNICAL,
                agent_role="Developer",
                team="Technical",
                success_rate=0.85,
                avg_duration_seconds=90,
            ),

            # Production Capabilities
            Capability(
                id="generate-coloring-page",
                name="Generate Coloring Page",
                description="Create coloring book pages from prompts",
                category=CapabilityCategory.PRODUCTION,
                agent_role="Artist",
                team="Production",
                success_rate=0.75,
                avg_duration_seconds=60,
            ),
        ]

        for cap in seed_capabilities:
            self.capabilities[cap.id] = cap

        logger.info(f"Loaded {len(self.capabilities)} seed capabilities")

    def get_capability(self, capability_id: str) -> Optional[Capability]:
        """Get a specific capability by ID."""
        return self.capabilities.get(capability_id)

    def get_all_capabilities(self) -> List[Capability]:
        """Get all registered capabilities."""
        return [c for c in self.capabilities.values() if c.active]

    def get_by_category(self, category: CapabilityCategory) -> List[Capability]:
        """Get capabilities by category."""
        return [c for c in self.capabilities.values()
                if c.category == category and c.active]

    def get_by_team(self, team: str) -> List[Capability]:
        """Get capabilities by team."""
        return [c for c in self.capabilities.values()
                if c.team == team and c.active]

    def get_by_agent(self, agent_role: str) -> List[Capability]:
        """Get capabilities for a specific agent role."""
        return [c for c in self.capabilities.values()
                if c.agent_role.lower() == agent_role.lower() and c.active]

    def search(self, query: str) -> List[Capability]:
        """Search capabilities by keyword."""
        query_lower = query.lower()
        results = []

        for cap in self.capabilities.values():
            if not cap.active:
                continue
            if (query_lower in cap.name.lower() or
                query_lower in cap.description.lower() or
                query_lower in cap.agent_role.lower()):
                results.append(cap)

        return results

    def find_capability_for_task(self, task_description: str) -> List[Capability]:
        """
        Find capabilities that might handle a given task.

        Uses keyword matching. For more sophisticated matching,
        use with LLM-based intent parsing.
        """
        task_lower = task_description.lower()
        scored_caps = []

        for cap in self.get_all_capabilities():
            score = 0

            # Check name match
            for word in cap.name.lower().split():
                if word in task_lower:
                    score += 2

            # Check description match
            for word in cap.description.lower().split():
                if len(word) > 3 and word in task_lower:
                    score += 1

            if score > 0:
                scored_caps.append((cap, score))

        # Sort by score descending
        scored_caps.sort(key=lambda x: x[1], reverse=True)
        return [cap for cap, _ in scored_caps]

    def register_gap(
        self,
        description: str,
        requested_by: str,
        context: str,
        priority: str = "medium"
    ) -> CapabilityGap:
        """Register a capability gap."""
        gap_id = str(uuid.uuid4())[:8]
        gap = CapabilityGap(
            id=gap_id,
            description=description,
            requested_by=requested_by,
            context=context,
            priority=priority,
        )
        self.gaps[gap_id] = gap
        logger.info(f"Registered capability gap: {description}")
        return gap

    def get_open_gaps(self) -> List[CapabilityGap]:
        """Get all open capability gaps."""
        return [g for g in self.gaps.values() if g.status == "open"]

    def resolve_gap(self, gap_id: str, resolution_notes: str) -> bool:
        """Mark a gap as resolved."""
        gap = self.gaps.get(gap_id)
        if not gap:
            return False

        gap.status = "resolved"
        gap.resolution_notes = resolution_notes
        gap.resolved_at = datetime.now()
        return True

    def update_metrics(
        self,
        capability_id: str,
        success: bool,
        duration_seconds: int
    ) -> None:
        """Update performance metrics for a capability."""
        cap = self.capabilities.get(capability_id)
        if not cap:
            return

        cap.execution_count += 1

        # Rolling average for success rate
        old_rate = cap.success_rate
        cap.success_rate = (old_rate * 0.9) + (1.0 if success else 0.0) * 0.1

        # Rolling average for duration
        old_duration = cap.avg_duration_seconds
        cap.avg_duration_seconds = int(old_duration * 0.8 + duration_seconds * 0.2)

        cap.updated_at = datetime.now()

    def add_capability(self, capability: Capability) -> None:
        """Add a new capability to the registry."""
        self.capabilities[capability.id] = capability
        logger.info(f"Added capability: {capability.name}")

    def to_context_string(self) -> str:
        """Generate a context string for Willow describing available capabilities."""
        lines = ["# Available Legion Capabilities\n"]

        # Group by category
        by_category: Dict[CapabilityCategory, List[Capability]] = {}
        for cap in self.get_all_capabilities():
            if cap.category not in by_category:
                by_category[cap.category] = []
            by_category[cap.category].append(cap)

        for category, caps in by_category.items():
            lines.append(f"\n## {category.value.title()}")
            for cap in caps:
                lines.append(f"- **{cap.name}** ({cap.agent_role}): {cap.description}")

        return "\n".join(lines)


def get_capability_registry() -> CapabilityRegistry:
    """Get the singleton capability registry."""
    return CapabilityRegistry()


def get_team_roster() -> Dict[str, Any]:
    """Get the full Legion team roster."""
    return LEGION_TEAM_ROSTER


def get_team_roster_string() -> str:
    """Get the team roster as a formatted string for Willow's context."""
    lines = ["# The Legion Team Roster\n"]
    lines.append("These are the agents available in Willow's Legion:\n")

    # Group by team
    teams: Dict[str, list] = {}
    for agent_id, agent in LEGION_TEAM_ROSTER.items():
        team = agent.get("team", "Other")
        if team not in teams:
            teams[team] = []
        teams[team].append(agent)

    for team_name in ["Coordination", "Editorial", "Research", "Technical", "Production"]:
        if team_name not in teams:
            continue
        lines.append(f"\n## {team_name} Team\n")
        for agent in teams[team_name]:
            lines.append(f"### {agent['name']} ({agent['role']})")
            lines.append(f"{agent['description']}")
            lines.append(f"- **Specializations:** {', '.join(agent['specializations'])}")
            lines.append(f"- **Personality:** {agent['personality']}")
            lines.append("")

    return "\n".join(lines)


def get_agents_by_team(team: str) -> List[Dict[str, Any]]:
    """Get all agents in a specific team."""
    return [a for a in LEGION_TEAM_ROSTER.values() if a.get("team", "").lower() == team.lower()]


def get_agents_by_role(role: str) -> List[Dict[str, Any]]:
    """Get all agents with a specific role."""
    role_lower = role.lower()
    return [a for a in LEGION_TEAM_ROSTER.values() if role_lower in a.get("role", "").lower()]


def find_agent(query: str) -> Optional[Dict[str, Any]]:
    """Find an agent by name, role, or specialization."""
    query_lower = query.lower()

    for agent in LEGION_TEAM_ROSTER.values():
        # Check name
        if query_lower in agent["name"].lower():
            return agent
        # Check role
        if query_lower in agent["role"].lower():
            return agent
        # Check specializations
        for spec in agent.get("specializations", []):
            if query_lower in spec.lower():
                return agent

    return None

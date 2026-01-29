"""
Intent Parser for Brain Trust / Legion

Parses abstract user intent into structured, actionable tasks.
Works with Willow to understand what the user truly wants.
"""

import os
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class IntentType(str, Enum):
    """Types of user intent."""
    CREATE = "create"          # Create something new
    EDIT = "edit"              # Modify existing content
    REVIEW = "review"          # Review/critique content
    FIND = "find"              # Search/locate something
    ORGANIZE = "organize"      # Organize/structure
    ANALYZE = "analyze"        # Analysis/research
    STATUS = "status"          # Check status of work
    APPROVE = "approve"        # Approve/reject work
    CONFIGURE = "configure"    # Change settings
    UNKNOWN = "unknown"


class ProjectScope(str, Enum):
    """Known project scopes."""
    LIFE_WITH_AI = "life_with_ai"
    COLORING_BOOK = "coloring_book"
    DIAMOND_AGE_PRIMER = "diamond_age_primer"
    IDLE_GAME = "idle_game"
    GENERAL = "general"


@dataclass
class Assumption:
    """
    An assumption made during intent parsing.

    Based on Karpathy insight: "Models make wrong assumptions and run with them without checking"
    """
    description: str
    confidence: float  # 0.0 - 1.0
    category: str  # "project", "scope", "artifact", "constraint", "interpretation"
    fallback: Optional[str] = None  # What to do if assumption is wrong


@dataclass
class ParsedIntent:
    """
    Structured representation of user intent.

    This is what Willow uses to plan and execute tasks.
    """

    # Core intent
    intent_type: IntentType
    summary: str  # One-line summary of what user wants

    # Target
    project: ProjectScope = ProjectScope.GENERAL
    target_artifact: Optional[str] = None  # e.g., "Chapter 3", "coloring page"

    # Requirements
    required_capabilities: List[str] = field(default_factory=list)
    suggested_agents: List[str] = field(default_factory=list)

    # Context
    context_needed: List[str] = field(default_factory=list)  # Files/docs to load
    constraints: List[str] = field(default_factory=list)  # e.g., "child-friendly"

    # Clarification
    needs_clarification: bool = False
    clarification_questions: List[str] = field(default_factory=list)

    # Confidence
    confidence: float = 1.0

    # Assumption tracking (Karpathy insight: surface assumptions explicitly)
    assumptions: List[Assumption] = field(default_factory=list)
    requires_assumption_confirmation: bool = False  # True if any assumption < 0.7 confidence

    def get_low_confidence_assumptions(self) -> List[Assumption]:
        """Return assumptions that need user confirmation."""
        return [a for a in self.assumptions if a.confidence < 0.7]

    def format_assumptions_for_user(self) -> str:
        """Format assumptions for display to user."""
        if not self.assumptions:
            return ""

        lines = ["I'm making the following assumptions:"]
        for a in self.assumptions:
            confidence_label = "High" if a.confidence >= 0.8 else "Medium" if a.confidence >= 0.5 else "Low"
            lines.append(f"  - [{confidence_label}] {a.description}")
            if a.fallback and a.confidence < 0.7:
                lines.append(f"    (If wrong: {a.fallback})")

        low_conf = self.get_low_confidence_assumptions()
        if low_conf:
            lines.append("")
            lines.append("Should I proceed, or would you like to clarify the items marked Low/Medium?")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_type": self.intent_type.value,
            "summary": self.summary,
            "project": self.project.value,
            "target_artifact": self.target_artifact,
            "required_capabilities": self.required_capabilities,
            "suggested_agents": self.suggested_agents,
            "context_needed": self.context_needed,
            "constraints": self.constraints,
            "needs_clarification": self.needs_clarification,
            "clarification_questions": self.clarification_questions,
            "confidence": self.confidence,
            "assumptions": [
                {
                    "description": a.description,
                    "confidence": a.confidence,
                    "category": a.category,
                    "fallback": a.fallback,
                }
                for a in self.assumptions
            ],
            "requires_assumption_confirmation": self.requires_assumption_confirmation,
        }


class IntentParser:
    """
    Parses user intent using both heuristics and LLM.

    The parser understands:
    - What the user wants to accomplish
    - Which project it relates to
    - What capabilities are needed
    - What context to gather
    """

    # Project detection patterns
    PROJECT_PATTERNS = {
        ProjectScope.LIFE_WITH_AI: [
            "life with ai", "maya", "pip", "story", "chapter",
            "life_with_ai", "lifewithai"
        ],
        ProjectScope.COLORING_BOOK: [
            "coloring", "colouring", "color page", "coloring book",
            "coloring_book"
        ],
        ProjectScope.DIAMOND_AGE_PRIMER: [
            "primer", "diamond age", "interactive", "educational"
        ],
        ProjectScope.IDLE_GAME: [
            "idle game", "game", "idle", "clicker"
        ],
    }

    # Intent detection patterns
    INTENT_PATTERNS = {
        IntentType.CREATE: [
            "write", "create", "generate", "make", "draft",
            "compose", "produce", "build"
        ],
        IntentType.EDIT: [
            "edit", "revise", "update", "modify", "change",
            "rewrite", "improve", "fix"
        ],
        IntentType.REVIEW: [
            "review", "check", "critique", "feedback", "evaluate",
            "assess", "analyze content"
        ],
        IntentType.FIND: [
            "find", "search", "locate", "where is", "look for",
            "get me", "fetch"
        ],
        IntentType.ORGANIZE: [
            "organize", "sort", "arrange", "structure", "categorize",
            "move", "file"
        ],
        IntentType.ANALYZE: [
            "analyze", "research", "investigate", "study",
            "understand", "explain"
        ],
        IntentType.STATUS: [
            "status", "progress", "what's happening", "where are we",
            "update me", "how is"
        ],
        IntentType.APPROVE: [
            "approve", "accept", "reject", "sign off", "looks good",
            "ship it", "publish"
        ],
        IntentType.CONFIGURE: [
            "configure", "setup", "settings", "preferences", "change config"
        ],
    }

    # Agent suggestions based on intent
    INTENT_TO_AGENTS = {
        IntentType.CREATE: ["Writer"],
        IntentType.EDIT: ["Editor", "Writer"],
        IntentType.REVIEW: ["Editor"],
        IntentType.FIND: ["Librarian"],
        IntentType.ORGANIZE: ["Librarian"],
        IntentType.ANALYZE: ["Researcher", "Editor"],
        IntentType.STATUS: [],
        IntentType.APPROVE: [],
        IntentType.CONFIGURE: [],
    }

    def __init__(self, use_llm: bool = True, parser_model: str = "gemini-2.0-flash"):
        """
        Initialize the intent parser.

        Args:
            use_llm: Use LLM for more accurate parsing
            parser_model: Model to use for LLM parsing
        """
        self.use_llm = use_llm
        self.parser_model = parser_model

    def parse(self, user_input: str, conversation_context: Optional[str] = None) -> ParsedIntent:
        """
        Parse user input into structured intent.

        Args:
            user_input: Raw user input text
            conversation_context: Previous conversation for context

        Returns:
            ParsedIntent with structured understanding
        """
        # Try LLM parsing first if enabled
        if self.use_llm:
            try:
                intent = self._parse_with_llm(user_input, conversation_context)
                if intent and intent.confidence > 0.6:
                    return intent
            except Exception as e:
                logger.warning(f"LLM parsing failed: {e}")

        # Fallback to heuristic parsing
        return self._parse_with_heuristics(user_input)

    def _parse_with_heuristics(self, user_input: str) -> ParsedIntent:
        """Parse using keyword matching."""
        input_lower = user_input.lower()

        # Detect intent type
        intent_type = IntentType.UNKNOWN
        for itype, patterns in self.INTENT_PATTERNS.items():
            for pattern in patterns:
                if pattern in input_lower:
                    intent_type = itype
                    break
            if intent_type != IntentType.UNKNOWN:
                break

        # Detect project
        project = ProjectScope.GENERAL
        for proj, patterns in self.PROJECT_PATTERNS.items():
            for pattern in patterns:
                if pattern in input_lower:
                    project = proj
                    break
            if project != ProjectScope.GENERAL:
                break

        # Get suggested agents
        suggested_agents = self.INTENT_TO_AGENTS.get(intent_type, [])

        # Detect constraints
        constraints = []
        if "child" in input_lower or "kid" in input_lower:
            constraints.append("child-friendly")
        if "short" in input_lower:
            constraints.append("concise")
        if "detailed" in input_lower:
            constraints.append("detailed")

        return ParsedIntent(
            intent_type=intent_type,
            summary=f"{intent_type.value.title()}: {user_input[:50]}...",
            project=project,
            suggested_agents=suggested_agents,
            constraints=constraints,
            confidence=0.6,  # Heuristic confidence is lower
        )

    def _parse_with_llm(
        self,
        user_input: str,
        conversation_context: Optional[str]
    ) -> Optional[ParsedIntent]:
        """Parse using LLM for better understanding."""
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI

            llm = ChatGoogleGenerativeAI(
                model=self.parser_model,
                google_api_key=os.getenv("GEMINI_API_KEY"),
                temperature=0.0,
            )

            context_section = ""
            if conversation_context:
                context_section = f"\n\nPrevious conversation:\n{conversation_context}\n"

            prompt = f"""Parse this user request into structured intent.
{context_section}
User request: "{user_input}"

Known projects: life_with_ai, coloring_book, diamond_age_primer, idle_game, general

IMPORTANT: Explicitly track assumptions you are making about the user's intent.
Do NOT silently assume - surface any uncertainty.

Respond with JSON only:
{{
    "intent_type": "create|edit|review|find|organize|analyze|status|approve|configure|unknown",
    "summary": "<one line summary of what user wants>",
    "project": "<project name or 'general'>",
    "target_artifact": "<specific thing being worked on, or null>",
    "required_capabilities": ["<capability1>", "<capability2>"],
    "suggested_agents": ["<agent role 1>", "<agent role 2>"],
    "constraints": ["<constraint1>"],
    "needs_clarification": true|false,
    "clarification_questions": ["<question if clarification needed>"],
    "confidence": <0.0-1.0>,
    "assumptions": [
        {{
            "description": "<what you are assuming>",
            "confidence": <0.0-1.0>,
            "category": "project|scope|artifact|constraint|interpretation",
            "fallback": "<what to do if this assumption is wrong>"
        }}
    ]
}}

Rules for assumptions:
- If the project isn't explicitly stated, that's an assumption
- If you're interpreting ambiguous words (e.g., "fix" could mean edit or debug), that's an assumption
- If you're guessing the scope (whole file vs specific section), that's an assumption
- Lower confidence = user should confirm before proceeding

Output only valid JSON."""

            response = llm.invoke(prompt)
            content = response.content.strip()

            # Clean up response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            data = json.loads(content.strip())

            # Map to enums
            intent_type = IntentType(data.get("intent_type", "unknown"))
            project = ProjectScope.GENERAL
            try:
                project = ProjectScope(data.get("project", "general"))
            except ValueError:
                pass

            # Parse assumptions
            assumptions = []
            for a_data in data.get("assumptions", []):
                assumptions.append(Assumption(
                    description=a_data.get("description", ""),
                    confidence=float(a_data.get("confidence", 0.5)),
                    category=a_data.get("category", "interpretation"),
                    fallback=a_data.get("fallback"),
                ))

            # Check if we need assumption confirmation
            requires_confirmation = any(a.confidence < 0.7 for a in assumptions)

            return ParsedIntent(
                intent_type=intent_type,
                summary=data.get("summary", user_input[:50]),
                project=project,
                target_artifact=data.get("target_artifact"),
                required_capabilities=data.get("required_capabilities", []),
                suggested_agents=data.get("suggested_agents", []),
                constraints=data.get("constraints", []),
                needs_clarification=data.get("needs_clarification", False),
                clarification_questions=data.get("clarification_questions", []),
                confidence=float(data.get("confidence", 0.8)),
                assumptions=assumptions,
                requires_assumption_confirmation=requires_confirmation,
            )

        except Exception as e:
            logger.error(f"LLM intent parsing failed: {e}")
            return None


def parse_intent(user_input: str, use_llm: bool = True) -> ParsedIntent:
    """Convenience function to parse intent."""
    parser = IntentParser(use_llm=use_llm)
    return parser.parse(user_input)

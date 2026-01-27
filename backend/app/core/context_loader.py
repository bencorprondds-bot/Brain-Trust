"""
TELOS Context Loader
Reads Markdown files from ~/.pai/context/ and injects them into agent prompts.
"""

import os
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass
import hashlib
import time


@dataclass
class TelosContext:
    """Immutable snapshot of user context."""
    mission: str
    goals: str
    beliefs: str
    identity: str
    loaded_at: float
    checksum: str  # For cache invalidation


class ContextLoader:
    """
    Singleton that loads TELOS context from ~/.pai/context/
    
    This is a PERSONAL tool. Each person who clones this project
    will have their own ~/.pai/ directory with their own context.
    
    OPTIMIZATION: In-memory cache with 60s TTL to avoid repeated file I/O.
    """
    
    _instance = None
    _cache: Optional[TelosContext] = None
    _cache_ttl: int = 60  # seconds
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ContextLoader, cls).__new__(cls)
        return cls._instance
    
    def load_context(self) -> TelosContext:
        """
        Load TELOS context from ~/.pai/context/
        
        This is a single-user system. Each person who clones this
        project will have their own ~/.pai/ directory.
        
        Returns:
            TelosContext object with mission, goals, beliefs
        
        Raises:
            FileNotFoundError: If TELOS files are missing
            PermissionError: If files are not readable
        """
        # Check cache
        if self._cache and (time.time() - self._cache.loaded_at) < self._cache_ttl:
            current_checksum = self._compute_checksum()
            if current_checksum == self._cache.checksum:
                return self._cache
        
        # Load from filesystem (single-user)
        base_path = Path.home() / ".pai" / "context"
        
        try:
            mission = self._read_file(base_path / "MISSION.md")
            goals = self._read_file(base_path / "GOALS.md")
            beliefs = self._read_file(base_path / "BELIEFS.md")
            identity = self._read_file(base_path / "IDENTITY.md", default="Personal AI Assistant")
            
            context = TelosContext(
                mission=mission,
                goals=goals,
                beliefs=beliefs,
                identity=identity,
                loaded_at=time.time(),
                checksum=self._compute_checksum()
            )
            
            self._cache = context
            return context
            
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"TELOS context not found. "
                f"Expected files in: {base_path}\n"
                f"Run: mkdir -p {base_path} and create MISSION.md, GOALS.md, BELIEFS.md\n"
                f"Missing: {e.filename}"
            )
    
    def _read_file(self, path: Path, default: Optional[str] = None) -> str:
        """Read file with fallback."""
        if not path.exists():
            if default is not None:
                return default
            raise FileNotFoundError(f"Required file not found: {path}")
        
        with open(path, 'r', encoding='utf-8') as f:
            return f.read().strip()
    
    def _compute_checksum(self) -> str:
        """Compute MD5 of all TELOS files for cache invalidation."""
        base_path = Path.home() / ".pai" / "context"
        files = ["MISSION.md", "GOALS.md", "BELIEFS.md", "IDENTITY.md"]
        
        hasher = hashlib.md5()
        for filename in files:
            filepath = base_path / filename
            if filepath.exists():
                hasher.update(filepath.read_bytes())
        
        return hasher.hexdigest()
    
    def inject_into_prompt(self, base_prompt: str, context: TelosContext) -> str:
        """
        Inject TELOS context into agent system prompt.
        
        CRITICAL FLAW #3: Prompt injection vulnerability.
        If MISSION.md contains malicious instructions, they execute.
        MITIGATION: Sanitize/validate Markdown content (not implemented here).
        """
        telos_header = f"""
# USER CONTEXT (TELOS LAYER)

## Mission
{context.mission}

## Core Beliefs & Constraints
{context.beliefs}

## Current Goals
{context.goals}

## Identity
You are assisting: {context.identity}

---

# AGENT INSTRUCTIONS
{base_prompt}
"""
        return telos_header.strip()
    
    def invalidate_cache(self):
        """Force reload on next access."""
        self._cache = None


class AgentPromptLoader:
    """
    Loads agent-specific prompts from backend/prompts/ directory.

    Agent prompts define personality, capabilities, and behavioral guidelines
    for specific agent roles (e.g., Librarian, Editor, Writer).
    """

    _prompts_cache: Dict[str, str] = {}

    @classmethod
    def get_prompts_dir(cls) -> Path:
        """Get the prompts directory path."""
        # Navigate from context_loader.py to backend/prompts/
        return Path(__file__).parent.parent.parent / "prompts"

    @classmethod
    def load_prompt(cls, role: str) -> Optional[str]:
        """
        Load an agent prompt by role name.

        Args:
            role: The agent role (e.g., 'librarian', 'editor')

        Returns:
            The prompt content, or None if not found
        """
        role_lower = role.lower().strip()

        # Check cache
        if role_lower in cls._prompts_cache:
            return cls._prompts_cache[role_lower]

        prompts_dir = cls.get_prompts_dir()
        prompt_file = prompts_dir / f"{role_lower}.md"

        if prompt_file.exists():
            content = prompt_file.read_text(encoding='utf-8').strip()
            cls._prompts_cache[role_lower] = content
            return content

        return None

    @classmethod
    def invalidate_cache(cls):
        """Clear the prompts cache."""
        cls._prompts_cache = {}

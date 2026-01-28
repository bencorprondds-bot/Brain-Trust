"""
State Manager for Brain Trust

Manages persistence and retrieval of agent state.

Storage Backends:
- SQLite (default): Local file storage at ~/.pai/state.db
- Supabase (optional): Cloud persistence for multi-device sync
- Redis (optional): High-performance caching layer

Usage:
    manager = StateManager()

    # Save state
    await manager.save(state)

    # Load state
    state = await manager.load("agent-123")

    # Get execution history
    history = await manager.get_history("agent-123", limit=10)
"""

import asyncio
import json
import logging
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.state.schema import AgentState

logger = logging.getLogger(__name__)


class StateManager:
    """
    Manages agent state persistence and retrieval.

    The state manager provides:
    - Atomic save/load operations
    - Version history for rollback
    - Query by workflow, agent, or time range
    - Automatic cleanup of old states
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        max_history: int = 100,
    ):
        """
        Initialize the state manager.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.pai/state.db
            max_history: Maximum state versions to keep per agent
        """
        if db_path is None:
            pai_dir = Path.home() / ".pai"
            pai_dir.mkdir(exist_ok=True)
            db_path = str(pai_dir / "state.db")

        self.db_path = db_path
        self.max_history = max_history
        self._initialized = False

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with proper settings."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")  # Better concurrency
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _ensure_initialized(self) -> None:
        """Ensure database tables exist."""
        if self._initialized:
            return

        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS agent_states (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id TEXT NOT NULL,
                    workflow_id TEXT NOT NULL,
                    state_hash TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    success INTEGER DEFAULT 0,
                    tokens_used INTEGER DEFAULT 0,
                    cost_usd REAL DEFAULT 0.0
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_states_agent_id
                ON agent_states(agent_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_states_workflow_id
                ON agent_states(workflow_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_agent_states_updated_at
                ON agent_states(updated_at)
            """)
            conn.commit()

        self._initialized = True
        logger.info(f"State database initialized at {self.db_path}")

    async def save(self, state: AgentState) -> int:
        """
        Persist agent state.

        Args:
            state: The agent state to save

        Returns:
            The database row ID
        """
        self._ensure_initialized()

        # Update timestamp
        state.updated_at = datetime.utcnow()

        def _save_sync():
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    INSERT INTO agent_states (
                        agent_id, workflow_id, state_hash, state_json,
                        created_at, updated_at, success, tokens_used, cost_usd
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    state.agent_id,
                    state.workflow_id,
                    state.state_hash(),
                    state.to_json(),
                    state.created_at.isoformat(),
                    state.updated_at.isoformat(),
                    1 if state.success else 0,
                    state.total_tokens_used,
                    state.total_cost_usd,
                ))
                conn.commit()

                # Cleanup old states if needed
                self._cleanup_old_states(conn, state.agent_id)

                return cursor.lastrowid

        # Run sync operation in thread pool
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _save_sync)

    def _cleanup_old_states(self, conn: sqlite3.Connection, agent_id: str) -> None:
        """Remove old state versions beyond max_history."""
        conn.execute("""
            DELETE FROM agent_states
            WHERE agent_id = ?
            AND id NOT IN (
                SELECT id FROM agent_states
                WHERE agent_id = ?
                ORDER BY updated_at DESC
                LIMIT ?
            )
        """, (agent_id, agent_id, self.max_history))
        conn.commit()

    async def load(self, agent_id: str) -> Optional[AgentState]:
        """
        Load the most recent state for an agent.

        Args:
            agent_id: The agent identifier

        Returns:
            AgentState or None if not found
        """
        self._ensure_initialized()

        def _load_sync():
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT state_json FROM agent_states
                    WHERE agent_id = ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                """, (agent_id,))
                row = cursor.fetchone()
                if row:
                    return AgentState.from_json(row["state_json"])
                return None

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _load_sync)

    async def load_by_workflow(self, workflow_id: str) -> List[AgentState]:
        """
        Load all agent states for a workflow.

        Args:
            workflow_id: The workflow identifier

        Returns:
            List of AgentState objects
        """
        self._ensure_initialized()

        def _load_sync():
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT DISTINCT agent_id, state_json FROM agent_states
                    WHERE workflow_id = ?
                    AND id IN (
                        SELECT MAX(id) FROM agent_states
                        WHERE workflow_id = ?
                        GROUP BY agent_id
                    )
                    ORDER BY updated_at DESC
                """, (workflow_id, workflow_id))
                return [AgentState.from_json(row["state_json"]) for row in cursor.fetchall()]

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _load_sync)

    async def get_history(
        self,
        agent_id: str,
        limit: int = 10,
        offset: int = 0,
    ) -> List[AgentState]:
        """
        Get historical states for an agent.

        Args:
            agent_id: The agent identifier
            limit: Maximum number of states to return
            offset: Number of states to skip

        Returns:
            List of AgentState objects, newest first
        """
        self._ensure_initialized()

        def _get_history_sync():
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT state_json FROM agent_states
                    WHERE agent_id = ?
                    ORDER BY updated_at DESC
                    LIMIT ? OFFSET ?
                """, (agent_id, limit, offset))
                return [AgentState.from_json(row["state_json"]) for row in cursor.fetchall()]

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _get_history_sync)

    async def get_successful_executions(
        self,
        agent_id: Optional[str] = None,
        role: Optional[str] = None,
        limit: int = 50,
    ) -> List[AgentState]:
        """
        Get successful execution states for learning.

        Args:
            agent_id: Filter by specific agent (optional)
            role: Filter by agent role (optional)
            limit: Maximum results

        Returns:
            List of successful AgentState objects
        """
        self._ensure_initialized()

        def _get_successful_sync():
            with self._get_connection() as conn:
                query = """
                    SELECT state_json FROM agent_states
                    WHERE success = 1
                """
                params = []

                if agent_id:
                    query += " AND agent_id = ?"
                    params.append(agent_id)

                query += " ORDER BY updated_at DESC LIMIT ?"
                params.append(limit)

                cursor = conn.execute(query, params)
                states = [AgentState.from_json(row["state_json"]) for row in cursor.fetchall()]

                # Filter by role in Python (role is in JSON)
                if role:
                    states = [s for s in states if role.lower() in s.role.lower()]

                return states

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _get_successful_sync)

    async def delete(self, agent_id: str) -> int:
        """
        Delete all states for an agent.

        Args:
            agent_id: The agent identifier

        Returns:
            Number of rows deleted
        """
        self._ensure_initialized()

        def _delete_sync():
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    DELETE FROM agent_states WHERE agent_id = ?
                """, (agent_id,))
                conn.commit()
                return cursor.rowcount

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _delete_sync)

    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about stored states."""
        self._ensure_initialized()

        def _get_stats_sync():
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT
                        COUNT(*) as total_states,
                        COUNT(DISTINCT agent_id) as unique_agents,
                        COUNT(DISTINCT workflow_id) as unique_workflows,
                        SUM(tokens_used) as total_tokens,
                        SUM(cost_usd) as total_cost,
                        SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                        MIN(created_at) as oldest_state,
                        MAX(updated_at) as newest_state
                    FROM agent_states
                """)
                row = cursor.fetchone()
                return {
                    "total_states": row["total_states"],
                    "unique_agents": row["unique_agents"],
                    "unique_workflows": row["unique_workflows"],
                    "total_tokens": row["total_tokens"] or 0,
                    "total_cost_usd": row["total_cost"] or 0.0,
                    "successful_executions": row["successful"],
                    "success_rate": (row["successful"] / row["total_states"] * 100) if row["total_states"] > 0 else 0,
                    "oldest_state": row["oldest_state"],
                    "newest_state": row["newest_state"],
                }

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _get_stats_sync)


# Singleton instance
_manager: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    """Get the singleton state manager instance."""
    global _manager
    if _manager is None:
        _manager = StateManager()
    return _manager

"""
Long-Term Memory for Brain Trust

Vector-based semantic memory that persists across sessions.

Enables agents to:
1. Remember past successful patterns
2. Recall relevant experiences for current tasks
3. Learn from mistakes
4. Build domain expertise over time

The memory system is designed to be lightweight initially,
with the ability to upgrade to more sophisticated vector stores
(ChromaDB, Pinecone, Qdrant) as needed.
"""

import asyncio
import hashlib
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.state.schema import AgentState

logger = logging.getLogger(__name__)


class MemoryEntry:
    """A single memory entry."""

    def __init__(
        self,
        content: str,
        agent_id: str,
        memory_type: str = "experience",
        metadata: Optional[Dict[str, Any]] = None,
        embedding: Optional[List[float]] = None,
    ):
        self.id = hashlib.sha256(
            f"{agent_id}:{content}:{datetime.utcnow().isoformat()}".encode()
        ).hexdigest()[:16]
        self.content = content
        self.agent_id = agent_id
        self.memory_type = memory_type  # "experience", "learning", "error", "success"
        self.metadata = metadata or {}
        self.embedding = embedding
        self.created_at = datetime.utcnow()
        self.access_count = 0
        self.last_accessed = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "agent_id": self.agent_id,
            "memory_type": self.memory_type,
            "metadata": self.metadata,
            "embedding": self.embedding,
            "created_at": self.created_at.isoformat(),
            "access_count": self.access_count,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MemoryEntry":
        entry = cls(
            content=data["content"],
            agent_id=data["agent_id"],
            memory_type=data.get("memory_type", "experience"),
            metadata=data.get("metadata", {}),
            embedding=data.get("embedding"),
        )
        entry.id = data["id"]
        entry.created_at = datetime.fromisoformat(data["created_at"])
        entry.access_count = data.get("access_count", 0)
        if data.get("last_accessed"):
            entry.last_accessed = datetime.fromisoformat(data["last_accessed"])
        return entry


class LongTermMemory:
    """
    Vector-based long-term memory for semantic retrieval.

    Uses a simple file-based approach initially, with optional
    upgrade path to more sophisticated vector stores.

    Storage:
    - SQLite for metadata and content
    - Embeddings stored as JSON (upgrade to FAISS/ChromaDB for scale)

    Retrieval:
    - Keyword matching (simple, fast)
    - Cosine similarity on embeddings (when available)
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        use_embeddings: bool = False,
        embedding_model: str = "text-embedding-3-small",
    ):
        """
        Initialize long-term memory.

        Args:
            db_path: Path to SQLite database. Defaults to ~/.pai/memory.db
            use_embeddings: Whether to generate and use embeddings
            embedding_model: Model for generating embeddings
        """
        if db_path is None:
            pai_dir = Path.home() / ".pai"
            pai_dir.mkdir(exist_ok=True)
            db_path = str(pai_dir / "memory.db")

        self.db_path = db_path
        self.use_embeddings = use_embeddings
        self.embedding_model = embedding_model
        self._initialized = False

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_initialized(self) -> None:
        """Ensure database tables exist."""
        if self._initialized:
            return

        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    agent_id TEXT NOT NULL,
                    content TEXT NOT NULL,
                    memory_type TEXT NOT NULL,
                    metadata_json TEXT,
                    embedding_json TEXT,
                    created_at TEXT NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_agent_id
                ON memories(agent_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_memories_type
                ON memories(memory_type)
            """)
            conn.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts
                USING fts5(content, agent_id, memory_type)
            """)
            conn.commit()

        self._initialized = True
        logger.info(f"Memory database initialized at {self.db_path}")

    async def remember(
        self,
        agent_id: str,
        content: str,
        memory_type: str = "experience",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store a memory.

        Args:
            agent_id: The agent this memory belongs to
            content: The memory content
            memory_type: Type of memory (experience, learning, error, success)
            metadata: Additional metadata

        Returns:
            Memory ID
        """
        self._ensure_initialized()

        entry = MemoryEntry(
            content=content,
            agent_id=agent_id,
            memory_type=memory_type,
            metadata=metadata,
        )

        # Generate embedding if enabled
        if self.use_embeddings:
            entry.embedding = await self._generate_embedding(content)

        def _store_sync():
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO memories
                    (id, agent_id, content, memory_type, metadata_json, embedding_json, created_at, access_count)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.id,
                    entry.agent_id,
                    entry.content,
                    entry.memory_type,
                    json.dumps(entry.metadata),
                    json.dumps(entry.embedding) if entry.embedding else None,
                    entry.created_at.isoformat(),
                    0,
                ))

                # Update FTS index
                conn.execute("""
                    INSERT OR REPLACE INTO memories_fts (rowid, content, agent_id, memory_type)
                    SELECT rowid, content, agent_id, memory_type
                    FROM memories WHERE id = ?
                """, (entry.id,))

                conn.commit()
                return entry.id

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _store_sync)

    async def recall(
        self,
        query: str,
        agent_id: Optional[str] = None,
        memory_type: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant memories.

        Args:
            query: Search query
            agent_id: Filter by agent (optional)
            memory_type: Filter by type (optional)
            limit: Maximum results

        Returns:
            List of memory entries with relevance scores
        """
        self._ensure_initialized()

        def _recall_sync():
            with self._get_connection() as conn:
                # Use FTS for keyword search
                fts_query = query.replace('"', '""')  # Escape quotes

                # Build WHERE clause
                conditions = []
                params = []

                if agent_id:
                    conditions.append("m.agent_id = ?")
                    params.append(agent_id)

                if memory_type:
                    conditions.append("m.memory_type = ?")
                    params.append(memory_type)

                where_clause = " AND ".join(conditions) if conditions else "1=1"

                # FTS search with ranking
                cursor = conn.execute(f"""
                    SELECT
                        m.id, m.content, m.agent_id, m.memory_type,
                        m.metadata_json, m.created_at, m.access_count,
                        bm25(memories_fts) as score
                    FROM memories_fts
                    JOIN memories m ON memories_fts.rowid = m.rowid
                    WHERE memories_fts MATCH ?
                    AND {where_clause}
                    ORDER BY score
                    LIMIT ?
                """, [fts_query] + params + [limit])

                results = []
                for row in cursor.fetchall():
                    results.append({
                        "id": row["id"],
                        "content": row["content"],
                        "agent_id": row["agent_id"],
                        "memory_type": row["memory_type"],
                        "metadata": json.loads(row["metadata_json"]) if row["metadata_json"] else {},
                        "created_at": row["created_at"],
                        "relevance_score": -row["score"],  # BM25 returns negative scores
                    })

                    # Update access count
                    conn.execute("""
                        UPDATE memories
                        SET access_count = access_count + 1, last_accessed = ?
                        WHERE id = ?
                    """, (datetime.utcnow().isoformat(), row["id"]))

                conn.commit()
                return results

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _recall_sync)

    async def recall_by_similarity(
        self,
        query: str,
        agent_id: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        Retrieve memories by semantic similarity (requires embeddings).

        This is a placeholder for when embedding support is enabled.
        Currently falls back to keyword search.
        """
        if not self.use_embeddings:
            return await self.recall(query, agent_id=agent_id, limit=limit)

        # TODO: Implement proper vector similarity search
        # For now, use FTS as fallback
        return await self.recall(query, agent_id=agent_id, limit=limit)

    async def learn_from_execution(
        self,
        state: AgentState,
        final_output: str,
        success: bool,
    ) -> List[str]:
        """
        Extract learnings from a completed execution.

        Analyzes the execution and stores relevant patterns as memories.

        Args:
            state: The final agent state
            final_output: The execution output
            success: Whether the execution was successful

        Returns:
            List of memory IDs created
        """
        memory_ids = []

        # Memory type based on success
        memory_type = "success" if success else "error"

        # Learn from completed steps
        for step in state.completed_steps:
            if step.tool_used and step.tool_output:
                # Store tool usage pattern
                content = f"Task: {step.description}\nTool: {step.tool_used}\nResult: {step.tool_output[:500]}"
                metadata = {
                    "step_id": step.step_id,
                    "tool": step.tool_used,
                    "workflow_id": state.workflow_id,
                    "role": state.role,
                    "success": success,
                    "tokens_used": step.tokens_used,
                }

                memory_id = await self.remember(
                    agent_id=state.agent_id,
                    content=content,
                    memory_type=memory_type,
                    metadata=metadata,
                )
                memory_ids.append(memory_id)

        # Store overall execution pattern
        execution_summary = f"""
Role: {state.role}
Goal: {state.current_goal}
Steps completed: {len(state.completed_steps)}
Success: {success}
Output summary: {final_output[:200]}
"""
        summary_id = await self.remember(
            agent_id=state.agent_id,
            content=execution_summary,
            memory_type="learning",
            metadata={
                "workflow_id": state.workflow_id,
                "total_tokens": state.total_tokens_used,
                "total_cost": state.total_cost_usd,
                "success": success,
            },
        )
        memory_ids.append(summary_id)

        logger.info(f"Learned {len(memory_ids)} patterns from execution {state.workflow_id}")
        return memory_ids

    async def forget(self, memory_id: str) -> bool:
        """Remove a specific memory."""
        self._ensure_initialized()

        def _forget_sync():
            with self._get_connection() as conn:
                cursor = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
                conn.commit()
                return cursor.rowcount > 0

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _forget_sync)

    async def forget_agent(self, agent_id: str) -> int:
        """Remove all memories for an agent."""
        self._ensure_initialized()

        def _forget_agent_sync():
            with self._get_connection() as conn:
                cursor = conn.execute("DELETE FROM memories WHERE agent_id = ?", (agent_id,))
                conn.commit()
                return cursor.rowcount

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _forget_agent_sync)

    async def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        self._ensure_initialized()

        def _get_stats_sync():
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT
                        COUNT(*) as total_memories,
                        COUNT(DISTINCT agent_id) as unique_agents,
                        SUM(CASE WHEN memory_type = 'success' THEN 1 ELSE 0 END) as successes,
                        SUM(CASE WHEN memory_type = 'error' THEN 1 ELSE 0 END) as errors,
                        SUM(CASE WHEN memory_type = 'learning' THEN 1 ELSE 0 END) as learnings,
                        SUM(access_count) as total_recalls
                    FROM memories
                """)
                row = cursor.fetchone()
                return {
                    "total_memories": row["total_memories"],
                    "unique_agents": row["unique_agents"],
                    "successes": row["successes"],
                    "errors": row["errors"],
                    "learnings": row["learnings"],
                    "total_recalls": row["total_recalls"],
                }

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _get_stats_sync)

    async def _generate_embedding(self, text: str) -> Optional[List[float]]:
        """
        Generate embedding for text.

        This is a placeholder for when embedding support is enabled.
        Can be upgraded to use OpenAI, Cohere, or local models.
        """
        # TODO: Implement actual embedding generation
        # For now, return None
        return None


# Singleton instance
_memory: Optional[LongTermMemory] = None


def get_memory() -> LongTermMemory:
    """Get the singleton memory instance."""
    global _memory
    if _memory is None:
        _memory = LongTermMemory()
    return _memory

"""
Context Cache for Brain Trust

Stores large file content in temporary files to avoid polluting
agent context with massive documents. Agents receive file references
(paths) instead of full content, which they can read on demand.

Design:
- Files < INLINE_THRESHOLD are passed directly in context
- Files >= INLINE_THRESHOLD are cached to disk, summary provided
- Cache auto-cleans after CACHE_TTL_HOURS
- Thread-safe for concurrent workflow execution
"""

import os
import json
import hashlib
import tempfile
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

# Configuration
INLINE_THRESHOLD = 4000  # Characters - files smaller than this are passed inline
CACHE_TTL_HOURS = 24     # Hours before cached files are cleaned up
SUMMARY_LENGTH = 500     # Characters for auto-generated summary prefix

# Cache directory
CACHE_DIR = Path(tempfile.gettempdir()) / "brain_trust_context_cache"


class ContextCache:
    """
    Thread-safe cache for storing large file content.

    Usage:
        cache = ContextCache()

        # Store content and get reference
        ref = cache.store("file_id_123", large_content, metadata={"name": "Character Profile"})

        # Reference contains: path, summary, original_length, etc.
        # Pass ref to downstream agent instead of full content

        # Agent can later read full content:
        content = cache.read(ref["cache_path"])
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern for shared cache access."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._cache_lock = threading.Lock()
        self._manifest: Dict[str, dict] = {}

        # Ensure cache directory exists
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # Load existing manifest if present
        self._manifest_path = CACHE_DIR / "manifest.json"
        self._load_manifest()

        # Clean stale entries on init
        self._clean_stale()

        self._initialized = True
        logger.info(f"ContextCache initialized at {CACHE_DIR}")

    def _load_manifest(self):
        """Load cache manifest from disk."""
        if self._manifest_path.exists():
            try:
                with open(self._manifest_path, 'r') as f:
                    self._manifest = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._manifest = {}

    def _save_manifest(self):
        """Persist manifest to disk."""
        with open(self._manifest_path, 'w') as f:
            json.dump(self._manifest, f, indent=2, default=str)

    def _clean_stale(self):
        """Remove cache entries older than TTL."""
        cutoff = datetime.now() - timedelta(hours=CACHE_TTL_HOURS)
        stale_keys = []

        for key, entry in self._manifest.items():
            try:
                created = datetime.fromisoformat(entry.get("created", ""))
                if created < cutoff:
                    stale_keys.append(key)
                    # Remove file if it exists
                    cache_path = Path(entry.get("cache_path", ""))
                    if cache_path.exists():
                        cache_path.unlink()
            except (ValueError, TypeError):
                stale_keys.append(key)

        for key in stale_keys:
            del self._manifest[key]

        if stale_keys:
            self._save_manifest()
            logger.info(f"Cleaned {len(stale_keys)} stale cache entries")

    def _generate_summary(self, content: str, metadata: Optional[dict] = None) -> str:
        """Generate a summary prefix for large content."""
        # Start with metadata if available
        parts = []
        if metadata:
            if metadata.get("name"):
                parts.append(f"Document: {metadata['name']}")
            if metadata.get("type"):
                parts.append(f"Type: {metadata['type']}")

        # Add content preview (first N chars, cleaned up)
        preview = content[:SUMMARY_LENGTH].strip()
        # Try to break at a sentence or word boundary
        for sep in ['. ', '\n', ' ']:
            if sep in preview[SUMMARY_LENGTH//2:]:
                idx = preview.rfind(sep, SUMMARY_LENGTH//2)
                if idx > 0:
                    preview = preview[:idx+1]
                    break

        parts.append(f"Preview: {preview}...")
        parts.append(f"[Full content: {len(content):,} characters - available via cache]")

        return "\n".join(parts)

    def should_cache(self, content: str) -> bool:
        """Determine if content should be cached vs passed inline."""
        return len(content) >= INLINE_THRESHOLD

    def store(
        self,
        file_id: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> dict:
        """
        Store content in cache and return a reference object.

        Args:
            file_id: Unique identifier (e.g., Google Drive file ID)
            content: The full file content
            metadata: Optional dict with name, type, source, etc.

        Returns:
            Reference dict with:
            - cache_path: Path to cached file
            - summary: Brief preview of content
            - original_length: Character count
            - file_id: Original file ID
            - cached: True
        """
        with self._cache_lock:
            # Generate cache key from file_id
            cache_key = hashlib.sha256(file_id.encode()).hexdigest()[:16]
            cache_path = CACHE_DIR / f"{cache_key}.txt"

            # Write content to cache file
            with open(cache_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # Generate summary
            summary = self._generate_summary(content, metadata)

            # Create manifest entry
            entry = {
                "file_id": file_id,
                "cache_path": str(cache_path),
                "original_length": len(content),
                "summary": summary,
                "metadata": metadata or {},
                "created": datetime.now().isoformat(),
            }

            self._manifest[cache_key] = entry
            self._save_manifest()

            logger.info(f"Cached {len(content):,} chars for file {file_id} at {cache_path}")

            return {
                "cached": True,
                "cache_path": str(cache_path),
                "file_id": file_id,
                "summary": summary,
                "original_length": len(content),
            }

    def read(self, cache_path: str) -> Optional[str]:
        """Read full content from a cache path."""
        path = Path(cache_path)
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        return None

    def get_or_create(
        self,
        file_id: str,
        content: str,
        metadata: Optional[dict] = None
    ) -> Tuple[str, dict]:
        """
        Smart content handling: inline for small, cache for large.

        Returns:
            Tuple of (content_for_context, reference_info)

            For small files:
                (full_content, {"cached": False, "original_length": N})

            For large files:
                (summary_with_path, {"cached": True, "cache_path": "...", ...})
        """
        if not self.should_cache(content):
            # Small file - return inline
            return content, {
                "cached": False,
                "file_id": file_id,
                "original_length": len(content),
            }

        # Large file - cache and return summary
        ref = self.store(file_id, content, metadata)

        # Create context-friendly output
        context_content = (
            f"{ref['summary']}\n\n"
            f"TO READ FULL CONTENT: The complete document is available at:\n"
            f"  Cache Path: {ref['cache_path']}\n"
            f"  File ID: {file_id}\n"
            f"Use the ReadCachedFile tool or DriveReadTool to access the full content."
        )

        return context_content, ref

    def clear(self):
        """Clear all cached files."""
        with self._cache_lock:
            for entry in self._manifest.values():
                try:
                    Path(entry["cache_path"]).unlink()
                except (FileNotFoundError, KeyError):
                    pass
            self._manifest = {}
            self._save_manifest()
            logger.info("Context cache cleared")


# Module-level convenience functions
_cache = None

def get_cache() -> ContextCache:
    """Get the singleton cache instance."""
    global _cache
    if _cache is None:
        _cache = ContextCache()
    return _cache

def cache_content(file_id: str, content: str, metadata: Optional[dict] = None) -> Tuple[str, dict]:
    """
    Cache content if large, return inline if small.

    This is the main entry point for workflow_parser and drive_tool.
    """
    return get_cache().get_or_create(file_id, content, metadata)

def read_cached_file(cache_path: str) -> Optional[str]:
    """Read full content from cache."""
    return get_cache().read(cache_path)

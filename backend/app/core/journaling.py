"""
Journaling Protocol
Writes execution summaries to both database and Markdown files.
"""

from pathlib import Path
from datetime import datetime
from typing import Dict, Any
import asyncio
from app.core.db import SupabaseManager


class JournalingProtocol:
    """
    Dual-persistence logger for personal use.
    
    Writes execution logs to both:
    - Supabase (structured, queryable)
    - ~/.pai/logs/YYYY-MM-DD.md (human-readable)
    
    OPTIMIZATION: File locking prevents corruption from concurrent writes.
    MAINTENANCE: Use rotate_logs() periodically to compress old files.
    """
    
    def __init__(self):
        self.logs_dir = Path.home() / ".pai" / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.db = SupabaseManager()
    
    async def log_execution(
        self,
        workflow_data: Dict,
        result: Any,
        agents_count: int,
        duration_seconds: float
    ):
        """
        Write execution log to both DB and Markdown.
        
        Runs in parallel for performance.
        """
        await asyncio.gather(
            self._log_to_database(workflow_data, result, agents_count, duration_seconds),
            self._log_to_markdown(workflow_data, result, agents_count, duration_seconds)
        )
    
    async def _log_to_database(self, workflow_data, result, agents_count, duration):
        """Write to Supabase (existing logic)."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self.db.save_execution,
            workflow_data,
            result,
            agents_count
        )
    
    async def _log_to_markdown(self, workflow_data, result, agents_count, duration):
        """Write to daily Markdown log."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._write_markdown_entry,
            workflow_data,
            result,
            agents_count,
            duration
        )
    
    def _write_markdown_entry(self, workflow_data, result, agents_count, duration):
        """
        Append entry to today's log file.
        
        Format:
        ## [HH:MM:SS] Workflow Execution
        - Agents: 3
        - Duration: 45.2s
        - Result: Success
        
        ### Summary
        <result text>
        """
        import sys
        
        # Get today's log file
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = self.logs_dir / f"{today}.md"
        
        # Create file with header if new
        if not log_file.exists():
            with open(log_file, 'w', encoding='utf-8') as f:
                f.write(f"# Execution Log - {today}\n\n")
        
        # Build entry
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"""
## [{timestamp}] Workflow Execution

- **Agents**: {agents_count}
- **Duration**: {duration:.1f}s
- **Status**: Success

### Summary
```
{str(result)[:500]}  # Truncate long results
```

---

"""
        
        # Append with file lock (platform-specific)
        with open(log_file, 'a', encoding='utf-8') as f:
            try:
                if sys.platform == 'win32':
                    # Windows file locking
                    import msvcrt
                    msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
                    f.write(entry)
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    # Unix file locking
                    import fcntl
                    fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                    f.write(entry)
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except Exception as e:
                # Fallback: write without lock (risk of corruption)
                print(f"WARNING: Could not acquire file lock: {e}")
                f.write(entry)
    
    def rotate_logs(self, max_age_days: int = 30):
        """
        Compress logs older than max_age_days.
        
        This should be called periodically (e.g., daily cron job).
        """
        import gzip
        
        for log_file in self.logs_dir.glob("*.md"):
            age_days = (datetime.now() - datetime.fromtimestamp(log_file.stat().st_mtime)).days
            
            if age_days > max_age_days and not log_file.suffix == '.gz':
                # Compress old log
                with open(log_file, 'rb') as f_in:
                    with gzip.open(f"{log_file}.gz", 'wb') as f_out:
                        f_out.writelines(f_in)
                
                # Delete original
                log_file.unlink()
                print(f"Compressed old log: {log_file}")

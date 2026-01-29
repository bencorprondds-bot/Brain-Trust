#!/usr/bin/env python
"""
Cross-platform server launcher with proper encoding support.

This script ensures UTF-8 encoding is configured before any other
modules are imported, preventing emoji-related encoding errors on Windows.
"""

import os
import sys

# Add backend to path for imports
backend_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, backend_dir)

# CRITICAL: Import Windows console fix FIRST, before any other imports
# This wraps stdout/stderr to handle encoding errors gracefully
import app.core.windows_console_fix

# Configure additional Windows settings
if sys.platform == "win32":
    os.environ["PYTHONIOENCODING"] = "utf-8"

    # Monkey-patch CrewAI's FilteredStream to handle Windows encoding errors
    # This must happen BEFORE crewai is imported by the application
    try:
        from crewai.llm import FilteredStream
        _original_write = FilteredStream.write

        def _safe_write(self, s):
            """Patched write method that handles Windows encoding errors."""
            with self._lock:
                lower_s = s.lower()
                # Skip noisy LiteLLM banners
                if (
                    "litellm.info:" in lower_s
                    or "Consider using a smaller input or implementing a text splitting strategy" in lower_s
                ):
                    return 0
                # Handle encoding errors
                try:
                    return self._original_stream.write(s)
                except UnicodeEncodeError:
                    safe_s = s.encode('ascii', 'replace').decode('ascii')
                    return self._original_stream.write(safe_s)

        FilteredStream.write = _safe_write
        print("[OK] CrewAI FilteredStream patched for Windows encoding")
    except ImportError:
        pass  # CrewAI not installed
    except Exception as e:
        print(f"[WARN] Could not patch CrewAI: {e}")

# Now import and run uvicorn
import uvicorn

if __name__ == "__main__":
    # Change to backend directory for proper imports
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(backend_dir)

    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info"
    )

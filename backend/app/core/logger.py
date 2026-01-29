import sys
import io
import asyncio
from app.core.websockets import manager

class PrintToWebSocket(io.StringIO):
    """
    Captures stdout and broadcasts it to WebSockets.
    Used to stream CrewAI verbose output.
    """
    def write(self, s):
        if s:
            # We need to run async in a sync method (write)
            # This is tricky. safest is verify if loop exists.
            try:
                loop = asyncio.get_running_loop()
                if loop.is_running():
                    loop.create_task(manager.broadcast(s))
                else:
                    # Fallback if no loop
                    pass
            except:
                pass
        # Still write to original stdout for debugging
        # Handle encoding errors on Windows (cp1252 doesn't support emojis)
        try:
            sys.__stdout__.write(s)
        except UnicodeEncodeError:
            # Replace problematic characters with ASCII equivalents
            safe_s = s.encode('ascii', 'replace').decode('ascii')
            sys.__stdout__.write(safe_s)

# Helper context manager
class StdoutInterceptor:
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = PrintToWebSocket()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._original_stdout

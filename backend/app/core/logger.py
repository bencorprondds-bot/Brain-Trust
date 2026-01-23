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
        sys.__stdout__.write(s)

# Helper context manager
class StdoutInterceptor:
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = PrintToWebSocket()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout = self._original_stdout

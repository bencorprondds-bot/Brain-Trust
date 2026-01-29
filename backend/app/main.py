import os
import sys
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Fix Windows console encoding for emoji support
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except AttributeError:
        # Python < 3.7 fallback
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    # Monkey-patch CrewAI's FilteredStream to handle Windows encoding errors
    try:
        from crewai.llm import FilteredStream
        _original_write = FilteredStream.write

        def _safe_write(self, s):
            """Patched write method that handles Windows encoding errors."""
            try:
                return _original_write(self, s)
            except UnicodeEncodeError:
                # Replace problematic characters with '?' for Windows console
                safe_s = s.encode('ascii', 'replace').decode('ascii')
                return self._original_stream.write(safe_s)

        FilteredStream.write = _safe_write
    except ImportError:
        pass  # CrewAI not installed

# Calculate absolute path to .env (backend/.env)
# __file__ is backend/app/main.py
# dirname -> backend/app
# dirname -> backend
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(base_dir, ".env")

# Load env variables (API keys)
load_dotenv(dotenv_path=env_path, override=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    # Startup
    discord_enabled = os.getenv("DISCORD_BOT_TOKEN") and os.getenv("DISCORD_CHANNEL_ID")

    if discord_enabled:
        try:
            from app.core.discord_notifier import start_discord_bot
            asyncio.create_task(start_discord_bot())
            print("Discord bot starting...")
        except Exception as e:
            print(f"Discord bot failed to start: {e}")

    yield

    # Shutdown
    if discord_enabled:
        try:
            from app.core.discord_notifier import stop_discord_bot
            await stop_discord_bot()
        except Exception:
            pass


app = FastAPI(
    title="Brain Trust v3.0 API - Legion",
    version="3.0.0",
    lifespan=lifespan,
)

# CORS (Allow Frontend to connect)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3001", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Brain Trust v2.0 AI Engine Online", "status": "active"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

from app.core.websockets import manager
from fastapi import WebSocket

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except Exception:
        manager.disconnect(websocket)

from app.api.routes import router as api_router
from app.api.eval_routes import router as eval_router
from app.api.v2 import router as v2_router

app.include_router(api_router, prefix="/api/v1")
app.include_router(eval_router, prefix="/api/v1")
app.include_router(v2_router, prefix="/api")

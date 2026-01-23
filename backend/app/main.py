import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# Load env variables (API keys)s
load_dotenv(dotenv_path="../.env")

app = FastAPI(title="Brain Trust v2.0 API", version="2.0.0")

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
app.include_router(api_router, prefix="/api/v1")


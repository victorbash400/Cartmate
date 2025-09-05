import asyncio
import logging
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from utils.logging import setup_logging
from services.storage.redis_client import redis_client
from agents.orchestrator import orchestrator_agent

# Set up logging
setup_logging()

app = FastAPI(
    title="CartMate API",
    description="AI Shopping Assistant Backend",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize application components on startup."""
    try:
        # Initialize Redis client
        await redis_client.initialize()
        # The orchestrator_agent is now initialized when its module is imported
        logging.info("Application startup completed successfully")
    except Exception as e:
        logging.error(f"Error during application startup: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up application components on shutdown."""
    try:
        # Close Redis connection
        await redis_client.close()
        logging.info("Application shutdown completed successfully")
    except Exception as e:
        logging.error(f"Error during application shutdown: {e}")

@app.get("/")
async def root():
    return {"message": "Welcome to CartMate API - Your AI Shopping Assistant"}

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            response = await orchestrator_agent.handle_message(data)
            await websocket.send_text(response)
    except WebSocketDisconnect:
        logging.info("WebSocket disconnected")
    except Exception as e:
        logging.error(f"Error in WebSocket endpoint: {e}")
        await websocket.close(code=1011)

@app.get("/health")
async def health_check():
    # Check if storage is available
    try:
        await redis_client.set("health_check", "ok", expire=10)
        value = await redis_client.get("health_check")
        if value == "ok":
            return {"status": "healthy", "storage": "connected"}
        else:
            return {"status": "degraded", "storage": "disconnected"}
    except Exception as e:
        return {"status": "degraded", "storage": "error", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
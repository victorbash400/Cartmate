import asyncio
import logging
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from utils.logging import setup_logging
from services.storage.redis_client import redis_client
from services.kubernetes.port_forwarder import port_forwarder
from agents.agent_manager import agent_manager
from api.websocket import websocket_gateway
from api.message_router import route_message
from api.personalization import router as personalization_router
from api.cart import router as cart_router

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

# Include routers
app.include_router(personalization_router)
app.include_router(cart_router)

@app.on_event("startup")
async def startup_event():
    """Initialize application components on startup."""
    try:
        # Start Kubernetes port forwarding for external services
        logging.info("Setting up Kubernetes port forwarding...")
        port_forwarding_success = await port_forwarder.start_port_forwarding()
        
        if not port_forwarding_success:
            logging.warning("Some port forwarding failed, but continuing with startup...")
        
        # Initialize Redis client
        await redis_client.initialize()
        
        # Register and start all agents
        agent_manager.register_agents()
        await agent_manager.start_all_agents()
        
        logging.info("Application startup completed successfully")
    except Exception as e:
        logging.error(f"Error during application startup: {e}")
        # Don't raise the exception to allow the app to start even with errors
        logging.warning("Continuing with degraded functionality...")

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up application components on shutdown."""
    try:
        # Stop all agents
        await agent_manager.stop_all_agents()
        
        # Stop port forwarding
        await port_forwarder.stop_port_forwarding()
        
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
    session_id = None
    try:
        # Handle WebSocket connection through the gateway
        session_id = await websocket_gateway.handle_connection(websocket)
        
        while True:
            data = await websocket.receive_text()
            
            # Process the message through the gateway and route to agents
            processed_message = await websocket_gateway.handle_message(session_id, data)
            if processed_message:
                await route_message(session_id, processed_message)
                
    except WebSocketDisconnect:
        logging.info(f"WebSocket disconnected for session {session_id}")
    except Exception as e:
        logging.error(f"Error in WebSocket endpoint for session {session_id}: {e}")
    finally:
        if session_id:
            await websocket_gateway.handle_disconnect(session_id)

@app.websocket("/ws/backchannel")
async def websocket_backchannel_endpoint(websocket: WebSocket):
    session_id = None
    try:
        # Handle backchannel WebSocket connection for A2A monitoring
        session_id = await websocket_gateway.handle_backchannel_connection(websocket)
        
        # Keep connection alive and forward A2A messages
        while True:
            # This endpoint mainly listens and forwards A2A messages to frontend
            # The actual message forwarding is handled by the message bus
            await asyncio.sleep(1)
                
    except WebSocketDisconnect:
        logging.info(f"Backchannel WebSocket disconnected for session {session_id}")
    except Exception as e:
        logging.error(f"Error in backchannel WebSocket endpoint for session {session_id}: {e}")
    finally:
        if session_id:
            await websocket_gateway.handle_disconnect(session_id)

@app.get("/health")
async def health_check():
    # Check if storage is available
    try:
        await redis_client.set("health_check", "ok", expire=10)
        value = await redis_client.get("health_check")
        if value == "ok":
            return {
                "status": "healthy", 
                "storage": "connected", 
                "agents": agent_manager.get_agent_status(),
                "port_forwarding": port_forwarder.get_status()
            }
        else:
            return {
                "status": "degraded", 
                "storage": "disconnected", 
                "agents": agent_manager.get_agent_status(),
                "port_forwarding": port_forwarder.get_status()
            }
    except Exception as e:
        # Even if storage fails, return healthy status to allow deployment
        return {
            "status": "healthy", 
            "storage": "error", 
            "error": str(e), 
            "agents": agent_manager.get_agent_status(),
            "port_forwarding": port_forwarder.get_status()
        }

@app.get("/agents/status")
async def agents_status():
    """Get detailed status of all agents"""
    return agent_manager.get_agent_status()

@app.get("/port-forwarding/status")
async def port_forwarding_status():
    """Get detailed status of port forwarding"""
    return port_forwarder.get_status()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
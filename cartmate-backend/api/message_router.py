import logging
from api.websocket import WebSocketMessage, websocket_gateway
from agents.agent_manager import agent_manager
from agents.orchestrator import orchestrator_agent
from services.storage.session_manager import session_manager

logger = logging.getLogger(__name__)

async def route_message(session_id: str, message: WebSocketMessage):
    """
    Routes incoming WebSocket messages to the appropriate handlers.
    """
    logger.info(f"Routing message type '{message.type}' for session {session_id}")

    if message.type == "new_chat":
        success = await session_manager.reset_session_context(session_id)
        # Also clear orchestrator context
        await orchestrator_agent.clear_session_context(session_id)
        if success:
            # Let the client know the chat has been reset
            await websocket_gateway.send_message(session_id, "chat_reset", {"message": "New chat started."})
        else:
            await websocket_gateway.send_error(session_id, "Failed to start new chat.")
    
    elif message.type == "new_chat_silent":
        # Silently reset session context without sending any response
        success = await session_manager.reset_session_context(session_id)
        # Also clear orchestrator context
        await orchestrator_agent.clear_session_context(session_id)
        if success:
            logger.info(f"Session context silently reset for session {session_id}")
        else:
            logger.error(f"Failed to silently reset session context for session {session_id}")

    elif message.type == "text":
        # Route text messages to the orchestrator agent
        if isinstance(message.content, str):
            # Get the orchestrator agent from agent manager
            orchestrator = agent_manager.get_agent_by_type("orchestrator")
            if orchestrator and orchestrator.is_running:
                response_text = await orchestrator.handle_user_message(message.content, session_id)
                # The orchestrator will handle sending responses via WebSocket
                # Only send a response here if the orchestrator returned an immediate response
                if response_text and not response_text.startswith("Let me"):
                    await websocket_gateway.send_message(session_id, "text", response_text)
            else:
                logger.error(f"Orchestrator agent not available for session {session_id}")
                await websocket_gateway.send_error(session_id, "Service temporarily unavailable", "The AI assistant is not ready. Please try again in a moment.")
        else:
            logger.warning(f"Received text message with non-string content for session {session_id}")
            await websocket_gateway.send_error(session_id, "Invalid message content", "Expected a string for 'text' message type.")
    
    else:
        logger.warning(f"No handler for message type '{message.type}'")
        await websocket_gateway.send_error(session_id, "Unknown message type", f"No handler for '{message.type}'")

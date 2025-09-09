"""
WebSocket Gateway for CartMate Backend

Provides real-time bidirectional communication with connection management,
session handling, and message routing capabilities.
"""

import json
import logging
import uuid
from typing import Dict, Set, Optional, Any
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel, ValidationError

from services.storage.session_manager import session_manager
from services.storage.redis_client import redis_client
from a2a.message_bus import a2a_message_bus

logger = logging.getLogger(__name__)


class AgentStep(BaseModel):
    """Represents a step in agent communication for frontend visibility."""
    id: str
    type: str  # "calling", "processing", "success", "error"
    agent_name: str
    message: str


class WebSocketMessage(BaseModel):
    """Standard WebSocket message format."""
    type: str
    content: Any
    session_id: Optional[str] = None
    timestamp: datetime = None
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)


class ConnectionManager:
    """Manages WebSocket connections and session mapping."""
    
    def __init__(self):
        # Active connections: session_id -> WebSocket
        self.active_connections: Dict[str, WebSocket] = {}
        # Connection metadata: session_id -> connection info
        self.connection_info: Dict[str, Dict[str, Any]] = {}
        # User to session mapping: user_id -> Set[session_id]
        self.user_sessions: Dict[str, Set[str]] = {}
        # Backchannel connections: session_id -> bool
        self.backchannel_connections: Set[str] = set()
        
    async def connect(self, websocket: WebSocket, session_id: str = None, user_id: str = None) -> str:
        """
        Accept WebSocket connection and create/retrieve session.
        
        Args:
            websocket: WebSocket connection
            session_id: Optional existing session ID
            user_id: Optional user ID for session creation
            
        Returns:
            str: Session ID for the connection
        """
        await websocket.accept()
        
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
            
        # Create or retrieve session
        session = await session_manager.get_session(session_id)
        if not session:
            if not user_id:
                user_id = f"anonymous_{uuid.uuid4().hex[:8]}"
            session = await session_manager.create_session(user_id, session_id)
            
        # Store connection
        self.active_connections[session_id] = websocket
        self.connection_info[session_id] = {
            "user_id": session.user_id,
            "connected_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "is_backchannel": False
        }
        
        # Update user sessions mapping
        if session.user_id not in self.user_sessions:
            self.user_sessions[session.user_id] = set()
        self.user_sessions[session.user_id].add(session_id)
        
        logger.info(f"WebSocket connected: session_id={session_id}, user_id={session.user_id}")
        
        # Send connection confirmation
        await self.send_message(session_id, WebSocketMessage(
            type="connection_established",
            content={
                "session_id": session_id,
                "user_id": session.user_id,
                "message": "Connected successfully"
            }
        ))
        
        return session_id
    
    async def connect_backchannel(self, websocket: WebSocket, session_id: str = None, user_id: str = None) -> str:
        """
        Accept backchannel WebSocket connection for A2A message monitoring.
        
        Args:
            websocket: WebSocket connection
            session_id: Optional existing session ID
            user_id: Optional user ID
            
        Returns:
            str: Session ID for the connection
        """
        await websocket.accept()
        
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
            
        # Create or retrieve session
        session = await session_manager.get_session(session_id)
        if not session:
            if not user_id:
                user_id = f"backchannel_{uuid.uuid4().hex[:8]}"
            session = await session_manager.create_session(user_id, session_id)
            
        # Store connection
        self.active_connections[session_id] = websocket
        self.connection_info[session_id] = {
            "user_id": session.user_id,
            "connected_at": datetime.utcnow(),
            "last_activity": datetime.utcnow(),
            "is_backchannel": True
        }
        
        # Add to backchannel connections
        self.backchannel_connections.add(session_id)
        
        # Register as frontend subscriber for A2A messages
        a2a_message_bus.add_frontend_subscriber(session_id)
        
        # Update user sessions mapping
        if session.user_id not in self.user_sessions:
            self.user_sessions[session.user_id] = set()
        self.user_sessions[session.user_id].add(session_id)
        
        logger.info(f"Backchannel WebSocket connected: session_id={session_id}, user_id={session.user_id}")
        
        # Send connection confirmation
        await self.send_message(session_id, WebSocketMessage(
            type="backchannel_connected",
            content={
                "session_id": session_id,
                "user_id": session.user_id,
                "message": "Backchannel connected successfully"
            }
        ))
        
        return session_id
    
    async def disconnect(self, session_id: str):
        """
        Handle WebSocket disconnection and cleanup.
        
        Args:
            session_id: Session ID to disconnect
        """
        if session_id in self.active_connections:
            connection_info = self.connection_info.get(session_id, {})
            user_id = connection_info.get("user_id")
            is_backchannel = connection_info.get("is_backchannel", False)
            
            # Remove from active connections
            del self.active_connections[session_id]
            del self.connection_info[session_id]
            
            # Remove from backchannel connections if applicable
            if is_backchannel:
                self.backchannel_connections.discard(session_id)
                # Unregister as frontend subscriber
                a2a_message_bus.remove_frontend_subscriber(session_id)
            
            # Update user sessions mapping
            if user_id and user_id in self.user_sessions:
                self.user_sessions[user_id].discard(session_id)
                if not self.user_sessions[user_id]:
                    del self.user_sessions[user_id]
            
            logger.info(f"WebSocket disconnected: session_id={session_id}, user_id={user_id}")
    
    async def send_message(self, session_id: str, message: WebSocketMessage) -> bool:
        """
        Send message to specific session.
        
        Args:
            session_id: Target session ID
            message: Message to send
            
        Returns:
            bool: True if message sent successfully
        """
        if session_id not in self.active_connections:
            logger.warning(f"Attempted to send message to inactive session: {session_id}")
            return False
            
        try:
            websocket = self.active_connections[session_id]
            message_data = message.model_dump_json()
            await websocket.send_text(message_data)
            
            # Update last activity
            if session_id in self.connection_info:
                self.connection_info[session_id]["last_activity"] = datetime.utcnow()
                
            return True
        except Exception as e:
            logger.error(f"Error sending message to session {session_id}: {e}")
            await self.disconnect(session_id)
            return False
    
    async def send_to_user(self, user_id: str, message: WebSocketMessage) -> int:
        """
        Send message to all sessions of a user.
        
        Args:
            user_id: Target user ID
            message: Message to send
            
        Returns:
            int: Number of sessions message was sent to
        """
        if user_id not in self.user_sessions:
            return 0
            
        sent_count = 0
        session_ids = list(self.user_sessions[user_id])  # Copy to avoid modification during iteration
        
        for session_id in session_ids:
            if await self.send_message(session_id, message):
                sent_count += 1
                
        return sent_count
    
    async def broadcast(self, message: WebSocketMessage, exclude_sessions: Set[str] = None) -> int:
        """
        Broadcast message to all active connections.
        
        Args:
            message: Message to broadcast
            exclude_sessions: Set of session IDs to exclude
            
        Returns:
            int: Number of sessions message was sent to
        """
        if exclude_sessions is None:
            exclude_sessions = set()
            
        sent_count = 0
        session_ids = list(self.active_connections.keys())  # Copy to avoid modification during iteration
        
        for session_id in session_ids:
            if session_id not in exclude_sessions:
                if await self.send_message(session_id, message):
                    sent_count += 1
                    
        return sent_count
    
    async def broadcast_to_backchannel(self, message: WebSocketMessage, exclude_sessions: Set[str] = None) -> int:
        """
        Broadcast message to all backchannel connections.
        
        Args:
            message: Message to broadcast
            exclude_sessions: Set of session IDs to exclude
            
        Returns:
            int: Number of sessions message was sent to
        """
        if exclude_sessions is None:
            exclude_sessions = set()
            
        sent_count = 0
        backchannel_sessions = list(self.backchannel_connections)  # Copy to avoid modification during iteration
        
        for session_id in backchannel_sessions:
            if session_id not in exclude_sessions:
                if await self.send_message(session_id, message):
                    sent_count += 1
                    
        return sent_count
    
    async def send_typing_indicator(self, session_id: str, is_typing: bool = True) -> bool:
        """
        Send typing indicator to session.
        
        Args:
            session_id: Target session ID
            is_typing: Whether typing is active
            
        Returns:
            bool: True if indicator sent successfully
        """
        message = WebSocketMessage(
            type="typing_indicator",
            content={"is_typing": is_typing}
        )
        return await self.send_message(session_id, message)
    
    def get_active_sessions(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all active sessions."""
        return self.connection_info.copy()
    
    def is_session_active(self, session_id: str) -> bool:
        """Check if session is currently connected."""
        return session_id in self.active_connections
    
    def get_user_sessions(self, user_id: str) -> Set[str]:
        """Get all active session IDs for a user."""
        return self.user_sessions.get(user_id, set()).copy()
    
    def get_backchannel_sessions(self) -> Set[str]:
        """Get all active backchannel session IDs."""
        return self.backchannel_connections.copy()


class WebSocketGateway:
    """Main WebSocket gateway class."""
    
    def __init__(self):
        self.connection_manager = ConnectionManager()
        
    async def handle_connection(self, websocket: WebSocket, session_id: str = None, user_id: str = None) -> str:
        """
        Handle new WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            session_id: Optional existing session ID
            user_id: Optional user ID
            
        Returns:
            str: Session ID for the connection
        """
        return await self.connection_manager.connect(websocket, session_id, user_id)
    
    async def handle_backchannel_connection(self, websocket: WebSocket, session_id: str = None, user_id: str = None) -> str:
        """
        Handle new backchannel WebSocket connection.
        
        Args:
            websocket: WebSocket connection
            session_id: Optional existing session ID
            user_id: Optional user ID
            
        Returns:
            str: Session ID for the connection
        """
        return await self.connection_manager.connect_backchannel(websocket, session_id, user_id)
    
    async def handle_message(self, session_id: str, raw_message: str) -> Optional[WebSocketMessage]:
        """
        Process incoming WebSocket message.
        
        Args:
            session_id: Source session ID
            raw_message: Raw message string
            
        Returns:
            WebSocketMessage: Processed message or None if invalid
        """
        try:
            # Try to parse as JSON first
            try:
                message_data = json.loads(raw_message)
                if isinstance(message_data, dict):
                    # Add session_id if not present
                    if 'session_id' not in message_data:
                        message_data['session_id'] = session_id
                    message = WebSocketMessage(**message_data)
                else:
                    # Plain text message
                    message = WebSocketMessage(
                        type="text",
                        content=raw_message,
                        session_id=session_id
                    )
            except (json.JSONDecodeError, ValidationError):
                # Treat as plain text message
                message = WebSocketMessage(
                    type="text",
                    content=raw_message,
                    session_id=session_id
                )
            
            # Update session context with message
            await session_manager.update_context(session_id, {
                "last_message": message.model_dump(),
                "last_activity": datetime.utcnow().isoformat()
            })
            
            return message
            
        except Exception as e:
            logger.error(f"Error processing message from session {session_id}: {e}")
            await self.send_error(session_id, "Invalid message format", str(e))
            return None
    
    async def send_message(self, session_id: str, message_type: str, content: Any) -> bool:
        """
        Send message to session.
        
        Args:
            session_id: Target session ID
            message_type: Type of message
            content: Message content
            
        Returns:
            bool: True if sent successfully
        """
        message = WebSocketMessage(
            type=message_type,
            content=content,
            session_id=session_id
        )
        return await self.connection_manager.send_message(session_id, message)
    
    async def send_a2a_message_to_backchannel(self, message_content: Any) -> bool:
        """
        Send A2A message to all backchannel connections for frontend visibility.
        
        Args:
            message_content: A2A message content to send
            
        Returns:
            bool: True if sent successfully to at least one backchannel
        """
        try:
            message = WebSocketMessage(
                type="a2a_message",
                content=message_content
            )
            sent_count = await self.connection_manager.broadcast_to_backchannel(message)
            return sent_count > 0
        except Exception as e:
            logger.error(f"Error sending A2A message to backchannel: {e}")
            return False
    
    async def send_error(self, session_id: str, error_message: str, details: str = None) -> bool:
        """
        Send error message to session.
        
        Args:
            session_id: Target session ID
            error_message: Error message
            details: Optional error details
            
        Returns:
            bool: True if sent successfully
        """
        error_content = {"error": error_message}
        if details:
            error_content["details"] = details
            
        return await self.send_message(session_id, "error", error_content)
    
    async def send_typing_indicator(self, session_id: str, is_typing: bool = True) -> bool:
        """
        Send typing indicator to session.
        
        Args:
            session_id: Target session ID
            is_typing: Whether typing is active
            
        Returns:
            bool: True if indicator sent successfully
        """
        return await self.connection_manager.send_typing_indicator(session_id, is_typing)
    
    async def send_agent_communication(self, session_id: str, agent_steps: list) -> bool:
        """
        Send agent communication steps to session for frontend visibility.
        
        Args:
            session_id: Target session ID
            agent_steps: List of AgentStep objects
            
        Returns:
            bool: True if sent successfully
        """
        try:
            # Convert AgentStep objects to dictionaries
            steps_data = [step.model_dump() if hasattr(step, 'model_dump') else step for step in agent_steps]
            
            message = WebSocketMessage(
                type="agent_communication",
                content={"steps": steps_data},
                session_id=session_id
            )
            return await self.connection_manager.send_message(session_id, message)
        except Exception as e:
            logger.error(f"Error sending agent communication to session {session_id}: {e}")
            return False
    
    async def update_agent_communication(self, session_id: str, agent_steps: list) -> bool:
        """
        Update agent communication steps for session.
        
        Args:
            session_id: Target session ID
            agent_steps: List of AgentStep objects
            
        Returns:
            bool: True if updated successfully
        """
        try:
            # Convert AgentStep objects to dictionaries
            steps_data = [step.model_dump() if hasattr(step, 'model_dump') else step for step in agent_steps]
            
            message = WebSocketMessage(
                type="agent_communication_update",
                content={"steps": steps_data},
                session_id=session_id
            )
            return await self.connection_manager.send_message(session_id, message)
        except Exception as e:
            logger.error(f"Error updating agent communication for session {session_id}: {e}")
            return False
    
    async def handle_disconnect(self, session_id: str):
        """Handle WebSocket disconnection."""
        await self.connection_manager.disconnect(session_id)
    
    async def broadcast_system_message(self, message: str, exclude_sessions: Set[str] = None) -> int:
        """
        Broadcast system message to all connections.
        
        Args:
            message: System message
            exclude_sessions: Sessions to exclude
            
        Returns:
            int: Number of sessions message was sent to
        """
        system_message = WebSocketMessage(
            type="system",
            content={"message": message}
        )
        return await self.connection_manager.broadcast(system_message, exclude_sessions)


# Global WebSocket gateway instance
websocket_gateway = WebSocketGateway()
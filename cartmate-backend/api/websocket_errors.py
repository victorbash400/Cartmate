"""
WebSocket Error Handling and Reconnection Logic

Provides comprehensive error handling, recovery mechanisms, and reconnection logic
for WebSocket connections.
"""

import logging
import asyncio
from typing import Dict, Optional, Any, Callable
from datetime import datetime, timedelta
from enum import Enum
from pydantic import BaseModel

from api.websocket import WebSocketMessage, websocket_gateway
from services.storage.session_manager import session_manager

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """WebSocket error codes."""
    CONNECTION_FAILED = "CONNECTION_FAILED"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    MESSAGE_INVALID = "MESSAGE_INVALID"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class WebSocketError(BaseModel):
    """WebSocket error model."""
    code: ErrorCode
    message: str
    details: Optional[str] = None
    severity: ErrorSeverity = ErrorSeverity.MEDIUM
    timestamp: datetime = None
    session_id: Optional[str] = None
    recoverable: bool = True
    retry_after: Optional[int] = None  # seconds
    
    def __init__(self, **data):
        if 'timestamp' not in data:
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)


class ConnectionState(str, Enum):
    """WebSocket connection states."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    FAILED = "failed"


class ReconnectionConfig(BaseModel):
    """Reconnection configuration."""
    max_attempts: int = 5
    initial_delay: int = 1  # seconds
    max_delay: int = 30  # seconds
    backoff_multiplier: float = 2.0
    jitter: bool = True


class ErrorHandler:
    """Handles WebSocket errors and recovery."""
    
    def __init__(self):
        # Connection states: session_id -> ConnectionState
        self.connection_states: Dict[str, ConnectionState] = {}
        # Error history: session_id -> List[WebSocketError]
        self.error_history: Dict[str, list] = {}
        # Reconnection attempts: session_id -> int
        self.reconnection_attempts: Dict[str, int] = {}
        # Rate limiting: session_id -> Dict[str, Any]
        self.rate_limits: Dict[str, Dict[str, Any]] = {}
        # Error handlers: ErrorCode -> Callable
        self.error_handlers: Dict[ErrorCode, Callable] = {}
        
        # Configuration
        self.reconnection_config = ReconnectionConfig()
        self.max_error_history = 50
        self.rate_limit_window = 60  # seconds
        self.rate_limit_max_messages = 100
        
        # Register default error handlers
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Register default error handlers."""
        self.error_handlers[ErrorCode.CONNECTION_FAILED] = self._handle_connection_failed
        self.error_handlers[ErrorCode.SESSION_EXPIRED] = self._handle_session_expired
        self.error_handlers[ErrorCode.RATE_LIMIT_EXCEEDED] = self._handle_rate_limit_exceeded
        self.error_handlers[ErrorCode.INTERNAL_ERROR] = self._handle_internal_error
        self.error_handlers[ErrorCode.SERVICE_UNAVAILABLE] = self._handle_service_unavailable
    
    async def handle_error(self, error: WebSocketError) -> bool:
        """
        Handle WebSocket error.
        
        Args:
            error: WebSocket error to handle
            
        Returns:
            bool: True if error was handled successfully
        """
        try:
            session_id = error.session_id
            
            # Log error
            logger.error(f"WebSocket error in session {session_id}: {error.code} - {error.message}")
            
            # Add to error history
            if session_id:
                self._add_to_error_history(session_id, error)
            
            # Send error message to client if session is active
            if session_id and websocket_gateway.connection_manager.is_session_active(session_id):
                await self._send_error_to_client(session_id, error)
            
            # Execute specific error handler
            if error.code in self.error_handlers:
                handler = self.error_handlers[error.code]
                await handler(error)
            
            return True
            
        except Exception as e:
            logger.critical(f"Error in error handler: {e}")
            return False
    
    async def _send_error_to_client(self, session_id: str, error: WebSocketError):
        """Send error message to client."""
        error_message = {
            "code": error.code,
            "message": error.message,
            "severity": error.severity,
            "timestamp": error.timestamp.isoformat(),
            "recoverable": error.recoverable
        }
        
        if error.retry_after:
            error_message["retry_after"] = error.retry_after
        
        if error.details:
            error_message["details"] = error.details
        
        await websocket_gateway.send_message(session_id, "error", error_message)
    
    def _add_to_error_history(self, session_id: str, error: WebSocketError):
        """Add error to session error history."""
        if session_id not in self.error_history:
            self.error_history[session_id] = []
        
        self.error_history[session_id].append(error)
        
        # Limit history size
        if len(self.error_history[session_id]) > self.max_error_history:
            self.error_history[session_id] = self.error_history[session_id][-self.max_error_history:]
    
    async def check_rate_limit(self, session_id: str) -> bool:
        """
        Check if session is within rate limits.
        
        Args:
            session_id: Session ID to check
            
        Returns:
            bool: True if within limits, False if exceeded
        """
        now = datetime.utcnow()
        
        if session_id not in self.rate_limits:
            self.rate_limits[session_id] = {
                "messages": [],
                "window_start": now
            }
        
        rate_data = self.rate_limits[session_id]
        
        # Clean old messages outside window
        window_start = now - timedelta(seconds=self.rate_limit_window)
        rate_data["messages"] = [
            msg_time for msg_time in rate_data["messages"] 
            if msg_time > window_start
        ]
        
        # Check if limit exceeded
        if len(rate_data["messages"]) >= self.rate_limit_max_messages:
            # Rate limit exceeded
            error = WebSocketError(
                code=ErrorCode.RATE_LIMIT_EXCEEDED,
                message="Rate limit exceeded",
                details=f"Maximum {self.rate_limit_max_messages} messages per {self.rate_limit_window} seconds",
                session_id=session_id,
                retry_after=self.rate_limit_window
            )
            await self.handle_error(error)
            return False
        
        # Add current message
        rate_data["messages"].append(now)
        return True
    
    def set_connection_state(self, session_id: str, state: ConnectionState):
        """Set connection state for session."""
        self.connection_states[session_id] = state
        logger.debug(f"Session {session_id} state changed to: {state}")
    
    def get_connection_state(self, session_id: str) -> ConnectionState:
        """Get connection state for session."""
        return self.connection_states.get(session_id, ConnectionState.DISCONNECTED)
    
    async def initiate_reconnection(self, session_id: str) -> bool:
        """
        Initiate reconnection process for session.
        
        Args:
            session_id: Session ID to reconnect
            
        Returns:
            bool: True if reconnection was initiated
        """
        try:
            current_state = self.get_connection_state(session_id)
            
            if current_state in [ConnectionState.CONNECTED, ConnectionState.RECONNECTING]:
                return False
            
            # Check reconnection attempts
            attempts = self.reconnection_attempts.get(session_id, 0)
            if attempts >= self.reconnection_config.max_attempts:
                logger.warning(f"Max reconnection attempts reached for session {session_id}")
                self.set_connection_state(session_id, ConnectionState.FAILED)
                return False
            
            # Set reconnecting state
            self.set_connection_state(session_id, ConnectionState.RECONNECTING)
            self.reconnection_attempts[session_id] = attempts + 1
            
            # Calculate delay with exponential backoff
            delay = min(
                self.reconnection_config.initial_delay * (
                    self.reconnection_config.backoff_multiplier ** attempts
                ),
                self.reconnection_config.max_delay
            )
            
            # Add jitter if enabled
            if self.reconnection_config.jitter:
                import random
                delay *= (0.5 + random.random() * 0.5)
            
            logger.info(f"Initiating reconnection for session {session_id} in {delay:.2f} seconds (attempt {attempts + 1})")
            
            # Schedule reconnection
            asyncio.create_task(self._perform_reconnection(session_id, delay))
            
            return True
            
        except Exception as e:
            logger.error(f"Error initiating reconnection for session {session_id}: {e}")
            return False
    
    async def _perform_reconnection(self, session_id: str, delay: float):
        """Perform actual reconnection after delay."""
        try:
            await asyncio.sleep(delay)
            
            # Check if session still needs reconnection
            if self.get_connection_state(session_id) != ConnectionState.RECONNECTING:
                return
            
            # Extend session if it exists
            session_extended = await session_manager.extend_session(session_id)
            
            if session_extended:
                # Send reconnection ready message
                await websocket_gateway.send_message(session_id, "reconnection_ready", {
                    "session_id": session_id,
                    "message": "Ready for reconnection",
                    "attempt": self.reconnection_attempts.get(session_id, 0)
                })
                
                logger.info(f"Reconnection ready for session {session_id}")
            else:
                logger.warning(f"Session {session_id} not found during reconnection")
                self.set_connection_state(session_id, ConnectionState.FAILED)
                
        except Exception as e:
            logger.error(f"Error performing reconnection for session {session_id}: {e}")
            self.set_connection_state(session_id, ConnectionState.FAILED)
    
    def reset_reconnection_attempts(self, session_id: str):
        """Reset reconnection attempts for successful connection."""
        if session_id in self.reconnection_attempts:
            del self.reconnection_attempts[session_id]
        self.set_connection_state(session_id, ConnectionState.CONNECTED)
    
    def cleanup_session(self, session_id: str):
        """Clean up error handler data for session."""
        self.connection_states.pop(session_id, None)
        self.error_history.pop(session_id, None)
        self.reconnection_attempts.pop(session_id, None)
        self.rate_limits.pop(session_id, None)
        
        logger.debug(f"Cleaned up error handler data for session {session_id}")
    
    # Default error handlers
    
    async def _handle_connection_failed(self, error: WebSocketError):
        """Handle connection failed errors."""
        if error.session_id:
            await self.initiate_reconnection(error.session_id)
    
    async def _handle_session_expired(self, error: WebSocketError):
        """Handle session expired errors."""
        if error.session_id:
            # Clean up session data
            await session_manager.delete_session(error.session_id)
            self.cleanup_session(error.session_id)
    
    async def _handle_rate_limit_exceeded(self, error: WebSocketError):
        """Handle rate limit exceeded errors."""
        # Rate limiting is already handled in check_rate_limit
        pass
    
    async def _handle_internal_error(self, error: WebSocketError):
        """Handle internal errors."""
        # Log for monitoring and alerting
        logger.critical(f"Internal error in WebSocket: {error.message}")
    
    async def _handle_service_unavailable(self, error: WebSocketError):
        """Handle service unavailable errors."""
        if error.session_id:
            # Queue message for later delivery
            from api.message_router import message_router
            service_message = WebSocketMessage(
                type="service_status",
                content={
                    "status": "unavailable",
                    "message": "Service temporarily unavailable, will retry automatically"
                }
            )
            await message_router.queue_message(error.session_id, service_message)
    
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics."""
        total_errors = sum(len(history) for history in self.error_history.values())
        error_counts = {}
        
        for history in self.error_history.values():
            for error in history:
                error_counts[error.code] = error_counts.get(error.code, 0) + 1
        
        return {
            "total_errors": total_errors,
            "error_counts": error_counts,
            "active_sessions": len(self.connection_states),
            "reconnecting_sessions": sum(
                1 for state in self.connection_states.values() 
                if state == ConnectionState.RECONNECTING
            ),
            "failed_sessions": sum(
                1 for state in self.connection_states.values() 
                if state == ConnectionState.FAILED
            ),
            "timestamp": datetime.utcnow().isoformat()
        }


# Global error handler instance
error_handler = ErrorHandler()
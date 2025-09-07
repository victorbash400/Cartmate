"""
Unit tests for WebSocket communication infrastructure.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch

from api.websocket import WebSocketGateway, ConnectionManager, WebSocketMessage
from api.message_router import MessageRouter, MessagePriority
from api.websocket_errors import ErrorHandler, WebSocketError, ErrorCode, ConnectionState
from services.storage.session_manager import SessionManager
from models.user import Session


class TestWebSocketMessage:
    """Test WebSocketMessage model."""
    
    def test_websocket_message_creation(self):
        """Test WebSocket message creation."""
        message = WebSocketMessage(
            type="test",
            content={"data": "test_data"}
        )
        
        assert message.type == "test"
        assert message.content == {"data": "test_data"}
        assert message.timestamp is not None
        assert isinstance(message.timestamp, datetime)
    
    def test_websocket_message_with_session_id(self):
        """Test WebSocket message with session ID."""
        session_id = "test_session_123"
        message = WebSocketMessage(
            type="chat",
            content="Hello world",
            session_id=session_id
        )
        
        assert message.session_id == session_id
        assert message.content == "Hello world"
    
    def test_websocket_message_serialization(self):
        """Test WebSocket message JSON serialization."""
        message = WebSocketMessage(
            type="test",
            content={"key": "value"},
            session_id="session_123"
        )
        
        json_data = message.model_dump_json()
        parsed_data = json.loads(json_data)
        
        assert parsed_data["type"] == "test"
        assert parsed_data["content"] == {"key": "value"}
        assert parsed_data["session_id"] == "session_123"
        assert "timestamp" in parsed_data


class TestConnectionManager:
    """Test ConnectionManager functionality."""
    
    @pytest.fixture
    def connection_manager(self):
        """Create ConnectionManager instance for testing."""
        return ConnectionManager()
    
    @pytest.fixture
    def mock_websocket(self):
        """Create mock WebSocket for testing."""
        websocket = AsyncMock()
        websocket.accept = AsyncMock()
        websocket.send_text = AsyncMock()
        return websocket
    
    @pytest.mark.asyncio
    async def test_connect_new_session(self, connection_manager, mock_websocket):
        """Test connecting with new session."""
        with patch('api.websocket.session_manager') as mock_session_manager:
            # Mock session creation
            mock_session = Session(
                id="test_session",
                user_id="test_user",
                expires_at=datetime.utcnow() + timedelta(hours=1)
            )
            mock_session_manager.get_session = AsyncMock(return_value=None)
            mock_session_manager.create_session = AsyncMock(return_value=mock_session)
            
            session_id = await connection_manager.connect(
                mock_websocket, 
                user_id="test_user"
            )
            
            assert session_id in connection_manager.active_connections
            assert connection_manager.active_connections[session_id] == mock_websocket
            assert session_id in connection_manager.connection_info
            
            mock_websocket.accept.assert_called_once()
            mock_websocket.send_text.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_connect_existing_session(self, connection_manager, mock_websocket):
        """Test connecting with existing session."""
        with patch('api.websocket.session_manager') as mock_session_manager:
            # Mock existing session
            existing_session_id = "existing_session"
            mock_session = Session(
                id=existing_session_id,
                user_id="test_user",
                expires_at=datetime.utcnow() + timedelta(hours=1)
            )
            mock_session_manager.get_session = AsyncMock(return_value=mock_session)
            mock_session_manager.create_session = AsyncMock()
            
            session_id = await connection_manager.connect(
                mock_websocket, 
                session_id=existing_session_id
            )
            
            assert session_id == existing_session_id
            assert session_id in connection_manager.active_connections
            mock_session_manager.create_session.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_disconnect(self, connection_manager, mock_websocket):
        """Test WebSocket disconnection."""
        # First connect
        with patch('api.websocket.session_manager') as mock_session_manager:
            mock_session = Session(
                id="test_session",
                user_id="test_user",
                expires_at=datetime.utcnow() + timedelta(hours=1)
            )
            mock_session_manager.get_session = AsyncMock(return_value=None)
            mock_session_manager.create_session = AsyncMock(return_value=mock_session)
            
            session_id = await connection_manager.connect(mock_websocket, user_id="test_user")
            
            # Then disconnect
            await connection_manager.disconnect(session_id)
            
            assert session_id not in connection_manager.active_connections
            assert session_id not in connection_manager.connection_info
    
    @pytest.mark.asyncio
    async def test_send_message_success(self, connection_manager, mock_websocket):
        """Test successful message sending."""
        with patch('api.websocket.session_manager') as mock_session_manager:
            mock_session = Session(
                id="test_session",
                user_id="test_user",
                expires_at=datetime.utcnow() + timedelta(hours=1)
            )
            mock_session_manager.get_session = AsyncMock(return_value=None)
            mock_session_manager.create_session = AsyncMock(return_value=mock_session)
            
            session_id = await connection_manager.connect(mock_websocket, user_id="test_user")
            
            message = WebSocketMessage(type="test", content="test message")
            result = await connection_manager.send_message(session_id, message)
            
            assert result is True
            assert mock_websocket.send_text.call_count >= 1  # At least connection + test message
    
    @pytest.mark.asyncio
    async def test_send_message_inactive_session(self, connection_manager):
        """Test sending message to inactive session."""
        message = WebSocketMessage(type="test", content="test message")
        result = await connection_manager.send_message("nonexistent_session", message)
        
        assert result is False
    
    @pytest.mark.asyncio
    async def test_broadcast(self, connection_manager):
        """Test message broadcasting."""
        with patch('api.websocket.session_manager') as mock_session_manager:
            # Create multiple mock sessions
            mock_sessions = []
            mock_websockets = []
            
            for i in range(3):
                mock_session = Session(
                    id=f"session_{i}",
                    user_id=f"user_{i}",
                    expires_at=datetime.utcnow() + timedelta(hours=1)
                )
                mock_websocket = AsyncMock()
                mock_websocket.accept = AsyncMock()
                mock_websocket.send_text = AsyncMock()
                
                mock_sessions.append(mock_session)
                mock_websockets.append(mock_websocket)
            
            mock_session_manager.get_session = AsyncMock(return_value=None)
            mock_session_manager.create_session = AsyncMock(side_effect=mock_sessions)
            
            # Connect multiple sessions
            session_ids = []
            for i, websocket in enumerate(mock_websockets):
                session_id = await connection_manager.connect(websocket, user_id=f"user_{i}")
                session_ids.append(session_id)
            
            # Broadcast message
            message = WebSocketMessage(type="broadcast", content="broadcast message")
            sent_count = await connection_manager.broadcast(message, exclude_sessions={session_ids[0]})
            
            # Should send to 2 sessions (excluding the first one)
            assert sent_count == 2
    
    def test_get_active_sessions(self, connection_manager):
        """Test getting active sessions info."""
        # Initially empty
        sessions = connection_manager.get_active_sessions()
        assert len(sessions) == 0
        
        # Add some connection info manually for testing
        connection_manager.connection_info["session_1"] = {
            "user_id": "user_1",
            "connected_at": datetime.utcnow(),
            "last_activity": datetime.utcnow()
        }
        
        sessions = connection_manager.get_active_sessions()
        assert len(sessions) == 1
        assert "session_1" in sessions
    
    def test_is_session_active(self, connection_manager):
        """Test session activity check."""
        # Add mock connection
        mock_websocket = Mock()
        connection_manager.active_connections["active_session"] = mock_websocket
        
        assert connection_manager.is_session_active("active_session") is True
        assert connection_manager.is_session_active("inactive_session") is False


class TestMessageRouter:
    """Test MessageRouter functionality."""
    
    @pytest.fixture
    def message_router(self):
        """Create MessageRouter instance for testing."""
        return MessageRouter()
    
    @pytest.mark.asyncio
    async def test_register_handler(self, message_router):
        """Test handler registration."""
        async def test_handler(session_id, message):
            return True
        
        message_router.register_handler("test_type", test_handler, MessagePriority.HIGH)
        
        assert "test_type" in message_router.handlers
        assert message_router.handlers["test_type"] == test_handler
        assert "test_type" in message_router.routes
        assert message_router.routes["test_type"].priority == MessagePriority.HIGH
    
    @pytest.mark.asyncio
    async def test_route_message_success(self, message_router):
        """Test successful message routing."""
        # Register test handler
        async def test_handler(session_id, message):
            assert session_id == "test_session"
            assert message.type == "test_type"
            return True
        
        message_router.register_handler("test_type", test_handler)
        
        message = WebSocketMessage(type="test_type", content="test")
        result = await message_router.route_message("test_session", message)
        
        assert result is True
    
    @pytest.mark.asyncio
    async def test_route_message_unknown_type(self, message_router):
        """Test routing unknown message type."""
        with patch('api.message_router.websocket_gateway') as mock_gateway:
            mock_gateway.send_error = AsyncMock()
            
            message = WebSocketMessage(type="unknown_type", content="test")
            result = await message_router.route_message("test_session", message)
            
            assert result is False
            mock_gateway.send_error.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_ping_handler(self, message_router):
        """Test default ping handler."""
        with patch('api.message_router.websocket_gateway') as mock_gateway:
            mock_gateway.send_message = AsyncMock(return_value=True)
            
            message = WebSocketMessage(type="ping", content={})
            result = await message_router.route_message("test_session", message)
            
            assert result is True
            mock_gateway.send_message.assert_called_once()
            
            # Check pong response
            call_args = mock_gateway.send_message.call_args
            assert call_args[0][0] == "test_session"  # session_id
            assert call_args[0][1] == "pong"  # message_type
    
    @pytest.mark.asyncio
    async def test_subscribe_handler(self, message_router):
        """Test subscription handler."""
        with patch('api.message_router.websocket_gateway') as mock_gateway:
            mock_gateway.send_message = AsyncMock(return_value=True)
            
            message = WebSocketMessage(
                type="subscribe", 
                content={"pattern": "test_pattern"}
            )
            result = await message_router.route_message("test_session", message)
            
            assert result is True
            assert "test_pattern" in message_router.subscriptions
            assert "test_session" in message_router.subscriptions["test_pattern"]
    
    @pytest.mark.asyncio
    async def test_broadcast_to_subscribers(self, message_router):
        """Test broadcasting to subscribers."""
        with patch('api.message_router.websocket_gateway') as mock_gateway:
            mock_gateway.send_message = AsyncMock(return_value=True)
            
            # Add subscribers
            message_router.subscriptions["test_pattern"] = {"session_1", "session_2", "session_3"}
            
            broadcast_message = WebSocketMessage(
                type="broadcast",
                content={"message": "test broadcast"}
            )
            
            sent_count = await message_router.broadcast_to_subscribers(
                "test_pattern", 
                broadcast_message, 
                exclude_sessions={"session_1"}
            )
            
            assert sent_count == 2  # Excluded session_1
    
    @pytest.mark.asyncio
    async def test_queue_message(self, message_router):
        """Test message queueing."""
        message = WebSocketMessage(type="test", content="queued message")
        
        await message_router.queue_message("test_session", message)
        
        assert "test_session" in message_router.message_queues
        assert len(message_router.message_queues["test_session"]) == 1
        assert message_router.message_queues["test_session"][0] == message
    
    @pytest.mark.asyncio
    async def test_deliver_queued_messages(self, message_router):
        """Test delivering queued messages."""
        with patch('api.message_router.websocket_gateway') as mock_gateway:
            mock_gateway.send_message = AsyncMock(return_value=True)
            
            # Queue some messages
            messages = [
                WebSocketMessage(type="test", content=f"message_{i}")
                for i in range(3)
            ]
            
            for message in messages:
                await message_router.queue_message("test_session", message)
            
            delivered_count = await message_router.deliver_queued_messages("test_session")
            
            assert delivered_count == 3
            assert "test_session" not in message_router.message_queues  # Queue should be cleared


class TestErrorHandler:
    """Test ErrorHandler functionality."""
    
    @pytest.fixture
    def error_handler(self):
        """Create ErrorHandler instance for testing."""
        return ErrorHandler()
    
    @pytest.mark.asyncio
    async def test_handle_error(self, error_handler):
        """Test error handling."""
        with patch('api.websocket_errors.websocket_gateway') as mock_gateway:
            mock_gateway.connection_manager.is_session_active.return_value = True
            mock_gateway.send_message = AsyncMock()
            
            error = WebSocketError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Test error",
                session_id="test_session"
            )
            
            result = await error_handler.handle_error(error)
            
            assert result is True
            assert "test_session" in error_handler.error_history
            assert len(error_handler.error_history["test_session"]) == 1
    
    @pytest.mark.asyncio
    async def test_rate_limit_check_within_limits(self, error_handler):
        """Test rate limit check within limits."""
        result = await error_handler.check_rate_limit("test_session")
        assert result is True
        
        # Add some messages within limit
        for _ in range(10):
            result = await error_handler.check_rate_limit("test_session")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_rate_limit_check_exceeded(self, error_handler):
        """Test rate limit check when exceeded."""
        # Reduce limits for testing
        error_handler.rate_limit_max_messages = 5
        
        # Add messages up to limit
        for _ in range(5):
            result = await error_handler.check_rate_limit("test_session")
            assert result is True
        
        # Next message should exceed limit
        with patch.object(error_handler, 'handle_error') as mock_handle_error:
            result = await error_handler.check_rate_limit("test_session")
            assert result is False
            mock_handle_error.assert_called_once()
    
    def test_connection_state_management(self, error_handler):
        """Test connection state management."""
        session_id = "test_session"
        
        # Initial state
        state = error_handler.get_connection_state(session_id)
        assert state == ConnectionState.DISCONNECTED
        
        # Set state
        error_handler.set_connection_state(session_id, ConnectionState.CONNECTED)
        state = error_handler.get_connection_state(session_id)
        assert state == ConnectionState.CONNECTED
    
    @pytest.mark.asyncio
    async def test_initiate_reconnection(self, error_handler):
        """Test reconnection initiation."""
        session_id = "test_session"
        
        # Set disconnected state
        error_handler.set_connection_state(session_id, ConnectionState.DISCONNECTED)
        
        result = await error_handler.initiate_reconnection(session_id)
        
        assert result is True
        assert error_handler.get_connection_state(session_id) == ConnectionState.RECONNECTING
        assert session_id in error_handler.reconnection_attempts
        assert error_handler.reconnection_attempts[session_id] == 1
    
    @pytest.mark.asyncio
    async def test_max_reconnection_attempts(self, error_handler):
        """Test maximum reconnection attempts."""
        session_id = "test_session"
        
        # Set max attempts reached
        error_handler.reconnection_attempts[session_id] = error_handler.reconnection_config.max_attempts
        error_handler.set_connection_state(session_id, ConnectionState.DISCONNECTED)
        
        result = await error_handler.initiate_reconnection(session_id)
        
        assert result is False
        assert error_handler.get_connection_state(session_id) == ConnectionState.FAILED
    
    def test_cleanup_session(self, error_handler):
        """Test session cleanup."""
        session_id = "test_session"
        
        # Add some data
        error_handler.set_connection_state(session_id, ConnectionState.CONNECTED)
        error_handler.error_history[session_id] = []
        error_handler.reconnection_attempts[session_id] = 1
        error_handler.rate_limits[session_id] = {"messages": []}
        
        # Cleanup
        error_handler.cleanup_session(session_id)
        
        assert session_id not in error_handler.connection_states
        assert session_id not in error_handler.error_history
        assert session_id not in error_handler.reconnection_attempts
        assert session_id not in error_handler.rate_limits
    
    def test_get_error_stats(self, error_handler):
        """Test error statistics."""
        # Add some test data
        error_handler.error_history["session_1"] = [
            WebSocketError(code=ErrorCode.INTERNAL_ERROR, message="Error 1"),
            WebSocketError(code=ErrorCode.TIMEOUT, message="Error 2")
        ]
        error_handler.error_history["session_2"] = [
            WebSocketError(code=ErrorCode.INTERNAL_ERROR, message="Error 3")
        ]
        
        error_handler.connection_states["session_1"] = ConnectionState.CONNECTED
        error_handler.connection_states["session_2"] = ConnectionState.RECONNECTING
        error_handler.connection_states["session_3"] = ConnectionState.FAILED
        
        stats = error_handler.get_error_stats()
        
        assert stats["total_errors"] == 3
        assert stats["error_counts"][ErrorCode.INTERNAL_ERROR] == 2
        assert stats["error_counts"][ErrorCode.TIMEOUT] == 1
        assert stats["active_sessions"] == 3
        assert stats["reconnecting_sessions"] == 1
        assert stats["failed_sessions"] == 1


class TestWebSocketGateway:
    """Test WebSocketGateway integration."""
    
    @pytest.fixture
    def websocket_gateway_instance(self):
        """Create WebSocketGateway instance for testing."""
        from api.websocket import WebSocketGateway
        return WebSocketGateway()
    
    @pytest.mark.asyncio
    async def test_handle_message_json(self, websocket_gateway_instance):
        """Test handling JSON message."""
        with patch('api.websocket.session_manager') as mock_session_manager:
            mock_session_manager.update_context = AsyncMock(return_value=True)
            
            raw_message = json.dumps({
                "type": "chat",
                "content": "Hello world"
            })
            
            message = await websocket_gateway_instance.handle_message("test_session", raw_message)
            
            assert message is not None
            assert message.type == "chat"
            assert message.content == "Hello world"
            assert message.session_id == "test_session"
    
    @pytest.mark.asyncio
    async def test_handle_message_plain_text(self, websocket_gateway_instance):
        """Test handling plain text message."""
        with patch('api.websocket.session_manager') as mock_session_manager:
            mock_session_manager.update_context = AsyncMock(return_value=True)
            
            raw_message = "Hello world"
            
            message = await websocket_gateway_instance.handle_message("test_session", raw_message)
            
            assert message is not None
            assert message.type == "text"
            assert message.content == "Hello world"
            assert message.session_id == "test_session"
    
    @pytest.mark.asyncio
    async def test_send_message(self, websocket_gateway_instance):
        """Test sending message through gateway."""
        with patch.object(websocket_gateway_instance.connection_manager, 'send_message') as mock_send:
            mock_send.return_value = True
            
            result = await websocket_gateway_instance.send_message(
                "test_session", 
                "response", 
                {"data": "test"}
            )
            
            assert result is True
            mock_send.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_send_error(self, websocket_gateway_instance):
        """Test sending error message."""
        with patch.object(websocket_gateway_instance, 'send_message') as mock_send:
            mock_send.return_value = True
            
            result = await websocket_gateway_instance.send_error(
                "test_session", 
                "Test error", 
                "Error details"
            )
            
            assert result is True
            mock_send.assert_called_once()
            
            # Check error message format
            call_args = mock_send.call_args
            assert call_args[0][1] == "error"  # message_type
            assert "error" in call_args[0][2]  # content
            assert "details" in call_args[0][2]  # content


if __name__ == "__main__":
    pytest.main([__file__])
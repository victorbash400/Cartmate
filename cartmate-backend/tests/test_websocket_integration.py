"""
Integration tests for WebSocket communication infrastructure.
"""

import pytest
import asyncio
import json
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket

from api.websocket import websocket_gateway
from api.message_router import message_router
from api.websocket_errors import error_handler, ConnectionState
from services.storage.session_manager import session_manager
from models.user import Session


class MockWebSocket:
    """Mock WebSocket for testing."""
    
    def __init__(self):
        self.messages_sent = []
        self.closed = False
        self.close_code = None
        
    async def accept(self):
        """Mock accept method."""
        pass
    
    async def send_text(self, data: str):
        """Mock send_text method."""
        if self.closed:
            raise Exception("WebSocket is closed")
        self.messages_sent.append(data)
    
    async def receive_text(self):
        """Mock receive_text method."""
        # This would normally block waiting for messages
        await asyncio.sleep(0.1)
        return "test message"
    
    async def close(self, code: int = 1000):
        """Mock close method."""
        self.closed = True
        self.close_code = code


class TestWebSocketIntegration:
    """Integration tests for WebSocket functionality."""
    
    @pytest.fixture
    async def setup_test_environment(self):
        """Set up test environment."""
        # Clear any existing state
        websocket_gateway.connection_manager.active_connections.clear()
        websocket_gateway.connection_manager.connection_info.clear()
        websocket_gateway.connection_manager.user_sessions.clear()
        
        message_router.subscriptions.clear()
        message_router.message_queues.clear()
        
        error_handler.connection_states.clear()
        error_handler.error_history.clear()
        error_handler.reconnection_attempts.clear()
        error_handler.rate_limits.clear()
        
        yield
        
        # Cleanup after test
        websocket_gateway.connection_manager.active_connections.clear()
        websocket_gateway.connection_manager.connection_info.clear()
        websocket_gateway.connection_manager.user_sessions.clear()
    
    @pytest.mark.asyncio
    async def test_full_connection_lifecycle(self, setup_test_environment):
        """Test complete WebSocket connection lifecycle."""
        mock_websocket = MockWebSocket()
        
        with patch('api.websocket.session_manager') as mock_session_manager:
            # Mock session creation
            mock_session = Session(
                id="integration_test_session",
                user_id="integration_test_user",
                expires_at=datetime.utcnow() + timedelta(hours=1)
            )
            mock_session_manager.get_session.return_value = None
            mock_session_manager.create_session.return_value = mock_session
            mock_session_manager.update_context = AsyncMock(return_value=True)
            
            # 1. Connect
            session_id = await websocket_gateway.handle_connection(
                mock_websocket, 
                user_id="integration_test_user"
            )
            
            assert session_id == "integration_test_session"
            assert len(mock_websocket.messages_sent) == 1  # Connection confirmation
            
            # Verify connection is tracked
            assert websocket_gateway.connection_manager.is_session_active(session_id)
            
            # 2. Send messages
            test_message = "Hello WebSocket!"
            processed_message = await websocket_gateway.handle_message(session_id, test_message)
            
            assert processed_message is not None
            assert processed_message.type == "text"
            assert processed_message.content == test_message
            
            # 3. Route message through router
            ping_message = json.dumps({"type": "ping", "content": {}})
            processed_ping = await websocket_gateway.handle_message(session_id, ping_message)
            
            result = await message_router.route_message(session_id, processed_ping)
            assert result is True
            
            # Should have received pong response
            assert len(mock_websocket.messages_sent) >= 2
            
            # 4. Disconnect
            await websocket_gateway.handle_disconnect(session_id)
            
            assert not websocket_gateway.connection_manager.is_session_active(session_id)
    
    @pytest.mark.asyncio
    async def test_subscription_and_broadcasting(self, setup_test_environment):
        """Test subscription and broadcasting functionality."""
        # Create multiple mock connections
        mock_websockets = [MockWebSocket() for _ in range(3)]
        session_ids = []
        
        with patch('api.websocket.session_manager') as mock_session_manager:
            # Mock sessions
            mock_sessions = [
                Session(
                    id=f"session_{i}",
                    user_id=f"user_{i}",
                    expires_at=datetime.utcnow() + timedelta(hours=1)
                )
                for i in range(3)
            ]
            
            mock_session_manager.get_session.return_value = None
            mock_session_manager.create_session.side_effect = mock_sessions
            mock_session_manager.update_context = AsyncMock(return_value=True)
            
            # Connect all sessions
            for i, websocket in enumerate(mock_websockets):
                session_id = await websocket_gateway.handle_connection(
                    websocket, 
                    user_id=f"user_{i}"
                )
                session_ids.append(session_id)
            
            # Subscribe sessions to a pattern
            for i, session_id in enumerate(session_ids[:2]):  # Only first 2 sessions
                subscribe_message = json.dumps({
                    "type": "subscribe",
                    "content": {"pattern": "test_channel"}
                })
                
                processed_message = await websocket_gateway.handle_message(session_id, subscribe_message)
                await message_router.route_message(session_id, processed_message)
            
            # Verify subscriptions
            assert "test_channel" in message_router.subscriptions
            assert len(message_router.subscriptions["test_channel"]) == 2
            
            # Broadcast message from third session
            broadcast_message = json.dumps({
                "type": "broadcast",
                "content": {
                    "pattern": "test_channel",
                    "message": "Hello subscribers!"
                }
            })
            
            processed_broadcast = await websocket_gateway.handle_message(session_ids[2], broadcast_message)
            await message_router.route_message(session_ids[2], processed_broadcast)
            
            # Verify broadcast was received by subscribers
            # Each subscriber should have: connection_confirmation + subscription_confirmation + broadcast
            for i in range(2):
                assert len(mock_websockets[i].messages_sent) >= 3
            
            # Third session (sender) should have: connection_confirmation + broadcast_sent_confirmation
            assert len(mock_websockets[2].messages_sent) >= 2
    
    @pytest.mark.asyncio
    async def test_error_handling_and_recovery(self, setup_test_environment):
        """Test error handling and recovery mechanisms."""
        mock_websocket = MockWebSocket()
        
        with patch('api.websocket.session_manager') as mock_session_manager:
            mock_session = Session(
                id="error_test_session",
                user_id="error_test_user",
                expires_at=datetime.utcnow() + timedelta(hours=1)
            )
            mock_session_manager.get_session.return_value = None
            mock_session_manager.create_session.return_value = mock_session
            mock_session_manager.update_context = AsyncMock(return_value=True)
            mock_session_manager.extend_session = AsyncMock(return_value=True)
            
            # Connect
            session_id = await websocket_gateway.handle_connection(mock_websocket, user_id="error_test_user")
            
            # Test rate limiting
            error_handler.rate_limit_max_messages = 3  # Reduce for testing
            
            # Send messages up to limit
            for i in range(3):
                result = await error_handler.check_rate_limit(session_id)
                assert result is True
            
            # Next message should trigger rate limit
            result = await error_handler.check_rate_limit(session_id)
            assert result is False
            
            # Verify error was logged
            assert session_id in error_handler.error_history
            assert len(error_handler.error_history[session_id]) > 0
            
            # Test reconnection logic
            error_handler.set_connection_state(session_id, ConnectionState.DISCONNECTED)
            
            reconnection_result = await error_handler.initiate_reconnection(session_id)
            assert reconnection_result is True
            
            # Verify reconnection state
            assert error_handler.get_connection_state(session_id) == ConnectionState.RECONNECTING
            assert session_id in error_handler.reconnection_attempts
    
    @pytest.mark.asyncio
    async def test_message_queueing_and_delivery(self, setup_test_environment):
        """Test message queueing for offline delivery."""
        mock_websocket = MockWebSocket()
        
        with patch('api.websocket.session_manager') as mock_session_manager:
            mock_session = Session(
                id="queue_test_session",
                user_id="queue_test_user",
                expires_at=datetime.utcnow() + timedelta(hours=1)
            )
            mock_session_manager.get_session.return_value = None
            mock_session_manager.create_session.return_value = mock_session
            mock_session_manager.update_context = AsyncMock(return_value=True)
            
            session_id = await websocket_gateway.handle_connection(mock_websocket, user_id="queue_test_user")
            
            # Disconnect to simulate offline state
            await websocket_gateway.handle_disconnect(session_id)
            
            # Queue some messages
            from api.websocket import WebSocketMessage
            
            queued_messages = [
                WebSocketMessage(type="notification", content=f"Message {i}")
                for i in range(3)
            ]
            
            for message in queued_messages:
                await message_router.queue_message(session_id, message)
            
            # Verify messages are queued
            assert session_id in message_router.message_queues
            assert len(message_router.message_queues[session_id]) == 3
            
            # Reconnect
            mock_websocket_new = MockWebSocket()
            new_session_id = await websocket_gateway.handle_connection(
                mock_websocket_new, 
                session_id=session_id
            )
            
            # Deliver queued messages
            delivered_count = await message_router.deliver_queued_messages(session_id)
            
            assert delivered_count == 3
            # Should have connection confirmation + 3 queued messages
            assert len(mock_websocket_new.messages_sent) >= 4
    
    @pytest.mark.asyncio
    async def test_session_context_management(self, setup_test_environment):
        """Test session context management across messages."""
        mock_websocket = MockWebSocket()
        
        with patch('api.websocket.session_manager') as mock_session_manager:
            mock_session = Session(
                id="context_test_session",
                user_id="context_test_user",
                expires_at=datetime.utcnow() + timedelta(hours=1),
                context={}
            )
            mock_session_manager.get_session.return_value = None
            mock_session_manager.create_session.return_value = mock_session
            
            # Track context updates
            context_updates = []
            
            async def mock_update_context(session_id, context):
                context_updates.append((session_id, context))
                return True
            
            mock_session_manager.update_context = mock_update_context
            
            session_id = await websocket_gateway.handle_connection(mock_websocket, user_id="context_test_user")
            
            # Send multiple messages
            messages = [
                "First message",
                json.dumps({"type": "chat", "content": "Second message"}),
                "Third message"
            ]
            
            for message in messages:
                await websocket_gateway.handle_message(session_id, message)
            
            # Verify context was updated for each message
            assert len(context_updates) == len(messages)
            
            for i, (updated_session_id, context) in enumerate(context_updates):
                assert updated_session_id == session_id
                assert "last_message" in context
                assert "last_activity" in context
    
    @pytest.mark.asyncio
    async def test_concurrent_connections(self, setup_test_environment):
        """Test handling multiple concurrent connections."""
        num_connections = 10
        mock_websockets = [MockWebSocket() for _ in range(num_connections)]
        session_ids = []
        
        with patch('api.websocket.session_manager') as mock_session_manager:
            # Mock sessions
            mock_sessions = [
                Session(
                    id=f"concurrent_session_{i}",
                    user_id=f"concurrent_user_{i}",
                    expires_at=datetime.utcnow() + timedelta(hours=1)
                )
                for i in range(num_connections)
            ]
            
            mock_session_manager.get_session.return_value = None
            mock_session_manager.create_session.side_effect = mock_sessions
            mock_session_manager.update_context = AsyncMock(return_value=True)
            
            # Connect all sessions concurrently
            connection_tasks = [
                websocket_gateway.handle_connection(websocket, user_id=f"concurrent_user_{i}")
                for i, websocket in enumerate(mock_websockets)
            ]
            
            session_ids = await asyncio.gather(*connection_tasks)
            
            # Verify all connections were established
            assert len(session_ids) == num_connections
            assert len(set(session_ids)) == num_connections  # All unique
            
            # Verify all are tracked
            for session_id in session_ids:
                assert websocket_gateway.connection_manager.is_session_active(session_id)
            
            # Send messages from all sessions concurrently
            message_tasks = [
                websocket_gateway.handle_message(session_id, f"Message from {session_id}")
                for session_id in session_ids
            ]
            
            processed_messages = await asyncio.gather(*message_tasks)
            
            # Verify all messages were processed
            assert len(processed_messages) == num_connections
            assert all(msg is not None for msg in processed_messages)
            
            # Disconnect all sessions
            disconnect_tasks = [
                websocket_gateway.handle_disconnect(session_id)
                for session_id in session_ids
            ]
            
            await asyncio.gather(*disconnect_tasks)
            
            # Verify all disconnected
            for session_id in session_ids:
                assert not websocket_gateway.connection_manager.is_session_active(session_id)
    
    @pytest.mark.asyncio
    async def test_system_statistics_and_monitoring(self, setup_test_environment):
        """Test system statistics and monitoring capabilities."""
        # Create some test data
        mock_websockets = [MockWebSocket() for _ in range(3)]
        
        with patch('api.websocket.session_manager') as mock_session_manager:
            mock_sessions = [
                Session(
                    id=f"stats_session_{i}",
                    user_id=f"stats_user_{i}",
                    expires_at=datetime.utcnow() + timedelta(hours=1)
                )
                for i in range(3)
            ]
            
            mock_session_manager.get_session.return_value = None
            mock_session_manager.create_session.side_effect = mock_sessions
            mock_session_manager.update_context = AsyncMock(return_value=True)
            mock_session_manager.get_session_stats = AsyncMock(return_value={
                "session_ttl": 3600,
                "cleanup_interval": 300
            })
            
            # Connect sessions
            session_ids = []
            for i, websocket in enumerate(mock_websockets):
                session_id = await websocket_gateway.handle_connection(
                    websocket, 
                    user_id=f"stats_user_{i}"
                )
                session_ids.append(session_id)
            
            # Add some subscriptions
            message_router.subscriptions["channel_1"] = {session_ids[0], session_ids[1]}
            message_router.subscriptions["channel_2"] = {session_ids[2]}
            
            # Add some error history
            from api.websocket_errors import WebSocketError, ErrorCode
            error_handler.error_history[session_ids[0]] = [
                WebSocketError(code=ErrorCode.TIMEOUT, message="Test timeout")
            ]
            
            # Get statistics
            connection_stats = websocket_gateway.connection_manager.get_active_sessions()
            router_stats = message_router.get_router_stats()
            error_stats = error_handler.get_error_stats()
            
            # Verify statistics
            assert len(connection_stats) == 3
            assert router_stats["active_subscriptions"] == 2
            assert router_stats["registered_handlers"] > 0
            assert error_stats["total_errors"] == 1
            assert error_stats["active_sessions"] == 1  # Only session with errors


if __name__ == "__main__":
    pytest.main([__file__])
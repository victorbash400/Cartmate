import logging
import json
from typing import Dict, Callable, Optional, Set
from services.storage.redis_client import redis_client
from models.a2a import A2AMessage, A2AMessageType
import asyncio

logger = logging.getLogger(__name__)

class A2AMessageBus:
    """Enhanced A2A message bus with routing capabilities"""
    
    def __init__(self):
        self.CHANNEL_NAME = "a2a_messages"
        self.direct_channels: Dict[str, asyncio.Queue] = {}  # agent_id -> message queue
        self.global_listeners: Dict[str, Callable] = {}  # listener_id -> callback
        self.message_handlers: Dict[str, Callable] = {}  # message_type -> handler
        self.frontend_subscribers: Set[Callable] = set()  # callback functions for frontend subscribers

    async def publish(self, message: str):
        """
        Publishes a message to the agent-to-agent chat channel.
        """
        logger.info(f"Publishing to A2A bus: {message}")
        await redis_client.publish(self.CHANNEL_NAME, message)

    async def subscribe(self):
        """
        Subscribes to the agent-to-agent chat channel.
        """
        return await redis_client.subscribe(self.CHANNEL_NAME)
    
    async def send_direct_message(self, agent_id: str, message: A2AMessage) -> bool:
        """
        Send a message directly to a specific agent.
        
        Args:
            agent_id: Target agent ID
            message: Message to send
            
        Returns:
            bool: True if message was sent successfully
        """
        try:
            message_json = message.model_dump_json()
            
            # Try direct channel first
            if agent_id in self.direct_channels:
                queue = self.direct_channels[agent_id]
                if not queue.full():
                    await queue.put(message_json)
                    logger.debug(f"Sent direct message to {agent_id}")
                    # Also forward to frontend subscribers for visibility
                    await self._forward_to_frontend(message)
                    return True
            
            # Fallback to Redis pub/sub
            channel = f"a2a:agent:{agent_id}"
            await redis_client.publish(channel, message_json)
            logger.debug(f"Sent message to {agent_id} via Redis")
            # Also forward to frontend subscribers for visibility
            await self._forward_to_frontend(message)
            return True
            
        except Exception as e:
            logger.error(f"Error sending direct message to {agent_id}: {e}")
            return False
    
    async def listen_for_agent(self, agent_id: str) -> asyncio.Queue:
        """
        Create a direct listening channel for an agent.
        
        Args:
            agent_id: Agent ID to listen for
            
        Returns:
            asyncio.Queue: Message queue for the agent
        """
        if agent_id not in self.direct_channels:
            self.direct_channels[agent_id] = asyncio.Queue(maxsize=100)
        return self.direct_channels[agent_id]
    
    def register_global_listener(self, listener_id: str, callback: Callable):
        """
        Register a global listener for all messages.
        
        Args:
            listener_id: Unique listener identifier
            callback: Function to call with message
        """
        self.global_listeners[listener_id] = callback
    
    def unregister_global_listener(self, listener_id: str):
        """
        Unregister a global listener.
        
        Args:
            listener_id: Listener identifier to remove
        """
        if listener_id in self.global_listeners:
            del self.global_listeners[listener_id]
    
    async def broadcast_message(self, message: A2AMessage) -> bool:
        """
        Broadcast a message to all listeners.
        
        Args:
            message: Message to broadcast
            
        Returns:
            bool: True if broadcast was successful
        """
        try:
            message_json = message.model_dump_json()
            
            # Notify global listeners
            for callback in self.global_listeners.values():
                try:
                    await callback(message)
                except Exception as e:
                    logger.error(f"Error in global listener callback: {e}")
            
            # Publish to Redis for external listeners
            await self.publish(message_json)
            
            # Also forward to frontend subscribers for visibility
            await self._forward_to_frontend(message)
            return True
        except Exception as e:
            logger.error(f"Error broadcasting message: {e}")
            return False
    
    def add_frontend_subscriber(self, callback: Callable):
        """
        Add a frontend subscriber callback to receive A2A messages.
        
        Args:
            callback: Function to call with message data for frontend
        """
        self.frontend_subscribers.add(callback)
        logger.debug(f"Added frontend subscriber. Total subscribers: {len(self.frontend_subscribers)}")
    
    def remove_frontend_subscriber(self, callback: Callable):
        """
        Remove a frontend subscriber callback.
        
        Args:
            callback: Function to remove from subscribers
        """
        self.frontend_subscribers.discard(callback)
        logger.debug(f"Removed frontend subscriber. Total subscribers: {len(self.frontend_subscribers)}")
    
    async def _forward_to_frontend(self, message: A2AMessage):
        """
        Forward A2A messages to frontend subscribers for real-time visibility.
        
        Args:
            message: A2A message to forward
        """
        if not self.frontend_subscribers:
            return
            
        try:
            # Filter to only forward frontend notification messages
            if message.type == A2AMessageType.FRONTEND_NOTIFICATION:
                message_dict = message.model_dump()
                logger.debug(f"Forwarding frontend notification to {len(self.frontend_subscribers)} subscribers")
                
                # Notify all frontend subscribers
                for callback in self.frontend_subscribers.copy():
                    try:
                        await callback(message_dict)
                    except Exception as e:
                        logger.error(f"Error forwarding message to frontend subscriber: {e}")
                        # Remove broken callbacks
                        self.frontend_subscribers.discard(callback)
        except Exception as e:
            logger.error(f"Error forwarding message to frontend: {e}")

# Singleton instance
a2a_message_bus = A2AMessageBus()

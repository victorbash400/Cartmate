import logging
import asyncio
import uuid
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod
from models.a2a import A2AMessage, A2ARequest, A2AResponse, A2AMessageType, A2ARequestType, A2ARegistration, A2AAcknowledgment, A2AFrontendNotification
from a2a.message_bus import a2a_message_bus
from a2a.coordinator import a2a_coordinator

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """Base class for all A2A agents"""
    
    def __init__(self, agent_id: str, agent_type: str):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.message_queue: Optional[asyncio.Queue] = None
        self.is_running = False
        self.registration = A2ARegistration(
            agent_id=agent_id,
            agent_type=agent_type,
            capabilities=[]
        )
        self.pending_acks = {}  # message_id -> ack info
        self.message_timeouts = {}  # message_id -> timeout task
        self.retry_attempts = {}  # message_id -> retry count
        self.max_retries = 3
    
    async def start(self):
        """Start the agent and begin listening for messages"""
        # Register with coordinator
        await a2a_coordinator.register_agent(self.registration)
        
        # Set up message listening
        self.message_queue = await a2a_message_bus.listen_for_agent(self.agent_id)
        self.is_running = True
        
        # Start message processing loop
        asyncio.create_task(self._process_messages())
        
        logger.info(f"Agent {self.agent_id} started")
    
    async def stop(self):
        """Stop the agent"""
        self.is_running = False
        
        # Cancel any pending timeouts
        for task in self.message_timeouts.values():
            if not task.done():
                task.cancel()
        
        # Deregister from coordinator
        await a2a_coordinator.deregister_agent(self.agent_id)
        
        logger.info(f"Agent {self.agent_id} stopped")
    
    def _deserialize_message(self, message_json: str) -> A2AMessage:
        """
        Deserialize a message JSON to the appropriate A2A message type.
        
        Args:
            message_json: JSON string of the message
            
        Returns:
            A2AMessage: Deserialized message of the correct type
        """
        import json
        try:
            # Parse JSON to get message type
            message_dict = json.loads(message_json)
            message_type = message_dict.get('type')
            
            # Deserialize to the appropriate type based on message type
            if message_type == A2AMessageType.REQUEST:
                return A2ARequest.model_validate(message_dict)
            elif message_type == A2AMessageType.RESPONSE:
                return A2AResponse.model_validate(message_dict)
            elif message_type == A2AMessageType.ACK:
                return A2AAcknowledgment.model_validate(message_dict)
            elif message_type == A2AMessageType.FRONTEND_NOTIFICATION:
                return A2AFrontendNotification.model_validate(message_dict)
            else:
                # Fallback to base message type
                return A2AMessage.model_validate(message_dict)
        except Exception as e:
            logger.error(f"Error deserializing message: {e}")
            # Fallback to base message type
            return A2AMessage.model_validate_json(message_json)
    
    async def _process_messages(self):
        """Process incoming messages"""
        while self.is_running:
            try:
                if self.message_queue and not self.message_queue.empty():
                    message_json = await self.message_queue.get()
                    message = self._deserialize_message(message_json)
                    
                    # Send acknowledgment if required
                    if message.requires_ack:
                        await self._send_acknowledgment(message)
                    
                    # Process the message
                    await self.handle_message(message)
                else:
                    await asyncio.sleep(0.1)  # Prevent busy waiting
            except Exception as e:
                logger.error(f"Error processing message in agent {self.agent_id}: {e}")
    
    async def _send_acknowledgment(self, message: A2AMessage) -> bool:
        """
        Send acknowledgment for a message that requires it.
        
        Args:
            message: Message to acknowledge
            
        Returns:
            bool: True if acknowledgment was sent successfully
        """
        try:
            ack = A2AAcknowledgment(
                sender=self.agent_id,
                receiver=message.sender,
                ack_for_message_id=message.id,
                success=True
            )
            
            return await self.send_message(message.sender, ack)
        except Exception as e:
            logger.error(f"Error sending acknowledgment for message {message.id}: {e}")
            return False
    
    async def send_message(self, receiver_id: str, message: A2AMessage) -> bool:
        """
        Send a message to another agent with error handling and retries.
        
        Args:
            receiver_id: ID of the receiving agent
            message: Message to send
            
        Returns:
            bool: True if message was sent successfully
        """
        attempt = 0
        while attempt <= self.max_retries:
            try:
                message.sender = self.agent_id
                success = await a2a_message_bus.send_direct_message(receiver_id, message)
                
                if success:
                    # If acknowledgment is required, set up timeout
                    if message.requires_ack:
                        self._setup_ack_timeout(message)
                    return True
                else:
                    logger.warning(f"Failed to send message to {receiver_id}, attempt {attempt + 1}")
                    
            except Exception as e:
                logger.error(f"Error sending message to {receiver_id}, attempt {attempt + 1}: {e}")
            
            attempt += 1
            if attempt <= self.max_retries:
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
        
        logger.error(f"Failed to send message to {receiver_id} after {self.max_retries} retries")
        return False
    
    def _setup_ack_timeout(self, message: A2AMessage):
        """
        Set up timeout for message acknowledgment.
        
        Args:
            message: Message to wait for acknowledgment
        """
        async def _timeout_handler():
            await asyncio.sleep(30)  # 30 second timeout
            if message.id in self.pending_acks:
                logger.warning(f"Timeout waiting for acknowledgment of message {message.id}")
                
                # Check if we should retry
                retry_count = self.retry_attempts.get(message.id, 0)
                if retry_count < self.max_retries:
                    logger.info(f"Retrying message {message.id}, attempt {retry_count + 1}")
                    self.retry_attempts[message.id] = retry_count + 1
                    
                    # Resend the message
                    await self.send_message(message.receiver, message)
                else:
                    logger.error(f"Max retries exceeded for message {message.id}")
                    # Handle failure - could notify orchestrator or log error
                    await self._handle_message_failure(message)
                
                # Clean up
                if message.id in self.pending_acks:
                    del self.pending_acks[message.id]
                if message.id in self.message_timeouts:
                    del self.message_timeouts[message.id]
        
        # Store the timeout task
        self.message_timeouts[message.id] = asyncio.create_task(_timeout_handler())
        self.pending_acks[message.id] = {
            "message": message,
            "timeout_task": self.message_timeouts[message.id]
        }
    
    async def _handle_message_failure(self, message: A2AMessage):
        """
        Handle message sending failure.
        
        Args:
            message: Failed message
        """
        try:
            # Log the failure
            logger.error(f"Message delivery failed: {message.type} from {message.sender} to {message.receiver}")
            
            # Send error notification to sender if it's a response
            if message.type == A2AMessageType.RESPONSE:
                error_notification = A2AMessage(
                    type=A2AMessageType.ERROR,
                    sender=self.agent_id,
                    receiver=message.sender,
                    content=f"Failed to deliver response to {message.receiver}"
                )
                await self.send_message(message.sender, error_notification)
            
            # For requests, we might want to notify the orchestrator
            elif message.type == A2AMessageType.REQUEST:
                # This would depend on your error handling strategy
                pass
                
        except Exception as e:
            logger.error(f"Error handling message failure: {e}")
    
    async def send_request(self, receiver_id: str, request_type: A2ARequestType, 
                          content: Dict[str, Any], conversation_id: Optional[str] = None) -> bool:
        """
        Send a request to another agent.
        
        Args:
            receiver_id: ID of the receiving agent
            request_type: Type of request
            content: Request content
            conversation_id: Optional conversation ID
            
        Returns:
            bool: True if request was sent successfully
        """
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
            
        request = A2ARequest(
            sender=self.agent_id,
            receiver=receiver_id,
            request_type=request_type,
            conversation_id=conversation_id,
            content=content,
            requires_ack=True
        )
        
        return await self.send_message(receiver_id, request)
    
    async def send_response(self, receiver_id: str, request_id: str, content: Any, 
                           success: bool = True, error: Optional[str] = None,
                           conversation_id: Optional[str] = None) -> bool:
        """
        Send a response to another agent.
        
        Args:
            receiver_id: ID of the receiving agent
            request_id: ID of the request being responded to
            content: Response content
            success: Whether the request was successful
            error: Error message if request failed
            conversation_id: Optional conversation ID
            
        Returns:
            bool: True if response was sent successfully
        """
        response = A2AResponse(
            sender=self.agent_id,
            receiver=receiver_id,
            request_id=request_id,
            conversation_id=conversation_id or str(uuid.uuid4()),
            success=success,
            content=content,
            error=error
        )
        
        return await self.send_message(receiver_id, response)
    
    async def broadcast_message(self, message: A2AMessage) -> bool:
        """
        Broadcast a message to all agents.
        
        Args:
            message: Message to broadcast
            
        Returns:
            bool: True if broadcast was successful
        """
        message.sender = self.agent_id
        return await a2a_message_bus.broadcast_message(message)
    
    async def handle_message(self, message: A2AMessage) -> bool:
        """
        Handle an incoming message.
        
        Args:
            message: Message to handle
            
        Returns:
            bool: True if message was handled successfully
        """
        try:
            # Handle acknowledgment messages
            if message.type == A2AMessageType.ACK:
                ack = A2AAcknowledgment.model_validate(message.model_dump())
                return await self._handle_acknowledgment(ack)
            
            # Handle other message types
            if message.type == A2AMessageType.REQUEST:
                request = A2ARequest.model_validate(message.model_dump())
                return await self.handle_request(request)
            elif message.type == A2AMessageType.RESPONSE:
                response = A2AResponse.model_validate(message.model_dump())
                return await self.handle_response(response)
            elif message.type == A2AMessageType.ERROR:
                logger.error(f"Received error message from {message.sender}: {message.content}")
                return True
            else:
                # Handle notification, error, etc.
                logger.info(f"Agent {self.agent_id} received {message.type} message: {message.content}")
                return True
        except Exception as e:
            logger.error(f"Error handling message in agent {self.agent_id}: {e}")
            return False
    
    async def _handle_acknowledgment(self, ack: A2AAcknowledgment) -> bool:
        """
        Handle an incoming acknowledgment.
        
        Args:
            ack: Acknowledgment to handle
            
        Returns:
            bool: True if acknowledgment was handled successfully
        """
        try:
            if ack.ack_for_message_id in self.pending_acks:
                # Cancel the timeout task
                timeout_task = self.pending_acks[ack.ack_for_message_id]["timeout_task"]
                if not timeout_task.done():
                    timeout_task.cancel()
                
                # Remove from pending acks
                del self.pending_acks[ack.ack_for_message_id]
                
                if ack.ack_for_message_id in self.message_timeouts:
                    del self.message_timeouts[ack.ack_for_message_id]
                
                if ack.ack_for_message_id in self.retry_attempts:
                    del self.retry_attempts[ack.ack_for_message_id]
                
                logger.debug(f"Received acknowledgment for message {ack.ack_for_message_id}")
                return True
            else:
                logger.warning(f"Received unexpected acknowledgment for message {ack.ack_for_message_id}")
                return False
        except Exception as e:
            logger.error(f"Error handling acknowledgment: {e}")
            return False
    
    async def handle_request(self, request: A2ARequest) -> bool:
        """
        Handle an incoming request.
        
        Args:
            request: Request to handle
            
        Returns:
            bool: True if request was handled successfully
        """
        # Default implementation - override in subclasses
        logger.warning(f"Agent {self.agent_id} received unhandled request type: {request.request_type}")
        return False
    
    async def handle_response(self, response: A2AResponse) -> bool:
        """
        Handle an incoming response.
        
        Args:
            response: Response to handle
            
        Returns:
            bool: True if response was handled successfully
        """
        # Default implementation - override in subclasses
        logger.info(f"Agent {self.agent_id} received response for request {response.request_id}")
        return True
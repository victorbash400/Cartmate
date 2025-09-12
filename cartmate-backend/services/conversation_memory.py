"""
Conversation Memory Service - Handles storage and retrieval of conversation history
"""
import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from services.storage.redis_client import redis_client

logger = logging.getLogger(__name__)

class ConversationMemoryService:
    """
    Service for managing conversation history and context.
    Stores full chat history in Redis for better intent analysis and context awareness.
    """
    
    def __init__(self):
        self.max_history_length = 50  # Keep last 50 messages
        self.max_context_length = 20  # Use last 20 messages for context
    
    async def store_message(self, session_id: str, message_type: str, content: str, 
                          sender: str = "user", metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Store a message in the conversation history.
        
        Args:
            session_id: Session identifier
            message_type: Type of message (text, product_search, price_comparison, etc.)
            content: Message content
            sender: Who sent the message (user, assistant, agent)
            metadata: Additional metadata about the message
            
        Returns:
            True if successful, False otherwise
        """
        try:
            key = f"conversation:{session_id}"
            
            # Get existing conversation history
            conversation_history = await self.get_conversation_history(session_id)
            
            # Create new message entry
            message_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "message_type": message_type,
                "content": content,
                "sender": sender,
                "metadata": metadata or {}
            }
            
            # Add to history
            conversation_history.append(message_entry)
            
            # Trim to max length
            if len(conversation_history) > self.max_history_length:
                conversation_history = conversation_history[-self.max_history_length:]
            
            # Store back to Redis
            data = json.dumps(conversation_history)
            await redis_client.set(key, data)
            
            logger.info(f"ConversationMemory stored {sender} message in conversation history for session {session_id}. Total messages: {len(conversation_history)}")
            return True
            
        except Exception as e:
            logger.error(f"ConversationMemoryService error storing message for session {session_id}: {e}")
            return False
    
    async def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get the full conversation history for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of conversation messages
        """
        try:
            key = f"conversation:{session_id}"
            data = await redis_client.get(key)
            
            if data:
                conversation_history = json.loads(data)
                logger.info(f"ConversationMemory retrieved {len(conversation_history)} messages from conversation history for session {session_id}")
                return conversation_history
            else:
                logger.info(f"ConversationMemory no conversation history found for session {session_id}")
                return []
                
        except Exception as e:
            logger.error(f"ConversationMemoryService error retrieving conversation history for session {session_id}: {e}")
            return []
    
    async def get_conversation_context(self, session_id: str) -> str:
        """
        Get formatted conversation context for AI prompts.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Formatted string with recent conversation context
        """
        try:
            conversation_history = await self.get_conversation_history(session_id)
            
            if not conversation_history:
                return ""
            
            # Get recent messages for context
            recent_messages = conversation_history[-self.max_context_length:]
            
            context_lines = []
            for msg in recent_messages:
                timestamp = msg.get('timestamp', '')
                sender = msg.get('sender', 'unknown')
                content = msg.get('content', '')
                message_type = msg.get('message_type', 'text')
                
                # Format timestamp for readability
                if timestamp:
                    try:
                        dt = datetime.fromisoformat(timestamp)
                        time_str = dt.strftime("%H:%M")
                    except:
                        time_str = ""
                else:
                    time_str = ""
                
                # Format message based on type and sender
                if sender == "user":
                    context_lines.append(f"[{time_str}] User: {content}")
                elif sender == "assistant":
                    context_lines.append(f"[{time_str}] Assistant: {content}")
                elif sender == "agent":
                    agent_name = msg.get('metadata', {}).get('agent_name', 'Agent')
                    context_lines.append(f"[{time_str}] {agent_name}: {content}")
            
            if context_lines:
                context = f"""
                
                Recent Conversation History:
                {chr(10).join(context_lines)}
                """
                return context
            
            return ""
                
        except Exception as e:
            logger.error(f"ConversationMemoryService error building conversation context for session {session_id}: {e}")
            return ""
    
    async def get_recent_products_from_conversation(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Extract ALL products mentioned in conversation history.
        Order doesn't matter - if user asks about ANY previously shown product, it's not a new search.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of all products from conversation
        """
        try:
            conversation_history = await self.get_conversation_history(session_id)
            all_products = []
            
            # Look for ALL product-related messages in conversation history
            # Order doesn't matter - if user asks about ANY previously shown product, it's not a new search
            for msg in conversation_history:
                if msg.get('message_type') == 'product_search' and msg.get('sender') == 'agent':
                    metadata = msg.get('metadata', {})
                    products = metadata.get('products', [])
                    if products:
                        all_products.extend(products)
            
            # Remove duplicates while preserving order
            seen = set()
            unique_products = []
            for product in all_products:
                product_id = product.get('id')
                if product_id and product_id not in seen:
                    seen.add(product_id)
                    unique_products.append(product)
            
            logger.info(f"ConversationMemory extracted {len(unique_products)} total products from conversation for session {session_id}: {[p.get('name') for p in unique_products]}")
            return unique_products
                
        except Exception as e:
            logger.error(f"ConversationMemoryService error extracting recent products for session {session_id}: {e}")
            return []
    
    async def clear_conversation_history(self, session_id: str) -> bool:
        """
        Clear conversation history for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if successful, False otherwise
        """
        try:
            key = f"conversation:{session_id}"
            await redis_client.delete(key)
            logger.info(f"Cleared conversation history for session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"ConversationMemoryService error clearing conversation history for session {session_id}: {e}")
            return False
    
    def build_intent_analysis_context(self, conversation_history: List[Dict[str, Any]], 
                                    recent_products: List[Dict[str, Any]]) -> str:
        """
        Build context string specifically for intent analysis.
        
        Args:
            conversation_history: List of conversation messages
            recent_products: List of recent products
            
        Returns:
            Formatted context string for intent analysis
        """
        try:
            context_parts = []
            
            # Add recent conversation context
            if conversation_history:
                recent_messages = conversation_history[-3:]  # Last 3 messages for clarity
                conversation_context = []
                for msg in recent_messages:
                    sender = msg.get('sender', 'unknown')
                    content = msg.get('content', '')
                    if sender == 'user':
                        conversation_context.append(f"User: {content}")
                    elif sender == 'assistant':
                        conversation_context.append(f"Assistant: {content}")
                    elif sender == 'agent':
                        agent_name = msg.get('metadata', {}).get('agent_name', 'Agent')
                        conversation_context.append(f"{agent_name}: {content}")
                
                if conversation_context:
                    context_parts.append(f"Recent conversation:\n{chr(10).join(conversation_context)}")
            
            # Add recent products context with clear formatting
            if recent_products:
                products_list = [p.get('name', '') for p in recent_products]  # Use ALL products, not just last 5
                context_parts.append(f"Recently shown products: {', '.join(products_list)}")
                context_parts.append("IMPORTANT: If user mentions any of these product names, it's NOT a new product search!")
            
            return "\n\n".join(context_parts) if context_parts else ""
                
        except Exception as e:
            logger.error(f"ConversationMemoryService error building intent analysis context: {e}")
            return ""

# Create global instance
conversation_memory = ConversationMemoryService()

import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from models.user import Session, ConversationContext
from services.storage.redis_client import redis_client
from services.conversation_memory import conversation_memory

logger = logging.getLogger(__name__)

class SessionManager:
    def __init__(self):
        self.session_ttl = 3600  # 1 hour default TTL
        
    def _get_session_key(self, session_id: str) -> str:
        """Generate storage key for session."""
        return f"session:{session_id}"
    
    async def create_session(self, user_id: str, session_id: str) -> Session:
        """Create a new session for a user."""
        try:
            expires_at = datetime.utcnow() + timedelta(seconds=self.session_ttl)
            session = Session(
                id=session_id,
                user_id=user_id,
                expires_at=expires_at
            )
            
            # Store in storage
            session_key = self._get_session_key(session_id)
            await redis_client.set(
                session_key, 
                session.model_dump_json(), 
                expire=self.session_ttl
            )
            
            logger.info(f"Created session {session_id} for user {user_id}")
            return session
        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Retrieve a session by ID."""
        try:
            session_key = self._get_session_key(session_id)
            session_data = await redis_client.get(session_key)
            
            if not session_data:
                return None
                
            session_dict = json.loads(session_data)
            # Convert datetime strings back to datetime objects
            session_dict['created_at'] = datetime.fromisoformat(session_dict['created_at'])
            session_dict['expires_at'] = datetime.fromisoformat(session_dict['expires_at'])
            
            return Session(**session_dict)
        except Exception as e:
            logger.error(f"Error retrieving session {session_id}: {e}")
            return None
    
    async def update_context(self, session_id: str, context: Dict[str, Any]) -> bool:
        """Update the conversation context for a session."""
        try:
            session = await self.get_session(session_id)
            if not session:
                return False
                
            # Update context
            session.context.update(context)
            
            # Store updated session
            session_key = self._get_session_key(session_id)
            await redis_client.set(
                session_key, 
                session.model_dump_json(), 
                expire=self.session_ttl
            )
            
            return True
        except Exception as e:
            logger.error(f"Error updating context for session {session_id}: {e}")
            return False
    
    async def reset_session_context(self, session_id: str) -> bool:
        """Reset the conversation context for a session while keeping the session active."""
        try:
            session = await self.get_session(session_id)
            if not session:
                return False
                
            # Reset context to empty state
            session.context = {}
            
            # Clear conversation memory
            await conversation_memory.clear_conversation_history(session_id)
            
            # Store updated session
            session_key = self._get_session_key(session_id)
            await redis_client.set(
                session_key, 
                session.model_dump_json(), 
                expire=self.session_ttl
            )
            
            logger.info(f"Reset context and conversation history for session {session_id}")
            return True
        except Exception as e:
            logger.error(f"Error resetting context for session {session_id}: {e}")
            return False
    
    async def cleanup_expired_sessions(self) -> int:
        """Clean up expired sessions (handled automatically by storage)."""
        # This is handled by storage expiry, but we can add additional cleanup logic here if needed
        return 0

# Global session manager instance
session_manager = SessionManager()
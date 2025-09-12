"""
Personalization Service - Handles user personalization data and context
"""
import logging
import json
from typing import Dict, Any, Optional
from services.storage.redis_client import redis_client

logger = logging.getLogger(__name__)

class PersonalizationService:
    """
    Service for managing user personalization data and context.
    Handles retrieval and storage of user preferences, style analysis, etc.
    """
    
    def __init__(self):
        pass

    async def get_personalization_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get personalization data for a session from Redis.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dict with personalization data or None if not found
        """
        try:
            key = f"personalization:{session_id}"
            data = await redis_client.get(key)
            
            if data:
                personalization_data = json.loads(data)
                logger.info(f"PersonalizationService retrieved personalization data for session {session_id}")
                return personalization_data
            else:
                logger.info(f"PersonalizationService no personalization data found for session {session_id}")
                return None
                
        except Exception as e:
            logger.error(f"PersonalizationService error retrieving personalization data for session {session_id}: {e}")
            return None

    async def store_personalization_context(self, session_id: str, personalization_data: Dict[str, Any]) -> bool:
        """
        Store personalization data for a session in Redis.
        
        Args:
            session_id: Session identifier
            personalization_data: Personalization data to store
            
        Returns:
            True if successful, False otherwise
        """
        try:
            key = f"personalization:{session_id}"
            data = json.dumps(personalization_data)
            await redis_client.set(key, data)
            logger.info(f"PersonalizationService stored personalization data for session {session_id}")
            return True
                
        except Exception as e:
            logger.error(f"PersonalizationService error storing personalization data for session {session_id}: {e}")
            return False

    def build_personalization_context_string(self, personalization_context: Optional[Dict[str, Any]]) -> str:
        """
        Build a formatted string from personalization context for use in AI prompts.
        
        Args:
            personalization_context: Personalization data
            
        Returns:
            Formatted string for AI prompts
        """
        if not personalization_context:
            return ""
        
        try:
            style_prefs = personalization_context.get('style_preferences', '')
            budget_range = personalization_context.get('budget_range', {})
            image_analysis = personalization_context.get('image_analysis', {})
            
            context_info = f"""
            
            User's Personalization Context:
            - Style Preferences: {style_prefs if style_prefs else 'Not specified'}
            - Budget Range: ${budget_range.get('min', 'N/A')} - ${budget_range.get('max', 'N/A')}
            - Image Analysis: {image_analysis}
            """
            
            return context_info
                
        except Exception as e:
            logger.error(f"PersonalizationService error building context string: {e}")
            return ""

    def build_recent_products_context_string(self, recent_products: list) -> str:
        """
        Build a formatted string from recent products for use in AI prompts.
        
        Args:
            recent_products: List of recent products
            
        Returns:
            Formatted string for AI prompts
        """
        if not recent_products:
            return ""
        
        try:
            products_list = []
            for product in recent_products[-5:]:  # Last 5 products
                name = product.get('name', 'Unknown')
                price = product.get('priceUsd', {})
                if isinstance(price, dict):
                    price_str = f"${price.get('units', 0)}.{str(price.get('nanos', 0))[:2]}"
                else:
                    price_str = str(price)
                products_list.append(f"- {name}: {price_str}")
            
            recent_products_info = f"""
            
            Recently Shown Products (user may refer to these):
            {chr(10).join(products_list)}
            """
            
            return recent_products_info
                
        except Exception as e:
            logger.error(f"PersonalizationService error building recent products context string: {e}")
            return ""

# Create global instance
personalization_service = PersonalizationService()

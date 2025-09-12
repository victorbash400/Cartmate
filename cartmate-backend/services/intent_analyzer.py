"""
Intent Analyzer Service - AI-powered intent analysis for user messages
"""
import logging
import asyncio
import json
from typing import Dict, Any, Optional, List
from google.cloud import aiplatform
from google.oauth2 import service_account
import vertexai
from vertexai.preview.generative_models import GenerativeModel
from services.conversation_memory import conversation_memory

logger = logging.getLogger(__name__)

class IntentAnalyzer:
    """
    Service for analyzing user intent using Gemini AI.
    Determines which agents should be involved based on user messages.
    """
    
    def __init__(self):
        self.chat_model = None
        self._initialize_vertex_ai()
    
    def _initialize_vertex_ai(self):
        """Initialize Vertex AI connection"""
        try:
            # Configure the project and location
            project_id = "imposing-kite-461508-v4"
            location = "us-central1"
            
            # Path to your service account key file
            key_path = "C:\\Users\\Victo\\Desktop\\CartMate\\cartmate-backend\\imposing-kite-461508-v4-71f861a0eecc.json"
            
            # Authenticate using the service account key
            credentials = service_account.Credentials.from_service_account_file(key_path)
            
            # Initialize Vertex AI
            vertexai.init(project=project_id, location=location, credentials=credentials)
            
            # Load the generative model
            self.chat_model = GenerativeModel("gemini-2.5-flash")
            
            logger.info("IntentAnalyzer Vertex AI initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing IntentAnalyzer Vertex AI: {e}")
            raise

    async def analyze_intent(self, message: str, session_id: str, recent_products: Optional[list] = None) -> Dict[str, Any]:
        """
        Analyze user intent to determine which agents to involve.
        Now uses full conversation history for better context awareness.
        
        Args:
            message: User's message
            session_id: Session identifier
            recent_products: List of recently shown products (optional, deprecated - will be extracted from conversation)
            
        Returns:
            Dict with intent analysis results
        """
        try:
            # Get conversation history and recent products from conversation memory
            conversation_history = await conversation_memory.get_conversation_history(session_id)
            recent_products_from_conversation = await conversation_memory.get_recent_products_from_conversation(session_id)
            
            # Debug logging
            logger.info(f"IntentAnalyzer conversation history length: {len(conversation_history)}")
            logger.info(f"IntentAnalyzer recent products from conversation: {len(recent_products_from_conversation)}")
            
            # Use products from conversation memory if available, otherwise fall back to provided recent_products
            if recent_products_from_conversation:
                recent_products = recent_products_from_conversation
                logger.info(f"IntentAnalyzer using products from conversation memory: {[p.get('name') for p in recent_products]}")
            elif not recent_products:
                recent_products = []
                logger.info("IntentAnalyzer no recent products available")
            
            # Build comprehensive context for intent analysis
            conversation_context = conversation_memory.build_intent_analysis_context(conversation_history, recent_products)
            logger.info(f"IntentAnalyzer conversation context length: {len(conversation_context)}")
            logger.info(f"IntentAnalyzer conversation context: {conversation_context}")
            
            analysis_prompt = f"""
            You are an intent analyzer for a shopping assistant. Analyze this user message: "{message}"
            
            {conversation_context}
            
            CRITICAL RULES - Follow these exactly:
            1. If the user mentions ANY product name that appears in the "Recently shown products" list, this is NOT a new product search
            2. If user asks about price, deals, value, comparison, or "good deal" for products already shown, this is PRICE COMPARISON
            3. Only classify as product_search for completely NEW product searches
            
            Respond with JSON only:
            {{
                "needs_product_search": boolean,
                "needs_price_comparison": boolean,
                "needs_cart_management": boolean,
                "needs_checkout": boolean,
                "search_query": "extracted product search terms if needed",
                "intent_type": "conversation|product_search|price_comparison|cart_management|checkout",
                "confidence": 0.0-1.0,
                "checkout_data": {{
                    "email": "extracted email if provided",
                    "address": "extracted address if provided", 
                    "payment_info": "extracted payment details if provided"
                }}
            }}
            
            SPECIFIC EXAMPLES:
            - "are the loafers a good deal?" + recent products: [loafers, sunglasses] → needs_product_search: false, needs_price_comparison: true
            - "what's the price of the watch?" + recent products: [watch, sunglasses] → needs_product_search: false, needs_price_comparison: true
            - "show me shoes" (no recent products) → needs_product_search: true, needs_price_comparison: false
            - "find cameras" (no recent products) → needs_product_search: true, needs_price_comparison: false
            - "add the loafers to cart" + recent products: [loafers] → needs_product_search: false, needs_cart_management: true
            - "checkout" → needs_checkout: true, checkout_data: {{"email": null, "address": null, "payment_info": null}}
            - "victorbash400@outlook.com, address is juja,kiambu and use any random payment detail" → needs_checkout: true, checkout_data: {{"email": "victorbash400@outlook.com", "address": "juja,kiambu", "payment_info": "any random payment detail"}}
            """
            
            # Use Gemini AI for analysis with retry logic
            max_retries = 2
            response = None
            
            for attempt in range(max_retries):
                try:
                    temp_session = self.chat_model.start_chat()
                    response = temp_session.send_message(analysis_prompt)
                    break  # Success, exit retry loop
                except Exception as e:
                    logger.warning(f"IntentAnalyzer Vertex AI attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        # Last attempt failed, will use fallback
                        raise e
                    # Wait before retry
                    await asyncio.sleep(1)
            
            # Try to parse JSON response
            try:
                response_text = response.text.strip()
                logger.info(f"IntentAnalyzer AI raw response: {response_text}")
                
                # Extract JSON if it's wrapped in markdown code blocks
                if "```json" in response_text:
                    start = response_text.find("```json") + 7
                    end = response_text.find("```", start)
                    response_text = response_text[start:end].strip()
                elif "```" in response_text:
                    start = response_text.find("```") + 3
                    end = response_text.find("```", start)
                    response_text = response_text[start:end].strip()
                
                # Try to find JSON object in the response
                if "{" in response_text and "}" in response_text:
                    start = response_text.find("{")
                    end = response_text.rfind("}") + 1
                    response_text = response_text[start:end]
                
                intent_data = json.loads(response_text)
                logger.info(f"IntentAnalyzer successfully parsed AI analysis: {intent_data}")
            except Exception as e:
                logger.error(f"IntentAnalyzer failed to parse AI analysis: {e}")
                logger.error(f"Raw response was: {response.text}")
                
                # Simple fallback logic
                message_lower = message.lower()
                needs_search = any(keyword in message_lower for keyword in ["show me", "find", "search", "products", "browse"])
                needs_price_comparison = any(keyword in message_lower for keyword in ["compare", "price", "deal"])
                needs_cart_management = any(keyword in message_lower for keyword in ["add to cart", "add these", "put in cart", "add them", "add it"])
                needs_checkout = any(keyword in message_lower for keyword in ["checkout", "place order", "buy now", "complete purchase", "proceed to checkout"])
                
                intent_data = {
                    "needs_product_search": needs_search,
                    "needs_price_comparison": needs_price_comparison,
                    "needs_cart_management": needs_cart_management,
                    "needs_checkout": needs_checkout,
                    "search_query": message if needs_search else "",
                    "intent_type": "checkout" if needs_checkout else ("cart_management" if needs_cart_management else ("price_comparison" if needs_price_comparison else ("product_search" if needs_search else "conversation"))),
                    "confidence": 0.3
                }
                logger.warning(f"IntentAnalyzer using fallback analysis: {intent_data}")
            
            logger.info(f"IntentAnalyzer analysis for session {session_id}: {intent_data}")
            return intent_data
            
        except Exception as e:
            logger.error(f"IntentAnalyzer error analyzing intent: {e}")
            # Fallback to simple keyword analysis
            return {
                "needs_product_search": any(keyword in message.lower() for keyword in ["search", "find", "show me", "products", "buy"]),
                "search_query": message,
                "intent_type": "conversation",
                "confidence": 0.3
            }

# Create global instance
intent_analyzer = IntentAnalyzer()

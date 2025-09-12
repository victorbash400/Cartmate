"""
Product Selector Service - AI-powered product identification and selection
"""
import logging
import asyncio
import json
import re
from typing import Dict, Any, Optional, List
from google.cloud import aiplatform
from google.oauth2 import service_account
import vertexai
from vertexai.preview.generative_models import GenerativeModel
from services.conversation_memory import conversation_memory

logger = logging.getLogger(__name__)

class ProductSelector:
    """
    Service for intelligently selecting products based on user requests.
    Uses Gemini AI to understand natural language product references.
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
            
            logger.info("ProductSelector Vertex AI initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing ProductSelector Vertex AI: {e}")
            raise

    async def find_product_for_price_comparison(self, message: str, recent_products: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Use AI to find the specific product the user is asking about for price comparison.
        Handles cases like "is the hairdrier a good deal?" when the product might be named differently.
        """
        try:
            if not recent_products:
                return None
            
            # Build a detailed product list for AI analysis
            products_info = []
            for i, product in enumerate(recent_products):
                name = product.get('name', 'Unknown Product')
                price = product.get('priceUsd', {})
                if isinstance(price, dict):
                    price_str = f"${price.get('units', 0)}.{str(price.get('nanos', 0))[:2]}"
                else:
                    price_str = str(price)
                
                # Add product description if available
                description = product.get('description', '')
                if description:
                    products_info.append(f"{i+1}. {name} - {price_str} (Description: {description})")
                else:
                    products_info.append(f"{i+1}. {name} - {price_str}")
            
            products_list = "\n".join(products_info)
            
            # Create AI prompt for price comparison product identification
            price_comparison_prompt = f"""
            The user is asking about price comparison for a product: "{message}"
            
            Available products (user might refer to these by name, description, or category):
            {products_list}
            
            Determine which specific product the user is asking about for price comparison.
            
            Respond with JSON format:
            {{
                "selected_product_index": number (1-based index from the list above, or null if no match),
                "confidence": 0.0-1.0,
                "reasoning": "explanation of why this product was selected",
                "analysis": "brief analysis of the user's request"
            }}
            
            Rules:
            - Look for exact name matches first
            - Look for partial name matches (e.g., "hairdrier" matches "Hair Dryer")
            - Look for category matches (e.g., "the watch" matches any watch product)
            - Look for description matches (e.g., "the electronic device" matches products with electronic descriptions)
            - Be smart about typos and variations (e.g., "hairdrier" = "hair dryer")
            - If user says "this", "that", "it" → select the most recent product (last in list)
            - If user says "the first one", "the second one" → select by position
            - If user mentions "expensive", "cheap", "highest price", "lowest price" → select accordingly
            - If no clear match, return null
            """
            
            # Use Gemini AI for analysis
            max_retries = 2
            response = None
            
            for attempt in range(max_retries):
                try:
                    temp_session = self.chat_model.start_chat()
                    response = temp_session.send_message(price_comparison_prompt)
                    break
                except Exception as e:
                    logger.warning(f"ProductSelector price comparison analysis attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        raise e
                    await asyncio.sleep(1)
            
            # Parse AI response
            try:
                response_text = response.text.strip()
                logger.info(f"ProductSelector price comparison analysis raw response: {response_text}")
                
                # Extract JSON from response
                if "```json" in response_text:
                    start = response_text.find("```json") + 7
                    end = response_text.find("```", start)
                    response_text = response_text[start:end].strip()
                elif "```" in response_text:
                    start = response_text.find("```") + 3
                    end = response_text.find("```", start)
                    response_text = response_text[start:end].strip()
                
                # Find JSON object
                if "{" in response_text and "}" in response_text:
                    start = response_text.find("{")
                    end = response_text.rfind("}") + 1
                    response_text = response_text[start:end]
                
                analysis_data = json.loads(response_text)
                logger.info(f"ProductSelector price comparison analysis result: {analysis_data}")
                
                # Get the selected product
                selected_index = analysis_data.get("selected_product_index")
                if selected_index is not None:
                    product_index = selected_index - 1  # Convert to 0-based
                    if 0 <= product_index < len(recent_products):
                        product = recent_products[product_index]
                        logger.info(f"ProductSelector selected product {product_index + 1}: {product.get('name')} - {analysis_data.get('reasoning')}")
                        return product
                
                logger.info(f"ProductSelector could not identify a specific product for price comparison")
                return None
                
            except Exception as e:
                logger.error(f"ProductSelector failed to parse price comparison analysis: {e}")
                logger.error(f"Raw response was: {response.text}")
                
                # Fallback to keyword-based selection
                logger.warning("ProductSelector falling back to keyword-based product selection for price comparison")
                return self._find_product_by_keywords(message, recent_products)
            
        except Exception as e:
            logger.error(f"ProductSelector error in price comparison analysis: {e}")
            # Fallback to keyword-based selection
            return self._find_product_by_keywords(message, recent_products)

    async def analyze_cart_request(self, message: str, recent_products: List[Dict[str, Any]], session_id: str = None) -> List[Dict[str, Any]]:
        """
        Use AI to analyze cart requests and determine which specific products to add.
        Now uses conversation context to understand what "it" refers to.
        """
        try:
            if not recent_products:
                return []
            
            # Get conversation context to understand what "it" refers to
            conversation_context = ""
            if session_id:
                conversation_history = await conversation_memory.get_conversation_history(session_id)
                conversation_context = conversation_memory.build_intent_analysis_context(conversation_history, recent_products)
            
            # Build a detailed product list for AI analysis
            products_info = []
            for i, product in enumerate(recent_products):
                name = product.get('name', 'Unknown Product')
                price = product.get('priceUsd', {})
                if isinstance(price, dict):
                    price_str = f"${price.get('units', 0)}.{str(price.get('nanos', 0))[:2]}"
                else:
                    price_str = str(price)
                
                products_info.append(f"{i+1}. {name} - {price_str}")
            
            products_list = "\n".join(products_info)
            
            # Create AI prompt for cart analysis with conversation context
            cart_analysis_prompt = f"""
            Analyze this user message about adding items to cart: "{message}"
            
            {conversation_context}
            
            Available products (user can refer to these by name, number, or description):
            {products_list}
            
            Determine which specific products the user wants to add to their cart.
            
            Respond with JSON format:
            {{
                "products_to_add": [
                    {{
                        "product_index": number (1-based index from the list above),
                        "reasoning": "why this product was selected"
                    }}
                ],
                "confidence": 0.0-1.0,
                "analysis": "brief explanation of the analysis"
            }}
            
            CRITICAL RULES:
            - Use conversation context to understand what "it", "this", "that" refers to
            - If user just asked about a specific product (like "is the tanktop a good deal?"), then "add it" refers to THAT product
            - If user says "add the first one", "add #1" → select product at index 1
            - If user says "add the glass jar" → select the product with "glass jar" in the name
            - If user says "add all", "add everything", "add these" → select all products
            - If user mentions specific product names → match by name
            - If user mentions "the expensive one" → select the highest priced product
            - If user mentions "the cheap one" → select the lowest priced product
            - Be smart about partial matches and synonyms
            - If unclear, select the most recent product as default
            """
            
            # Use Gemini AI for analysis
            max_retries = 2
            response = None
            
            for attempt in range(max_retries):
                try:
                    temp_session = self.chat_model.start_chat()
                    response = temp_session.send_message(cart_analysis_prompt)
                    break
                except Exception as e:
                    logger.warning(f"ProductSelector cart analysis attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        raise e
                    await asyncio.sleep(1)
            
            # Parse AI response
            try:
                response_text = response.text.strip()
                logger.info(f"ProductSelector cart analysis raw response: {response_text}")
                
                # Extract JSON from response
                if "```json" in response_text:
                    start = response_text.find("```json") + 7
                    end = response_text.find("```", start)
                    response_text = response_text[start:end].strip()
                elif "```" in response_text:
                    start = response_text.find("```") + 3
                    end = response_text.find("```", start)
                    response_text = response_text[start:end].strip()
                
                # Find JSON object
                if "{" in response_text and "}" in response_text:
                    start = response_text.find("{")
                    end = response_text.rfind("}") + 1
                    response_text = response_text[start:end]
                
                analysis_data = json.loads(response_text)
                logger.info(f"ProductSelector cart analysis result: {analysis_data}")
                
                # Convert AI analysis to actual products
                products_to_add = []
                for item in analysis_data.get("products_to_add", []):
                    product_index = item.get("product_index", 1) - 1  # Convert to 0-based
                    if 0 <= product_index < len(recent_products):
                        product = recent_products[product_index]
                        products_to_add.append(product)
                        logger.info(f"ProductSelector selected product {product_index + 1}: {product.get('name')} - {item.get('reasoning')}")
                
                logger.info(f"ProductSelector cart analysis selected {len(products_to_add)} products from {len(recent_products)} available")
                return products_to_add
                
            except Exception as e:
                logger.error(f"ProductSelector failed to parse cart analysis: {e}")
                logger.error(f"Raw response was: {response.text}")
                
                # Fallback to keyword-based selection
                logger.warning("ProductSelector falling back to keyword-based product selection")
                return self._find_products_by_keywords(message, recent_products)
            
        except Exception as e:
            logger.error(f"ProductSelector error in cart analysis: {e}")
            # Fallback to keyword-based selection
            return self._find_products_by_keywords(message, recent_products)

    def _find_product_by_keywords(self, message: str, recent_products: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Fallback keyword-based product selection for price comparison."""
        try:
            if not recent_products:
                return None
            
            message_lower = message.lower()
            
            # Look for exact product name matches first
            for product in recent_products:
                product_name = product.get('name', '').lower()
                if product_name in message_lower:
                    logger.info(f"ProductSelector keyword analysis: found exact match for '{product_name}'")
                    return product
            
            # Look for partial matches with significant words
            for product in recent_products:
                product_name = product.get('name', '').lower()
                product_words = product_name.split()
                for word in product_words:
                    if len(word) > 3 and word in message_lower:
                        logger.info(f"ProductSelector keyword analysis: found partial match '{word}' from '{product_name}'")
                        return product
            
            # Look for demonstrative references
            if any(word in message_lower for word in ["this", "that", "it"]):
                logger.info("ProductSelector keyword analysis: user wants the most recent product")
                return recent_products[-1]
            
            # Default to most recent product
            logger.info("ProductSelector keyword analysis: defaulting to most recent product")
            return recent_products[-1]
            
        except Exception as e:
            logger.error(f"ProductSelector error in keyword-based product selection: {e}")
            return None

    def _find_products_by_keywords(self, message: str, recent_products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Fallback keyword-based product selection for cart requests."""
        try:
            if not recent_products:
                return []
            
            message_lower = message.lower()
            
            # Check for "all" or "everything" keywords
            if any(keyword in message_lower for keyword in ["all", "everything", "these"]):
                logger.info("ProductSelector keyword analysis: user wants all products")
                return recent_products
            
            # Look for specific product matches
            for product in recent_products:
                product_name = product.get('name', '').lower()
                if product_name in message_lower:
                    logger.info(f"ProductSelector keyword analysis: found exact match for '{product_name}'")
                    return [product]
            
            # Look for demonstrative references
            if any(word in message_lower for word in ["this", "that", "it"]):
                logger.info("ProductSelector keyword analysis: user wants the most recent product")
                return [recent_products[-1]]
            
            # Default to most recent product
            logger.info("ProductSelector keyword analysis: defaulting to most recent product")
            return [recent_products[-1]]
            
        except Exception as e:
            logger.error(f"ProductSelector error in keyword-based product selection: {e}")
            return []

# Create global instance
product_selector = ProductSelector()

import logging
import asyncio
import uuid
from typing import Dict, Any, Optional
from google.cloud import aiplatform
from google.oauth2 import service_account
import vertexai
from vertexai.preview.generative_models import GenerativeModel, ChatSession

from agents.base import BaseAgent
from models.a2a import A2AMessage, A2ARequest, A2AResponse, A2ARequestType, A2AMessageType, A2AFrontendNotification
from a2a.coordinator import a2a_coordinator
from api.websocket import websocket_gateway, AgentStep
from services.storage.redis_client import redis_client

logger = logging.getLogger(__name__)

class OrchestratorAgent(BaseAgent):
    """
    The primary conversational AI agent that coordinates with specialized agents.
    Acts as the main shopping assistant and intelligent coordinator.
    """
    
    def __init__(self):
        super().__init__("orchestrator_001", "orchestrator")
        self.registration.capabilities = [
            "conversation", 
            "intent_analysis", 
            "agent_coordination", 
            "response_synthesis"
        ]
        
        # Vertex AI components
        self.chat_model = None
        self.chat_sessions = {}  # session_id -> ChatSession
        self.pending_requests = {}  # request_id -> request info
        self.recent_products = {}  # session_id -> list of recent products shown
        
        # Initialize Vertex AI
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
            
            # Test the connection with a simple request
            try:
                test_session = self.chat_model.start_chat()
                test_response = test_session.send_message("Hello")
                logger.info("Vertex AI connection test successful")
            except Exception as test_error:
                logger.warning(f"Vertex AI connection test failed: {test_error}")
                # Don't raise here, just log the warning
            
            logger.info("Vertex AI initialized successfully for OrchestratorAgent")

        except Exception as e:
            logger.error(f"Error initializing Vertex AI: {e}")
            raise

    async def start(self):
        """Start the orchestrator agent"""
        await super().start()
        logger.info("Orchestrator Agent started and ready for conversations")

    async def handle_user_message(self, message: str, session_id: str) -> str:
        """
        Main entry point for handling user messages.
        This is called by the WebSocket gateway.
        """
        try:
            logger.info(f"Orchestrator processing message from session {session_id}: {message}")
            
            # Get or create chat session for this user session
            if session_id not in self.chat_sessions:
                self.chat_sessions[session_id] = self.chat_model.start_chat()
            
            chat_session = self.chat_sessions[session_id]
            
            # Send typing indicator to user
            await websocket_gateway.send_typing_indicator(session_id, True)
            
            # Step 1: Analyze intent and determine if we need other agents
            intent_analysis = await self._analyze_intent(message, session_id)
            
            # Step 2: Handle the message based on intent
            if intent_analysis.get("needs_product_search", False):
                # Delegate to product discovery agent
                response = await self._handle_product_search_request(message, session_id, intent_analysis)
            elif intent_analysis.get("needs_price_comparison", False):
                # Delegate to price comparison agent
                response = await self._handle_price_comparison_request(message, session_id, intent_analysis)
            elif intent_analysis.get("needs_cart_management", False):
                # Delegate to cart management agent
                response = await self._handle_cart_management_request(message, session_id, intent_analysis)
            else:
                # Handle conversationally with Vertex AI
                response = await self._handle_conversational_request(message, session_id, chat_session)
            
            # Stop typing indicator
            await websocket_gateway.send_typing_indicator(session_id, False)
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling user message: {e}")
            await websocket_gateway.send_typing_indicator(session_id, False)
            return "I'm sorry, I encountered an error processing your request. Please try again."

    async def _analyze_intent(self, message: str, session_id: str) -> Dict[str, Any]:
        """
        Analyze user intent to determine which agents to involve.
        """
        try:
            # Enhanced intent analysis prompt for Vertex AI
            # Check if user is asking about recently shown products
            recent_products_context = ""
            if session_id in self.recent_products and self.recent_products[session_id]:
                recent_products_list = [p.get('name', '').lower() for p in self.recent_products[session_id][-5:]]
                recent_products_context = f"""
                
                Recently shown products: {', '.join(recent_products_list)}
                """
            
            analysis_prompt = f"""
            Analyze this user message for shopping intent: "{message}"
            {recent_products_context}
            
            Respond with JSON format:
            {{
                "needs_product_search": boolean,
                "needs_price_comparison": boolean,
                "needs_cart_management": boolean,
                "search_query": "extracted product search terms if needed",
                "intent_type": "conversation|product_search|price_comparison|cart_management",
                "confidence": 0.0-1.0
            }}
            
            Rules:
            - If user mentions a recently shown product and asks questions about it, set needs_product_search to FALSE
            - Set needs_price_comparison to TRUE for price comparison requests about shown products
            - Set needs_product_search to TRUE for browsing/searching for new products
            - Set needs_cart_management to TRUE for cart operations: "add to cart", "add these", "put in cart", "add them", "add it"
            """
            
            # Send notification to frontend about analysis
            notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver="frontend",
                notification_type="agent_thinking",
                agent_name="Orchestrator",
                agent_id=self.agent_id,
                content="Analyzing your request..."
            )
            await websocket_gateway.send_a2a_message_to_backchannel(notification.model_dump())
            
            # Use a simple chat session for analysis with retry logic
            max_retries = 2
            response = None
            
            for attempt in range(max_retries):
                try:
                    temp_session = self.chat_model.start_chat()
                    response = temp_session.send_message(analysis_prompt)
                    break  # Success, exit retry loop
                except Exception as e:
                    logger.warning(f"Vertex AI attempt {attempt + 1} failed: {e}")
                    if attempt == max_retries - 1:
                        # Last attempt failed, will use fallback
                        raise e
                    # Wait before retry
                    await asyncio.sleep(1)
            
            # Try to parse JSON response
            import json
            try:
                response_text = response.text.strip()
                logger.info(f"AI intent analysis raw response: {response_text}")
                
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
                logger.info(f"Successfully parsed AI intent analysis: {intent_data}")
            except Exception as e:
                logger.error(f"Failed to parse AI intent analysis: {e}")
                logger.error(f"Raw response was: {response.text}")
                
                # Simple fallback logic
                message_lower = message.lower()
                needs_search = any(keyword in message_lower for keyword in ["show me", "find", "search", "products", "browse"])
                needs_price_comparison = any(keyword in message_lower for keyword in ["compare", "price", "deal"])
                needs_cart_management = any(keyword in message_lower for keyword in ["add to cart", "add these", "put in cart", "add them", "add it"])
                
                intent_data = {
                    "needs_product_search": needs_search,
                    "needs_price_comparison": needs_price_comparison,
                    "needs_cart_management": needs_cart_management,
                    "search_query": message if needs_search else "",
                    "intent_type": "cart_management" if needs_cart_management else ("price_comparison" if needs_price_comparison else ("product_search" if needs_search else "conversation")),
                    "confidence": 0.3
                }
                logger.warning(f"Using fallback intent analysis: {intent_data}")
            
            logger.info(f"Intent analysis for session {session_id}: {intent_data}")
            return intent_data
            
        except Exception as e:
            logger.error(f"Error analyzing intent: {e}")
            # Fallback to simple keyword analysis
            return {
                "needs_product_search": any(keyword in message.lower() for keyword in ["search", "find", "show me", "products", "buy"]),
                "search_query": message,
                "intent_type": "conversation",
                "confidence": 0.3
            }

    async def _handle_product_search_request(self, message: str, session_id: str, intent_analysis: Dict[str, Any]) -> str:
        """
        Handle requests that need product search by delegating to product discovery agent.
        """
        try:
            search_query = intent_analysis.get('search_query', message)
            # If search_query is empty, use the original message
            if not search_query or search_query.strip() == '':
                search_query = message
            
            # Get personalization data for this session
            personalization_context = await self._get_personalization_context(session_id)
            
            # Step 1: Acknowledge and show we're calling the product agent
            acknowledgment = f"I'll help you find products! Let me search our catalog for: '{search_query}'"
            await websocket_gateway.send_message(session_id, "text", acknowledgment)
            
            # Step 2: Send notification that we're calling the product discovery agent
            notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver="frontend",
                notification_type="agent_delegation",
                agent_name="Orchestrator",
                agent_id=self.agent_id,
                content=f"🔍 Calling Product Discovery Agent with query: '{search_query}'"
            )
            await websocket_gateway.send_a2a_message_to_backchannel(notification.model_dump())
            
            # Step 3: Find product discovery agent
            product_agent = a2a_coordinator.find_agent_by_type("product_discovery")
            if not product_agent:
                error_msg = "❌ Product search service is currently unavailable. Please try again later."
                await websocket_gateway.send_message(session_id, "text", error_msg)
                return ""
            
            # Step 4: Send initial agent communication with calling step
            agent_steps = [
                AgentStep(
                    id="calling",
                    type="calling",
                    agent_name="Product Discovery Agent",
                    message="Connecting..."
                )
            ]
            await websocket_gateway.send_agent_communication(session_id, agent_steps)
            
            # Create request for product discovery agent
            request_id = str(uuid.uuid4())
            conversation_id = session_id
            
            # Store request info for when we get the response
            self.pending_requests[request_id] = {
                "session_id": session_id,
                "original_message": message,
                "request_type": "product_search"
            }
            
            # Step 5: Send A2A request to product discovery agent with explicit request ID
            request_content = {
                "query": search_query,
                "session_id": session_id
            }
            
            # Add personalization context if available
            if personalization_context:
                request_content["personalization"] = personalization_context
                logger.info(f"Added personalization context to product search request: {personalization_context}")
            
            request = A2ARequest(
                id=request_id,
                sender=self.agent_id,
                receiver=product_agent.agent_id,
                request_type=A2ARequestType.SEARCH_PRODUCTS,
                conversation_id=conversation_id,
                content=request_content,
                requires_ack=True
            )
            
            success = await self.send_message(product_agent.agent_id, request)
            
            if not success:
                error_msg = "❌ Having trouble connecting to the product search service. Please try again."
                await websocket_gateway.send_message(session_id, "text", error_msg)
                return ""
            
            # Don't return anything here - the response will come via handle_response
            return ""
            
        except Exception as e:
            logger.error(f"Error handling product search request: {e}")
            error_msg = "❌ I encountered an error while searching for products. Please try again."
            await websocket_gateway.send_message(session_id, "text", error_msg)
            return ""

    async def _handle_price_comparison_request(self, message: str, session_id: str, intent_analysis: Dict[str, Any]) -> str:
        """
        Handle requests that need price comparison by delegating to price comparison agent.
        """
        try:
            # Get the most recent product for price comparison
            if session_id not in self.recent_products or not self.recent_products[session_id]:
                error_msg = "I don't see any products to compare prices for. Please search for products first, then ask me to compare prices."
                await websocket_gateway.send_message(session_id, "text", error_msg)
                return ""
            
            # Find the specific product the user is asking about
            target_product = self._find_product_in_message(message, session_id)
            if not target_product:
                # Fallback to most recent product
                target_product = self.recent_products[session_id][-1]
                logger.warning(f"Could not find specific product in message '{message}', using most recent product")
            
            product_name = target_product.get('name', 'Unknown Product')
            
            # Step 1: Acknowledge and show we're calling the price comparison agent
            acknowledgment = f"I'll help you compare prices for '{product_name}'! Let me search for competitive pricing and similar products."
            await websocket_gateway.send_message(session_id, "text", acknowledgment)
            
            # Step 2: Send notification that we're calling the price comparison agent
            notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver="frontend",
                notification_type="agent_delegation",
                agent_name="Orchestrator",
                agent_id=self.agent_id,
                content=f"💰 Calling Price Comparison Agent for '{product_name}'"
            )
            await websocket_gateway.send_a2a_message_to_backchannel(notification.model_dump())
            
            # Step 3: Find price comparison agent
            price_agent = a2a_coordinator.find_agent_by_type("price_comparison")
            if not price_agent:
                error_msg = "❌ Price comparison service is currently unavailable. Please try again later."
                await websocket_gateway.send_message(session_id, "text", error_msg)
                return ""
            
            # Step 4: Send initial agent communication with calling step
            agent_steps = [
                AgentStep(
                    id="calling",
                    type="calling",
                    agent_name="Price Comparison Agent",
                    message="Connecting..."
                )
            ]
            await websocket_gateway.send_agent_communication(session_id, agent_steps)
            
            # Create request for price comparison agent
            request_id = str(uuid.uuid4())
            conversation_id = session_id
            
            # Store request info for when we get the response
            self.pending_requests[request_id] = {
                "session_id": session_id,
                "original_message": message,
                "request_type": "price_comparison"
            }
            
            # Step 5: Send A2A request to price comparison agent
            request_content = {
                "product": target_product,
                "session_id": session_id
            }
            
            request = A2ARequest(
                id=request_id,
                sender=self.agent_id,
                receiver=price_agent.agent_id,
                request_type=A2ARequestType.COMPARE_PRICES,
                conversation_id=conversation_id,
                content=request_content,
                requires_ack=True
            )
            
            success = await self.send_message(price_agent.agent_id, request)
            
            if not success:
                error_msg = "❌ Having trouble connecting to the price comparison service. Please try again."
                await websocket_gateway.send_message(session_id, "text", error_msg)
                return ""
            
            # Don't return anything here - the response will come via handle_response
            return ""
            
        except Exception as e:
            logger.error(f"Error handling price comparison request: {e}")
            error_msg = "❌ I encountered an error while comparing prices. Please try again."
            await websocket_gateway.send_message(session_id, "text", error_msg)
            return ""

    async def _handle_conversational_request(self, message: str, session_id: str, chat_session: ChatSession) -> str:
        """
        Handle requests conversationally using Vertex AI with personalization context.
        """
        try:
            # Get personalization data for this session
            personalization_context = await self._get_personalization_context(session_id)
            
            # Build context-aware prompt
            context_info = ""
            if personalization_context:
                style_prefs = personalization_context.get('style_preferences', '')
                budget_range = personalization_context.get('budget_range', {})
                image_analysis = personalization_context.get('image_analysis', {})
                
                context_info = f"""
                
                User's Personalization Context:
                - Style Preferences: {style_prefs if style_prefs else 'Not specified'}
                - Budget Range: ${budget_range.get('min', 'N/A')} - ${budget_range.get('max', 'N/A')}
                - Image Analysis: {image_analysis}
                """
                logger.info(f"Using personalization context for conversational request: {personalization_context}")
            
            # Add recent products context
            recent_products_info = ""
            if session_id in self.recent_products and self.recent_products[session_id]:
                products_list = []
                for product in self.recent_products[session_id][-5:]:  # Last 5 products
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
                logger.info(f"Using recent products context for session {session_id}: {len(self.recent_products[session_id])} products")
            
            # Enhance the message with shopping context and personalization
            enhanced_prompt = f"""
            You are CartMate, a friendly AI shopping assistant. Respond naturally to this message: "{message}"
            {context_info}
            {recent_products_info}
            
            Guidelines:
            - Be helpful and conversational
            - Use the user's personalization context when relevant (style preferences, budget, image analysis)
            - If they ask about their style, reference their personalization data if available
            - If they ask about specific products (like "the glass jar", "that watch", etc.), refer to the recently shown products list
            - When referencing recently shown products, use their exact names and prices
            - Offer shopping advice when relevant
            - Ask clarifying questions to better understand needs
            - If they want to search for specific products, let them know you can help with that
            - Keep responses concise but informative
            """
            
            response = chat_session.send_message(enhanced_prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Error in conversational request: {e}")
            return "I'm here to help with your shopping needs! What can I assist you with today?"

    async def handle_response(self, response: A2AResponse) -> bool:
        """
        Handle responses from other agents and forward to user.
        """
        try:
            logger.info(f"Orchestrator received response for request {response.request_id}")
            logger.info(f"Pending requests: {list(self.pending_requests.keys())}")
            
            if response.request_id not in self.pending_requests:
                logger.warning(f"Received response for unknown request {response.request_id}")
                return False
            
            request_info = self.pending_requests[response.request_id]
            session_id = request_info["session_id"]
            
            if response.success:
                # Process the response based on request type
                if request_info["request_type"] == "product_search":
                    # Update agent communication with processing step
                    agent_steps = [
                        AgentStep(
                            id="calling",
                            type="success",
                            agent_name="Product Discovery Agent",
                            message="Connected"
                        ),
                        AgentStep(
                            id="processing",
                            type="processing",
                            agent_name="Product Discovery Agent",
                            message="Processing results..."
                        )
                    ]
                    await websocket_gateway.update_agent_communication(session_id, agent_steps)
                    
                    # Format product search results for user
                    products = response.content
                    formatted_response = await self._format_product_search_response(products, session_id)
                    
                    # Store recent products for conversational context
                    if session_id not in self.recent_products:
                        self.recent_products[session_id] = []
                    self.recent_products[session_id].extend(products)
                    # Keep only last 10 products to avoid memory bloat
                    if len(self.recent_products[session_id]) > 10:
                        self.recent_products[session_id] = self.recent_products[session_id][-10:]
                    
                    logger.info(f"Stored {len(products)} products in recent products for session {session_id}")
                    
                    # Send products as structured data for frontend rendering
                    message_content = {
                        "message": formatted_response,
                        "products": products
                    }
                    await websocket_gateway.send_message(session_id, "text", message_content)
                    
                    # Send final success step
                    final_agent_steps = [
                        AgentStep(
                            id="calling",
                            type="success",
                            agent_name="Product Discovery Agent",
                            message="Connected"
                        ),
                        AgentStep(
                            id="processing",
                            type="success",
                            agent_name="Product Discovery Agent",
                            message="Completed"
                        )
                    ]
                    await websocket_gateway.update_agent_communication(session_id, final_agent_steps)
                    
                    # Send final formatted response to user
                    await websocket_gateway.send_message(session_id, "text", formatted_response)
                    
                elif request_info["request_type"] == "price_comparison":
                    # Format price comparison results for user
                    price_data = response.content
                    formatted_response = await self._format_price_comparison_response(price_data, session_id)
                    
                    # Send final success steps
                    final_agent_steps = [
                        AgentStep(id="calling", type="success", agent_name="Price Comparison Agent", message="Connected"),
                        AgentStep(id="searching", type="success", agent_name="Price Comparison Agent", message="Search completed"),
                        AgentStep(id="api_request", type="success", agent_name="Price Comparison Agent", message="API request completed"),
                        AgentStep(id="parsing", type="success", agent_name="Price Comparison Agent", message="Analysis completed")
                    ]
                    
                    # Send agent communication update with price comparison data
                    additional_data = {
                        "message": formatted_response,
                        "price_comparison": price_data
                    }
                    await websocket_gateway.send_agent_communication_with_data(session_id, final_agent_steps, additional_data)
                    
                    # Send final formatted response to user
                    await websocket_gateway.send_message(session_id, "text", formatted_response)
                    
                elif request_info["request_type"] == "cart_management":
                    # Format cart management results for user
                    cart_data = response.content
                    formatted_response = await self._format_cart_management_response(cart_data, session_id)
                    
                    # Send final success steps
                    final_agent_steps = [
                        AgentStep(id="calling", type="success", agent_name="Cart Management Agent", message="Connected"),
                        AgentStep(id="processing", type="success", agent_name="Cart Management Agent", message="Items added to cart")
                    ]
                    
                    # Send agent communication update with cart data
                    additional_data = {
                        "message": formatted_response,
                        "cart_update": cart_data
                    }
                    await websocket_gateway.send_agent_communication_with_data(session_id, final_agent_steps, additional_data)
                    
                    # Send final formatted response to user
                    await websocket_gateway.send_message(session_id, "text", formatted_response)
                    
                else:
                    # Generic response handling
                    await websocket_gateway.send_message(session_id, "text", str(response.content))
            else:
                # Handle error response
                if request_info["request_type"] == "price_comparison":
                    error_message = f"❌ Price Comparison Agent encountered an error: {response.error}. Please try again."
                elif request_info["request_type"] == "cart_management":
                    error_message = f"❌ Cart Management Agent encountered an error: {response.error}. Please try again."
                else:
                    error_message = f"❌ Product Discovery Agent encountered an error: {response.error}. Please try again."
                await websocket_gateway.send_message(session_id, "text", error_message)
            
            # Clean up pending request
            del self.pending_requests[response.request_id]
            return True
            
        except Exception as e:
            logger.error(f"Error handling response: {e}")
            return False

    async def _format_product_search_response(self, products: list, session_id: str) -> str:
        """
        Format product search results into a user-friendly response.
        """
        if not products:
            return "I couldn't find any products matching your search. Try different keywords or let me know what specific type of item you're looking for!"
        
        # Since we're sending products as structured data, just provide a clean summary
        response = f"I found {len(products)} products for you! Browse through them below and let me know if you'd like more details about any specific item, or if you'd like to search for something else."
        
        return response

    async def _format_price_comparison_response(self, price_data: Dict[str, Any], session_id: str) -> str:
        """Format price comparison results into a conversational response."""
        try:
            if price_data.get("error"):
                return f"Sorry, I ran into an issue while checking prices: {price_data['error']}. Let me try again in a moment."
            
            product_name = price_data.get("original_product", {}).get("name", "Unknown Product")
            current_price = price_data.get("current_price", "Unknown")
            price_analysis = price_data.get("price_analysis", "")
            
            response = f"Here's what I found about the {product_name} at {current_price}:\n\n"
            if price_analysis:
                response += f"{price_analysis}\n\n"
            
            similar_products = price_data.get("similar_products", [])
            if similar_products:
                response += f"I found {len(similar_products)} similar options for you:\n"
                for product in similar_products[:3]:
                    name = product.get("name", "Similar product")
                    price = product.get("price", "Unknown")
                    retailer = product.get("retailer", "Various retailers")
                    response += f"• {name} - {price} ({retailer})\n"
                response += "\n"
            
            sources = price_data.get("sources", [])
            if sources:
                response += f"*Based on analysis of {len(sources)} market sources. Prices can vary by location and retailer.*"
            else:
                response += f"*This analysis is based on current market data. Prices may vary by retailer and location.*"
            
            return response
            
        except Exception as e:
            logger.error(f"Error formatting price comparison response: {e}")
            return "I found some price comparison data, but had trouble formatting it. The analysis is available in the detailed results below."

    async def _format_cart_management_response(self, cart_data: Dict[str, Any], session_id: str) -> str:
        """Format cart management results into a conversational response."""
        try:
            if not cart_data.get("success", False):
                return "❌ I encountered an issue adding items to your cart. Please try again."
            
            added_items = cart_data.get("added_items", [])
            failed_items = cart_data.get("failed_items", [])
            total_added = cart_data.get("total_added", 0)
            
            if total_added == 0:
                return "❌ No items were added to your cart. Please check the product details and try again."
            
            response = f"✅ Successfully added {total_added} item(s) to your cart!\n\n"
            
            if added_items:
                response += "**Added to cart:**\n"
                for item in added_items:
                    name = item.get("name", "Unknown Product")
                    quantity = item.get("quantity", 1)
                    response += f"• {name} (qty: {quantity})\n"
                response += "\n"
            
            if failed_items:
                response += f"⚠️ Note: {len(failed_items)} item(s) could not be added to your cart.\n\n"
            
            response += "You can view your cart anytime by clicking the cart icon in the sidebar. Would you like to continue shopping or see what's in your cart?"
            
            return response
            
        except Exception as e:
            logger.error(f"Error formatting cart management response: {e}")
            return "✅ Items have been added to your cart! You can view your cart anytime by clicking the cart icon in the sidebar."

    def _find_product_in_message(self, message: str, session_id: str) -> Optional[Dict[str, Any]]:
        """Find the specific product the user is asking about in their message."""
        try:
            if session_id not in self.recent_products or not self.recent_products[session_id]:
                return None
            
            message_lower = message.lower()
            recent_products = self.recent_products[session_id]
            
            # Look for exact product name matches first
            for product in recent_products:
                product_name = product.get('name', '').lower()
                if product_name in message_lower:
                    return product
            
            # Look for partial matches
            for product in recent_products:
                product_name = product.get('name', '').lower()
                product_words = product_name.split()
                for word in product_words:
                    if len(word) > 3 and word in message_lower:
                        return product
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding product in message: {e}")
            return None

    async def _handle_cart_management_request(self, message: str, session_id: str, intent_analysis: Dict[str, Any]) -> str:
        """
        Handle cart management requests by delegating to cart management agent.
        """
        try:
            # Check if we have recent products to add to cart
            recent_products = self.recent_products.get(session_id, [])
            
            if not recent_products:
                return "I don't see any products to add to your cart. Please search for products first, then I can help you add them to your cart."
            
            # Step 1: Acknowledge and show we're calling the cart agent
            acknowledgment = f"I'll add those products to your cart! Let me process your request."
            await websocket_gateway.send_message(session_id, "text", acknowledgment)
            
            # Step 2: Send notification that we're calling the cart management agent
            notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver="frontend",
                notification_type="agent_delegation",
                agent_name="Orchestrator",
                agent_id=self.agent_id,
                content=f"🛒 Calling Cart Management Agent to add {len(recent_products)} item(s)"
            )
            await websocket_gateway.send_a2a_message_to_backchannel(notification.model_dump())
            
            # Step 3: Find cart management agent
            cart_agent = a2a_coordinator.find_agent_by_type("cart_management")
            if not cart_agent:
                error_msg = "❌ Cart service is currently unavailable. Please try again later."
                await websocket_gateway.send_message(session_id, "text", error_msg)
                return ""
            
            # Step 4: Send initial agent communication
            agent_steps = [
                AgentStep(
                    id="calling",
                    type="calling",
                    agent_name="Cart Management Agent",
                    message="Connecting..."
                )
            ]
            await websocket_gateway.send_agent_communication(session_id, agent_steps)
            
            # Create request for cart management agent
            request_id = str(uuid.uuid4())
            
            # Store request info for when we get the response
            import time
            self.pending_requests[request_id] = {
                "session_id": session_id,
                "original_message": message,
                "request_type": "cart_management",
                "created_at": time.time()
            }
            
            logger.info(f"Created cart management request {request_id} for session {session_id}")
            
            # Step 5: Send A2A request to cart management agent
            request_content = {
                "session_id": session_id,
                "products": recent_products
            }
            
            request = A2ARequest(
                id=request_id,
                sender=self.agent_id,
                receiver=cart_agent.agent_id,
                conversation_id=session_id,
                request_type=A2ARequestType.ADD_TO_CART,
                content=request_content
            )
            
            # Send the request
            logger.info(f"Sending cart management request {request_id} to agent {cart_agent.agent_id}")
            success = await self.send_message(cart_agent.agent_id, request)
            if not success:
                error_msg = "❌ Failed to communicate with cart service. Please try again."
                await websocket_gateway.send_message(session_id, "text", error_msg)
                # Clean up the pending request since we failed to send
                if request_id in self.pending_requests:
                    del self.pending_requests[request_id]
                return ""
            
            logger.info(f"Cart management request {request_id} sent successfully, waiting for response")
            # Return empty string since response will come via A2A callback
            return ""
            
        except Exception as e:
            logger.error(f"Error in cart management request: {e}")
            error_msg = "I'm sorry, I encountered an error adding items to your cart. Please try again."
            await websocket_gateway.send_message(session_id, "text", error_msg)
            return ""

    async def _get_personalization_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get personalization data for a session from Redis.
        """
        try:
            key = f"personalization:{session_id}"
            data = await redis_client.get(key)
            
            if data:
                import json
                personalization_data = json.loads(data)
                logger.info(f"Retrieved personalization data for session {session_id}")
                return personalization_data
            else:
                logger.info(f"No personalization data found for session {session_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error retrieving personalization data for session {session_id}: {e}")
            return None

    async def clear_session_context(self, session_id: str):
        """
        Clear session-specific context (recent products, chat sessions).
        """
        try:
            # Clear recent products
            if session_id in self.recent_products:
                del self.recent_products[session_id]
            
            # Clear chat session
            if session_id in self.chat_sessions:
                del self.chat_sessions[session_id]
            
            logger.info(f"Cleared session context for session {session_id}")
        except Exception as e:
            logger.error(f"Error clearing session context for session {session_id}: {e}")

# Create a single instance of the agent
orchestrator_agent = OrchestratorAgent()
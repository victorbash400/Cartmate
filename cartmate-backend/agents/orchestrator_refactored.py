"""
Refactored Orchestrator Agent - Much smaller and focused on coordination only
"""
import logging
import asyncio
import uuid
import time
from typing import Dict, Any, Optional
from google.cloud import aiplatform
from google.oauth2 import service_account
import vertexai
from vertexai.preview.generative_models import GenerativeModel, ChatSession

from agents.base import BaseAgent
from models.a2a import A2AMessage, A2ARequest, A2AResponse, A2ARequestType, A2AMessageType, A2AFrontendNotification
from a2a.coordinator import a2a_coordinator
from api.websocket import websocket_gateway, AgentStep

# Import our new services
from services.intent_analyzer import intent_analyzer
from services.product_selector import product_selector
from services.response_formatter import response_formatter
from services.personalization_service import personalization_service
from services.conversation_memory import conversation_memory

logger = logging.getLogger(__name__)

class OrchestratorAgent(BaseAgent):
    """
    The primary conversational AI agent that coordinates with specialized agents.
    Now much smaller and focused only on coordination and conversation.
    """
    
    def __init__(self):
        super().__init__("orchestrator_001", "orchestrator")
        self.registration.capabilities = [
            "conversation", 
            "intent_analysis", 
            "agent_coordination", 
            "response_synthesis"
        ]
        
        # Vertex AI components for direct conversation
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
            
            logger.info("OrchestratorAgent Vertex AI initialized successfully")

        except Exception as e:
            logger.error(f"Error initializing OrchestratorAgent Vertex AI: {e}")
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
            
            # Store user message in conversation memory
            logger.info(f"Orchestrator storing user message in conversation memory: {message[:50]}...")
            success = await conversation_memory.store_message(
                session_id=session_id,
                message_type="text",
                content=message,
                sender="user"
            )
            logger.info(f"Orchestrator conversation memory store result: {success}")
            
            # Get or create chat session for this user session
            if session_id not in self.chat_sessions:
                self.chat_sessions[session_id] = self.chat_model.start_chat()
            
            chat_session = self.chat_sessions[session_id]
            
            # Send typing indicator to user
            await websocket_gateway.send_typing_indicator(session_id, True)
            
            # Step 1: Analyze intent using IntentAnalyzer service (now with conversation history)
            recent_products = self.recent_products.get(session_id, [])
            intent_analysis = await intent_analyzer.analyze_intent(message, session_id, recent_products)
            
            # Step 2: Handle the message based on intent
            if intent_analysis.get("needs_product_search", False):
                response = await self._handle_product_search_request(message, session_id, intent_analysis)
            elif intent_analysis.get("needs_price_comparison", False):
                response = await self._handle_price_comparison_request(message, session_id, intent_analysis)
            elif intent_analysis.get("needs_cart_management", False):
                response = await self._handle_cart_management_request(message, session_id, intent_analysis)
            elif intent_analysis.get("needs_checkout", False):
                response = await self._handle_checkout_request(message, session_id, intent_analysis)
            else:
                response = await self._handle_conversational_request(message, session_id, chat_session)
            
            # Stop typing indicator
            await websocket_gateway.send_typing_indicator(session_id, False)
            
            return response
            
        except Exception as e:
            logger.error(f"Error handling user message: {e}")
            await websocket_gateway.send_typing_indicator(session_id, False)
            return "I'm sorry, I encountered an error processing your request. Please try again."

    async def _handle_product_search_request(self, message: str, session_id: str, intent_analysis: Dict[str, Any]) -> str:
        """Handle product search requests by delegating to product discovery agent."""
        try:
            search_query = intent_analysis.get('search_query', message)
            if not search_query or search_query.strip() == '':
                search_query = message
            
            # Get personalization context
            personalization_context = await personalization_service.get_personalization_context(session_id)
            
            # Acknowledge and show we're calling the product agent
            acknowledgment = f"I'll help you find products! Let me search our catalog for: '{search_query}'"
            await websocket_gateway.send_message(session_id, "text", acknowledgment)
            
            # Send notification
            notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver="frontend",
                notification_type="agent_delegation",
                agent_name="Orchestrator",
                agent_id=self.agent_id,
                content=f"🔍 Calling Product Discovery Agent with query: '{search_query}'"
            )
            await websocket_gateway.send_a2a_message_to_backchannel(notification.model_dump())
            
            # Find product discovery agent
            product_agent = a2a_coordinator.find_agent_by_type("product_discovery")
            if not product_agent:
                error_msg = "❌ Product search service is currently unavailable. Please try again later."
                await websocket_gateway.send_message(session_id, "text", error_msg)
                return ""
            
            # Send initial agent communication
            agent_steps = [
                AgentStep(
                    id="calling",
                    type="calling",
                    agent_name="Product Discovery Agent",
                    message="Connecting..."
                )
            ]
            await websocket_gateway.send_agent_communication(session_id, agent_steps)
            
            # Create request
            request_id = str(uuid.uuid4())
            self.pending_requests[request_id] = {
                "session_id": session_id,
                "original_message": message,
                "request_type": "product_search"
            }
            
            # Prepare request content
            request_content = {
                "query": search_query,
                "session_id": session_id
            }
            
            if personalization_context:
                request_content["personalization"] = personalization_context
                logger.info(f"Added personalization context to product search request")
            
            request = A2ARequest(
                id=request_id,
                sender=self.agent_id,
                receiver=product_agent.agent_id,
                request_type=A2ARequestType.SEARCH_PRODUCTS,
                conversation_id=session_id,
                content=request_content,
                requires_ack=True
            )
            
            success = await self.send_message(product_agent.agent_id, request)
            if not success:
                error_msg = "❌ Having trouble connecting to the product search service. Please try again."
                await websocket_gateway.send_message(session_id, "text", error_msg)
                return ""
            
            return ""
            
        except Exception as e:
            logger.error(f"Error handling product search request: {e}")
            error_msg = "❌ I encountered an error while searching for products. Please try again."
            await websocket_gateway.send_message(session_id, "text", error_msg)
            return ""

    async def _handle_price_comparison_request(self, message: str, session_id: str, intent_analysis: Dict[str, Any]) -> str:
        """Handle price comparison requests by delegating to price comparison agent."""
        try:
            recent_products = self.recent_products.get(session_id, [])
            if not recent_products:
                error_msg = "I don't see any products to compare prices for. Please search for products first, then ask me to compare prices."
                await websocket_gateway.send_message(session_id, "text", error_msg)
                return ""
            
            # Use ProductSelector service to find the specific product
            target_product = await product_selector.find_product_for_price_comparison(message, recent_products)
            if not target_product:
                target_product = recent_products[-1]
                logger.warning(f"Could not identify specific product in message '{message}', using most recent product")
            
            product_name = target_product.get('name', 'Unknown Product')
            
            # Acknowledge
            acknowledgment = f"I'll help you compare prices for '{product_name}'! Let me search for competitive pricing and similar products."
            await websocket_gateway.send_message(session_id, "text", acknowledgment)
            
            # Send notification
            notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver="frontend",
                notification_type="agent_delegation",
                agent_name="Orchestrator",
                agent_id=self.agent_id,
                content=f"💰 Calling Price Comparison Agent for '{product_name}'"
            )
            await websocket_gateway.send_a2a_message_to_backchannel(notification.model_dump())
            
            # Find price comparison agent
            price_agent = a2a_coordinator.find_agent_by_type("price_comparison")
            if not price_agent:
                error_msg = "❌ Price comparison service is currently unavailable. Please try again later."
                await websocket_gateway.send_message(session_id, "text", error_msg)
                return ""
            
            # Send initial agent communication
            agent_steps = [
                AgentStep(
                    id="calling",
                    type="calling",
                    agent_name="Price Comparison Agent",
                    message="Connecting..."
                )
            ]
            await websocket_gateway.send_agent_communication(session_id, agent_steps)
            
            # Create request
            request_id = str(uuid.uuid4())
            self.pending_requests[request_id] = {
                "session_id": session_id,
                "original_message": message,
                "request_type": "price_comparison"
            }
            
            request_content = {
                "product": target_product,
                "session_id": session_id
            }
            
            request = A2ARequest(
                id=request_id,
                sender=self.agent_id,
                receiver=price_agent.agent_id,
                request_type=A2ARequestType.COMPARE_PRICES,
                conversation_id=session_id,
                content=request_content,
                requires_ack=True
            )
            
            success = await self.send_message(price_agent.agent_id, request)
            if not success:
                error_msg = "❌ Having trouble connecting to the price comparison service. Please try again."
                await websocket_gateway.send_message(session_id, "text", error_msg)
                return ""
            
            return ""
            
        except Exception as e:
            logger.error(f"Error handling price comparison request: {e}")
            error_msg = "❌ I encountered an error while comparing prices. Please try again."
            await websocket_gateway.send_message(session_id, "text", error_msg)
            return ""

    async def _handle_cart_management_request(self, message: str, session_id: str, intent_analysis: Dict[str, Any]) -> str:
        """Handle cart management requests by delegating to cart management agent."""
        try:
            recent_products = self.recent_products.get(session_id, [])
            if not recent_products:
                return "I don't see any products to add to your cart. Please search for products first, then I can help you add them to your cart."
            
            # Use ProductSelector service to determine which products to add
            products_to_add = await product_selector.analyze_cart_request(message, recent_products, session_id)
            
            if not products_to_add:
                return "I don't see any products to add to your cart. Please search for products first, then I can help you add them to your cart."
            
            # Determine acknowledgment message
            if len(products_to_add) == 1:
                product_name = products_to_add[0].get('name', 'the product')
                acknowledgment = f"I'll add '{product_name}' to your cart! Let me process your request."
                notification_content = f"🛒 Calling Cart Management Agent to add '{product_name}'"
            else:
                acknowledgment = f"I'll add {len(products_to_add)} products to your cart! Let me process your request."
                notification_content = f"🛒 Calling Cart Management Agent to add {len(products_to_add)} item(s)"
            
            # Acknowledge
            await websocket_gateway.send_message(session_id, "text", acknowledgment)
            
            # Send notification
            notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver="frontend",
                notification_type="agent_delegation",
                agent_name="Orchestrator",
                agent_id=self.agent_id,
                content=notification_content
            )
            await websocket_gateway.send_a2a_message_to_backchannel(notification.model_dump())
            
            # Find cart management agent
            cart_agent = a2a_coordinator.find_agent_by_type("cart_management")
            if not cart_agent:
                error_msg = "❌ Cart service is currently unavailable. Please try again later."
                await websocket_gateway.send_message(session_id, "text", error_msg)
                return ""
            
            # Send initial agent communication
            agent_steps = [
                AgentStep(
                    id="calling",
                    type="calling",
                    agent_name="Cart Management Agent",
                    message="Connecting..."
                )
            ]
            await websocket_gateway.send_agent_communication(session_id, agent_steps)
            
            # Create request
            request_id = str(uuid.uuid4())
            self.pending_requests[request_id] = {
                "session_id": session_id,
                "original_message": message,
                "request_type": "cart_management",
                "created_at": time.time()
            }
            
            request_content = {
                "session_id": session_id,
                "products": products_to_add
            }
            
            request = A2ARequest(
                id=request_id,
                sender=self.agent_id,
                receiver=cart_agent.agent_id,
                conversation_id=session_id,
                request_type=A2ARequestType.ADD_TO_CART,
                content=request_content
            )
            
            success = await self.send_message(cart_agent.agent_id, request)
            if not success:
                error_msg = "❌ Failed to communicate with cart service. Please try again."
                await websocket_gateway.send_message(session_id, "text", error_msg)
                if request_id in self.pending_requests:
                    del self.pending_requests[request_id]
                return ""
            
            return ""
            
        except Exception as e:
            logger.error(f"Error in cart management request: {e}")
            error_msg = "I'm sorry, I encountered an error adding items to your cart. Please try again."
            await websocket_gateway.send_message(session_id, "text", error_msg)
            return ""

    async def _handle_checkout_request(self, message: str, session_id: str, intent_analysis: Dict[str, Any]) -> str:
        """Handle checkout requests by delegating to checkout agent."""
        try:
            # Get checkout data from intent analysis
            checkout_data = intent_analysis.get("checkout_data", {})
            
            # Check if we have the required checkout information
            email = checkout_data.get("email") if checkout_data else None
            address = checkout_data.get("address") if checkout_data else None
            payment_info = checkout_data.get("payment_info") if checkout_data else None
            
            if not email or not address or not payment_info:
                # Send checkout form component to frontend
                await websocket_gateway.send_message(session_id, "checkout_form", {
                    "message": "I'd be happy to help you checkout! Please fill out the form below with your details:",
                    "form_data": {
                        "email": email or "",
                        "address": address if isinstance(address, dict) else {"street_address": address or "", "city": "", "state": "", "country": "", "zip_code": ""},
                        "credit_card": payment_info if isinstance(payment_info, dict) else {"number": "", "cvv": "", "expiration_year": "", "expiration_month": ""}
                    }
                })
                return ""
            
            # Acknowledge
            acknowledgment = "I'll process your checkout now! Let me handle your order."
            await websocket_gateway.send_message(session_id, "text", acknowledgment)
            
            # Send notification
            notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver="frontend",
                notification_type="agent_delegation",
                agent_name="Orchestrator",
                agent_id=self.agent_id,
                content="💳 Calling Checkout Agent to process your order"
            )
            await websocket_gateway.send_a2a_message_to_backchannel(notification.model_dump())
            
            # Find checkout agent
            checkout_agent = a2a_coordinator.find_agent_by_type("checkout")
            if not checkout_agent:
                error_msg = "❌ Checkout service is currently unavailable. Please try again later."
                await websocket_gateway.send_message(session_id, "text", error_msg)
                return ""
            
            # Send initial agent communication
            agent_steps = [
                AgentStep(
                    id="calling",
                    type="calling",
                    agent_name="Checkout Agent",
                    message="Connecting..."
                )
            ]
            await websocket_gateway.send_agent_communication(session_id, agent_steps)
            
            # Create request
            request_id = str(uuid.uuid4())
            self.pending_requests[request_id] = {
                "session_id": session_id,
                "original_message": message,
                "request_type": "checkout",
                "created_at": time.time()
            }
            
            request_content = {
                "session_id": session_id,
                "checkout_data": {
                    "email": email,
                    "address": address,
                    "payment_info": payment_info
                }
            }
            
            request = A2ARequest(
                id=request_id,
                sender=self.agent_id,
                receiver=checkout_agent.agent_id,
                conversation_id=session_id,
                request_type=A2ARequestType.PROCESS_CHECKOUT,
                content=request_content
            )
            
            success = await self.send_message(checkout_agent.agent_id, request)
            if not success:
                error_msg = "❌ Failed to communicate with checkout service. Please try again."
                await websocket_gateway.send_message(session_id, "text", error_msg)
                if request_id in self.pending_requests:
                    del self.pending_requests[request_id]
                return ""
            
            return ""
            
        except Exception as e:
            logger.error(f"Error in checkout request: {e}")
            error_msg = "I'm sorry, I encountered an error processing your checkout. Please try again."
            await websocket_gateway.send_message(session_id, "text", error_msg)
            return ""

    async def _handle_conversational_request(self, message: str, session_id: str, chat_session: ChatSession) -> str:
        """Handle conversational requests using Vertex AI with personalization context."""
        try:
            # Get personalization data
            personalization_context = await personalization_service.get_personalization_context(session_id)
            
            # Get conversation context for better responses
            conversation_context = await conversation_memory.get_conversation_context(session_id)
            
            # Build context-aware prompt
            context_info = personalization_service.build_personalization_context_string(personalization_context)
            recent_products_info = personalization_service.build_recent_products_context_string(
                self.recent_products.get(session_id, [])
            )
            
            # Enhance the message with shopping context and personalization
            enhanced_prompt = f"""
            You are CartMate, a friendly AI shopping assistant. Respond naturally to this message: "{message}"
            {context_info}
            {recent_products_info}
            {conversation_context}
            
            Guidelines:
            - Be helpful and conversational
            - Use the user's personalization context when relevant (style preferences, budget, image analysis)
            - If they ask about their style, reference their personalization data if available
            - If they ask about specific products (like "the glass jar", "that watch", etc.), refer to the recently shown products list
            - When referencing recently shown products, use their exact names and prices
            - Use conversation history to provide contextually appropriate responses
            - Offer shopping advice when relevant
            - Ask clarifying questions to better understand needs
            - If they want to search for specific products, let them know you can help with that
            - Keep responses concise but informative
            """
            
            response = chat_session.send_message(enhanced_prompt)
            
            # Store assistant response in conversation memory
            logger.info(f"Orchestrator storing assistant response in conversation memory: {response.text[:50]}...")
            success = await conversation_memory.store_message(
                session_id=session_id,
                message_type="text",
                content=response.text,
                sender="assistant"
            )
            logger.info(f"Orchestrator assistant response store result: {success}")
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error in conversational request: {e}")
            error_response = "I'm here to help with your shopping needs! What can I assist you with today?"
            
            # Store error response in conversation memory
            await conversation_memory.store_message(
                session_id=session_id,
                message_type="text",
                content=error_response,
                sender="assistant"
            )
            
            return error_response

    async def handle_response(self, response: A2AResponse) -> bool:
        """Handle responses from other agents and forward to user."""
        try:
            logger.info(f"Orchestrator received response for request {response.request_id}")
            
            if response.request_id not in self.pending_requests:
                logger.warning(f"Received response for unknown request {response.request_id}")
                return False
            
            request_info = self.pending_requests[response.request_id]
            session_id = request_info["session_id"]
            
            if response.success:
                # Process the response based on request type
                if request_info["request_type"] == "product_search":
                    # Update agent communication
                    agent_steps = [
                        AgentStep(id="calling", type="success", agent_name="Product Discovery Agent", message="Connected"),
                        AgentStep(id="processing", type="processing", agent_name="Product Discovery Agent", message="Processing results...")
                    ]
                    await websocket_gateway.update_agent_communication(session_id, agent_steps)
                    
                    # Format and send response
                    products = response.content
                    formatted_response = response_formatter.format_product_search_response(products, session_id)
                    
                    # Store recent products
                    if session_id not in self.recent_products:
                        self.recent_products[session_id] = []
                    self.recent_products[session_id].extend(products)
                    if len(self.recent_products[session_id]) > 10:
                        self.recent_products[session_id] = self.recent_products[session_id][-10:]
                    
                    # Store product search response in conversation memory
                    await conversation_memory.store_message(
                        session_id=session_id,
                        message_type="product_search",
                        content=formatted_response,
                        sender="agent",
                        metadata={
                            "agent_name": "Product Discovery Agent",
                            "products": products,
                            "product_count": len(products)
                        }
                    )
                    
                    # Send products as structured data
                    message_content = {
                        "message": formatted_response,
                        "products": products
                    }
                    await websocket_gateway.send_message(session_id, "text", message_content)
                    
                    # Send final success step
                    final_agent_steps = [
                        AgentStep(id="calling", type="success", agent_name="Product Discovery Agent", message="Connected"),
                        AgentStep(id="processing", type="success", agent_name="Product Discovery Agent", message="Completed")
                    ]
                    await websocket_gateway.update_agent_communication(session_id, final_agent_steps)
                    await websocket_gateway.send_message(session_id, "text", formatted_response)
                    
                elif request_info["request_type"] == "price_comparison":
                    # Format and send response
                    price_data = response.content
                    formatted_response = response_formatter.format_price_comparison_response(price_data, session_id)
                    
                    # Store price comparison response in conversation memory
                    await conversation_memory.store_message(
                        session_id=session_id,
                        message_type="price_comparison",
                        content=formatted_response,
                        sender="agent",
                        metadata={
                            "agent_name": "Price Comparison Agent",
                            "price_data": price_data
                        }
                    )
                    
                    # Send final success steps
                    final_agent_steps = [ 
                        AgentStep(id="calling", type="success", agent_name="Price Comparison Agent", message="Connected"),
                        AgentStep(id="searching", type="success", agent_name="Price Comparison Agent", message="Search completed"),
                        AgentStep(id="api_request", type="success", agent_name="Price Comparison Agent", message="API request completed"),
                        AgentStep(id="parsing", type="success", agent_name="Price Comparison Agent", message="Analysis completed")
                    ]
                    
                    additional_data = {
                        "message": formatted_response,
                        "price_comparison": price_data
                    }
                    await websocket_gateway.send_agent_communication_with_data(session_id, final_agent_steps, additional_data)
                    await websocket_gateway.send_message(session_id, "text", formatted_response)
                    
                elif request_info["request_type"] == "cart_management":
                    # Format and send response
                    cart_data = response.content
                    formatted_response = response_formatter.format_cart_management_response(cart_data, session_id)
                    
                    # Send final success steps
                    final_agent_steps = [
                        AgentStep(id="calling", type="success", agent_name="Cart Management Agent", message="Connected"),
                        AgentStep(id="processing", type="success", agent_name="Cart Management Agent", message="Items added to cart")
                    ]
                    
                    additional_data = {
                        "message": formatted_response,
                        "cart_update": cart_data
                    }
                    await websocket_gateway.send_agent_communication_with_data(session_id, final_agent_steps, additional_data)
                    await websocket_gateway.send_message(session_id, "text", formatted_response)
                    
                elif request_info["request_type"] == "checkout":
                    # Format and send response
                    checkout_data = response.content
                    formatted_response = response_formatter.format_checkout_response(checkout_data, session_id)
                    
                    # Send final success steps
                    final_agent_steps = [
                        AgentStep(id="calling", type="success", agent_name="Checkout Agent", message="Connected"),
                        AgentStep(id="processing", type="success", agent_name="Checkout Agent", message="Order processed")
                    ]
                    
                    additional_data = {
                        "message": formatted_response,
                        "checkout_result": checkout_data
                    }
                    await websocket_gateway.send_agent_communication_with_data(session_id, final_agent_steps, additional_data)
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
                elif request_info["request_type"] == "checkout":
                    error_message = f"❌ Checkout Agent encountered an error: {response.error}. Please try again."
                else:
                    error_message = f"❌ Product Discovery Agent encountered an error: {response.error}. Please try again."
                await websocket_gateway.send_message(session_id, "text", error_message)
            
            # Clean up pending request
            del self.pending_requests[response.request_id]
            return True
            
        except Exception as e:
            logger.error(f"Error handling response: {e}")
            return False

    async def clear_session_context(self, session_id: str):
        """Clear session-specific context (recent products, chat sessions, conversation memory)."""
        try:
            # Clear recent products
            if session_id in self.recent_products:
                del self.recent_products[session_id]
            
            # Clear chat session
            if session_id in self.chat_sessions:
                del self.chat_sessions[session_id]
            
            # Clear conversation memory
            await conversation_memory.clear_conversation_history(session_id)
            
            logger.info(f"Cleared session context for session {session_id}")
        except Exception as e:
            logger.error(f"Error clearing session context for session {session_id}: {e}")

# Create a single instance of the refactored agent
orchestrator_agent_refactored = OrchestratorAgent()

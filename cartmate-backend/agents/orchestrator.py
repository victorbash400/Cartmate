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
            analysis_prompt = f"""
            Analyze this user message for shopping intent: "{message}"
            
            Respond with JSON format:
            {{
                "needs_product_search": boolean,
                "search_query": "extracted product search terms if needed",
                "intent_type": "conversation|product_search|style_analysis|cart_management|price_comparison",
                "confidence": 0.0-1.0
            }}
            
            Set needs_product_search to TRUE if the user is:
            - Asking about products ("what products", "show me items", "what do you have")
            - Looking for specific items ("find shoes", "search for dresses")
            - Browsing inventory ("what's available", "what can I buy")
            - Requesting product recommendations ("suggest something", "what should I get")
            
            Examples that need product search:
            - "what products are available?"
            - "show me some clothes"
            - "find me a dress"
            - "what do you have in stock?"
            - "I'm looking for shoes"
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
            
            # Use a simple chat session for analysis
            temp_session = self.chat_model.start_chat()
            response = temp_session.send_message(analysis_prompt)
            
            # Try to parse JSON response
            import json
            try:
                response_text = response.text.strip()
                # Extract JSON if it's wrapped in markdown code blocks
                if "```json" in response_text:
                    start = response_text.find("```json") + 7
                    end = response_text.find("```", start)
                    response_text = response_text[start:end].strip()
                elif "```" in response_text:
                    start = response_text.find("```") + 3
                    end = response_text.find("```", start)
                    response_text = response_text[start:end].strip()
                
                intent_data = json.loads(response_text)
            except Exception as e:
                logger.warning(f"Failed to parse AI intent analysis: {e}")
                # Enhanced fallback logic
                message_lower = message.lower()
                product_keywords = ["product", "item", "available", "stock", "buy", "shop", "find", "search", "show me", "what do you have", "recommend", "suggest"]
                needs_search = any(keyword in message_lower for keyword in product_keywords)
                
                intent_data = {
                    "needs_product_search": needs_search,
                    "search_query": message if needs_search else "",
                    "intent_type": "product_search" if needs_search else "conversation",
                    "confidence": 0.7 if needs_search else 0.5
                }
            
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
            request = A2ARequest(
                id=request_id,
                sender=self.agent_id,
                receiver=product_agent.agent_id,
                request_type=A2ARequestType.SEARCH_PRODUCTS,
                conversation_id=conversation_id,
                content={
                    "query": search_query,
                    "session_id": session_id
                },
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

    async def _handle_conversational_request(self, message: str, session_id: str, chat_session: ChatSession) -> str:
        """
        Handle requests conversationally using Vertex AI.
        """
        try:
            # Enhance the message with shopping context
            enhanced_prompt = f"""
            You are CartMate, a friendly AI shopping assistant. Respond naturally to this message: "{message}"
            
            Guidelines:
            - Be helpful and conversational
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
                else:
                    # Generic response handling
                    await websocket_gateway.send_message(session_id, "text", str(response.content))
            else:
                # Handle error response
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

# Create a single instance of the agent
orchestrator_agent = OrchestratorAgent()
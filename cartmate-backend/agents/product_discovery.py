import logging
import asyncio
from services.boutique.product_catalog_client import product_catalog_client
from agents.base import BaseAgent
from models.a2a import A2AMessage, A2ARequest, A2AResponse, A2AMessageType, A2ARequestType, A2AFrontendNotification
from google.protobuf.json_format import MessageToDict

logger = logging.getLogger(__name__)

class ProductDiscoveryAgent(BaseAgent):
    """
    Agent responsible for searching for products via A2A messaging.
    """
    
    def __init__(self):
        super().__init__("product_discovery_001", "product_discovery")
        self.registration.capabilities = ["search_products", "get_product_details"]

    async def start(self):
        """Start the product discovery agent"""
        await super().start()
        logger.info("Product Discovery Agent started")

    async def handle_message(self, message: A2AMessage) -> bool:
        """
        Handle incoming A2A messages.
        """
        try:
            if message.type == A2AMessageType.REQUEST:
                request = A2ARequest.model_validate(message.model_dump())
                return await self.handle_request(request)
            else:
                logger.info(f"ProductDiscoveryAgent received {message.type} message: {message.content}")
                return True
        except Exception as e:
            logger.error(f"Error handling message in ProductDiscoveryAgent: {e}")
            return False

    async def handle_request(self, request: A2ARequest) -> bool:
        """
        Handle incoming requests from other agents.
        """
        logger.info(f"ProductDiscoveryAgent received request: {request.request_type}")
        
        try:
            if request.request_type == A2ARequestType.SEARCH_PRODUCTS:
                query = request.content.get("query", "")
                logger.info(f"Searching for products: {query}")
                
                # Send notification that we're processing the request
                notification = A2AFrontendNotification(
                    sender=self.agent_id,
                    receiver=request.sender,
                    notification_type="agent_thinking",
                    agent_name="Product Discovery Agent",
                    agent_id=self.agent_id,
                    content=f"Searching for products matching '{query}'"
                )
                await self.send_message(request.sender, notification)
                
                # Perform the search
                products = product_catalog_client.search_products(query)
                logger.info(f"Found {len(products)} products.")
                
                # Send notification about completion
                completion_notification = A2AFrontendNotification(
                    sender=self.agent_id,
                    receiver=request.sender,
                    notification_type="agent_action",
                    agent_name="Product Discovery Agent",
                    agent_id=self.agent_id,
                    content=f"Found {len(products)} products for '{query}'"
                )
                await self.send_message(request.sender, completion_notification)
                
                # Convert protobuf objects to dictionaries
                product_dicts = [MessageToDict(p) for p in products]
                
                # Send response back to requester
                await self.send_response(
                    request.sender,
                    request.id,
                    product_dicts,
                    success=True,
                    conversation_id=request.conversation_id
                )
                
                return True
            else:
                logger.warning(f"ProductDiscoveryAgent received unsupported request type: {request.request_type}")
                
                # Send error response
                await self.send_response(
                    request.sender,
                    request.id,
                    [],
                    success=False,
                    error=f"Unsupported request type: {request.request_type}",
                    conversation_id=request.conversation_id
                )
                
                return False
                
        except Exception as e:
            logger.error(f"Error processing request in ProductDiscoveryAgent: {e}")
            
            # Send error notification
            error_notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver=request.sender,
                notification_type="agent_error",
                agent_name="Product Discovery Agent",
                agent_id=self.agent_id,
                content=f"Error searching for products: {str(e)}"
            )
            await self.send_message(request.sender, error_notification)
            
            # Send error response
            await self.send_response(
                request.sender,
                request.id,
                [],
                success=False,
                error=str(e),
                conversation_id=request.conversation_id
            )
            
            return False

# Singleton instance
product_discovery_agent = ProductDiscoveryAgent()

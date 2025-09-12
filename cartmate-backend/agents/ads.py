"""
Ads Agent - Handles ad serving and context-based advertising
"""
import logging
import asyncio
import grpc
from typing import Dict, Any, List, Optional
from agents.base import BaseAgent
from models.a2a import A2AMessage, A2ARequest, A2AResponse, A2ARequestType, A2AMessageType, A2AFrontendNotification
from a2a.coordinator import a2a_coordinator
from api.websocket import websocket_gateway
from protos.generated import demo_pb2, demo_pb2_grpc
from services.storage.redis_client import redis_client

logger = logging.getLogger(__name__)

class AdsAgent(BaseAgent):
    """
    Agent responsible for serving contextual ads based on user interactions.
    Integrates with Google's Online Boutique AdService via gRPC.
    """
    
    def __init__(self):
        super().__init__("ads_001", "ads")
        self.registration.capabilities = [
            "get_ads",
            "contextual_ads",
            "random_ads"
        ]
        
        # gRPC client for ads service
        self.ads_channel = None
        self.ads_stub = None
        
    async def start(self):
        """Initialize the ads agent"""
        await super().start()
        
        # Initialize gRPC connection to ads service with retry
        await self._initialize_ads_connection()
            
        logger.info("Ads Agent started and ready for ad operations")

    async def _initialize_ads_connection(self, max_retries=3, delay=2):
        """Initialize gRPC connection with retry logic - graceful failure if service unavailable"""
        from config.settings import settings
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to connect to AdService (attempt {attempt + 1}/{max_retries})")
                
                self.ads_channel = grpc.insecure_channel(
                    f"{settings.AD_SERVICE_HOST}:{settings.AD_SERVICE_PORT}"
                )
                self.ads_stub = demo_pb2_grpc.AdServiceStub(self.ads_channel)
                
                # Test the connection with a simple call
                test_request = demo_pb2.AdRequest(context_keys=["test"])
                try:
                    # This will work even with test data
                    self.ads_stub.GetAds(test_request, timeout=3)
                    logger.info("Ads Agent connected to AdService successfully")
                    return
                except grpc.RpcError as e:
                    if e.code() in [grpc.StatusCode.UNAVAILABLE, grpc.StatusCode.DEADLINE_EXCEEDED]:
                        raise
                    else:
                        # Other errors are expected for test data
                        logger.info("Ads Agent connected to AdService successfully")
                        return
                        
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.warning(f"Failed to connect to AdService after {max_retries} attempts: {e}")
                    logger.warning("Ads Agent will start in offline mode - ads functionality will be limited")
                    # Don't raise the exception - allow the agent to start in offline mode
                    self.ads_stub = None
                    self.ads_channel = None
                    return

    async def handle_message(self, message: A2AMessage) -> bool:
        """Handle incoming messages"""
        try:
            if message.type == A2AMessageType.REQUEST:
                request = A2ARequest.model_validate(message.model_dump())
                return await self.handle_request(request)
            else:
                logger.info(f"AdsAgent received {message.type} message: {message.content}")
                return True
        except Exception as e:
            logger.error(f"Error handling message in AdsAgent: {e}")
            return False

    async def handle_request(self, request: A2ARequest) -> bool:
        """Handle ads requests from other agents"""
        logger.info(f"AdsAgent received request: {request.request_type}")
        
        try:
            if request.request_type == A2ARequestType.GET_ADS:
                return await self._handle_get_ads(request)
            else:
                logger.warning(f"Unsupported request type: {request.request_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error handling ads request: {e}")
            return False

    async def _handle_get_ads(self, request: A2ARequest) -> bool:
        """Get contextual ads based on user context"""
        try:
            # Parse request content
            content_dict = request.content if isinstance(request.content, dict) else {}
            
            session_id = content_dict.get("session_id")
            context_keys = content_dict.get("context_keys", [])
            
            if not session_id:
                logger.error("Missing session_id in get ads request")
                return False
            
            # Check if ads service is available
            if not self.ads_stub:
                logger.warning("Ads service not available - providing mock ads response")
                # Provide mock ads when service is unavailable
                mock_ads = [
                    {
                        "redirect_url": "/product/mock1",
                        "text": "Special offer! 20% off selected items"
                    },
                    {
                        "redirect_url": "/product/mock2", 
                        "text": "New arrivals - Shop now!"
                    }
                ]
                
                # Send ads to frontend
                await websocket_gateway.send_message(session_id, "ads", {
                    "ads": mock_ads,
                    "context": context_keys
                })
                
                # Send response back to orchestrator
                response = A2AResponse(
                    request_id=request.id,
                    sender=self.agent_id,
                    receiver=request.sender,
                    content={"ads": mock_ads, "context": context_keys},
                    success=True
                )
                
                return await self.send_message(request.sender, response)
            
            # Create ads request
            ads_request = demo_pb2.AdRequest(context_keys=context_keys)
            
            # Call ads service
            logger.info(f"Calling ads service with context: {context_keys}")
            ads_response = self.ads_stub.GetAds(ads_request)
            
            # Convert response to dict
            ads_list = []
            for ad in ads_response.ads:
                ads_list.append({
                    "redirect_url": ad.redirect_url,
                    "text": ad.text
                })
            
            logger.info(f"Received {len(ads_list)} ads from service")
            
            # Send ads to frontend
            await websocket_gateway.send_message(session_id, "ads", {
                "ads": ads_list,
                "context": context_keys
            })
            
            # Send response back to orchestrator
            response = A2AResponse(
                request_id=request.id,
                sender=self.agent_id,
                receiver=request.sender,
                content={"ads": ads_list, "context": context_keys},
                success=True
            )
            
            logger.info(f"Sending ads response back to {request.sender} for request {request.id}")
            success = await self.send_message(request.sender, response)
            logger.info(f"Ads response sent successfully: {success}")
            return success
            
        except Exception as e:
            logger.error(f"Error in _handle_get_ads: {e}")
            return False

    async def stop(self):
        """Clean up resources"""
        if self.ads_channel:
            self.ads_channel.close()
        await super().stop()

# Create global instance
ads_agent = AdsAgent()

"""
Cart Management Agent - Handles shopping cart operations
"""
import logging
import grpc
import asyncio
from typing import Dict, Any, List, Optional
from agents.base import BaseAgent
from models.a2a import A2AMessage, A2ARequest, A2AResponse, A2ARequestType, A2AMessageType, A2AFrontendNotification
from a2a.coordinator import a2a_coordinator
from api.websocket import websocket_gateway
from protos.generated import demo_pb2, demo_pb2_grpc
from services.storage.redis_client import redis_client

logger = logging.getLogger(__name__)

class CartManagementAgent(BaseAgent):
    """
    Agent responsible for managing shopping cart operations.
    Integrates with Google's Online Boutique CartService via gRPC.
    """
    
    def __init__(self):
        super().__init__("cart_management_001", "cart_management")
        self.registration.capabilities = [
            "add_to_cart",
            "remove_from_cart", 
            "get_cart",
            "clear_cart",
            "update_quantity"
        ]
        
        # gRPC client for cart service
        self.cart_channel = None
        self.cart_stub = None
        
    async def start(self):
        """Initialize the cart management agent"""
        await super().start()
        
        # Initialize gRPC connection to cart service with retry
        await self._initialize_cart_connection()
            
        logger.info("Cart Management Agent started and ready for cart operations")

    async def _initialize_cart_connection(self, max_retries=5, delay=2):
        """Initialize gRPC connection with retry logic"""
        from config.settings import settings
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to connect to CartService (attempt {attempt + 1}/{max_retries})")
                
                self.cart_channel = grpc.insecure_channel(
                    f"{settings.CART_SERVICE_HOST}:{settings.CART_SERVICE_PORT}"
                )
                self.cart_stub = demo_pb2_grpc.CartServiceStub(self.cart_channel)
                
                # Test the connection with a simple call
                test_request = demo_pb2.GetCartRequest(user_id="test_connection")
                try:
                    # This will fail but should establish the connection
                    self.cart_stub.GetCart(test_request, timeout=5)
                except grpc.RpcError as e:
                    if e.code() == grpc.StatusCode.NOT_FOUND:
                        # This is expected - the test user doesn't exist, but connection works
                        logger.info("Cart Management Agent connected to CartService successfully")
                        return
                    else:
                        raise
                        
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Failed to connect to CartService after {max_retries} attempts: {e}")
                    raise

    async def _test_cart_connection(self) -> bool:
        """Test if cart service connection is working"""
        try:
            if not self.cart_stub:
                return False
            
            # Try a simple call with a short timeout
            test_request = demo_pb2.GetCartRequest(user_id="connection_test")
            try:
                self.cart_stub.GetCart(test_request, timeout=2)
            except grpc.RpcError as e:
                if e.code() in [grpc.StatusCode.NOT_FOUND, grpc.StatusCode.OK]:
                    # Connection is working (NOT_FOUND is expected for test user)
                    return True
                else:
                    logger.warning(f"Cart service connection test failed: {e}")
                    return False
            return True
            
        except Exception as e:
            logger.warning(f"Cart service connection test failed: {e}")
            return False

    async def handle_message(self, message: A2AMessage) -> bool:
        """Handle incoming messages"""
        try:
            if message.type == A2AMessageType.REQUEST:
                request = A2ARequest.model_validate(message.model_dump())
                return await self.handle_request(request)
            else:
                logger.info(f"CartManagementAgent received {message.type} message: {message.content}")
                return True
        except Exception as e:
            logger.error(f"Error handling message in CartManagementAgent: {e}")
            return False

    async def handle_request(self, request: A2ARequest) -> bool:
        """Handle cart management requests from other agents"""
        logger.info(f"CartManagementAgent received request: {request.request_type}")
        
        try:
            if request.request_type == A2ARequestType.ADD_TO_CART:
                return await self._handle_add_to_cart(request)
            elif request.request_type == A2ARequestType.UPDATE_CART_ITEM:
                return await self._handle_update_cart_item(request)
            elif request.request_type == A2ARequestType.REMOVE_FROM_CART:
                return await self._handle_remove_from_cart(request)
            elif request.request_type == A2ARequestType.GET_CART:
                return await self._handle_get_cart(request)
            elif request.request_type == A2ARequestType.CLEAR_CART:
                return await self._handle_clear_cart(request)
            else:
                logger.warning(f"Unsupported request type: {request.request_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error handling cart request: {e}")
            return False

    async def _handle_add_to_cart(self, request: A2ARequest) -> bool:
        """Add items to cart"""
        try:
            session_id = request.content.get("session_id")
            products = request.content.get("products", [])
            
            if not session_id or not products:
                logger.error("Missing session_id or products in add to cart request")
                return False
            
            # Check if cart service is available and test connection
            if not self.cart_stub:
                logger.error("Cart service not available - cannot add items to cart")
                return False
            
            # Test connection before proceeding
            if not await self._test_cart_connection():
                logger.error("Cart service connection failed - cannot add items to cart")
                return False
            
            # Convert session_id to user_id for cart service
            user_id = f"user_{session_id}"
            
            # Send notification that we're processing
            notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver=request.sender,
                notification_type="agent_thinking",
                agent_name="Cart Management Agent",
                agent_id=self.agent_id,
                content="Adding items to cart..."
            )
            await self.send_message(request.sender, notification)
            
            added_items = []
            failed_items = []
            
            # Add each product to cart
            for product in products:
                try:
                    product_id = product.get("id")
                    quantity = product.get("quantity", 1)
                    
                    if not product_id:
                        failed_items.append(product)
                        continue
                    
                    # Create cart item request
                    cart_item = demo_pb2.CartItem(
                        product_id=product_id,
                        quantity=quantity
                    )
                    
                    add_request = demo_pb2.AddItemRequest(
                        user_id=user_id,
                        item=cart_item
                    )
                    
                    # Call cart service
                    response = self.cart_stub.AddItem(add_request)
                    added_items.append({
                        "id": product_id,
                        "name": product.get("name", "Unknown Product"),
                        "quantity": quantity
                    })
                    
                except Exception as e:
                    logger.error(f"Failed to add product {product.get('id')} to cart: {e}")
                    failed_items.append(product)
            
            # Prepare response
            response_content = {
                "success": len(added_items) > 0,
                "added_items": added_items,
                "failed_items": failed_items,
                "total_added": len(added_items)
            }
            
            # Send completion notification
            if added_items:
                completion_msg = f"✅ Added {len(added_items)} item(s) to cart"
                if failed_items:
                    completion_msg += f" ({len(failed_items)} failed)"
            else:
                completion_msg = "❌ Failed to add items to cart"
                
            completion_notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver=request.sender,
                notification_type="agent_action",
                agent_name="Cart Management Agent",
                agent_id=self.agent_id,
                content=completion_msg
            )
            await self.send_message(request.sender, completion_notification)
            
            # Send response back to orchestrator
            response = A2AResponse(
                request_id=request.id,
                sender=self.agent_id,
                receiver=request.sender,
                content=response_content,
                success=len(added_items) > 0
            )
            
            logger.info(f"Sending cart response back to {request.sender} for request {request.id}")
            success = await self.send_message(request.sender, response)
            logger.info(f"Cart response sent successfully: {success}")
            return success
            
        except Exception as e:
            logger.error(f"Error in _handle_add_to_cart: {e}")
            return False

    async def _handle_update_cart_item(self, request: A2ARequest) -> bool:
        """Update quantity of an item in cart"""
        try:
            session_id = request.content.get("session_id")
            product_id = request.content.get("product_id")
            quantity = request.content.get("quantity")
            
            if not session_id or not product_id or quantity is None:
                logger.error("Missing required fields in update cart item request")
                return False
            
            # Check if cart service is available
            if not self.cart_stub:
                logger.error("Cart service not available - cannot update cart item")
                return False
            
            # Test connection before proceeding
            if not await self._test_cart_connection():
                logger.error("Cart service connection failed - cannot update cart item")
                return False
            
            # Convert session_id to user_id for cart service
            user_id = f"user_{session_id}"
            
            # Send notification
            notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver=request.sender,
                notification_type="agent_thinking",
                agent_name="Cart Management Agent",
                agent_id=self.agent_id,
                content="Updating cart item..."
            )
            await self.send_message(request.sender, notification)
            
            # Update cart item
            cart_item = demo_pb2.CartItem(
                product_id=product_id,
                quantity=quantity
            )
            
            add_request = demo_pb2.AddItemRequest(user_id=user_id, item=cart_item)
            self.cart_stub.AddItem(add_request)
            
            # Send completion notification
            completion_notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver=request.sender,
                notification_type="agent_action",
                agent_name="Cart Management Agent",
                agent_id=self.agent_id,
                content=f"✅ Updated quantity to {quantity}"
            )
            await self.send_message(request.sender, completion_notification)
            
            # Send response
            response = A2AResponse(
                request_id=request.id,
                sender=self.agent_id,
                receiver=request.sender,
                content={"success": True, "message": f"Updated quantity to {quantity}"},
                success=True
            )
            
            return await self.send_message(request.sender, response)
            
        except Exception as e:
            logger.error(f"Error in _handle_update_cart_item: {e}")
            return False

    async def _handle_remove_from_cart(self, request: A2ARequest) -> bool:
        """Remove an item from cart"""
        try:
            session_id = request.content.get("session_id")
            product_id = request.content.get("product_id")
            
            if not session_id or not product_id:
                logger.error("Missing required fields in remove from cart request")
                return False
            
            # Check if cart service is available
            if not self.cart_stub:
                logger.error("Cart service not available - cannot remove from cart")
                return False
            
            # Test connection before proceeding
            if not await self._test_cart_connection():
                logger.error("Cart service connection failed - cannot remove from cart")
                return False
            
            # Convert session_id to user_id for cart service
            user_id = f"user_{session_id}"
            
            # Send notification
            notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver=request.sender,
                notification_type="agent_thinking",
                agent_name="Cart Management Agent",
                agent_id=self.agent_id,
                content="Removing item from cart..."
            )
            await self.send_message(request.sender, notification)
            
            # Get current cart contents
            get_request = demo_pb2.GetCartRequest(user_id=user_id)
            cart_response = self.cart_stub.GetCart(get_request)
            
            # Filter out the item we want to remove
            remaining_items = []
            for item in cart_response.items:
                if item.product_id != product_id and item.quantity > 0:
                    remaining_items.append(item)
            
            logger.info(f"Removing {product_id}, keeping {len(remaining_items)} items")
            
            # Clear the entire cart
            clear_request = demo_pb2.EmptyCartRequest(user_id=user_id)
            self.cart_stub.EmptyCart(clear_request)
            
            # Re-add all items except the one we want to remove
            for item in remaining_items:
                add_request = demo_pb2.AddItemRequest(user_id=user_id, item=item)
                self.cart_stub.AddItem(add_request)
            
            logger.info(f"Removed item {product_id} from cart for user {user_id}")
            
            # Send completion notification
            completion_notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver=request.sender,
                notification_type="agent_action",
                agent_name="Cart Management Agent",
                agent_id=self.agent_id,
                content="✅ Item removed from cart"
            )
            await self.send_message(request.sender, completion_notification)
            
            # Send response
            response = A2AResponse(
                request_id=request.id,
                sender=self.agent_id,
                receiver=request.sender,
                content={"success": True, "message": "Item removed from cart"},
                success=True
            )
            
            return await self.send_message(request.sender, response)
            
        except Exception as e:
            logger.error(f"Error in _handle_remove_from_cart: {e}")
            return False

    async def _handle_get_cart(self, request: A2ARequest) -> bool:
        """Get current cart contents"""
        try:
            session_id = request.content.get("session_id")
            if not session_id:
                logger.error("Missing session_id in get cart request")
                return False
            
            user_id = f"user_{session_id}"
            
            # Send notification
            notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver=request.sender,
                notification_type="agent_thinking",
                agent_name="Cart Management Agent",
                agent_id=self.agent_id,
                content="Retrieving cart contents..."
            )
            await self.send_message(request.sender, notification)
            
            # Get cart from service
            get_request = demo_pb2.GetCartRequest(user_id=user_id)
            cart_response = self.cart_stub.GetCart(get_request)
            
            # Convert to frontend-friendly format
            cart_items = []
            for item in cart_response.items:
                cart_items.append({
                    "product_id": item.product_id,
                    "quantity": item.quantity
                })
            
            response_content = {
                "user_id": cart_response.user_id,
                "items": cart_items,
                "total_items": len(cart_items)
            }
            
            # Send response
            response = A2AResponse(
                request_id=request.id,
                sender=self.agent_id,
                receiver=request.sender,
                content=response_content,
                success=True
            )
            
            return await self.send_message(request.sender, response)
            
        except Exception as e:
            logger.error(f"Error in _handle_get_cart: {e}")
            return False

    async def _handle_clear_cart(self, request: A2ARequest) -> bool:
        """Clear the entire cart"""
        try:
            session_id = request.content.get("session_id")
            if not session_id:
                logger.error("Missing session_id in clear cart request")
                return False
            
            user_id = f"user_{session_id}"
            
            # Send notification
            notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver=request.sender,
                notification_type="agent_thinking",
                agent_name="Cart Management Agent",
                agent_id=self.agent_id,
                content="Clearing cart..."
            )
            await self.send_message(request.sender, notification)
            
            # Clear cart
            clear_request = demo_pb2.EmptyCartRequest(user_id=user_id)
            self.cart_stub.EmptyCart(clear_request)
            
            # Send completion notification
            completion_notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver=request.sender,
                notification_type="agent_action",
                agent_name="Cart Management Agent",
                agent_id=self.agent_id,
                content="✅ Cart cleared successfully"
            )
            await self.send_message(request.sender, completion_notification)
            
            # Send response
            response = A2AResponse(
                request_id=request.id,
                sender=self.agent_id,
                receiver=request.sender,
                content={"success": True, "message": "Cart cleared"},
                success=True
            )
            
            return await self.send_message(request.sender, response)
            
        except Exception as e:
            logger.error(f"Error in _handle_clear_cart: {e}")
            return False

    async def stop(self):
        """Clean up resources"""
        if self.cart_channel:
            self.cart_channel.close()
        await super().stop()

# Create global instance
cart_management_agent = CartManagementAgent()


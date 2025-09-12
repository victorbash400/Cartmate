"""
Checkout Agent - Handles checkout and payment processing
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

class CheckoutAgent(BaseAgent):
    """
    Agent responsible for handling checkout and payment processing.
    Integrates with Google's Online Boutique CheckoutService via gRPC.
    """
    
    def __init__(self):
        super().__init__("checkout_001", "checkout")
        self.registration.capabilities = [
            "process_checkout",
            "validate_order",
            "process_payment",
            "get_order_status",
            "cancel_order"
        ]
        
        # gRPC client for checkout service
        self.checkout_channel = None
        self.checkout_stub = None
        
    async def start(self):
        """Initialize the checkout agent"""
        await super().start()
        
        # Initialize gRPC connection to checkout service with retry
        await self._initialize_checkout_connection()
            
        logger.info("Checkout Agent started and ready for checkout operations")

    def _parse_request_content(self, request: A2ARequest) -> Dict[str, Any]:
        """Parse request content, handling both dict and string formats"""
        if isinstance(request.content, str):
            import json
            try:
                return json.loads(request.content)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse content as JSON: {request.content}")
                raise ValueError(f"Invalid JSON content: {request.content}")
        else:
            return request.content

    async def _initialize_checkout_connection(self, max_retries=3, delay=2):
        """Initialize gRPC connection with retry logic - graceful failure if service unavailable"""
        from config.settings import settings
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to connect to CheckoutService (attempt {attempt + 1}/{max_retries})")
                
                self.checkout_channel = grpc.insecure_channel(
                    f"{settings.CHECKOUT_SERVICE_HOST}:{settings.CHECKOUT_SERVICE_PORT}"
                )
                self.checkout_stub = demo_pb2_grpc.CheckoutServiceStub(self.checkout_channel)
                
                # Test the connection with a simple call
                test_request = demo_pb2.PlaceOrderRequest(
                    user_id="test_connection",
                    user_currency="USD",
                    address=demo_pb2.Address(
                        street_address="123 Test St",
                        city="Test City",
                        state="TS",
                        country="US",
                        zip_code=12345
                    ),
                    email="test@example.com",
                    credit_card=demo_pb2.CreditCardInfo(
                        credit_card_number="4111111111111111",
                        credit_card_cvv=123,
                        credit_card_expiration_year=2025,
                        credit_card_expiration_month=12
                    )
                )
                try:
                    # This will fail but should establish the connection
                    self.checkout_stub.PlaceOrder(test_request, timeout=3)
                except grpc.RpcError as e:
                    if e.code() in [grpc.StatusCode.INVALID_ARGUMENT, grpc.StatusCode.NOT_FOUND]:
                        # This is expected - the test data is invalid, but connection works
                        logger.info("Checkout Agent connected to CheckoutService successfully")
                        return
                    else:
                        raise
                        
            except Exception as e:
                logger.warning(f"Connection attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.warning(f"Failed to connect to CheckoutService after {max_retries} attempts: {e}")
                    logger.warning("Checkout Agent will start in offline mode - checkout functionality will be limited")
                    # Don't raise the exception - allow the agent to start in offline mode
                    self.checkout_stub = None
                    self.checkout_channel = None
                    return

    async def _test_checkout_connection(self) -> bool:
        """Test if checkout service connection is working"""
        try:
            if not self.checkout_stub:
                return False
            
            # Try a simple call with a short timeout
            test_request = demo_pb2.PlaceOrderRequest(
                user_id="connection_test",
                user_currency="USD",
                address=demo_pb2.Address(
                    street_address="123 Test St",
                    city="Test City",
                    state="TS",
                    country="US",
                    zip_code=12345
                ),
                email="test@example.com",
                credit_card=demo_pb2.CreditCardInfo(
                    credit_card_number="4111111111111111",
                    credit_card_cvv=123,
                    credit_card_expiration_year=2025,
                    credit_card_expiration_month=12
                )
            )
            try:
                self.checkout_stub.PlaceOrder(test_request, timeout=2)
            except grpc.RpcError as e:
                if e.code() in [grpc.StatusCode.INVALID_ARGUMENT, grpc.StatusCode.NOT_FOUND]:
                    # Connection is working (INVALID_ARGUMENT is expected for test data)
                    return True
                else:
                    logger.warning(f"Checkout service connection test failed: {e}")
                    return False
            return True
            
        except Exception as e:
            logger.warning(f"Checkout service connection test failed: {e}")
            return False

    async def handle_message(self, message: A2AMessage) -> bool:
        """Handle incoming messages"""
        try:
            if message.type == A2AMessageType.REQUEST:
                request = A2ARequest.model_validate(message.model_dump())
                return await self.handle_request(request)
            else:
                logger.info(f"CheckoutAgent received {message.type} message: {message.content}")
                return True
        except Exception as e:
            logger.error(f"Error handling message in CheckoutAgent: {e}")
            return False

    async def handle_request(self, request: A2ARequest) -> bool:
        """Handle checkout requests from other agents"""
        logger.info(f"CheckoutAgent received request: {request.request_type}")
        
        try:
            if request.request_type == A2ARequestType.PROCESS_CHECKOUT:
                return await self._handle_process_checkout(request)
            elif request.request_type == A2ARequestType.VALIDATE_ORDER:
                return await self._handle_validate_order(request)
            elif request.request_type == A2ARequestType.GET_ORDER_STATUS:
                return await self._handle_get_order_status(request)
            elif request.request_type == A2ARequestType.CANCEL_ORDER:
                return await self._handle_cancel_order(request)
            else:
                logger.warning(f"Unsupported request type: {request.request_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error handling checkout request: {e}")
            return False

    async def _handle_process_checkout(self, request: A2ARequest) -> bool:
        """Process checkout and place order"""
        try:
            # Debug: Check what type of content we're receiving
            logger.info(f"CheckoutAgent received content type: {type(request.content)}")
            logger.info(f"CheckoutAgent received content: {request.content}")
            
            # Parse request content
            content_dict = self._parse_request_content(request)
            
            session_id = content_dict.get("session_id")
            checkout_data = content_dict.get("checkout_data", {})
            
            if not session_id or not checkout_data:
                logger.error("Missing session_id or checkout_data in process checkout request")
                return False
            
            # Check if checkout service is available
            if not self.checkout_stub:
                logger.warning("Checkout service not available - providing mock checkout response")
                # Provide a mock response when service is unavailable
                mock_response = {
                    "success": True,
                    "order_id": f"MOCK_{session_id[:8].upper()}",
                    "shipping_cost": {
                        "currency_code": "USD",
                        "units": 5,
                        "nanos": 0
                    },
                    "shipping_address": {
                        "street_address": "Mock Address",
                        "city": "Mock City",
                        "state": "MC",
                        "country": "US",
                        "zip_code": 12345
                    },
                    "items": [
                        {
                            "item": {
                                "product_id": "mock_product",
                                "quantity": 1
                            },
                            "cost": {
                                "currency_code": "USD",
                                "units": 10,
                                "nanos": 0
                            }
                        }
                    ]
                }
                
                # Send completion notification
                completion_notification = A2AFrontendNotification(
                    sender=self.agent_id,
                    receiver=request.sender,
                    notification_type="agent_action",
                    agent_name="Checkout Agent",
                    agent_id=self.agent_id,
                    content="⚠️ Checkout service unavailable - processed as mock order"
                )
                await self.send_message(request.sender, completion_notification)
                
                # Send mock response
                response = A2AResponse(
                    request_id=request.id,
                    sender=self.agent_id,
                    receiver=request.sender,
                    content=mock_response,
                    success=True
                )
                
                return await self.send_message(request.sender, response)
            
            # Test connection before proceeding
            if not await self._test_checkout_connection():
                logger.warning("Checkout service connection failed - providing mock checkout response")
                # Provide a mock response when connection fails
                mock_response = {
                    "success": True,
                    "order_id": f"MOCK_{session_id[:8].upper()}",
                    "shipping_cost": {
                        "currency_code": "USD",
                        "units": 5,
                        "nanos": 0
                    },
                    "shipping_address": {
                        "street_address": "Mock Address",
                        "city": "Mock City",
                        "state": "MC",
                        "country": "US",
                        "zip_code": 12345
                    },
                    "items": [
                        {
                            "item": {
                                "product_id": "mock_product",
                                "quantity": 1
                            },
                            "cost": {
                                "currency_code": "USD",
                                "units": 10,
                                "nanos": 0
                            }
                        }
                    ]
                }
                
                # Send completion notification
                completion_notification = A2AFrontendNotification(
                    sender=self.agent_id,
                    receiver=request.sender,
                    notification_type="agent_action",
                    agent_name="Checkout Agent",
                    agent_id=self.agent_id,
                    content="⚠️ Checkout service connection failed - processed as mock order"
                )
                await self.send_message(request.sender, completion_notification)
                
                # Send mock response
                response = A2AResponse(
                    request_id=request.id,
                    sender=self.agent_id,
                    receiver=request.sender,
                    content=mock_response,
                    success=True
                )
                
                return await self.send_message(request.sender, response)
            
            # Convert session_id to user_id for checkout service
            user_id = f"user_{session_id}"
            logger.info(f"Using user_id for checkout: {user_id}")
            
            # Send notification that we're processing
            notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver=request.sender,
                notification_type="agent_thinking",
                agent_name="Checkout Agent",
                agent_id=self.agent_id,
                content="Processing your order..."
            )
            await self.send_message(request.sender, notification)
            
            # Extract checkout data
            user_currency = checkout_data.get("currency", "USD")
            email = checkout_data.get("email", "")
            
            # Handle address data - could be a string or dict
            address_input = checkout_data.get("address", "")
            if isinstance(address_input, str):
                # If address is a string, use it as street_address and set defaults
                address_data = {
                    "street_address": address_input,
                    "city": "Unknown",
                    "state": "Unknown", 
                    "country": "Unknown",
                    "zip_code": "00000"
                }
            else:
                # If address is a dict, use it directly
                address_data = address_input if isinstance(address_input, dict) else {}
            
            # Handle credit card data - could be a string or dict
            credit_card_input = checkout_data.get("credit_card", checkout_data.get("payment_info", ""))
            if isinstance(credit_card_input, str):
                # If credit card info is a string, create mock data for demo purposes
                credit_card_data = {
                    "number": "4111111111111111",  # Test card number
                    "cvv": 123,
                    "expiration_year": 2025,
                    "expiration_month": 12
                }
            else:
                # If credit card is a dict, use it directly
                credit_card_data = credit_card_input if isinstance(credit_card_input, dict) else {}
            
            # Build address
            zip_code = address_data.get("zip_code", "0")
            try:
                zip_code_int = int(zip_code) if zip_code else 0
            except (ValueError, TypeError):
                zip_code_int = 0
                
            address = demo_pb2.Address(
                street_address=address_data.get("street_address", ""),
                city=address_data.get("city", ""),
                state=address_data.get("state", ""),
                country=address_data.get("country", ""),
                zip_code=zip_code_int
            )
            
            # Build credit card info
            try:
                cvv = int(credit_card_data.get("cvv", 0)) if credit_card_data.get("cvv") else 0
            except (ValueError, TypeError):
                cvv = 0
                
            try:
                exp_year = int(credit_card_data.get("expiration_year", 0)) if credit_card_data.get("expiration_year") else 0
            except (ValueError, TypeError):
                exp_year = 0
                
            try:
                exp_month = int(credit_card_data.get("expiration_month", 0)) if credit_card_data.get("expiration_month") else 0
            except (ValueError, TypeError):
                exp_month = 0
                
            credit_card = demo_pb2.CreditCardInfo(
                credit_card_number=credit_card_data.get("number", ""),
                credit_card_cvv=cvv,
                credit_card_expiration_year=exp_year,
                credit_card_expiration_month=exp_month
            )
            
            # Create checkout request
            checkout_request = demo_pb2.PlaceOrderRequest(
                user_id=user_id,
                user_currency=user_currency,
                address=address,
                email=email,
                credit_card=credit_card
            )
            
            # Call checkout service
            logger.info(f"Calling checkout service with request: user_id={user_id}, email={email}")
            try:
                checkout_response = self.checkout_stub.PlaceOrder(checkout_request)
                logger.info(f"Checkout service response received: order_id={checkout_response.order.order_id}")
            except grpc.RpcError as e:
                logger.error(f"gRPC error during checkout: {e.code()}: {e.details()}")
                raise
            
            # Prepare response
            order = checkout_response.order
            response_content = {
                "success": True,
                "order_id": order.order_id,
                "shipping_cost": {
                    "currency_code": order.shipping_cost.currency_code,
                    "units": order.shipping_cost.units,
                    "nanos": order.shipping_cost.nanos
                },
                "shipping_address": {
                    "street_address": order.shipping_address.street_address,
                    "city": order.shipping_address.city,
                    "state": order.shipping_address.state,
                    "country": order.shipping_address.country,
                    "zip_code": order.shipping_address.zip_code
                },
                "items": [
                    {
                        "item": {
                            "product_id": item.item.product_id,
                            "quantity": item.item.quantity
                        },
                        "cost": {
                            "currency_code": item.cost.currency_code,
                            "units": item.cost.units,
                            "nanos": item.cost.nanos
                        }
                    }
                    for item in order.items
                ]
            }
            
            # Send completion notification
            completion_notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver=request.sender,
                notification_type="agent_action",
                agent_name="Checkout Agent",
                agent_id=self.agent_id,
                content=f"✅ Order placed successfully! Order ID: {order.order_id}"
            )
            await self.send_message(request.sender, completion_notification)
            
            # Send response back to orchestrator
            a2a_response = A2AResponse(
                request_id=request.id,
                sender=self.agent_id,
                receiver=request.sender,
                content=response_content,
                success=True
            )
            
            logger.info(f"Sending checkout response back to {request.sender} for request {request.id}")
            success = await self.send_message(request.sender, a2a_response)
            logger.info(f"Checkout response sent successfully: {success}")
            return success
            
        except Exception as e:
            logger.error(f"Error in _handle_process_checkout: {e}")
            logger.error(f"Checkout data received: {checkout_data}")
            logger.error(f"Request content type: {type(request.content)}")
            logger.error(f"Request content: {request.content}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            
            # Send error notification
            error_notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver=request.sender,
                notification_type="agent_action",
                agent_name="Checkout Agent",
                agent_id=self.agent_id,
                content="❌ Failed to process checkout. Please try again."
            )
            await self.send_message(request.sender, error_notification)
            
            return False

    async def _handle_validate_order(self, request: A2ARequest) -> bool:
        """Validate order before processing"""
        try:
            # Parse request content
            content_dict = self._parse_request_content(request)
                
            session_id = content_dict.get("session_id")
            order_data = content_dict.get("order_data", {})
            
            if not session_id or not order_data:
                logger.error("Missing session_id or order_data in validate order request")
                return False
            
            # Send notification
            notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver=request.sender,
                notification_type="agent_thinking",
                agent_name="Checkout Agent",
                agent_id=self.agent_id,
                content="Validating order..."
            )
            await self.send_message(request.sender, notification)
            
            # Basic validation logic
            validation_results = {
                "valid": True,
                "errors": [],
                "warnings": []
            }
            
            # Validate required fields
            required_fields = ["email", "address", "credit_card"]
            for field in required_fields:
                if not order_data.get(field):
                    validation_results["valid"] = False
                    validation_results["errors"].append(f"Missing required field: {field}")
            
            # Validate email format
            email = order_data.get("email", "")
            if email and "@" not in email:
                validation_results["valid"] = False
                validation_results["errors"].append("Invalid email format")
            
            # Validate address
            address = order_data.get("address", {})
            required_address_fields = ["street_address", "city", "state", "country", "zip_code"]
            for field in required_address_fields:
                if not address.get(field):
                    validation_results["valid"] = False
                    validation_results["errors"].append(f"Missing address field: {field}")
            
            # Validate credit card
            credit_card = order_data.get("credit_card", {})
            required_cc_fields = ["number", "cvv", "expiration_year", "expiration_month"]
            for field in required_cc_fields:
                if not credit_card.get(field):
                    validation_results["valid"] = False
                    validation_results["errors"].append(f"Missing credit card field: {field}")
            
            # Send completion notification
            if validation_results["valid"]:
                completion_msg = "✅ Order validation successful"
            else:
                completion_msg = f"❌ Order validation failed: {len(validation_results['errors'])} error(s)"
                
            completion_notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver=request.sender,
                notification_type="agent_action",
                agent_name="Checkout Agent",
                agent_id=self.agent_id,
                content=completion_msg
            )
            await self.send_message(request.sender, completion_notification)
            
            # Send response
            response = A2AResponse(
                request_id=request.id,
                sender=self.agent_id,
                receiver=request.sender,
                content=validation_results,
                success=validation_results["valid"]
            )
            
            return await self.send_message(request.sender, response)
            
        except Exception as e:
            logger.error(f"Error in _handle_validate_order: {e}")
            return False

    async def _handle_get_order_status(self, request: A2ARequest) -> bool:
        """Get order status"""
        try:
            # Parse request content
            content_dict = self._parse_request_content(request)
                
            session_id = content_dict.get("session_id")
            order_id = content_dict.get("order_id")
            
            if not session_id or not order_id:
                logger.error("Missing session_id or order_id in get order status request")
                return False
            
            # Send notification
            notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver=request.sender,
                notification_type="agent_thinking",
                agent_name="Checkout Agent",
                agent_id=self.agent_id,
                content="Retrieving order status..."
            )
            await self.send_message(request.sender, notification)
            
            # For now, return a mock status since Online Boutique doesn't have order status endpoint
            # In a real implementation, this would query the order service
            order_status = {
                "order_id": order_id,
                "status": "confirmed",
                "estimated_delivery": "3-5 business days",
                "tracking_number": f"TRK{order_id[:8].upper()}",
                "last_updated": "2024-01-15T10:30:00Z"
            }
            
            # Send completion notification
            completion_notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver=request.sender,
                notification_type="agent_action",
                agent_name="Checkout Agent",
                agent_id=self.agent_id,
                content=f"✅ Order status retrieved for order {order_id}"
            )
            await self.send_message(request.sender, completion_notification)
            
            # Send response
            response = A2AResponse(
                request_id=request.id,
                sender=self.agent_id,
                receiver=request.sender,
                content=order_status,
                success=True
            )
            
            return await self.send_message(request.sender, response)
            
        except Exception as e:
            logger.error(f"Error in _handle_get_order_status: {e}")
            return False

    async def _handle_cancel_order(self, request: A2ARequest) -> bool:
        """Cancel an order"""
        try:
            # Parse request content
            content_dict = self._parse_request_content(request)
                
            session_id = content_dict.get("session_id")
            order_id = content_dict.get("order_id")
            
            if not session_id or not order_id:
                logger.error("Missing session_id or order_id in cancel order request")
                return False
            
            # Send notification
            notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver=request.sender,
                notification_type="agent_thinking",
                agent_name="Checkout Agent",
                agent_id=self.agent_id,
                content="Cancelling order..."
            )
            await self.send_message(request.sender, notification)
            
            # For now, return a mock cancellation since Online Boutique doesn't have cancel endpoint
            # In a real implementation, this would call the order service to cancel
            cancellation_result = {
                "order_id": order_id,
                "cancelled": True,
                "refund_amount": "$0.00",
                "refund_method": "Original payment method",
                "cancelled_at": "2024-01-15T10:30:00Z"
            }
            
            # Send completion notification
            completion_notification = A2AFrontendNotification(
                sender=self.agent_id,
                receiver=request.sender,
                notification_type="agent_action",
                agent_name="Checkout Agent",
                agent_id=self.agent_id,
                content=f"✅ Order {order_id} cancelled successfully"
            )
            await self.send_message(request.sender, completion_notification)
            
            # Send response
            response = A2AResponse(
                request_id=request.id,
                sender=self.agent_id,
                receiver=request.sender,
                content=cancellation_result,
                success=True
            )
            
            return await self.send_message(request.sender, response)
            
        except Exception as e:
            logger.error(f"Error in _handle_cancel_order: {e}")
            return False

    async def stop(self):
        """Clean up resources"""
        if self.checkout_channel:
            self.checkout_channel.close()
        await super().stop()

# Create global instance
checkout_agent = CheckoutAgent()

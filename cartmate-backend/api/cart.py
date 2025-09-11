"""
Cart API endpoints for frontend integration
"""
import logging
from fastapi import APIRouter, HTTPException, Form, File, UploadFile
from typing import Optional, List, Dict, Any
from pydantic import BaseModel
from agents.cart_management import cart_management_agent
from a2a.coordinator import a2a_coordinator
from models.a2a import A2ARequest, A2ARequestType
import uuid

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cart", tags=["cart"])

class CartItem(BaseModel):
    product_id: str
    quantity: int = 1

class CartResponse(BaseModel):
    success: bool
    message: str
    cart_data: Optional[Dict[str, Any]] = None

@router.get("/{session_id}", response_model=CartResponse)
async def get_cart(session_id: str):
    """Get current cart contents for a session"""
    try:
        logger.info(f"Getting cart for session: {session_id}")
        
        # Find cart management agent
        cart_agent = a2a_coordinator.find_agent_by_type("cart_management")
        if not cart_agent:
            raise HTTPException(status_code=503, detail="Cart service unavailable")
        
        # Create A2A request
        request_id = str(uuid.uuid4())
        request_content = {
            "session_id": session_id
        }
        
        request = A2ARequest(
            request_id=request_id,
            sender="api",
            receiver=cart_agent.agent_id,
            conversation_id=session_id,
            request_type=A2ARequestType.GET_CART,
            content=request_content
        )
        
        # Call the cart service directly
        from protos.generated import demo_pb2, demo_pb2_grpc
        import grpc
        from config.settings import settings
        
        # Create gRPC connection to cart service
        channel = grpc.insecure_channel(f"{settings.CART_SERVICE_HOST}:{settings.CART_SERVICE_PORT}")
        cart_stub = demo_pb2_grpc.CartServiceStub(channel)
        
        # Get cart from service
        user_id = f"user_{session_id}"
        get_request = demo_pb2.GetCartRequest(user_id=user_id)
        cart_response = cart_stub.GetCart(get_request)
        
        logger.info(f"Raw cart response for {user_id}: {len(cart_response.items)} total items")
        for item in cart_response.items:
            logger.info(f"  - {item.product_id}: quantity {item.quantity}")
        
        # Convert to frontend-friendly format with product details
        # Filter out items with quantity 0 (removed items)
        cart_items = []
        for item in cart_response.items:
            if item.quantity <= 0:
                continue  # Skip items with quantity 0 or negative
            # Get product details from product catalog
            try:
                from services.boutique.product_catalog_client import product_catalog_client
                product_details = await product_catalog_client.get_product(item.product_id)
                
                # Format price properly
                price_usd = product_details.get("price_usd", {})
                units = price_usd.get("units", 0)
                nanos = price_usd.get("nanos", 0)
                price = f"${units}.{nanos:09d}" if nanos > 0 else f"${units}"
                
                cart_items.append({
                    "product_id": item.product_id,
                    "name": product_details.get("name", "Unknown Product"),
                    "price": price,
                    "quantity": item.quantity,
                    "image_url": product_details.get("picture", ""),
                    "picture": product_details.get("picture", "")
                })
            except Exception as e:
                logger.warning(f"Could not fetch product details for {item.product_id}: {e}")
                # Fallback with minimal info
                cart_items.append({
                    "product_id": item.product_id,
                    "name": f"Product {item.product_id}",
                    "price": "Price unavailable",
                    "quantity": item.quantity,
                    "image_url": "",
                    "picture": ""
                })
        
        cart_data = {
            "user_id": cart_response.user_id,
            "items": cart_items,
            "total_items": len(cart_items)
        }
        
        return CartResponse(
            success=True,
            message="Cart retrieved successfully",
            cart_data=cart_data
        )
        
    except Exception as e:
        logger.error(f"Error getting cart: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/add", response_model=CartResponse)
async def add_to_cart(
    session_id: str,
    product_id: str = Form(...),
    quantity: int = Form(1)
):
    """Add a single item to cart"""
    try:
        logger.info(f"Adding item {product_id} (qty: {quantity}) to cart for session: {session_id}")
        
        # Find cart management agent
        cart_agent = a2a_coordinator.find_agent_by_type("cart_management")
        if not cart_agent:
            raise HTTPException(status_code=503, detail="Cart service unavailable")
        
        # Create A2A request
        request_id = str(uuid.uuid4())
        request_content = {
            "session_id": session_id,
            "products": [{
                "id": product_id,
                "quantity": quantity
            }]
        }
        
        request = A2ARequest(
            request_id=request_id,
            sender="api",
            receiver=cart_agent.agent_id,
            conversation_id=session_id,
            request_type=A2ARequestType.ADD_TO_CART,
            content=request_content
        )
        
        # Send request
        success = await cart_management_agent.send_message("api", request)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to communicate with cart service")
        
        return CartResponse(
            success=True,
            message=f"Added {quantity} item(s) to cart"
        )
        
    except Exception as e:
        logger.error(f"Error adding to cart: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/clear", response_model=CartResponse)
async def clear_cart(session_id: str):
    """Clear all items from cart"""
    try:
        logger.info(f"Clearing cart for session: {session_id}")
        
        # Find cart management agent
        cart_agent = a2a_coordinator.find_agent_by_type("cart_management")
        if not cart_agent:
            raise HTTPException(status_code=503, detail="Cart service unavailable")
        
        # Create A2A request
        request_id = str(uuid.uuid4())
        request_content = {
            "session_id": session_id
        }
        
        request = A2ARequest(
            request_id=request_id,
            sender="api",
            receiver=cart_agent.agent_id,
            conversation_id=session_id,
            request_type=A2ARequestType.CLEAR_CART,
            content=request_content
        )
        
        # Send request
        success = await cart_management_agent.send_message("api", request)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to communicate with cart service")
        
        return CartResponse(
            success=True,
            message="Cart cleared successfully"
        )
        
    except Exception as e:
        logger.error(f"Error clearing cart: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/update", response_model=CartResponse)
async def update_cart_item(
    session_id: str,
    request_data: dict
):
    """Update quantity of an item in cart"""
    try:
        product_id = request_data.get("product_id")
        quantity = request_data.get("quantity")
        
        if not product_id or quantity is None:
            raise HTTPException(status_code=400, detail="Missing product_id or quantity")
        
        logger.info(f"Updating item {product_id} quantity to {quantity} in cart for session: {session_id}")
        
        # Call cart service directly
        from protos.generated import demo_pb2, demo_pb2_grpc
        import grpc
        from config.settings import settings
        
        # Create gRPC connection to cart service
        channel = grpc.insecure_channel(f"{settings.CART_SERVICE_HOST}:{settings.CART_SERVICE_PORT}")
        cart_stub = demo_pb2_grpc.CartServiceStub(channel)
        
        # Update the item quantity directly
        user_id = f"user_{session_id}"
        cart_item = demo_pb2.CartItem(
            product_id=product_id,
            quantity=quantity
        )
        
        add_request = demo_pb2.AddItemRequest(user_id=user_id, item=cart_item)
        cart_stub.AddItem(add_request)
        
        logger.info(f"Successfully updated item {product_id} quantity to {quantity}")
        
        return CartResponse(
            success=True,
            message=f"Updated item quantity to {quantity}"
        )
        
    except Exception as e:
        logger.error(f"Error updating cart item: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{session_id}/remove", response_model=CartResponse)
async def remove_cart_item(
    session_id: str,
    request_data: dict
):
    """Remove an item from cart"""
    try:
        product_id = request_data.get("product_id")
        
        if not product_id:
            raise HTTPException(status_code=400, detail="Missing product_id")
        
        logger.info(f"Removing item {product_id} from cart for session: {session_id}")
        
        # Call cart service directly
        from protos.generated import demo_pb2, demo_pb2_grpc
        import grpc
        from config.settings import settings
        
        # Create gRPC connection to cart service
        channel = grpc.insecure_channel(f"{settings.CART_SERVICE_HOST}:{settings.CART_SERVICE_PORT}")
        cart_stub = demo_pb2_grpc.CartServiceStub(channel)
        
        # Get current cart contents
        user_id = f"user_{session_id}"
        get_request = demo_pb2.GetCartRequest(user_id=user_id)
        cart_response = cart_stub.GetCart(get_request)
        
        # Filter out the item we want to remove
        remaining_items = []
        for item in cart_response.items:
            if item.product_id != product_id and item.quantity > 0:
                remaining_items.append(item)
        
        logger.info(f"Removing {product_id}, keeping {len(remaining_items)} items")
        
        # Clear the entire cart
        clear_request = demo_pb2.EmptyCartRequest(user_id=user_id)
        cart_stub.EmptyCart(clear_request)
        
        # Re-add all items except the one we want to remove
        for item in remaining_items:
            add_request = demo_pb2.AddItemRequest(user_id=user_id, item=item)
            cart_stub.AddItem(add_request)
        
        logger.info(f"Successfully removed item {product_id} from cart")
        
        return CartResponse(
            success=True,
            message="Item removed from cart"
        )
        
    except Exception as e:
        logger.error(f"Error removing cart item: {e}")
        raise HTTPException(status_code=500, detail=str(e))


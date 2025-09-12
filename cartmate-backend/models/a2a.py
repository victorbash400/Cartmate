from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
from datetime import datetime
from enum import Enum
import uuid


class A2AMessageType(str, Enum):
    """Types of A2A messages"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"
    HEARTBEAT = "heartbeat"
    REGISTER = "register"
    DEREGISTER = "deregister"
    ACK = "ack"
    FRONTEND_NOTIFICATION = "frontend_notification"


class A2ARequestType(str, Enum):
    """Types of A2A requests"""
    SEARCH_PRODUCTS = "search_products"
    GET_PRODUCT_DETAILS = "get_product_details"
    CREATE_CART = "create_cart"
    ADD_TO_CART = "add_to_cart"
    UPDATE_CART_ITEM = "update_cart_item"
    REMOVE_FROM_CART = "remove_from_cart"
    GET_CART = "get_cart"
    CLEAR_CART = "clear_cart"
    ANALYZE_STYLE = "analyze_style"
    COMPARE_PRICES = "compare_prices"
    PROCESS_CHECKOUT = "process_checkout"
    VALIDATE_ORDER = "validate_order"
    GET_ORDER_STATUS = "get_order_status"
    CANCEL_ORDER = "cancel_order"


class A2AMessage(BaseModel):
    """Base A2A message format"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Unique message identifier")
    type: A2AMessageType = Field(..., description="Type of message")
    sender: str = Field(..., description="Sender agent identifier")
    receiver: str = Field(..., description="Receiver agent identifier")
    conversation_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="Conversation identifier")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    content: Union[str, Dict[str, Any]] = Field(..., description="Message content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    requires_ack: bool = Field(default=False, description="Whether acknowledgment is required")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class A2ARequest(A2AMessage):
    """A2A request message"""
    type: A2AMessageType = A2AMessageType.REQUEST
    request_type: A2ARequestType = Field(..., description="Type of request")
    content: Dict[str, Any] = Field(default_factory=dict, description="Request parameters")
    requires_ack: bool = Field(default=True, description="Whether acknowledgment is required")


class A2AResponse(A2AMessage):
    """A2A response message"""
    type: A2AMessageType = A2AMessageType.RESPONSE
    request_id: str = Field(..., description="ID of the request this responds to")
    success: bool = Field(True, description="Whether the request was successful")
    content: Union[str, Dict[str, Any], List[Dict[str, Any]]] = Field(..., description="Response content")
    error: Optional[str] = Field(None, description="Error message if request failed")


class A2ARegistration(BaseModel):
    """Agent registration information"""
    agent_id: str = Field(..., description="Unique agent identifier")
    agent_type: str = Field(..., description="Type of agent")
    capabilities: List[str] = Field(default_factory=list, description="Agent capabilities")
    status: str = Field(default="active", description="Agent status")
    registered_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class A2AAcknowledgment(A2AMessage):
    """A2A acknowledgment message"""
    type: A2AMessageType = A2AMessageType.ACK
    ack_for_message_id: str = Field(..., description="ID of the message being acknowledged")
    success: bool = Field(True, description="Whether the message was received successfully")
    error: Optional[str] = Field(None, description="Error message if acknowledgment failed")
    content: Dict[str, Any] = Field(default_factory=lambda: {}, description="Acknowledgment content")


class A2AFrontendNotification(A2AMessage):
    """A2A frontend notification message for group chat display"""
    type: A2AMessageType = A2AMessageType.FRONTEND_NOTIFICATION
    notification_type: str = Field(..., description="Type of notification (e.g., 'agent_thinking', 'agent_action', 'agent_response')")
    agent_name: str = Field(..., description="Human-readable name of the agent")
    agent_id: str = Field(..., description="ID of the agent sending the notification")
    content: str = Field(..., description="Notification content")
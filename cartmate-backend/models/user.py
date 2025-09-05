from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from enum import Enum

class UserType(str, Enum):
    REGULAR = "regular"
    PREMIUM = "premium"

class User(BaseModel):
    id: str = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email address")
    name: Optional[str] = Field(None, description="User's full name")
    type: UserType = Field(UserType.REGULAR, description="User account type")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class Session(BaseModel):
    id: str = Field(..., description="Unique session identifier")
    user_id: str = Field(..., description="Associated user identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: datetime = Field(..., description="Session expiration time")
    context: Dict[str, Any] = Field(default_factory=dict, description="Conversation context")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ConversationContext(BaseModel):
    history: List[Dict[str, Any]] = Field(default_factory=list, description="Conversation history")
    user_preferences: Dict[str, Any] = Field(default_factory=dict, description="User preferences")
    current_task: Optional[str] = Field(None, description="Current task being processed")
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }
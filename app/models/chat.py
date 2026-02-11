from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime


# Request Models
class ChatMessageRequest(BaseModel):
    """Request model for sending a chat message"""
    session_id: Optional[str] = Field(None, description="Existing session ID")
    interaction_id: Optional[str] = Field(None, description="Existing interaction ID")
    message: str = Field(..., min_length=1, max_length=10000, description="User message")
    
    @validator('message')
    def sanitize_message(cls, v):
        return v.strip()


class NewInteractionRequest(BaseModel):
    """Request model for creating a new interaction"""
    session_id: str = Field(..., description="Session ID to associate interaction with")


class GetHistoryRequest(BaseModel):
    """Query parameters for getting chat history"""
    interaction_id: Optional[str] = Field(None, description="Specific interaction ID")
    limit: int = Field(50, ge=1, le=500, description="Number of messages to retrieve")


# Response Models
class MessagePair(BaseModel):
    """Model for a single message exchange"""
    message_id: str
    user_message: str
    ai_response: str
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


class ChatMessageResponse(BaseModel):
    """Response model for chat message"""
    session_id: str
    interaction_id: str
    message_id: str
    user_message: str
    ai_response: str
    timestamp: str


class InteractionResponse(BaseModel):
    """Response model for interaction"""
    interaction_id: str
    session_id: str
    created_at: str
    messages_count: int


class ChatHistoryResponse(BaseModel):
    """Response model for chat history"""
    interaction_id: str
    session_id: str
    messages: List[MessagePair]
    total_messages: int
    created_at: str
    last_updated: str


class SessionInfoResponse(BaseModel):
    """Response model for session information"""
    session_id: str
    user_id: str
    interaction_ids: List[str]
    created_at: str
    last_active: str
    is_active: bool


# Internal Models
class AIMessage(BaseModel):
    """Model for AI message format"""
    role: str = Field(..., description="Message role (user/assistant)")
    content: str = Field(..., description="Message content")
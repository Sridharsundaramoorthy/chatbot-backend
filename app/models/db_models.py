from typing import List, Optional, Dict, Any
from datetime import datetime


# MongoDB Document Schemas (as dictionaries)

def user_document(
    user_id: str,
    email: str,
    hashed_password: str,
    name: Optional[str] = None
) -> Dict[str, Any]:
    """Schema for users collection"""
    return {
        "user_id": user_id,
        "email": email,
        "hashed_password": hashed_password,
        "name": name,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "is_active": True
    }


def session_document(
    session_id: str,
    user_id: str
) -> Dict[str, Any]:
    """Schema for sessions collection"""
    return {
        "session_id": session_id,
        "user_id": user_id,
        "interaction_ids": [],
        "created_at": datetime.utcnow(),
        "last_active": datetime.utcnow(),
        "is_active": True
    }


def interaction_document(
    interaction_id: str,
    session_id: str,
    user_id: str
) -> Dict[str, Any]:
    """Schema for interactions collection"""
    return {
        "interaction_id": interaction_id,
        "session_id": session_id,
        "user_id": user_id,
        "messages": [],
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "last_message_at": datetime.utcnow(),
        "is_active": True
    }


def message_pair(
    message_id: str,
    user_message: str,
    ai_response: str,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Schema for message pair within interaction"""
    return {
        "message_id": message_id,
        "user_message": user_message,
        "ai_response": ai_response,
        "timestamp": datetime.utcnow(),
        "metadata": metadata or {}
    }


def refresh_token_document(
    token_id: str,
    user_id: str,
    refresh_token: str,
    expires_at: datetime
) -> Dict[str, Any]:
    """Schema for refresh_tokens collection"""
    return {
        "token_id": token_id,
        "user_id": user_id,
        "refresh_token": refresh_token,
        "created_at": datetime.utcnow(),
        "expires_at": expires_at,
        "is_revoked": False
    }


# Collection names constants
USERS_COLLECTION = "users"
SESSIONS_COLLECTION = "sessions"
INTERACTIONS_COLLECTION = "interactions"
REFRESH_TOKENS_COLLECTION = "refresh_tokens"
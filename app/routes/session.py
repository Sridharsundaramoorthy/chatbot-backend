from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis
from app.config import get_db, get_redis
from app.services import ChatService, CacheService
from app.middleware.auth import get_current_user
from app.utils import build_success_response, format_timestamp
from typing import Dict
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/session", tags=["Session"])


async def get_chat_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> ChatService:
    """Dependency to get ChatService instance"""
    cache_service = CacheService(redis)
    return ChatService(db, cache_service)


@router.post("/create", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_session(
    current_user: Dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Create a new chat session for the user
    
    A session can contain multiple interactions
    """
    try:
        user_id = current_user["user_id"]
        
        session = await chat_service.create_session(user_id)
        
        logger.info(f"Session created: {session['session_id']}")
        
        return build_success_response(
            data=session,
            message="Session created successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session"
        )


@router.get("/{session_id}", response_model=dict)
async def get_session_info(
    session_id: str,
    current_user: Dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Get information about a specific session
    
    Returns session details including all interaction IDs
    """
    try:
        user_id = current_user["user_id"]
        
        session = await chat_service.get_session(session_id, user_id)
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or does not belong to user"
            )
        
        logger.info(f"Session info retrieved: {session_id}")
        
        return build_success_response(
            data={
                "session_id": session["session_id"],
                "user_id": session["user_id"],
                "interaction_ids": session.get("interaction_ids", []),
                "created_at": session["created_at"],
                "last_active": session["last_active"],
                "is_active": True
            },
            message="Session info retrieved successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get session info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session info"
        )


@router.delete("/{session_id}", response_model=dict)
async def delete_session(
    session_id: str,
    current_user: Dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Delete a session and all its interactions
    
    This action cannot be undone
    """
    try:
        user_id = current_user["user_id"]
        
        # Verify session belongs to user
        session = await chat_service.get_session(session_id, user_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or does not belong to user"
            )
        
        # Delete all interactions in the session
        interaction_ids = session.get("interaction_ids", [])
        for interaction_id in interaction_ids:
            try:
                await chat_service.delete_interaction(user_id, interaction_id)
            except Exception as e:
                logger.warning(f"Failed to delete interaction {interaction_id}: {e}")
        
        # Delete session from MongoDB
        sessions_collection = chat_service.db["sessions"]
        await sessions_collection.delete_one({"session_id": session_id})
        
        # Delete from cache
        await chat_service.cache.delete_session(session_id)
        
        logger.info(f"Session deleted: {session_id}")
        
        return build_success_response(
            data={"session_id": session_id},
            message="Session deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete session: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete session"
        )
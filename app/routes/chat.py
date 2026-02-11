from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from redis.asyncio import Redis
from app.config import get_db, get_redis
from app.models import (
    ChatMessageRequest,
    NewInteractionRequest,
    ChatMessageResponse,
    InteractionResponse,
    ChatHistoryResponse
)
from app.services import ChatService, CacheService
from app.middleware.auth import get_current_user
from app.utils import build_success_response, build_error_response
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


async def get_chat_service(
    db: AsyncIOMotorDatabase = Depends(get_db),
    redis: Redis = Depends(get_redis)
) -> ChatService:
    """Dependency to get ChatService instance"""
    cache_service = CacheService(redis)
    return ChatService(db, cache_service)


async def get_cache_service(redis: Redis = Depends(get_redis)) -> CacheService:
    """Dependency to get CacheService instance"""
    return CacheService(redis)


@router.post("/message", response_model=dict)
async def send_message(
    request: ChatMessageRequest,
    current_user: Dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service),
    cache_service: CacheService = Depends(get_cache_service)
):
    """
    Send a message and receive AI response
    
    - If session_id is not provided, a new session will be created
    - If interaction_id is not provided, a new interaction will be created
    - If interaction has expired, user must create a new interaction explicitly
    """
    try:
        user_id = current_user["user_id"]
        
        # Check rate limit
        within_limit = await cache_service.check_rate_limit(user_id)
        if not within_limit:
            rate_info = await cache_service.get_rate_limit_info(user_id)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Try again in {rate_info['reset_in_seconds']} seconds"
            )
        
        # Send message
        result = await chat_service.send_message(
            user_id=user_id,
            message=request.message,
            session_id=request.session_id,
            interaction_id=request.interaction_id
        )
        
        logger.info(f"Message sent by user {user_id}")
        
        return build_success_response(
            data=result,
            message="Message sent successfully"
        )
        
    except ValueError as ve:
        logger.warning(f"Validation error: {ve}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send message: {e}")
        error_msg = str(e)
        if "AI_SERVICE_ERROR" in error_msg or "Failed to generate AI response" in error_msg:
            return build_error_response(
                code="AI_SERVICE_ERROR",
                message="Failed to get AI response",
                details=error_msg
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send message"
        )


@router.post("/interaction/new", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_new_interaction(
    request: NewInteractionRequest,
    current_user: Dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Create a new interaction within an existing session
    
    Required when previous interaction has expired
    """
    try:
        user_id = current_user["user_id"]
        
        # Verify session belongs to user
        session = await chat_service.get_session(request.session_id, user_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found or does not belong to user"
            )
        
        # Create new interaction
        result = await chat_service.create_interaction(
            session_id=request.session_id,
            user_id=user_id
        )
        
        logger.info(f"New interaction created: {result['interaction_id']}")
        
        return build_success_response(
            data=result,
            message="New interaction created successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create interaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create interaction"
        )


@router.get("/history/{interaction_id}", response_model=dict)
async def get_chat_history(
    interaction_id: str,
    limit: int = 50,
    current_user: Dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Get chat history for a specific interaction
    
    Returns all message pairs in the interaction (limited by query param)
    """
    try:
        user_id = current_user["user_id"]
        
        history = await chat_service.get_chat_history(
            user_id=user_id,
            interaction_id=interaction_id,
            limit=min(limit, 500)  # Max 500 messages
        )
        
        logger.info(f"Chat history retrieved for interaction: {interaction_id}")
        
        return build_success_response(
            data=history,
            message="Chat history retrieved successfully"
        )
        
    except ValueError as ve:
        logger.warning(f"Validation error: {ve}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Failed to get chat history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve chat history"
        )


@router.delete("/interaction/{interaction_id}", response_model=dict)
async def delete_interaction(
    interaction_id: str,
    current_user: Dict = Depends(get_current_user),
    chat_service: ChatService = Depends(get_chat_service)
):
    """
    Delete an interaction and all its messages
    
    This action cannot be undone
    """
    try:
        user_id = current_user["user_id"]
        
        await chat_service.delete_interaction(
            user_id=user_id,
            interaction_id=interaction_id
        )
        
        logger.info(f"Interaction deleted: {interaction_id}")
        
        return build_success_response(
            data={"interaction_id": interaction_id},
            message="Interaction deleted successfully"
        )
        
    except ValueError as ve:
        logger.warning(f"Validation error: {ve}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve)
        )
    except Exception as e:
        logger.error(f"Failed to delete interaction: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete interaction"
        )


@router.get("/rate-limit", response_model=dict)
async def get_rate_limit_status(
    current_user: Dict = Depends(get_current_user),
    cache_service: CacheService = Depends(get_cache_service)
):
    """
    Get current rate limit status for the user
    
    Shows requests made, limit, and time until reset
    """
    try:
        user_id = current_user["user_id"]
        
        rate_info = await cache_service.get_rate_limit_info(user_id)
        
        return build_success_response(
            data=rate_info,
            message="Rate limit info retrieved successfully"
        )
        
    except Exception as e:
        logger.error(f"Failed to get rate limit info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve rate limit info"
        )
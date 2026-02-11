from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.services.auth_service import auth_service
from typing import Dict
import logging

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, str]:
    """
    Dependency to get current authenticated user from JWT token
    
    Returns:
        Dict with user_id and email
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials
    
    payload = auth_service.verify_access_token(token)
    
    if not payload:
        logger.warning("Invalid or expired access token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "user_id": payload.get("user_id"),
        "email": payload.get("email")
    }


async def verify_refresh_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, str]:
    """
    Dependency to verify refresh token
    
    Returns:
        Dict with user_id and email
    
    Raises:
        HTTPException: If token is invalid or expired
    """
    token = credentials.credentials
    
    payload = auth_service.verify_refresh_token(token)
    
    if not payload:
        logger.warning("Invalid or expired refresh token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return {
        "user_id": payload.get("user_id"),
        "email": payload.get("email")
    }
from fastapi import APIRouter, Depends, HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from app.config import get_db
from app.models import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    TokenRefreshRequest,
    UserResponse,
    user_document,
    refresh_token_document,
    USERS_COLLECTION,
    REFRESH_TOKENS_COLLECTION
)
from app.services.auth_service import auth_service
from app.middleware.auth import verify_refresh_token
from app.utils import generate_uuid, build_success_response, build_error_response, format_timestamp
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegisterRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Register a new user"""
    try:
        users_collection = db[USERS_COLLECTION]
        
        # Check if user already exists
        existing_user = await users_collection.find_one({"email": user_data.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        
        # Hash password
        hashed_password = auth_service.hash_password(user_data.password)
        
        # Create user document
        user_id = f"user_{generate_uuid()}"
        user_doc = user_document(
            user_id=user_id,
            email=user_data.email,
            hashed_password=hashed_password,
            name=user_data.name
        )
        
        # Save to database
        await users_collection.insert_one(user_doc)
        
        logger.info(f"User registered: {user_id}")
        
        return build_success_response(
            data={
                "user_id": user_id,
                "email": user_data.email,
                "name": user_data.name,
                "created_at": format_timestamp(user_doc["created_at"])
            },
            message="User registered successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )


@router.post("/login", response_model=dict)
async def login(
    credentials: UserLoginRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """User login"""
    try:
        users_collection = db[USERS_COLLECTION]
        refresh_tokens_collection = db[REFRESH_TOKENS_COLLECTION]
        
        # Find user
        user = await users_collection.find_one({"email": credentials.email})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Verify password
        if not auth_service.verify_password(credentials.password, user["hashed_password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )
        
        # Check if user is active
        if not user.get("is_active", True):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is disabled"
            )
        
        # Generate tokens
        access_token = auth_service.create_access_token(
            user["user_id"],
            user["email"]
        )
        refresh_token = auth_service.create_refresh_token(
            user["user_id"],
            user["email"]
        )
        
        # Store refresh token in database
        token_doc = refresh_token_document(
            token_id=f"token_{generate_uuid()}",
            user_id=user["user_id"],
            refresh_token=refresh_token,
            expires_at=datetime.utcnow() + timedelta(days=auth_service.refresh_token_expire)
        )
        await refresh_tokens_collection.insert_one(token_doc)
        
        logger.info(f"User logged in: {user['user_id']}")
        
        return build_success_response(
            data={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "token_type": "bearer",
                "expires_in": auth_service.access_token_expire * 60,
                "user": {
                    "user_id": user["user_id"],
                    "email": user["email"],
                    "name": user.get("name")
                }
            },
            message="Login successful"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )


@router.post("/refresh", response_model=dict)
async def refresh_token(
    token_data: TokenRefreshRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Refresh access token using refresh token"""
    try:
        refresh_tokens_collection = db[REFRESH_TOKENS_COLLECTION]
        
        # Verify refresh token
        payload = auth_service.verify_refresh_token(token_data.refresh_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token"
            )
        
        # Check if token exists and not revoked
        token_doc = await refresh_tokens_collection.find_one({
            "refresh_token": token_data.refresh_token,
            "is_revoked": False
        })
        
        if not token_doc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Refresh token revoked or not found"
            )
        
        # Generate new access token
        access_token = auth_service.create_access_token(
            payload["user_id"],
            payload["email"]
        )
        
        logger.info(f"Token refreshed for user: {payload['user_id']}")
        
        return build_success_response(
            data={
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": auth_service.access_token_expire * 60
            },
            message="Token refreshed successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token refresh failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )


@router.post("/logout", response_model=dict)
async def logout(
    token_data: TokenRefreshRequest,
    db: AsyncIOMotorDatabase = Depends(get_db)
):
    """Logout user by revoking refresh token"""
    try:
        refresh_tokens_collection = db[REFRESH_TOKENS_COLLECTION]
        
        # Revoke refresh token
        result = await refresh_tokens_collection.update_one(
            {"refresh_token": token_data.refresh_token},
            {"$set": {"is_revoked": True}}
        )
        
        if result.modified_count == 0:
            logger.warning("Token already revoked or not found")
        
        logger.info("User logged out")
        
        return build_success_response(
            data={"message": "Logged out successfully"},
            message="Logout successful"
        )
        
    except Exception as e:
        logger.error(f"Logout failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed"
        )
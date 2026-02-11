from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
import re


class UserRegisterRequest(BaseModel):
    """Request model for user registration"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=8, max_length=72, description="User password")
    name: Optional[str] = Field(None, max_length=100, description="User name")
    
    @validator('password')
    def validate_password(cls, v):
        if len(v.encode("utf-8")) > 72:
            raise ValueError("Password cannot exceed 72 bytes")
        
        if not re.search(r'[A-Z]', v):
            raise ValueError('Password must contain at least one uppercase letter')
        if not re.search(r'[a-z]', v):
            raise ValueError('Password must contain at least one lowercase letter')
        if not re.search(r'[0-9]', v):
            raise ValueError('Password must contain at least one digit')
        
        return v



class UserLoginRequest(BaseModel):
    """Request model for user login"""
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class TokenResponse(BaseModel):
    """Response model for authentication tokens"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenRefreshRequest(BaseModel):
    """Request model for token refresh"""
    refresh_token: str = Field(..., description="Refresh token")


class UserResponse(BaseModel):
    """Response model for user information"""
    user_id: str
    email: str
    name: Optional[str]
    created_at: str


class TokenPayload(BaseModel):
    """Model for JWT token payload"""
    user_id: str
    email: str
    exp: int
    type: str = "access"  # access or refresh
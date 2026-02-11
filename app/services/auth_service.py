from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from app.config.settings import settings
from app.utils import generate_uuid, get_current_timestamp
from typing import Optional, Dict
import logging
import hashlib

logger = logging.getLogger(__name__)

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for authentication operations"""
    
    def __init__(self):
        self.secret_key = settings.JWT_SECRET_KEY
        self.algorithm = settings.JWT_ALGORITHM
        self.access_token_expire = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        self.refresh_token_expire = settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS

    def hash_password(self, password: str) -> str:
        # Pre-hash to avoid bcrypt 72-byte limit
        sha256_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return pwd_context.hash(sha256_hash)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        sha256_hash = hashlib.sha256(plain_password.encode("utf-8")).hexdigest()
        return pwd_context.verify(sha256_hash, hashed_password)

        
    def create_access_token(self, user_id: str, email: str) -> str:
        """Create JWT access token"""
        expire = datetime.utcnow() + timedelta(minutes=self.access_token_expire)
        
        payload = {
            "user_id": user_id,
            "email": email,
            "exp": expire,
            "type": "access"
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def create_refresh_token(self, user_id: str, email: str) -> str:
        """Create JWT refresh token"""
        expire = datetime.utcnow() + timedelta(days=self.refresh_token_expire)
        
        payload = {
            "user_id": user_id,
            "email": email,
            "exp": expire,
            "type": "refresh"
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return token
    
    def decode_token(self, token: str) -> Optional[Dict]:
        """Decode and validate JWT token"""
        try:
            payload = jwt.decode(
                token, 
                self.secret_key, 
                algorithms=[self.algorithm]
            )
            return payload
        except JWTError as e:
            logger.error(f"JWT decode error: {e}")
            return None
    
    def verify_access_token(self, token: str) -> Optional[Dict]:
        """Verify access token and return payload"""
        payload = self.decode_token(token)
        
        if not payload:
            return None
        
        if payload.get("type") != "access":
            logger.warning("Invalid token type - expected access token")
            return None
        
        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.utcnow() > datetime.fromtimestamp(exp):
            logger.warning("Access token expired")
            return None
        
        return payload
    
    def verify_refresh_token(self, token: str) -> Optional[Dict]:
        """Verify refresh token and return payload"""
        payload = self.decode_token(token)
        
        if not payload:
            return None
        
        if payload.get("type") != "refresh":
            logger.warning("Invalid token type - expected refresh token")
            return None
        
        # Check expiration
        exp = payload.get("exp")
        if exp and datetime.utcnow() > datetime.fromtimestamp(exp):
            logger.warning("Refresh token expired")
            return None
        
        return payload


# Global auth service instance
auth_service = AuthService()
from redis.asyncio import Redis
from app.config.settings import settings
from app.utils import serialize_for_redis, deserialize_from_redis
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class CacheService:
    """Service for Redis cache operations"""
    
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.session_ttl = settings.REDIS_TTL_SESSION
        self.interaction_ttl = settings.REDIS_TTL_INTERACTION
    
    # Session Cache Methods
    async def cache_session(self, session_id: str, session_data: Dict[str, Any]) -> bool:
        """Cache session data in Redis"""
        try:
            key = f"session:{session_id}"
            value = serialize_for_redis(session_data)
            await self.redis.setex(key, self.session_ttl, value)
            logger.debug(f"Cached session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cache session {session_id}: {e}")
            return False
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session data from Redis"""
        try:
            key = f"session:{session_id}"
            value = await self.redis.get(key)
            if value:
                return deserialize_from_redis(value)
            return None
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    async def delete_session(self, session_id: str) -> bool:
        """Delete session from Redis"""
        try:
            key = f"session:{session_id}"
            await self.redis.delete(key)
            logger.debug(f"Deleted session: {session_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    async def update_session_activity(self, session_id: str) -> bool:
        """Update session last active timestamp and refresh TTL"""
        try:
            key = f"session:{session_id}"
            exists = await self.redis.exists(key)
            if exists:
                await self.redis.expire(key, self.session_ttl)
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to update session activity {session_id}: {e}")
            return False
    
    # Interaction Cache Methods
    async def cache_interaction(
        self, 
        interaction_id: str, 
        interaction_data: Dict[str, Any]
    ) -> bool:
        """Cache interaction data in Redis"""
        try:
            key = f"interaction:{interaction_id}"
            value = serialize_for_redis(interaction_data)
            await self.redis.setex(key, self.interaction_ttl, value)
            logger.debug(f"Cached interaction: {interaction_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to cache interaction {interaction_id}: {e}")
            return False
    
    async def get_interaction(self, interaction_id: str) -> Optional[Dict[str, Any]]:
        """Get interaction data from Redis"""
        try:
            key = f"interaction:{interaction_id}"
            value = await self.redis.get(key)
            if value:
                data = deserialize_from_redis(value)
                # Refresh TTL on access
                await self.redis.expire(key, self.interaction_ttl)
                return data
            return None
        except Exception as e:
            logger.error(f"Failed to get interaction {interaction_id}: {e}")
            return None
    
    async def delete_interaction(self, interaction_id: str) -> bool:
        """Delete interaction from Redis"""
        try:
            key = f"interaction:{interaction_id}"
            await self.redis.delete(key)
            logger.debug(f"Deleted interaction: {interaction_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete interaction {interaction_id}: {e}")
            return False
    
    async def check_interaction_expired(self, interaction_id: str) -> bool:
        """Check if interaction has expired in Redis"""
        try:
            key = f"interaction:{interaction_id}"
            exists = await self.redis.exists(key)
            return not exists
        except Exception as e:
            logger.error(f"Failed to check interaction expiry {interaction_id}: {e}")
            return True
    
    # Rate Limiting Methods
    async def check_rate_limit(self, user_id: str) -> bool:
        """
        Check if user has exceeded rate limit
        Returns True if within limit, False if exceeded
        """
        try:
            key = f"rate_limit:{user_id}"
            current = await self.redis.get(key)
            
            if current is None:
                # First request, set counter
                await self.redis.setex(
                    key, 
                    settings.RATE_LIMIT_PERIOD, 
                    1
                )
                return True
            
            current_count = int(current)
            if current_count >= settings.RATE_LIMIT_REQUESTS:
                logger.warning(f"Rate limit exceeded for user: {user_id}")
                return False
            
            # Increment counter
            await self.redis.incr(key)
            return True
            
        except Exception as e:
            logger.error(f"Failed to check rate limit for {user_id}: {e}")
            # Allow request on error
            return True
    
    async def get_rate_limit_info(self, user_id: str) -> Dict[str, int]:
        """Get rate limit information for user"""
        try:
            key = f"rate_limit:{user_id}"
            current = await self.redis.get(key)
            ttl = await self.redis.ttl(key)
            
            return {
                "requests_made": int(current) if current else 0,
                "requests_limit": settings.RATE_LIMIT_REQUESTS,
                "reset_in_seconds": ttl if ttl > 0 else 0
            }
        except Exception as e:
            logger.error(f"Failed to get rate limit info for {user_id}: {e}")
            return {
                "requests_made": 0,
                "requests_limit": settings.RATE_LIMIT_REQUESTS,
                "reset_in_seconds": 0
            }
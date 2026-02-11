from motor.motor_asyncio import AsyncIOMotorClient
from redis.asyncio import Redis
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)


class Database:
    """Database connection manager for MongoDB and Redis"""
    
    def __init__(self):
        self.mongodb_client: AsyncIOMotorClient = None
        self.mongodb = None
        self.redis_client: Redis = None
    
    async def connect_mongodb(self):
        """Connect to MongoDB"""
        try:
            self.mongodb_client = AsyncIOMotorClient(settings.MONGODB_URL)
            self.mongodb = self.mongodb_client[settings.MONGODB_DB_NAME]
            
            # Test connection
            await self.mongodb_client.admin.command('ping')
            logger.info("✅ MongoDB connected successfully")
        except Exception as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            raise
    
    async def close_mongodb(self):
        """Close MongoDB connection"""
        if self.mongodb_client:
            self.mongodb_client.close()
            logger.info("MongoDB connection closed")
    
    async def connect_redis(self):
        """Connect to Redis"""
        try:
            self.redis_client = Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                password=settings.REDIS_PASSWORD if settings.REDIS_PASSWORD else None,
                decode_responses=True,
                socket_connect_timeout=5
            )
            
            # Test connection
            await self.redis_client.ping()
            logger.info("✅ Redis connected successfully")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            raise
    
    async def close_redis(self):
        """Close Redis connection"""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Redis connection closed")
    
    def get_mongodb(self):
        """Get MongoDB database instance"""
        return self.mongodb
    
    def get_redis(self):
        """Get Redis client instance"""
        return self.redis_client


# Global database instance
db = Database()


async def get_db():
    """Dependency to get MongoDB instance"""
    return db.get_mongodb()


async def get_redis():
    """Dependency to get Redis instance"""
    return db.get_redis()
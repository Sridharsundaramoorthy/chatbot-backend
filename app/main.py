from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import logging
import sys

from app.config import settings, db
from app.routes import auth, chat, session
from app.middleware.error_handler import (
    validation_exception_handler,
    generic_exception_handler
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for startup and shutdown events
    """
    # Startup
    logger.info("🚀 Starting AI Chatbot API...")
    
    try:
        # Connect to MongoDB
        await db.connect_mongodb()
        
        # Connect to Redis
        await db.connect_redis()
        
        # Create indexes
        await create_indexes()
        
        logger.info("✅ All services connected successfully")
        logger.info(f"🌐 API running on {settings.HOST}:{settings.PORT}")
        logger.info(f"📚 Documentation: http://{settings.HOST}:{settings.PORT}/docs")
        
    except Exception as e:
        logger.error(f"❌ Failed to start services: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down AI Chatbot API...")
    
    try:
        await db.close_mongodb()
        await db.close_redis()
        logger.info("✅ All connections closed")
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")


async def create_indexes():
    """Create database indexes for optimized queries"""
    try:
        mongodb = db.get_mongodb()
        
        # Users collection indexes
        await mongodb.users.create_index("email", unique=True)
        await mongodb.users.create_index("user_id", unique=True)
        
        # Sessions collection indexes
        await mongodb.sessions.create_index("session_id", unique=True)
        await mongodb.sessions.create_index("user_id")
        await mongodb.sessions.create_index("last_active")
        
        # Interactions collection indexes
        await mongodb.interactions.create_index("interaction_id", unique=True)
        await mongodb.interactions.create_index("session_id")
        await mongodb.interactions.create_index("user_id")
        await mongodb.interactions.create_index("last_message_at")
        
        # Refresh tokens collection indexes
        await mongodb.refresh_tokens.create_index("token_id", unique=True)
        await mongodb.refresh_tokens.create_index("user_id")
        await mongodb.refresh_tokens.create_index("refresh_token", unique=True)
        await mongodb.refresh_tokens.create_index("expires_at")
        
        logger.info("✅ Database indexes created")
        
    except Exception as e:
        logger.warning(f"⚠️ Failed to create some indexes: {e}")


# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Production-ready AI Chatbot API with HuggingFace integration",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include routers
app.include_router(auth.router, prefix=f"/api/{settings.API_VERSION}")
app.include_router(chat.router, prefix=f"/api/{settings.API_VERSION}")
app.include_router(session.router, prefix=f"/api/{settings.API_VERSION}")


@app.get("/")
async def root():
    """Root endpoint - API health check"""
    return {
        "status": "healthy",
        "service": settings.APP_NAME,
        "version": "1.0.0",
        "api_version": settings.API_VERSION,
        "docs": f"/docs"
    }


@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    try:
        # Check MongoDB
        mongodb_status = "connected"
        try:
            await db.mongodb_client.admin.command('ping')
        except:
            mongodb_status = "disconnected"
        
        # Check Redis
        redis_status = "connected"
        try:
            await db.redis_client.ping()
        except:
            redis_status = "disconnected"
        
        overall_status = "healthy" if (
            mongodb_status == "connected" and 
            redis_status == "connected"
        ) else "unhealthy"
        
        return {
            "status": overall_status,
            "services": {
                "mongodb": mongodb_status,
                "redis": redis_status,
                "ai_service": "ready"
            },
            "timestamp": logging.Formatter().formatTime(logging.LogRecord(
                name="", level=0, pathname="", lineno=0,
                msg="", args=(), exc_info=None
            ))
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
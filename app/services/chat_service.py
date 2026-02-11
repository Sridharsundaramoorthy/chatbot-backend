from motor.motor_asyncio import AsyncIOMotorDatabase
from app.services.cache_service import CacheService
from app.services.ai_service import ai_service
from app.models import (
    session_document,
    interaction_document,
    message_pair,
    SESSIONS_COLLECTION,
    INTERACTIONS_COLLECTION
)
from app.utils import (
    generate_session_id,
    generate_interaction_id,
    generate_message_id,
    get_current_timestamp,
    format_timestamp,
    sanitize_message
)
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


class ChatService:
    """Service for chat business logic"""
    
    def __init__(self, db: AsyncIOMotorDatabase, cache_service: CacheService):
        self.db = db
        self.cache = cache_service
        self.sessions_collection = self.db[SESSIONS_COLLECTION]
        self.interactions_collection = self.db[INTERACTIONS_COLLECTION]
    
    async def create_session(self, user_id: str) -> Dict[str, Any]:
        """Create a new chat session"""
        try:
            session_id = generate_session_id()
            
            # Create session document
            session_doc = session_document(session_id, user_id)
            
            # Save to MongoDB
            await self.sessions_collection.insert_one(session_doc)
            
            # Cache session
            await self.cache.cache_session(session_id, {
                "session_id": session_id,
                "user_id": user_id,
                "interaction_ids": [],
                "created_at": format_timestamp(session_doc["created_at"]),
                "last_active": format_timestamp(session_doc["last_active"])
            })
            
            logger.info(f"Created session: {session_id} for user: {user_id}")
            
            return {
                "session_id": session_id,
                "user_id": user_id,
                "created_at": format_timestamp(session_doc["created_at"])
            }
            
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    async def get_session(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get session information"""
        try:
            # Try cache first
            cached = await self.cache.get_session(session_id)
            if cached and cached.get("user_id") == user_id:
                await self.cache.update_session_activity(session_id)
                return cached
            
            # Fallback to database
            session = await self.sessions_collection.find_one({
                "session_id": session_id,
                "user_id": user_id
            })
            
            if not session:
                return None
            
            # Update last active
            await self.sessions_collection.update_one(
                {"session_id": session_id},
                {"$set": {"last_active": get_current_timestamp()}}
            )
            
            session_data = {
                "session_id": session["session_id"],
                "user_id": session["user_id"],
                "interaction_ids": session.get("interaction_ids", []),
                "created_at": format_timestamp(session["created_at"]),
                "last_active": format_timestamp(get_current_timestamp())
            }
            
            # Re-cache
            await self.cache.cache_session(session_id, session_data)
            
            return session_data
            
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    async def create_interaction(
        self, 
        session_id: str, 
        user_id: str
    ) -> Dict[str, Any]:
        """Create a new interaction within a session"""
        try:
            interaction_id = generate_interaction_id()
            
            # Create interaction document
            interaction_doc = interaction_document(interaction_id, session_id, user_id)
            
            # Save to MongoDB
            await self.interactions_collection.insert_one(interaction_doc)
            
            # Update session with new interaction
            await self.sessions_collection.update_one(
                {"session_id": session_id},
                {
                    "$push": {"interaction_ids": interaction_id},
                    "$set": {"last_active": get_current_timestamp()}
                }
            )
            
            # Cache interaction
            await self.cache.cache_interaction(interaction_id, {
                "interaction_id": interaction_id,
                "session_id": session_id,
                "user_id": user_id,
                "messages": [],
                "created_at": format_timestamp(interaction_doc["created_at"])
            })
            
            # Update session cache
            await self.cache.delete_session(session_id)  # Invalidate to force refresh
            
            logger.info(f"Created interaction: {interaction_id} in session: {session_id}")
            
            return {
                "interaction_id": interaction_id,
                "session_id": session_id,
                "created_at": format_timestamp(interaction_doc["created_at"]),
                "messages_count": 0
            }
            
        except Exception as e:
            logger.error(f"Failed to create interaction: {e}")
            raise
    
    async def send_message(
        self,
        user_id: str,
        message: str,
        session_id: Optional[str] = None,
        interaction_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send a message and get AI response
        Handles session and interaction creation if not provided
        """
        try:
            # Sanitize message
            message = sanitize_message(message)
            
            # Create session if not provided
            if not session_id:
                session = await self.create_session(user_id)
                session_id = session["session_id"]
            else:
                # Verify session exists and belongs to user
                session = await self.get_session(session_id, user_id)
                if not session:
                    raise ValueError("Invalid session_id")
            
            # Check if interaction expired
            if interaction_id:
                is_expired = await self.cache.check_interaction_expired(interaction_id)
                if is_expired:
                    logger.info(f"Interaction {interaction_id} expired, user must create new one")
                    raise ValueError("Interaction expired. Please create a new interaction.")
            
            # Create interaction if not provided
            if not interaction_id:
                interaction = await self.create_interaction(session_id, user_id)
                interaction_id = interaction["interaction_id"]
            
            # Get conversation history
            history = await self._get_interaction_messages(interaction_id)
            
            # Format messages for AI
            formatted_messages = ai_service.format_conversation_history(
                history,
                message
            )
            
            # Get AI response
            ai_response = await ai_service.generate_response(formatted_messages)
            
            # Create message pair
            message_id = generate_message_id()
            msg_pair = message_pair(message_id, message, ai_response)
            
            # Save to MongoDB
            await self.interactions_collection.update_one(
                {"interaction_id": interaction_id},
                {
                    "$push": {"messages": msg_pair},
                    "$set": {
                        "updated_at": get_current_timestamp(),
                        "last_message_at": get_current_timestamp()
                    }
                }
            )
            
            # Update cache
            cached_interaction = await self.cache.get_interaction(interaction_id)
            if cached_interaction:
                cached_interaction["messages"].append({
                    "message_id": message_id,
                    "user_message": message,
                    "ai_response": ai_response,
                    "timestamp": format_timestamp(msg_pair["timestamp"])
                })
                await self.cache.cache_interaction(interaction_id, cached_interaction)
            
            logger.info(f"Message sent in interaction: {interaction_id}")
            
            return {
                "session_id": session_id,
                "interaction_id": interaction_id,
                "message_id": message_id,
                "user_message": message,
                "ai_response": ai_response,
                "timestamp": format_timestamp(msg_pair["timestamp"])
            }
            
        except ValueError as ve:
            raise ve
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise Exception(f"Failed to send message: {str(e)}")
    
    async def get_chat_history(
        self,
        user_id: str,
        interaction_id: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """Get chat history for an interaction"""
        try:
            # Try cache first
            cached = await self.cache.get_interaction(interaction_id)
            if cached and cached.get("user_id") == user_id:
                messages = cached.get("messages", [])[-limit:]
                return {
                    "interaction_id": interaction_id,
                    "session_id": cached.get("session_id"),
                    "messages": messages,
                    "total_messages": len(cached.get("messages", [])),
                    "created_at": cached.get("created_at"),
                    "last_updated": format_timestamp(get_current_timestamp())
                }
            
            # Fallback to database
            interaction = await self.interactions_collection.find_one({
                "interaction_id": interaction_id,
                "user_id": user_id
            })
            
            if not interaction:
                raise ValueError("Interaction not found")
            
            messages = interaction.get("messages", [])[-limit:]
            
            # Format messages
            formatted_messages = [
                {
                    "message_id": msg["message_id"],
                    "user_message": msg["user_message"],
                    "ai_response": msg["ai_response"],
                    "timestamp": format_timestamp(msg["timestamp"]),
                    "metadata": msg.get("metadata", {})
                }
                for msg in messages
            ]
            
            return {
                "interaction_id": interaction_id,
                "session_id": interaction["session_id"],
                "messages": formatted_messages,
                "total_messages": len(interaction.get("messages", [])),
                "created_at": format_timestamp(interaction["created_at"]),
                "last_updated": format_timestamp(interaction["updated_at"])
            }
            
        except Exception as e:
            logger.error(f"Failed to get chat history: {e}")
            raise
    
    async def delete_interaction(
        self,
        user_id: str,
        interaction_id: str
    ) -> bool:
        """Delete an interaction"""
        try:
            # Verify ownership
            interaction = await self.interactions_collection.find_one({
                "interaction_id": interaction_id,
                "user_id": user_id
            })
            
            if not interaction:
                raise ValueError("Interaction not found")
            
            # Delete from MongoDB
            await self.interactions_collection.delete_one({
                "interaction_id": interaction_id
            })
            
            # Delete from cache
            await self.cache.delete_interaction(interaction_id)
            
            # Update session
            await self.sessions_collection.update_one(
                {"session_id": interaction["session_id"]},
                {"$pull": {"interaction_ids": interaction_id}}
            )
            
            logger.info(f"Deleted interaction: {interaction_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete interaction: {e}")
            raise
    
    async def _get_interaction_messages(self, interaction_id: str) -> List[Dict[str, str]]:
        """Get all messages from an interaction for AI context"""
        try:
            # Try cache first
            cached = await self.cache.get_interaction(interaction_id)
            if cached:
                return cached.get("messages", [])
            
            # Fallback to database
            interaction = await self.interactions_collection.find_one({
                "interaction_id": interaction_id
            })
            
            if not interaction:
                return []
            
            return interaction.get("messages", [])
            
        except Exception as e:
            logger.error(f"Failed to get interaction messages: {e}")
            return []
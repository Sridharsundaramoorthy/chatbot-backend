from huggingface_hub import InferenceClient
from app.config.settings import settings
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class AIService:
    """Service for HuggingFace AI interactions"""
    
    def __init__(self):
        """Initialize HuggingFace client"""
        self.client = InferenceClient(token=settings.HUGGINGFACE_TOKEN)
        self.model = settings.HUGGINGFACE_MODEL
        self.max_tokens = settings.MAX_TOKENS
    
    async def generate_response(self, messages: List[Dict[str, str]]) -> str:
        """
        Generate AI response using HuggingFace model
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
                     Format: [{"role": "user", "content": "message"}]
        
        Returns:
            AI generated response as string
        
        Raises:
            Exception: If AI service fails
        """
        try:
            logger.info(f"Sending request to HuggingFace model: {self.model}")
            logger.debug(f"Messages: {messages}")
            
            response = self.client.chat_completion(
                model=self.model,
                messages=messages,
                max_tokens=self.max_tokens
            )
            
            ai_response = response.choices[0].message["content"]
            logger.info(f"Received AI response (length: {len(ai_response)})")
            
            return ai_response
            
        except Exception as e:
            logger.error(f"AI Service Error: {str(e)}")
            raise Exception(f"Failed to generate AI response: {str(e)}")
    
    def format_conversation_history(
        self, 
        messages_history: List[Dict[str, str]],
        current_message: str
    ) -> List[Dict[str, str]]:
        """
        Format conversation history for AI model
        
        Args:
            messages_history: List of previous message pairs
                             [{"user": "...", "assistant": "..."}]
            current_message: Current user message
        
        Returns:
            Formatted messages list for AI model
        """
        formatted_messages = []
        
        # Add all previous messages
        for msg in messages_history:
            formatted_messages.append({
                "role": "user",
                "content": msg.get("user_message", "")
            })
            formatted_messages.append({
                "role": "assistant",
                "content": msg.get("ai_response", "")
            })
        
        # Add current message
        formatted_messages.append({
            "role": "user",
            "content": current_message
        })
        
        return formatted_messages


# Global AI service instance
ai_service = AIService()
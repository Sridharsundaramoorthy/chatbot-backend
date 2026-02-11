from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import json


def get_current_timestamp() -> datetime:
    """Get current UTC timestamp"""
    return datetime.utcnow()


def format_timestamp(dt: datetime) -> str:
    """Format datetime to ISO 8601 string"""
    return dt.isoformat() + "Z"


def parse_timestamp(timestamp_str: str) -> datetime:
    """Parse ISO 8601 timestamp string to datetime"""
    if timestamp_str.endswith("Z"):
        timestamp_str = timestamp_str[:-1]
    return datetime.fromisoformat(timestamp_str)


def calculate_expiry(minutes: int) -> datetime:
    """Calculate expiry time from now"""
    return get_current_timestamp() + timedelta(minutes=minutes)


def is_expired(expiry_time: datetime) -> bool:
    """Check if a timestamp has expired"""
    return get_current_timestamp() > expiry_time


def serialize_for_redis(data: Dict[Any, Any]) -> str:
    """Serialize data for Redis storage"""
    return json.dumps(data, default=str)


def deserialize_from_redis(data: str) -> Dict[Any, Any]:
    """Deserialize data from Redis"""
    if not data:
        return {}
    return json.loads(data)


def sanitize_message(message: str, max_length: int = 10000) -> str:
    """Sanitize and truncate message"""
    message = message.strip()
    if len(message) > max_length:
        message = message[:max_length]
    return message


def build_error_response(code: str, message: str, details: Optional[str] = None) -> Dict:
    """Build standardized error response"""
    error_response = {
        "success": False,
        "error": {
            "code": code,
            "message": message
        }
    }
    if details:
        error_response["error"]["details"] = details
    return error_response


def build_success_response(data: Any, message: Optional[str] = None) -> Dict:
    """Build standardized success response"""
    response = {
        "success": True,
        "data": data
    }
    if message:
        response["message"] = message
    return response
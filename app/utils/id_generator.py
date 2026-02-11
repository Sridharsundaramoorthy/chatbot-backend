import uuid
from typing import Optional


def generate_uuid() -> str:
    """Generate a unique UUID v4"""
    return str(uuid.uuid4())


def generate_session_id() -> str:
    """Generate a unique session ID"""
    return f"session_{generate_uuid()}"


def generate_interaction_id() -> str:
    """Generate a unique interaction ID"""
    return f"interaction_{generate_uuid()}"


def generate_message_id() -> str:
    """Generate a unique message ID"""
    return f"message_{generate_uuid()}"


def validate_uuid(uuid_string: str) -> bool:
    """Validate if a string is a valid UUID"""
    try:
        uuid.UUID(uuid_string)
        return True
    except (ValueError, AttributeError):
        return False


def extract_uuid_from_prefixed_id(prefixed_id: str, prefix: str) -> Optional[str]:
    """Extract UUID from prefixed ID (e.g., 'session_uuid' -> 'uuid')"""
    if prefixed_id.startswith(f"{prefix}_"):
        return prefixed_id[len(prefix) + 1:]
    return None
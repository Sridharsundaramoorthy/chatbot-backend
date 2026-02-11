from app.models.chat import (
    ChatMessageRequest,
    NewInteractionRequest,
    GetHistoryRequest,
    ChatMessageResponse,
    InteractionResponse,
    ChatHistoryResponse,
    SessionInfoResponse,
    MessagePair,
    AIMessage
)

from app.models.auth import (
    UserRegisterRequest,
    UserLoginRequest,
    TokenResponse,
    TokenRefreshRequest,
    UserResponse,
    TokenPayload
)

from app.models.db_models import (
    user_document,
    session_document,
    interaction_document,
    message_pair,
    refresh_token_document,
    USERS_COLLECTION,
    SESSIONS_COLLECTION,
    INTERACTIONS_COLLECTION,
    REFRESH_TOKENS_COLLECTION
)

__all__ = [
    # Chat models
    "ChatMessageRequest",
    "NewInteractionRequest",
    "GetHistoryRequest",
    "ChatMessageResponse",
    "InteractionResponse",
    "ChatHistoryResponse",
    "SessionInfoResponse",
    "MessagePair",
    "AIMessage",
    # Auth models
    "UserRegisterRequest",
    "UserLoginRequest",
    "TokenResponse",
    "TokenRefreshRequest",
    "UserResponse",
    "TokenPayload",
    # DB models
    "user_document",
    "session_document",
    "interaction_document",
    "message_pair",
    "refresh_token_document",
    "USERS_COLLECTION",
    "SESSIONS_COLLECTION",
    "INTERACTIONS_COLLECTION",
    "REFRESH_TOKENS_COLLECTION"
]
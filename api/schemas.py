# api/schemas.py
from typing import Any, Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    house_details: Optional[dict[str, Any]] = None
    conversation_id: Optional[str] = None
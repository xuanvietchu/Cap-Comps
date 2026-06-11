from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant", "agent"]
    content: str


class ChatRequest(BaseModel):
    message: str
    house_details: Optional[dict[str, Any]] = None
    conversation_id: Optional[str] = None
    conversation_history: list[ChatHistoryMessage] = Field(default_factory=list)


class PdfHouseDetailsRequest(BaseModel):
    filename: str
    mime_type: str = "application/pdf"
    data_base64: str


class PdfHouseDetailsResponse(BaseModel):
    details: dict[str, Any] = Field(default_factory=dict)
    summary: str = ""


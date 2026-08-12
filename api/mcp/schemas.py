from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HouseDetailsInput(BaseModel):
    house_details: dict[str, Any] = Field(default_factory=dict)


class TopNInput(HouseDetailsInput):
    top_n: int = 15


class ExplainInput(HouseDetailsInput):
    top_n: int = 5


class ExportCompsCsvInput(BaseModel):
    message: str = ""
    last_analysis: dict[str, Any] | None = None
    top_n: int | None = None
    addresses: list[str] | None = None


class ParseHousePdfInput(BaseModel):
    data_base64: str
    mime_type: str = "application/pdf"


class ChatTurnInput(BaseModel):
    message: str
    house_details: dict[str, Any] | None = None
    conversation_id: str | None = None
    conversation_history: list[dict[str, Any]] | None = None

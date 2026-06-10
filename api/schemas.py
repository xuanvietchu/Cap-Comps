# api/schemas.py
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


class PredictionBand(BaseModel):
    predicted_price: float
    predicted_price_low: float
    predicted_price_high: float
    confidence_level: str
    interval_width: float
    interval_width_ratio: float


class CompResult(BaseModel):
    address: str
    sold_price: float
    sold_date: str = ""
    distance_km: Optional[float] = None
    similarity_score: float
    leaf_similarity_score: Optional[float] = None
    price_per_sqft_similarity: Optional[float] = None
    leaf_matches: Optional[int] = None
    leaf_count: Optional[int] = None
    subject_price_per_sqft: Optional[float] = None
    candidate_price_per_sqft: Optional[float] = None
    predicted_value: Optional[float] = None
    yearBuilt: Optional[int] = None


class DisplayOptions(BaseModel):
    show_prediction: bool = False
    show_comps: bool = False
    show_csv_export: bool = False


class ChatResponse(BaseModel):
    answer: str
    conversation_id: Optional[str] = None
    confidence_level: str = "low"
    prediction: Optional[PredictionBand] = None
    comps: list[CompResult] = Field(default_factory=list)
    intent: str = "general"
    prompt: Optional[str] = None
    explanation: Optional[dict[str, Any]] = None
    display: DisplayOptions = Field(default_factory=DisplayOptions)
    intent_analysis: Optional[dict[str, Any]] = None
    agent_trace: list[dict[str, Any]] = Field(default_factory=list)
    export_csv: Optional[dict[str, Any]] = None

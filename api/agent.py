"""Compatibility wrapper for the tool-driven Gemini comps agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from api.comps_service import build_response
from api.tools import (
    explain_comps,
    explain_house_price,
    predict_house_price,
    rank_comps,
)


@dataclass
class Message:
    role: str
    content: str


@dataclass
class CompsAgent:
    tools = {
        "PREDICT_PRICE": predict_house_price,
        "GET_COMPS": rank_comps,
        "EXPLAIN_PRICE": explain_house_price,
        "EXPLAIN_COMPS": explain_comps,
    }

    def invoke(self, payload: dict[str, Any]) -> dict[str, Any]:
        messages = payload.get("messages") or []
        message = messages[-1]["content"] if messages else ""
        conversation_history = messages[:-1]
        house_details = payload.get("house_details")
        conversation_id = payload.get("conversation_id")
        result = build_response(
            message,
            house_details,
            conversation_id,
            conversation_history=conversation_history,
        )
        return {
            "messages": [
                Message(role="assistant", content=result["answer"]),
            ],
            "result": result,
        }


agent = CompsAgent()
agent_tools = CompsAgent.tools

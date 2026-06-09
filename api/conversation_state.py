from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from api.tools.tool_utils import safe_str


@dataclass
class ConversationState:
    house_details: dict[str, Any] | None = None
    last_analysis: dict[str, Any] | None = None
    messages: list[dict[str, str]] = field(default_factory=list)


CONVERSATIONS: dict[str, ConversationState] = {}


def format_house_summary(details: dict[str, Any] | None) -> str:
    if not details:
        return "Subject property details are unavailable."

    parts: list[str] = []
    address = safe_str(details.get("address"))
    if address:
        parts.append(address)

    size_parts = []
    for key, label in (("bedroomsCount", "bed"), ("bathroomsCount", "bath"), ("livingArea", "sqft")):
        value = safe_str(details.get(key))
        if value:
            size_parts.append(f"{value} {label}")
    if size_parts:
        parts.append(" ".join(size_parts))

    year_built = safe_str(details.get("yearBuilt"))
    if year_built:
        parts.append(f"built in {year_built}")

    return ", ".join(parts) if parts else "Subject property details are unavailable."


def merge_house_details(
    previous: dict[str, Any] | None,
    incoming: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if incoming:
        merged = dict(previous or {})
        merged.update(incoming)
        return merged
    return dict(previous) if previous else None


def normalize_history_message(message: dict[str, Any]) -> dict[str, str] | None:
    role = str(message.get("role") or "").strip().lower()
    content = str(message.get("content") or "").strip()
    if not content:
        return None
    if role == "agent":
        role = "assistant"
    if role not in {"user", "assistant"}:
        return None
    return {"role": role, "content": content[:2400]}


def hydrate_conversation_history(
    state: ConversationState,
    conversation_history: list[dict[str, Any]] | None,
) -> None:
    if not conversation_history:
        return

    messages = [
        normalized
        for message in conversation_history
        if (normalized := normalize_history_message(message)) is not None
    ]
    state.messages = messages[-20:]


def recent_conversation(state: ConversationState, limit: int = 12) -> list[dict[str, str]]:
    return state.messages[-limit:]

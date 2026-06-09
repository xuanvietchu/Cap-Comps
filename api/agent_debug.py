from __future__ import annotations

import json
from typing import Any


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [json_safe(item) for item in value]
    if hasattr(value, "item"):
        return value.item()
    return value


def preview(value: Any, limit: int = 900) -> Any:
    safe_value = json_safe(value)
    encoded = json.dumps(safe_value, default=str)
    if len(encoded) <= limit:
        return safe_value
    if isinstance(safe_value, dict):
        compact = dict(safe_value)
        if isinstance(compact.get("comps"), list):
            compact["comps"] = compact["comps"][:3]
        compact["_preview_truncated"] = True
        return compact
    if isinstance(safe_value, list):
        return {"items": safe_value[:3], "_preview_truncated": True}
    return str(safe_value)[:limit]


def compact_tool_result(value: Any) -> Any:
    safe_value = json_safe(value)
    encoded = json.dumps(safe_value, default=str)
    if len(encoded) <= 18000:
        return safe_value
    if isinstance(safe_value, dict):
        compact = dict(safe_value)
        if isinstance(compact.get("comps"), list):
            compact["comps"] = compact["comps"][:10]
        compact["_truncated"] = True
        return compact
    if isinstance(safe_value, list):
        return {"items": safe_value[:10], "_truncated": True}
    return {"value": str(safe_value)[:18000], "_truncated": True}


class AgentTrace(list[dict[str, Any]]):
    def __init__(self, emit=None):
        super().__init__()
        self.emit = emit


def trace(trace_events: list[dict[str, Any]], step: str, detail: str, payload: Any | None = None) -> None:
    event = {"step": step, "detail": detail}
    if payload is not None:
        event["payload"] = preview(payload)
    trace_events.append(event)
    emit = getattr(trace_events, "emit", None)
    if emit:
        emit(event)
    print(f"[agent] {step}: {detail}", flush=True)

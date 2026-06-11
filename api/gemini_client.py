from __future__ import annotations

import json
import os
from typing import Any
from urllib.request import Request, urlopen

from api.config import GOOGLE_API_KEY, MODEL_NAME, TOOL_DECLARATIONS


def call_gemini(
    contents: list[dict[str, Any]],
    system_text: str,
    use_tools: bool = True,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "systemInstruction": {
            "parts": [
                {"text": system_text}
            ]
        },
        "contents": contents,
        "generationConfig": {"temperature": 0.25},
    }
    if use_tools:
        payload["tools"] = [{"functionDeclarations": TOOL_DECLARATIONS}]

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent?key={GOOGLE_API_KEY}"
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=float(os.getenv("GEMINI_TIMEOUT_SECONDS", "30"))) as response:
        return json.loads(response.read().decode("utf-8"))


def parts_from_response(response: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = response.get("candidates") or []
    if not candidates:
        return []
    return candidates[0].get("content", {}).get("parts", []) or []


def text_from_parts(parts: list[dict[str, Any]]) -> str:
    return " ".join(str(part.get("text", "")).strip() for part in parts if part.get("text")).strip()


def tool_calls_from_parts(parts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    calls = []
    for part in parts:
        function_call = part.get("functionCall") or part.get("function_call")
        if function_call:
            calls.append(function_call)
    return calls


def parse_json_object(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.lower().startswith("json"):
            stripped = stripped[4:].strip()
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end >= start:
        stripped = stripped[start : end + 1]
    parsed = json.loads(stripped)
    return parsed if isinstance(parsed, dict) else {}

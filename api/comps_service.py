from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError

from api.agent_debug import AgentTrace, json_safe, preview, trace
from api.config import MODEL_NAME, SYSTEM_PROMPT
from api.conversation_state import (
    CONVERSATIONS,
    ConversationState,
    format_house_summary,
    hydrate_conversation_history,
    merge_house_details,
    recent_conversation,
)
from api.gemini_client import (
    call_gemini,
    parse_json_object,
    parts_from_response,
    text_from_parts,
    tool_calls_from_parts,
)
from api.tool_orchestration import (
    build_display_options,
    build_explanation_payload,
    collect_analysis,
    fallback_answer,
    invoke_agent_tool,
    tool_dependencies,
    tool_response_part,
)


@dataclass
class AgentRunResult:
    answer: str
    tool_results: dict[str, Any]
    intent_analysis: dict[str, Any]


def _analyze_intent(
    message: str,
    house_details: dict[str, Any] | None,
    state: ConversationState,
    trace_events: list[dict[str, Any]],
) -> dict[str, Any]:
    context = {
        "user_message": message,
        "subject_property_summary": format_house_summary(house_details),
        "previous_analysis_available": bool(state.last_analysis),
        "recent_conversation": recent_conversation(state),
        "available_actions": ["PREDICT_PRICE", "GET_COMPS", "EXPLAIN_PRICE", "EXPLAIN_COMPS"],
    }
    contents = [
        {
            "role": "user",
            "parts": [
                {
                    "text": (
                        "Return only JSON with keys intent, confidence, summary, planned_tools. "
                        "intent must be one of price, comps, explain, general. "
                        "planned_tools must use only PREDICT_PRICE, GET_COMPS, EXPLAIN_PRICE, EXPLAIN_COMPS. "
                        "For a price-only request, planned_tools must be exactly [\"PREDICT_PRICE\"]. "
                        "For a comps request, planned_tools must be exactly [\"GET_COMPS\"]. GET_COMPS includes price estimation internally. "
                        "For a price explanation request, include PREDICT_PRICE before EXPLAIN_PRICE. "
                        "For a comps explanation request, planned_tools must be exactly [\"GET_COMPS\", \"EXPLAIN_COMPS\"]. "
                        "Use recent_conversation to resolve follow-up questions and pronouns. "
                        f"Context JSON: {json.dumps(json_safe(context), default=str)}"
                    )
                }
            ],
        }
    ]
    response = call_gemini(
        contents,
        system_text=(
            "You analyze a housing comps chat request. Return compact JSON only. "
            "Do not call tools in this phase."
        ),
        use_tools=False,
    )
    intent_analysis = parse_json_object(text_from_parts(parts_from_response(response)))
    planned_tools = intent_analysis.get("planned_tools")
    if not isinstance(planned_tools, list):
        planned_tools = []
    allowed_tools = {"PREDICT_PRICE", "GET_COMPS", "EXPLAIN_PRICE", "EXPLAIN_COMPS"}
    intent_analysis = {
        "intent": intent_analysis.get("intent", "general"),
        "confidence": intent_analysis.get("confidence", "low"),
        "summary": intent_analysis.get("summary", "Gemini analyzed the request."),
        "planned_tools": [tool for tool in planned_tools if tool in allowed_tools],
    }
    trace(
        trace_events,
        "intent",
        f"{intent_analysis['intent']} intent: {intent_analysis['summary']}",
        intent_analysis,
    )
    return intent_analysis


def _build_agent_prompt_context(
    message: str,
    house_details: dict[str, Any] | None,
    state: ConversationState,
) -> dict[str, Any]:
    return {
        "user_message": message,
        "subject_property_summary": format_house_summary(house_details),
        "subject_property": house_details,
        "previous_analysis_available": bool(state.last_analysis),
        "previous_analysis": preview(state.last_analysis, limit=3000) if state.last_analysis else None,
        "recent_conversation": recent_conversation(state),
    }


def _initial_agent_contents(context: dict[str, Any], intent_analysis: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "role": "user",
            "parts": [
                {
                    "text": (
                        "Handle this request by choosing from exactly these actions only: "
                        "PREDICT_PRICE, GET_COMPS, EXPLAIN_PRICE, EXPLAIN_COMPS. "
                        "If the user only asks for the price, call only PREDICT_PRICE. "
                        "If the user asks for comps, call only GET_COMPS. GET_COMPS includes price estimation internally. "
                        "If the user asks to explain price, call PREDICT_PRICE before EXPLAIN_PRICE. "
                        "Use EXPLAIN_COMPS only when the user explicitly asks why comps match or asks to explain comps. "
                        "When EXPLAIN_COMPS is used, read path_comparison_output and synthesize a comp analysis under 200 words; do not paste raw tree paths. "
                        "Use recent_conversation and previous_analysis to answer follow-up questions in context. "
                        "GET_COMPS should usually request 10 to 15 comps, defaulting to 12. "
                        "After tool results are available, write the final answer in markdown. "
                        "Do not invent valuation numbers. Context JSON: "
                        f"{json.dumps(json_safe(context), default=str)} "
                        f"Intent analysis JSON: {json.dumps(json_safe(intent_analysis), default=str)}"
                    )
                }
            ],
        }
    ]


def _run_tool_call(
    call: dict[str, Any],
    intent_analysis: dict[str, Any],
    house_details: dict[str, Any] | None,
    executed_tools: set[str],
    tool_results: dict[str, Any],
    trace_events: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    name = call.get("name", "")
    args = call.get("args") or {}

    if intent_analysis.get("intent") == "price" and name != "PREDICT_PRICE":
        result = {
            "error": "skipped_by_policy",
            "reason": "Price-only requests may only call PREDICT_PRICE.",
        }
        trace(trace_events, "tool", f"{name} skipped by price-only policy", result)
        return [tool_response_part(name, result)]

    response_parts: list[dict[str, Any]] = []
    for dependency_name in tool_dependencies(name):
        if dependency_name in executed_tools:
            continue
        dependency_result = invoke_agent_tool(dependency_name, {}, house_details, trace_events)
        tool_results[dependency_name] = dependency_result
        executed_tools.add(dependency_name)
        response_parts.append(tool_response_part(dependency_name, dependency_result))

    result = invoke_agent_tool(name, args, house_details, trace_events)
    tool_results[name] = result
    executed_tools.add(name)
    response_parts.append(tool_response_part(name, result))
    return response_parts


def _gemini_agent_response(
    message: str,
    house_details: dict[str, Any] | None,
    state: ConversationState,
    trace_events: list[dict[str, Any]],
) -> AgentRunResult:
    intent_analysis = _analyze_intent(message, house_details, state, trace_events)
    context = _build_agent_prompt_context(message, house_details, state)
    contents = _initial_agent_contents(context, intent_analysis)
    tool_results: dict[str, Any] = {}
    executed_tools: set[str] = set()

    for _ in range(5):
        response = call_gemini(contents, system_text=SYSTEM_PROMPT, use_tools=True)
        parts = parts_from_response(response)
        calls = tool_calls_from_parts(parts)
        if not calls:
            answer = text_from_parts(parts)
            trace(trace_events, "final", "Gemini wrote the final answer", {"answer": answer})
            return AgentRunResult(answer=answer, tool_results=tool_results, intent_analysis=intent_analysis)

        contents.append({"role": "model", "parts": parts})
        response_parts: list[dict[str, Any]] = []
        for call in calls:
            response_parts.extend(
                _run_tool_call(
                    call,
                    intent_analysis,
                    house_details,
                    executed_tools,
                    tool_results,
                    trace_events,
                )
            )
        contents.append({"role": "user", "parts": response_parts})

    trace(trace_events, "final", "Gemini stopped after the tool loop limit")
    return AgentRunResult(answer="", tool_results=tool_results, intent_analysis=intent_analysis)


def build_response(
    message: str,
    house_details: dict[str, Any] | None,
    conversation_id: str | None,
    conversation_history: list[dict[str, Any]] | None = None,
    trace_sink=None,
) -> dict[str, Any]:
    conversation_id = conversation_id or "default"
    state = CONVERSATIONS.setdefault(conversation_id, ConversationState())
    hydrate_conversation_history(state, conversation_history)
    state.messages.append({"role": "user", "content": message})

    effective_house = merge_house_details(state.house_details, house_details)
    if effective_house is not None:
        state.house_details = effective_house

    trace_events: list[dict[str, Any]] = AgentTrace(trace_sink)
    trace(trace_events, "start", "Received chat request", {"conversation_id": conversation_id})

    source = "gemini"
    try:
        run_result = _gemini_agent_response(message, effective_house, state, trace_events)
        answer = run_result.answer
        tool_results = run_result.tool_results
        intent_analysis = run_result.intent_analysis
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
        source = "fallback"
        intent_analysis = {
            "intent": "general",
            "confidence": "low",
            "summary": f"Gemini was unavailable, so the service returned a minimal fallback: {exc.__class__.__name__}.",
            "planned_tools": [],
        }
        tool_results = {}
        answer = fallback_answer(effective_house)
        trace(trace_events, "fallback", intent_analysis["summary"])

    analysis = collect_analysis(tool_results, state.last_analysis)
    explanation = build_explanation_payload(tool_results)
    display = build_display_options(intent_analysis, tool_results)
    if not answer:
        answer = fallback_answer(effective_house)

    result = {
        "answer": answer,
        "conversation_id": conversation_id,
        "confidence_level": (analysis or {}).get("confidence_level", "low"),
        "prediction": (analysis or {}).get("prediction"),
        "comps": (analysis or {}).get("comps", []),
        "intent": intent_analysis.get("intent", "general"),
        "prompt": f"{source}:{MODEL_NAME}:tool-driven",
        "explanation": explanation,
        "display": display,
        "intent_analysis": intent_analysis,
        "agent_trace": trace_events,
    }

    if result["prediction"] or result["comps"] or result["explanation"]:
        state.last_analysis = result
    state.messages.append({"role": "assistant", "content": answer})
    return result

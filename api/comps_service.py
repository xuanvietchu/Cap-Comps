from __future__ import annotations

import json
import re
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
from api.tools.comps_export import is_export_request
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
    """Internal result from one agent turn before it is shaped for the API."""

    answer: str
    tool_results: dict[str, Any]
    intent_analysis: dict[str, Any]


def _extract_requested_comp_count(message: str) -> int | None:
    """Pull explicit comp counts from natural language before tool execution."""
    patterns = [
        r"\b(?:top|best|first|nearest|closest)\s+(\d{1,4})\s+(?:comps?|comparables?|properties|homes)\b",
        r"\b(?:show|find|get|return|give|list)\s+(?:me\s+)?(\d{1,4})\s+(?:comps?|comparables?|properties|homes)\b",
        r"\b(\d{1,4})\s+(?:comps?|comparables?)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, message, flags=re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _analyze_intent(
    message: str,
    house_details: dict[str, Any] | None,
    state: ConversationState,
    trace_events: list[dict[str, Any]],
) -> dict[str, Any]:
    """Ask Gemini for a compact routing decision before tools are available."""
    context = {
        "user_message": message,
        "subject_property_summary": format_house_summary(house_details),
        "previous_analysis_available": bool(state.last_analysis),
        "recent_conversation": recent_conversation(state),
        "available_actions": ["PREDICT_PRICE", "GET_COMPS", "EXPLAIN_PRICE", "EXPLAIN_COMPS", "EXPORT_COMPS_CSV"],
    }
    contents = [
        {
            "role": "user",
            "parts": [
                {
                    "text": (
                        "Return only JSON with keys intent, confidence, summary, planned_tools. "
                        "intent must be one of price, comps, explain, export, general. "
                        "planned_tools must use only PREDICT_PRICE, GET_COMPS, EXPLAIN_PRICE, EXPLAIN_COMPS, EXPORT_COMPS_CSV. "
                        "For a price-only request, planned_tools must be exactly [\"PREDICT_PRICE\"]. "
                        "For a comps request, planned_tools must be exactly [\"GET_COMPS\"]. GET_COMPS includes price estimation internally. "
                        "For a price explanation request, include PREDICT_PRICE before EXPLAIN_PRICE. "
                        "For a comps explanation request, planned_tools must be exactly [\"GET_COMPS\", \"EXPLAIN_COMPS\"]. "
                        "For a CSV export request, planned_tools must be exactly [\"EXPORT_COMPS_CSV\"]. "
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
    allowed_tools = {"PREDICT_PRICE", "GET_COMPS", "EXPLAIN_PRICE", "EXPLAIN_COMPS", "EXPORT_COMPS_CSV"}
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
    """Bundle subject, conversation, and prior analysis context for the tool agent."""
    return {
        "user_message": message,
        "subject_property_summary": format_house_summary(house_details),
        "subject_property": house_details,
        "requested_comp_count": _extract_requested_comp_count(message),
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
                        "PREDICT_PRICE, GET_COMPS, EXPLAIN_PRICE, EXPLAIN_COMPS, EXPORT_COMPS_CSV. "
                        "If the user only asks for the price, call only PREDICT_PRICE. "
                        "If the user asks for comps, call only GET_COMPS. GET_COMPS includes price estimation internally. "
                        "If the user asks to explain price, call PREDICT_PRICE before EXPLAIN_PRICE. "
                        "Use EXPLAIN_COMPS only when the user explicitly asks why comps match or asks to explain comps. "
                        "If the user asks to export, download, save, or create a CSV for comps, call only EXPORT_COMPS_CSV. "
                        "EXPORT_COMPS_CSV uses the latest comps table in this conversation. "
                        "When EXPLAIN_COMPS is used, read path_comparison_output and synthesize a comp analysis under 200 words; do not paste raw tree paths. "
                        "Use recent_conversation and previous_analysis to answer follow-up questions in context. "
                        "When the user asks for a specific number of comps, call GET_COMPS with that number as top_n. "
                        "When no count is requested, GET_COMPS should default to 15 comps. "
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
    internal_cache: dict[str, Any],
) -> list[dict[str, Any]]:
    """Execute one Gemini tool call, including required dependency tools."""
    name = call.get("name", "")
    args = call.get("args") or {}
    requested_comp_count = intent_analysis.get("requested_comp_count")

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
        dependency_args = (
            {"top_n": requested_comp_count if requested_comp_count is not None else args.get("top_n")}
            if dependency_name == "GET_COMPS"
            else {}
        )
        dependency_result = invoke_agent_tool(
            dependency_name,
            dependency_args,
            house_details,
            trace_events,
            internal_cache,
        )
        tool_results[dependency_name] = dependency_result
        executed_tools.add(dependency_name)
        response_parts.append(tool_response_part(dependency_name, dependency_result))

    if name == "GET_COMPS" and requested_comp_count is not None:
        args = {**args, "top_n": requested_comp_count}

    result = invoke_agent_tool(name, args, house_details, trace_events, internal_cache)
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
    """Run the intent pass, tool loop, and final-answer pass for one message."""
    intent_analysis = _analyze_intent(message, house_details, state, trace_events)
    if is_export_request(message):
        intent_analysis = {
            **intent_analysis,
            "intent": "export",
            "confidence": "high",
            "summary": "The user asked to export comps as a CSV from the latest comps table.",
            "planned_tools": ["EXPORT_COMPS_CSV"],
        }
        trace(trace_events, "intent", f"export intent: {intent_analysis['summary']}", intent_analysis)
    requested_comp_count = _extract_requested_comp_count(message)
    if requested_comp_count is not None:
        intent_analysis["requested_comp_count"] = requested_comp_count
    context = _build_agent_prompt_context(message, house_details, state)
    contents = _initial_agent_contents(context, intent_analysis)
    tool_results: dict[str, Any] = {}
    executed_tools: set[str] = set()
    internal_cache: dict[str, Any] = {
        "LAST_ANALYSIS": state.last_analysis,
        "USER_MESSAGE": message,
    }

    if intent_analysis.get("intent") == "export":
        result = invoke_agent_tool(
            "EXPORT_COMPS_CSV",
            {"top_n": requested_comp_count} if requested_comp_count is not None else {},
            house_details,
            trace_events,
            internal_cache,
        )
        row_count = result.get("row_count", 0) if isinstance(result, dict) else 0
        missing = result.get("missing_addresses", []) if isinstance(result, dict) else []
        if isinstance(result, dict) and result.get("status") == "ready":
            answer = f"Exported {row_count} comp row{'s' if row_count != 1 else ''} to CSV."
            if missing:
                answer += f" I could not find {len(missing)} requested address{'es' if len(missing) != 1 else ''} in the training data."
        else:
            answer = (
                "I could not export comps yet because this conversation does not have a recent comps table. "
                "Ask me for comps first, then ask me to export them as CSV."
            )
        trace(trace_events, "final", "Export tool produced the final answer", {"answer": answer})
        return AgentRunResult(
            answer=answer,
            tool_results={"EXPORT_COMPS_CSV": result},
            intent_analysis=intent_analysis,
        )

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
                    internal_cache,
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
    """Build the public chat response and update in-memory conversation state."""
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
    export_csv = tool_results.get("EXPORT_COMPS_CSV") if isinstance(tool_results.get("EXPORT_COMPS_CSV"), dict) else None
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
        "export_csv": export_csv,
    }

    if result["prediction"] or result["comps"] or result["explanation"]:
        state.last_analysis = result
    state.messages.append({"role": "assistant", "content": answer})
    return result

from __future__ import annotations

from typing import Any

from api.agent_debug import compact_tool_result, trace
from api.tools.comps_tools import (
    explain_comps,
    explain_house_price,
    predict_house_price,
    rank_comps,
    rank_comps_with_details,
    summarize_comp,
)
from api.tools.comps_export import build_csv_export_payload


PROPERTY_TOOLS = {"PREDICT_PRICE", "GET_COMPS", "EXPLAIN_PRICE", "EXPLAIN_COMPS"}
CONVERSATION_TOOLS = {"EXPORT_COMPS_CSV"}
DEPENDENCY_TOOLS: dict[str, list[str]] = {
    "EXPLAIN_PRICE": ["PREDICT_PRICE"],
    "EXPLAIN_COMPS": ["GET_COMPS"],
}


def safe_int(value: Any, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def normalize_comp_count(value: Any) -> int:
    return max(1, safe_int(value, 15))


def invoke_agent_tool(
    name: str,
    args: dict[str, Any],
    house_details: dict[str, Any] | None,
    trace_events: list[dict[str, Any]],
    internal_cache: dict[str, Any],
) -> Any:
    if name in PROPERTY_TOOLS and house_details is None:
        result = {"error": "house_details_missing"}
        trace(trace_events, "tool", f"{name} skipped because house details are missing", result)
        return result

    trace(trace_events, "tool", f"Calling {name}", args)
    if name == "PREDICT_PRICE":
        result = predict_house_price(house_details or {})
    elif name == "GET_COMPS":
        comps_with_details = rank_comps_with_details(
            house_details or {},
            top_n=normalize_comp_count(args.get("top_n")),
        )
        internal_cache["GET_COMPS_DETAILS"] = comps_with_details
        result = [summarize_comp(comp) for comp in comps_with_details]
    elif name == "EXPLAIN_PRICE":
        result = explain_house_price(house_details or {}, top_n=safe_int(args.get("top_n"), 5))
    elif name == "EXPLAIN_COMPS":
        result = explain_comps(
            house_details or {},
            top_n=safe_int(args.get("top_n"), 5),
            comps_with_details=internal_cache.get("GET_COMPS_DETAILS"),
        )
    elif name == "EXPORT_COMPS_CSV":
        addresses = args.get("addresses")
        result = build_csv_export_payload(
            internal_cache.get("USER_MESSAGE", ""),
            internal_cache.get("LAST_ANALYSIS"),
            top_n=safe_int(args.get("top_n"), 0) or None,
            addresses=addresses if isinstance(addresses, list) else None,
        )
    else:
        result = {"error": f"Unknown tool: {name}"}

    trace(trace_events, "tool_result", f"{name} returned", result)
    return result


def collect_analysis(tool_results: dict[str, Any], fallback_analysis: dict[str, Any] | None) -> dict[str, Any] | None:
    analysis = dict(fallback_analysis or {})

    prediction = tool_results.get("PREDICT_PRICE")
    if isinstance(prediction, dict) and "error" not in prediction:
        analysis["prediction"] = prediction

    comps = tool_results.get("GET_COMPS")
    if isinstance(comps, list):
        analysis["comps"] = comps

    comps_explanation = tool_results.get("EXPLAIN_COMPS")
    if isinstance(comps_explanation, dict) and isinstance(comps_explanation.get("top_comps"), list):
        analysis["comps"] = comps_explanation["top_comps"]

    if analysis.get("prediction"):
        analysis["confidence_level"] = analysis["prediction"].get("confidence_level", "low")

    return analysis or None


def build_explanation_payload(tool_results: dict[str, Any]) -> dict[str, Any] | None:
    payload: dict[str, Any] = {}
    price_explanation = tool_results.get("EXPLAIN_PRICE")
    if isinstance(price_explanation, dict) and "error" not in price_explanation:
        payload["price"] = {
            key: value
            for key, value in price_explanation.items()
            if key != "baseline_price"
        }
    return payload or None


def build_display_options(intent_analysis: dict[str, Any], tool_results: dict[str, Any]) -> dict[str, bool]:
    intent = intent_analysis.get("intent")
    planned_tools = set(intent_analysis.get("planned_tools") or [])
    return {
        "show_prediction": intent == "price" and "PREDICT_PRICE" in tool_results,
        "show_comps": intent == "comps" and "GET_COMPS" in tool_results and "EXPLAIN_COMPS" not in planned_tools,
        "show_csv_export": intent == "export" and tool_results.get("EXPORT_COMPS_CSV", {}).get("status") == "ready",
    }


def tool_dependencies(name: str) -> list[str]:
    return DEPENDENCY_TOOLS.get(name, [])


def tool_response_part(name: str, result: Any) -> dict[str, Any]:
    return {
        "functionResponse": {
            "name": name,
            "response": {"result": compact_tool_result(result)},
        }
    }


def fallback_answer(house_details: dict[str, Any] | None) -> str:
    if house_details:
        return "There was an Error in the Backend. Check Agent intent for more details"
    return "I can help with price, comps, or explain a result once you share the property details."

from __future__ import annotations

from typing import Any


def _predict_house_price(details: dict[str, Any]) -> dict[str, Any]:
    from api.tools.price_tools import predict_house_price

    return predict_house_price(details)


def _rank_and_summarize_comps(house_details: dict[str, Any], top_n: int) -> list[dict[str, Any]]:
    from api.tools.comp_ranking import rank_comps_with_details, summarize_comp

    comps_with_details = rank_comps_with_details(house_details, top_n=top_n)
    return [summarize_comp(comp) for comp in comps_with_details]


def _explain_house_price(details: dict[str, Any], top_n: int) -> dict[str, Any]:
    from api.tools.price_tools import explain_house_price

    return explain_house_price(details, top_n=top_n)


def _explain_comps(details: dict[str, Any], top_n: int) -> dict[str, Any]:
    from api.tools.comp_explanations import explain_comps

    return explain_comps(details, top_n=top_n)


def _build_csv_export_payload(
    message: str,
    last_analysis: dict[str, Any] | None,
    top_n: int | None,
    addresses: list[str] | None,
) -> dict[str, Any]:
    from api.tools.comps_export import build_csv_export_payload

    return build_csv_export_payload(
        message,
        last_analysis,
        top_n=top_n,
        addresses=addresses,
    )


def _parse_house_details_pdf(data_base64: str, mime_type: str) -> dict[str, Any]:
    from api.pdf_form_parser import parse_house_details_pdf

    return parse_house_details_pdf(data_base64, mime_type)


def _build_response(
    message: str,
    house_details: dict[str, Any] | None,
    conversation_id: str | None,
    conversation_history: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    from api.comps_service import build_response

    return build_response(
        message,
        house_details,
        conversation_id,
        conversation_history=conversation_history,
    )


def predict_price(house_details: dict[str, Any]) -> dict[str, Any]:
    """Predict the subject property's sale price band and confidence."""
    return _predict_house_price(house_details)


def get_comps(house_details: dict[str, Any], top_n: int = 15) -> list[dict[str, Any]]:
    """Find and rank comparable sold homes for the subject property."""
    return _rank_and_summarize_comps(house_details, top_n=top_n)


def explain_price(house_details: dict[str, Any], top_n: int = 5) -> dict[str, Any]:
    """Explain model price drivers for the subject property."""
    return _explain_house_price(house_details, top_n=top_n)


def explain_comps(house_details: dict[str, Any], top_n: int = 5) -> dict[str, Any]:
    """Explain why the top comps match the subject property."""
    return _explain_comps(house_details, top_n=top_n)


def export_comps_csv(
    message: str = "",
    last_analysis: dict[str, Any] | None = None,
    top_n: int | None = None,
    addresses: list[str] | None = None,
) -> dict[str, Any]:
    """Export rows for the latest comparable-sales table as CSV."""
    return _build_csv_export_payload(
        message,
        last_analysis,
        top_n=top_n,
        addresses=addresses,
    )


def parse_house_pdf(
    data_base64: str,
    mime_type: str = "application/pdf",
) -> dict[str, Any]:
    """Extract supported house-detail form fields from an uploaded PDF."""
    return _parse_house_details_pdf(data_base64, mime_type)


def run_chat_turn(
    message: str,
    house_details: dict[str, Any] | None = None,
    conversation_id: str | None = None,
    conversation_history: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Run one complete agent turn using the existing chat service contract."""
    return _build_response(
        message,
        house_details,
        conversation_id,
        conversation_history=conversation_history,
    )


def register_tools(mcp: Any) -> None:
    """Register Cap-Comps tools on a FastMCP-compatible server."""
    mcp.tool()(predict_price)
    mcp.tool()(get_comps)
    mcp.tool()(explain_price)
    mcp.tool()(explain_comps)
    mcp.tool()(export_comps_csv)
    mcp.tool()(parse_house_pdf)
    mcp.tool()(run_chat_turn)

"""MCP adapter package for the Cap-Comps backend."""

from api.mcp.tools import (
    explain_comps,
    explain_price,
    export_comps_csv,
    get_comps,
    parse_house_pdf,
    predict_price,
    register_tools,
    run_chat_turn,
)


def create_server():
    """Create the MCP server without importing the SDK during package import."""
    from api.mcp.server import create_server as _create_server

    return _create_server()


__all__ = [
    "create_server",
    "explain_comps",
    "explain_price",
    "export_comps_csv",
    "get_comps",
    "parse_house_pdf",
    "predict_price",
    "register_tools",
    "run_chat_turn",
]

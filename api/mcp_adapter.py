"""
MCP Adapter: In-process bridge for calling MCP tools from FastAPI.

This module provides a unified interface to execute Cap-Comps operations
as MCP tools, enabling both HTTP (FastAPI) and stdio (MCP) clients to use
the same underlying implementations.
"""

from __future__ import annotations

from typing import Any
from api.mcp.tools import (
    predict_price,
    get_comps,
    explain_price,
    explain_comps,
    export_comps_csv,
    parse_house_pdf,
    run_chat_turn,
)


class MCPAdapter:
    """In-process executor for MCP Cap-Comps tools."""

    def __init__(self):
        """Initialize the adapter with tool mappings."""
        self.tools = {
            "predict_price": predict_price,
            "get_comps": get_comps,
            "explain_price": explain_price,
            "explain_comps": explain_comps,
            "export_comps_csv": export_comps_csv,
            "parse_house_pdf": parse_house_pdf,
            "run_chat_turn": run_chat_turn,
        }

    def call_tool(self, tool_name: str, **kwargs) -> Any:
        """
        Execute an MCP tool by name with the given arguments.

        Args:
            tool_name: Name of the tool to execute (e.g., 'predict_price', 'get_comps')
            **kwargs: Tool-specific keyword arguments

        Returns:
            Tool result

        Raises:
            ValueError: If tool not found
        """
        if tool_name not in self.tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        tool = self.tools[tool_name]
        return tool(**kwargs)

    def predict_price(self, house_details: dict[str, Any]) -> dict[str, Any]:
        """Predict the subject property's sale price band and confidence."""
        return predict_price(house_details)

    def get_comps(
        self,
        house_details: dict[str, Any],
        top_n: int = 15,
    ) -> list[dict[str, Any]]:
        """Find and rank comparable sold homes for the subject property."""
        return get_comps(house_details, top_n=top_n)

    def explain_price(
        self,
        house_details: dict[str, Any],
        top_n: int = 5,
    ) -> dict[str, Any]:
        """Explain model price drivers for the subject property."""
        return explain_price(house_details, top_n=top_n)

    def explain_comps(
        self,
        house_details: dict[str, Any],
        top_n: int = 5,
    ) -> dict[str, Any]:
        """Explain why the top comps match the subject property."""
        return explain_comps(house_details, top_n=top_n)

    def export_comps_csv(
        self,
        message: str = "",
        last_analysis: dict[str, Any] | None = None,
        top_n: int | None = None,
        addresses: list[str] | None = None,
    ) -> dict[str, Any]:
        """Export rows for the latest comparable-sales table as CSV."""
        return export_comps_csv(
            message=message,
            last_analysis=last_analysis,
            top_n=top_n,
            addresses=addresses,
        )

    def parse_house_pdf(
        self,
        data_base64: str,
        mime_type: str = "application/pdf",
    ) -> dict[str, Any]:
        """Extract supported house-detail form fields from an uploaded PDF."""
        return parse_house_pdf(data_base64, mime_type=mime_type)

    def run_chat_turn(
        self,
        message: str,
        house_details: dict[str, Any] | None = None,
        conversation_id: str | None = None,
        conversation_history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Run one complete agent turn using the chat service."""
        return run_chat_turn(
            message,
            house_details=house_details,
            conversation_id=conversation_id,
            conversation_history=conversation_history,
        )


# Global adapter instance
_adapter = MCPAdapter()


def get_adapter() -> MCPAdapter:
    """Get the global MCP adapter instance."""
    return _adapter

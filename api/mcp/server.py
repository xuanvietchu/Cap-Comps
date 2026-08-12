"""
MCP Server for Cap-Comps: Real Estate Valuation and Comparable Sales Analysis

This module implements a Model Context Protocol (MCP) server that exposes Cap-Comps
tools for integration with Claude and other LLM clients. The server can run in two modes:

1. **Stdio Mode** (default): Runs as a subprocess accessible via stdin/stdout
   - Perfect for Claude integration
   - Run: `python -m api.mcp.server`
   
2. **In-Process Mode**: Imported and used by FastAPI
   - Used internally by the HTTP API layer
   - Enables tool reuse across HTTP and stdio interfaces

Architecture:
- MCP tools are defined in `api/mcp/tools.py` (single source of truth)
- MCP adapter in `api/mcp_adapter.py` provides in-process execution
- FastAPI uses the adapter to serve HTTP endpoints
- MCP server registers the same tools for stdio/LLM access
- All callers (HTTP or stdio) use identical tool implementations

Supported Tools:
- predict_price: Estimate property sale price band
- get_comps: Find and rank comparable sold homes
- explain_price: Explain price drivers
- explain_comps: Explain why comps match subject property
- export_comps_csv: Export comps as CSV
- parse_house_pdf: Extract details from PDF
- run_chat_turn: Full agent turn with Gemini orchestration
"""

from __future__ import annotations

from mcp.server.mcpserver.server import MCPServer

from api.mcp.tools import register_tools


def create_server() -> MCPServer:
    """Create and configure the MCP server for Cap-Comps."""
    mcp = MCPServer("Cap-Comps")
    register_tools(mcp)
    return mcp


def main() -> None:
    """Run the MCP server in stdio mode for LLM client integration."""
    server = create_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()


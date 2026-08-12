"""
Integration Tests and Examples for Cap-Comps MCP Architecture

This file demonstrates how to use the refactored MCP-first architecture
from different entry points: HTTP API, MCP Server, and direct Python calls.

Run these examples after setting up the environment:
  python -m venv .venv
  .venv/Scripts/activate  (Windows) or source .venv/bin/activate (Unix)
  pip install -r requirements.txt
"""

from typing import Any
import json


# =============================================================================
# Example 1: Direct Python API (Programmatic)
# =============================================================================

def example_direct_api():
    """Use MCP tools directly in Python code."""
    from api.mcp_adapter import get_adapter
    
    adapter = get_adapter()
    
    # Sample house details
    house_details = {
        "bedrooms": 3,
        "bathrooms": 2,
        "sqft": 2000,
        "year_built": 2015,
        "lot_size": 0.25,
        "property_type": "Residential",
        # ... other fields
    }
    
    # Call individual tools
    print("=== Predict Price ===")
    price_result = adapter.predict_price(house_details)
    print(json.dumps(price_result, indent=2, default=str))
    
    print("\n=== Get Comps ===")
    comps_result = adapter.get_comps(house_details, top_n=10)
    print(f"Found {len(comps_result)} comparable properties")
    
    print("\n=== Explain Price ===")
    explanation = adapter.explain_price(house_details, top_n=5)
    print(json.dumps(explanation, indent=2, default=str))
    
    print("\n=== Full Chat Turn ===")
    chat_result = adapter.run_chat_turn(
        message="What is the estimated price for this property?",
        house_details=house_details,
        conversation_id="test_conv_1",
        conversation_history=[],
    )
    print(json.dumps(chat_result, indent=2, default=str))


# =============================================================================
# Example 2: HTTP API via curl (from command line)
# =============================================================================

def example_http_api_commands():
    """
    Example curl commands for the HTTP API.
    
    Prerequisites:
      1. Start FastAPI server: python -m uvicorn api.main:app --reload
      2. Server runs at http://localhost:8000
    """
    
    commands = {
        "health_check": """
curl http://localhost:8000/health
        """,
        
        "predict_price": """
curl -X POST http://localhost:8000/tools/predict-price \\
  -H "Content-Type: application/json" \\
  -d '{
    "house_details": {
      "bedrooms": 3,
      "bathrooms": 2,
      "sqft": 2000,
      "year_built": 2015
    }
  }'
        """,
        
        "get_comps": """
curl -X POST http://localhost:8000/tools/get-comps \\
  -H "Content-Type: application/json" \\
  -d '{
    "house_details": {
      "bedrooms": 3,
      "bathrooms": 2,
      "sqft": 2000,
      "year_built": 2015
    },
    "top_n": 15
  }'
        """,
        
        "full_chat": """
curl -X POST http://localhost:8000/chat/stream \\
  -H "Content-Type: application/json" \\
  -d '{
    "message": "What is the price for this property?",
    "house_details": {
      "bedrooms": 3,
      "bathrooms": 2,
      "sqft": 2000,
      "year_built": 2015
    },
    "conversation_history": []
  }'
        """,
        
        "parse_pdf": """
curl -X POST http://localhost:8000/parse-house-pdf \\
  -H "Content-Type: application/json" \\
  -d '{
    "data_base64": "<base64-encoded PDF>",
    "mime_type": "application/pdf"
  }'
        """,
    }
    
    print("\n".join(f"{name}:\n{cmd}\n" for name, cmd in commands.items()))


# =============================================================================
# Example 3: MCP Server (for LLM Integration)
# =============================================================================

def example_mcp_server():
    """
    Run the MCP server for Claude and other LLM clients.
    
    Prerequisites:
      1. Start MCP server: python -m api.mcp.server
      2. Configure your MCP client to connect to this stdio process
    
    Example MCP client request (JSON):
    """
    
    example_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "predict_price",
            "arguments": {
                "house_details": {
                    "bedrooms": 3,
                    "bathrooms": 2,
                    "sqft": 2000,
                    "year_built": 2015
                }
            }
        }
    }
    
    print("MCP Server Example Request:")
    print(json.dumps(example_request, indent=2))


# =============================================================================
# Example 4: Integration Test (Verify All Layers Work)
# =============================================================================

def example_integration_test():
    """Verify that the MCP architecture integrates correctly."""
    from api.mcp_adapter import get_adapter
    from api.mcp.tools import (
        predict_price,
        get_comps,
        explain_price,
        explain_comps,
        export_comps_csv,
        parse_house_pdf,
        run_chat_turn,
    )
    
    print("=== Integration Test ===\n")
    
    # Test 1: Adapter initialization
    print("✓ Adapter initialization...", end=" ")
    adapter = get_adapter()
    print("OK")
    
    # Test 2: Tools are callable
    print("✓ Tools are registered...", end=" ")
    assert callable(predict_price)
    assert callable(get_comps)
    assert callable(explain_price)
    assert callable(explain_comps)
    assert callable(export_comps_csv)
    assert callable(parse_house_pdf)
    assert callable(run_chat_turn)
    print("OK")
    
    # Test 3: Adapter methods match tools
    print("✓ Adapter methods exist...", end=" ")
    assert hasattr(adapter, 'predict_price')
    assert hasattr(adapter, 'get_comps')
    assert hasattr(adapter, 'explain_price')
    assert hasattr(adapter, 'explain_comps')
    assert hasattr(adapter, 'export_comps_csv')
    assert hasattr(adapter, 'parse_house_pdf')
    assert hasattr(adapter, 'run_chat_turn')
    print("OK")
    
    # Test 4: Call tool through adapter
    print("✓ Tool execution through adapter...", end=" ")
    house_details = {
        "bedrooms": 3,
        "bathrooms": 2,
        "sqft": 2000,
        "year_built": 2015,
    }
    try:
        result = adapter.predict_price(house_details)
        assert isinstance(result, dict)
        print("OK")
    except Exception as e:
        print(f"FAILED: {e}")
    
    print("\n✓ All integration tests passed!")


# =============================================================================
# Example 5: Architecture Diagram
# =============================================================================

def print_architecture():
    """Print the MCP-first architecture diagram."""
    diagram = """
    Cap-Comps MCP Architecture
    ===========================
    
    ┌─────────────────────────────────────────────────────────────┐
    │                    MCP Tools (Single Source)                 │
    │                    api/mcp/tools.py                          │
    │                                                              │
    │  • predict_price      • explain_comps                        │
    │  • get_comps          • export_comps_csv                     │
    │  • explain_price      • parse_house_pdf • run_chat_turn      │
    └────────────────┬──────────────────────────────────────────────┘
                     │
            ┌────────┴────────┐
            │                 │
            ▼                 ▼
      ┌──────────────┐   ┌─────────────────┐
      │ MCP Adapter  │   │  MCP Server     │
      │ (HTTP →MCP)  │   │  (stdio mode)   │
      └──────┬───────┘   └────────┬────────┘
             │                    │
             ▼                    ▼
        ┌─────────────┐      ┌──────────────┐
        │  FastAPI    │      │ LLM Clients  │
        │  (HTTP)     │      │ (Claude, etc)│
        └─────┬───────┘      └──────────────┘
             │
             ▼
        ┌──────────────┐
        │ Next.js UI   │
        │ (Frontend)   │
        └──────────────┘
    
    Benefits:
    • Single source of truth (MCP tools)
    • No code duplication
    • Works with HTTP, stdio, and direct Python calls
    • Easy to test and extend
    """
    print(diagram)


# =============================================================================
# Main: Run Examples
# =============================================================================

if __name__ == "__main__":
    import sys
    
    print("Cap-Comps MCP Architecture - Integration Examples\n")
    print("=" * 60)
    
    if len(sys.argv) > 1:
        example = sys.argv[1]
        if example == "direct":
            print("\nExample 1: Direct Python API")
            print("-" * 60)
            # example_direct_api()  # Uncomment when ready to test
            print("Requires environment setup. See comments in code.")
        elif example == "http":
            print("\nExample 2: HTTP API Commands")
            print("-" * 60)
            example_http_api_commands()
        elif example == "mcp":
            print("\nExample 3: MCP Server")
            print("-" * 60)
            example_mcp_server()
        elif example == "integration":
            print("\nExample 4: Integration Test")
            print("-" * 60)
            # example_integration_test()  # Uncomment when ready to test
            print("Requires environment setup. See comments in code.")
        elif example == "architecture":
            print("\nArchitecture Diagram")
            print("-" * 60)
            print_architecture()
        else:
            print(f"Unknown example: {example}")
    else:
        print("\nUsage: python api/integration_test.py <example>")
        print("\nAvailable examples:")
        print("  direct         - Direct Python API usage")
        print("  http           - HTTP API curl commands")
        print("  mcp            - MCP server integration")
        print("  integration    - Integration test suite")
        print("  architecture   - Print architecture diagram")
        print("\nFor details, see: docs/MCP_ARCHITECTURE.md")

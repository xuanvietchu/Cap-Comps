# Cap-Comps MCP Architecture

## Overview

Cap-Comps has been refactored from a traditional client-server architecture to an **MCP-first design with HTTP adapter**. This enables seamless integration with both LLM clients (via MCP stdio) and web frontends (via HTTP).

## Architecture Diagram

```
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
```

## Components

### 1. MCP Tools (`api/mcp/tools.py`)

**The single source of truth** for all Cap-Comps functionality.

- Defines 7 core tools with consistent interfaces
- Each tool wraps implementation functions from `api/tools/`
- Used by both FastAPI and the MCP server
- Registered on the MCP server for LLM access

**Tools:**

- `predict_price(house_details)` → price band with confidence
- `get_comps(house_details, top_n=15)` → ranked comparable properties
- `explain_price(house_details, top_n=5)` → price driver explanations
- `explain_comps(house_details, top_n=5)` → comp matching explanations
- `export_comps_csv(message, last_analysis, top_n, addresses)` → CSV payload
- `parse_house_pdf(data_base64, mime_type)` → extracted house details
- `run_chat_turn(message, house_details, conversation_id, history)` → full agent turn

### 2. MCP Adapter (`api/mcp_adapter.py`)

**In-process bridge** that FastAPI uses to call MCP tools.

- Provides `MCPAdapter` class with methods for each tool
- `call_tool(tool_name, **kwargs)` for generic tool invocation
- Eliminates code duplication between HTTP and stdio
- Lightweight wrapper—no additional processing

**Usage:**

```python
from api.mcp_adapter import get_adapter

adapter = get_adapter()
result = adapter.predict_price(house_details)
```

### 3. FastAPI Server (`api/main.py`)

**HTTP layer** for the Next.js frontend.

Endpoints use the adapter to delegate to MCP tools:

**Core Endpoints:**

- `POST /chat/stream` → Agent turn (via `run_chat_turn` tool)
- `POST /parse-house-pdf` → PDF parsing (via `parse_house_pdf` tool)
- `GET /health` → Health check

**Individual Tool Endpoints:**

- `POST /tools/predict-price` → Price prediction
- `POST /tools/get-comps` → Comparable sales
- `POST /tools/explain-price` → Price explanations
- `POST /tools/explain-comps` → Comp explanations
- `POST /tools/export-comps-csv` → CSV export

### 4. MCP Server (`api/mcp/server.py`)

**Stdio interface** for LLM clients like Claude.

- Registers all 7 tools from `api/mcp/tools.py`
- Runs in stdio mode by default
- Identical tool implementations as FastAPI (via MCP tools)

**Run MCP Server:**

```bash
python -m api.mcp.server
```

## Data Flow

### HTTP Request (Next.js → FastAPI → Tools)

```
1. Next.js frontend sends POST /chat/stream
2. FastAPI endpoint gets request
3. Gets MCP adapter: adapter = get_adapter()
4. Calls adapter.run_chat_turn(...)
5. Adapter calls MCP tool: tools.run_chat_turn(...)
6. MCP tool calls comps_service.build_response(...)
7. Result streams back to frontend as NDJSON
```

### MCP Request (Claude → MCP Server → Tools)

```
1. Claude (via MCP client) requests "predict_price" tool
2. MCP server receives request
3. Server invokes registered tool: tools.predict_price(...)
4. Tool calls price_tools.predict_house_price(...)
5. Result returned to Claude
```

## Usage Examples

### As HTTP API (from Frontend)

```bash
# Chat with agent
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What is the price for this property?",
    "house_details": {"bedrooms": 3, "bathrooms": 2, ...},
    "conversation_history": []
  }'

# Direct tool call
curl -X POST http://localhost:8000/tools/predict-price \
  -H "Content-Type: application/json" \
  -d '{
    "house_details": {"bedrooms": 3, "bathrooms": 2, ...}
  }'
```

### As MCP Server (from Claude)

```json
{
  "method": "tools/call",
  "params": {
    "name": "predict_price",
    "arguments": {
      "house_details": {"bedrooms": 3, "bathrooms": 2, ...}
    }
  }
}
```

### Programmatic (Python)

```python
from api.mcp_adapter import get_adapter

adapter = get_adapter()

# Single tool
price = adapter.predict_price(house_details)

# Full chat turn
result = adapter.run_chat_turn(
    message="Show me comps",
    house_details=house_details,
    conversation_id="conv_123"
)
```

## Benefits of MCP-First Architecture

| Aspect            | Benefit                                       |
| ----------------- | --------------------------------------------- |
| **Single Source** | All tools in one place; no duplication        |
| **Flexibility**   | Use via HTTP, stdio, or direct Python calls   |
| **Scalability**   | Easy to add new tools or extend functionality |
| **Testing**       | Tools can be tested independently             |
| **Integration**   | Works with Claude, other LLMs, custom clients |
| **Maintenance**   | Changes to tool logic propagate everywhere    |

## Migration from Client-Server

### What Changed

- ❌ Removed: Direct `comps_service.build_response()` calls in FastAPI
- ✅ Added: `MCPAdapter` layer for consistent tool invocation
- ✅ Added: Individual tool endpoints for granular API access
- ✅ Enhanced: MCP server documentation and architecture clarity

### What Stayed the Same

- Frontend remains unchanged (Next.js still calls HTTP endpoints)
- Tool implementations unchanged (logic in `api/tools/`)
- Database/model loading unchanged
- Conversation state management unchanged

## Deployment

### Development

```bash
# Terminal 1: Start FastAPI (with HTTP + adapter to MCP tools)
python -m uvicorn api.main:app --reload --port 8000

# Terminal 2: Start MCP Server (optional, for LLM direct access)
python -m api.mcp.server

# Terminal 3: Start Next.js frontend
cd app && npm run dev
```

### Production

- FastAPI serves both HTTP endpoints and hosts the adapter
- MCP server can run as a separate process for LLM integration
- Environment variables configure models, API keys, etc.

## Configuration

Key environment variables (see `api/config.py`):

- `GEMINI_API_KEY` → Google Gemini API key
- `MODEL_NAME` → LLM model to use (default: "gemini-1.5-flash")
- Data loading from `data/train/train.csv` and `models/house_price_lgbm_pipeline.joblib`

## Future Enhancements

- [ ] Add authentication layer to MCP server
- [ ] Implement request queueing for concurrent tools
- [ ] Add caching layer for tool results
- [ ] Extend with additional analysis tools
- [ ] Support for multiple property markets

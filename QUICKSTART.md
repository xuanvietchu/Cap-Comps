# Cap-Comps MCP Architecture - Quick Start Guide

## 30-Second Overview

Cap-Comps is now built on MCP (Model Context Protocol):

- **All tools** in `api/mcp/tools.py` (single source of truth)
- **HTTP adapter** (`api/mcp_adapter.py`) bridges FastAPI to MCP tools
- **Frontend** (Next.js) stays unchanged, still calls HTTP endpoints
- **MCP Server** can run in parallel for LLM integrations (C laude, etc.)

## Running the Application

### Option 1: Full Stack (Recommended for Demo)

```bash
# Terminal 1: Start the backend
cd c:\Users\vietx\Desktop\work\Cap-Comps
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

pip install -r requirements.txt
python -m uvicorn api.main:app --reload --port 8000

# Terminal 2: Start the frontend
cd app
npm install
npm run dev
```

Then open http://localhost:3000 in your browser.

### Option 2: With MCP Server (for Claude Integration)

```bash
# Terminal 1: MCP Server
cd c:\Users\vietx\Desktop\work\Cap-Comps
python -m api.mcp.server

# Terminal 2: FastAPI (same as above)
python -m uvicorn api.main:app --reload --port 8000

# Terminal 3: Frontend (same as above)
cd app && npm run dev
```

### Option 3: API-Only (Testing)

```bash
# Start backend
python -m uvicorn api.main:app --reload --port 8000

# In another terminal, test endpoints:
curl http://localhost:8000/health
curl http://localhost:8000/docs  # OpenAPI documentation
```

## Quick API Tests

### Via curl

```bash
# Predict price
curl -X POST http://localhost:8000/tools/predict-price \
  -H "Content-Type: application/json" \
  -d '{"house_details": {"bedrooms": 3, "bathrooms": 2, "sqft": 2000, "year_built": 2015}}'

# Get comps
curl -X POST http://localhost:8000/tools/get-comps \
  -H "Content-Type: application/json" \
  -d '{"house_details": {"bedrooms": 3, "bathrooms": 2, "sqft": 2000}, "top_n": 10}'

# Full chat
curl -X POST http://localhost:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the price?", "house_details": {"bedrooms": 3, "bathrooms": 2, "sqft": 2000}}'
```

### Via Python

```python
from api.mcp_adapter import get_adapter

adapter = get_adapter()

# Predict price
result = adapter.predict_price({
    "bedrooms": 3,
    "bathrooms": 2,
    "sqft": 2000,
    "year_built": 2015
})

# Get comps
comps = adapter.get_comps(
    {"bedrooms": 3, "bathrooms": 2, "sqft": 2000},
    top_n=15
)

# Full chat
chat_result = adapter.run_chat_turn(
    message="Show me comps",
    house_details={...},
    conversation_history=[]
)
```

## Key Files

| File                       | Purpose                           |
| -------------------------- | --------------------------------- |
| `api/mcp/tools.py`         | **All MCP tools** (single source) |
| `api/mcp_adapter.py`       | **HTTP → MCP bridge** for FastAPI |
| `api/main.py`              | FastAPI endpoints using adapter   |
| `api/mcp/server.py`        | MCP server for stdio/LLM clients  |
| `docs/MCP_ARCHITECTURE.md` | Full architecture documentation   |
| `api/integration_test.py`  | Examples and integration tests    |

## Available MCP Tools

```
predict_price(house_details)
  → Returns: price band with confidence

get_comps(house_details, top_n=15)
  → Returns: ranked comparable properties

explain_price(house_details, top_n=5)
  → Returns: price driver explanations

explain_comps(house_details, top_n=5)
  → Returns: why comps match analysis

export_comps_csv(message, last_analysis, top_n, addresses)
  → Returns: CSV export payload

parse_house_pdf(data_base64, mime_type='application/pdf')
  → Returns: extracted house details

run_chat_turn(message, house_details, conversation_id, conversation_history)
  → Returns: full agent turn with Gemini orchestration
```

## HTTP Endpoints

### Core Endpoints (Used by Frontend)

- `POST /chat/stream` → Stream agent turns as NDJSON
- `POST /parse-house-pdf` → Extract details from PDF
- `GET /health` → Health check

### Individual Tool Endpoints (API Access)

- `POST /tools/predict-price` → Direct price prediction
- `POST /tools/get-comps` → Direct comparable lookup
- `POST /tools/explain-price` → Direct price explanation
- `POST /tools/explain-comps` → Direct comps explanation
- `POST /tools/export-comps-csv` → Direct CSV export

### Documentation

- `GET /docs` → Interactive OpenAPI documentation (Swagger UI)
- `GET /redoc` → ReDoc documentation

## Troubleshooting

### Import errors

```bash
# Make sure venv is activated
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # macOS/Linux

# Reinstall dependencies
pip install -r requirements.txt
```

### Port already in use

```bash
# Use a different port
python -m uvicorn api.main:app --port 8001

# Or find and kill the process using port 8000
lsof -ti:8000 | xargs kill  # macOS/Linux
netstat -ano | findstr :8000  # Windows
```

### Missing environment variables

```bash
# Ensure .env exists in project root
echo GOOGLE_API_KEY=your_api_key_here > .env

# Or set via environment
$env:GOOGLE_API_KEY="your_api_key_here"  # PowerShell
export GOOGLE_API_KEY="your_api_key_here"  # Bash
```

### Frontend can't connect to backend

```bash
# Check CORS settings in api/main.py
# Check that FastAPI is running on localhost:8000
# Check that Next.js frontend is configured to call http://localhost:8000
```

## Learn More

- **Architecture Details**: [docs/MCP_ARCHITECTURE.md](docs/MCP_ARCHITECTURE.md)
- **API Reference**: [docs/API.md](docs/API.md)
- **Integration Examples**: [api/integration_test.py](api/integration_test.py)
- **Original README**: [README.md](README.md)

## Development Workflow

### Adding a New Tool

1. Implement tool function in `api/tools/` or update existing one
2. Add wrapper in `api/mcp/tools.py`:
   ```python
   def my_new_tool(param1: str, param2: int) -> dict[str, Any]:
       """Tool description."""
       from api.tools.my_tools import my_impl
       return my_impl(param1, param2)
   ```
3. Register in `register_tools()`:
   ```python
   mcp.tool()(my_new_tool)
   ```
4. Adapter automatically gets method via `MCPAdapter.__init__()`
5. HTTP endpoint automatically available if added to `api/main.py`

### Testing a Tool

```python
# Direct Python
from api.mcp_adapter import get_adapter
adapter = get_adapter()
result = adapter.my_new_tool("param1", 123)

# Via HTTP
curl -X POST http://localhost:8000/tools/my-new-tool \
  -H "Content-Type: application/json" \
  -d '{"param1": "value", "param2": 123}'
```

## Support

For issues or questions about the MCP architecture refactoring:

1. Check [docs/MCP_ARCHITECTURE.md](docs/MCP_ARCHITECTURE.md)
2. Review [api/integration_test.py](api/integration_test.py) examples
3. Check logs for error messages
4. Verify all dependencies are installed: `pip list | grep -E "fastapi|mcp|gemini"`

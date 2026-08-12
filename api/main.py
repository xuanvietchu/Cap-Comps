from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json
from queue import Queue
from threading import Thread

from api.mcp_adapter import get_adapter
from api.schemas import (
    ChatHistoryMessage,
    ChatRequest,
    PdfHouseDetailsRequest,
    PdfHouseDetailsResponse,
)


app = FastAPI(
    title="HousingComps Agent API",
    description="Tool-driven property valuation, comparable sale ranking, PDF parsing, and CSV export API.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def serialize_history(messages: list[ChatHistoryMessage]) -> list[dict[str, str]]:
    """Trim Pydantic history objects to the role/content shape Gemini expects."""
    return [{"role": message.role, "content": message.content} for message in messages]


@app.post("/chat/stream")
def chat_stream(req: ChatRequest) -> StreamingResponse:
    """Stream trace events as NDJSON, then emit the final chat response.
    
    Uses MCP adapter to execute the chat turn through the unified tool interface.
    """
    def events():
        queue: Queue[dict[str, object] | None] = Queue()

        def emit_trace(event: dict[str, object]) -> None:
            queue.put({"type": "trace", "event": event})

        def run_agent() -> None:
            try:
                adapter = get_adapter()
                result = adapter.run_chat_turn(
                    req.message,
                    house_details=req.house_details,
                    conversation_id=req.conversation_id,
                    conversation_history=serialize_history(req.conversation_history),
                )
                queue.put({"type": "final", "response": result})
            except Exception as exc:
                queue.put({"type": "error", "message": str(exc)})
            finally:
                queue.put(None)

        Thread(target=run_agent, daemon=True).start()

        while True:
            event = queue.get()
            if event is None:
                break
            yield json.dumps(event, default=str) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson")


@app.post("/parse-house-pdf")
def parse_house_pdf(req: PdfHouseDetailsRequest) -> PdfHouseDetailsResponse:
    """Extract supported house-detail form fields from an uploaded PDF.
    
    Uses MCP adapter to execute PDF parsing through the unified tool interface.
    """
    adapter = get_adapter()
    result = adapter.parse_house_pdf(req.data_base64, mime_type=req.mime_type)
    return PdfHouseDetailsResponse(**result)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


# Individual MCP Tool Endpoints
# These endpoints provide direct access to Cap-Comps tools via the unified MCP interface


@app.post("/tools/predict-price")
def tool_predict_price(house_details: dict[str, object]) -> dict[str, object]:
    """MCP Tool: Predict the subject property's sale price band and confidence.
    
    **Request body:**
    ```json
    {
      "house_details": {
        "bedrooms": 3,
        "bathrooms": 2,
        "sqft": 2000,
        ...
      }
    }
    ```
    """
    adapter = get_adapter()
    return adapter.predict_price(house_details)  # type: ignore


@app.post("/tools/get-comps")
def tool_get_comps(
    house_details: dict[str, object],
    top_n: int = 15,
) -> list[dict[str, object]]:
    """MCP Tool: Find and rank comparable sold homes for the subject property.
    
    **Request body:**
    ```json
    {
      "house_details": {...},
      "top_n": 15
    }
    ```
    """
    adapter = get_adapter()
    return adapter.get_comps(house_details, top_n=top_n)  # type: ignore


@app.post("/tools/explain-price")
def tool_explain_price(
    house_details: dict[str, object],
    top_n: int = 5,
) -> dict[str, object]:
    """MCP Tool: Explain model price drivers for the subject property.
    
    **Request body:**
    ```json
    {
      "house_details": {...},
      "top_n": 5
    }
    ```
    """
    adapter = get_adapter()
    return adapter.explain_price(house_details, top_n=top_n)  # type: ignore


@app.post("/tools/explain-comps")
def tool_explain_comps(
    house_details: dict[str, object],
    top_n: int = 5,
) -> dict[str, object]:
    """MCP Tool: Explain why the top comps match the subject property.
    
    **Request body:**
    ```json
    {
      "house_details": {...},
      "top_n": 5
    }
    ```
    """
    adapter = get_adapter()
    return adapter.explain_comps(house_details, top_n=top_n)  # type: ignore


@app.post("/tools/export-comps-csv")
def tool_export_comps_csv(
    message: str = "",
    last_analysis: dict[str, object] | None = None,
    top_n: int | None = None,
    addresses: list[str] | None = None,
) -> dict[str, object]:
    """MCP Tool: Export rows for the latest comparable-sales table as CSV.
    
    **Request body:**
    ```json
    {
      "message": "export the comps",
      "last_analysis": {...},
      "top_n": 15,
      "addresses": ["123 Main St", ...]
    }
    ```
    """
    adapter = get_adapter()
    return adapter.export_comps_csv(  # type: ignore
        message=message,
        last_analysis=last_analysis,
        top_n=top_n,
        addresses=addresses,
    )

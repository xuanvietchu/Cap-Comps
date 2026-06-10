from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json
from queue import Queue
from threading import Thread

from api.comps_service import build_response
from api.pdf_form_parser import parse_house_details_pdf
from api.schemas import (
    ChatHistoryMessage,
    ChatRequest,
    PdfHouseDetailsRequest,
    PdfHouseDetailsResponse,
)

app = FastAPI(
    title="KV-Capital Comps Agent API",
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
    """Stream trace events as NDJSON, then emit the final chat response."""
    def events():
        queue: Queue[dict[str, object] | None] = Queue()

        def emit_trace(event: dict[str, object]) -> None:
            queue.put({"type": "trace", "event": event})

        def run_agent() -> None:
            try:
                result = build_response(
                    req.message,
                    req.house_details,
                    req.conversation_id,
                    conversation_history=serialize_history(req.conversation_history),
                    trace_sink=emit_trace,
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
    """Extract supported house-detail form fields from an uploaded PDF."""
    result = parse_house_details_pdf(req.data_base64, req.mime_type)
    return PdfHouseDetailsResponse(**result)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

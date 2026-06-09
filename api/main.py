from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import json
from queue import Queue
from threading import Thread

from api.comps_service import build_response
from api.schemas import ChatHistoryMessage, ChatRequest, ChatResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def serialize_history(messages: list[ChatHistoryMessage]) -> list[dict[str, str]]:
    return [{"role": message.role, "content": message.content} for message in messages]


@app.post("/chat")
def chat(req: ChatRequest) -> ChatResponse:
    result = build_response(
        req.message,
        req.house_details,
        req.conversation_id,
        conversation_history=serialize_history(req.conversation_history),
    )
    return ChatResponse(**result)


@app.post("/chat/stream")
def chat_stream(req: ChatRequest) -> StreamingResponse:
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


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

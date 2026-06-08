# uvicorn api.main:app --reload

from fastapi import FastAPI

from api.schemas import ChatRequest
from api.agent import agent

app = FastAPI()


@app.post("/chat")
def chat(req: ChatRequest):
    result = agent.invoke({
        "messages": [
            {"role": "user", "content": req.message}
        ]
    })

    return {
        "answer": result["messages"][-1].content
    }
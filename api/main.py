# uvicorn api.main:app --reload
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


from api.schemas import ChatRequest
from api.agent import agent

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/chat")
def chat(req: ChatRequest):
    user_content = req.message

    if req.house_details:
        user_content = f"""
User message:
{req.message}

House details:
{req.house_details}
""".strip()

    result = agent.invoke({
        "messages": [
            {"role": "user", "content": user_content}
        ],
        "conversation_id": req.conversation_id,
        "house_details": req.house_details,
    })

    return {
        "answer": result["messages"][-1].content,
        "conversation_id": req.conversation_id,
    }
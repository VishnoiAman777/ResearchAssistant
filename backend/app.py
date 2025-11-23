from dotenv import load_dotenv
_=load_dotenv()

from fastapi import FastAPI
from pydantic import BaseModel
from agents.deep_agent import DeepAgents


app = FastAPI()
# Creating a deep agent for updates
deep_agent = DeepAgents()

class ChatRequest(BaseModel):
    message: str


@app.post("/chat")
async def chat_endpoint(chat_request: ChatRequest):
    """Accept chat text and respond with a placeholder message."""
    # result = deep_agent.invoke(chat_request.message, thread_id="1")
    # print(result)
    return {"message": "backend running fine"}

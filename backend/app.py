# app.py
from dotenv import load_dotenv
load_dotenv()

import os
import uuid
import traceback
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agents.deep_agent import DeepAgents
import redis
import time

app = FastAPI(title="Research Assistant Backend")

# === CONFIG ===
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

# === ROBUST REDIS CONNECTION WITH RETRY ===
def get_redis_client():
    print(f"Connecting to Redis at {REDIS_HOST}:{REDIS_PORT}...")
    for attempt in range(15):
        try:
            client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True, db=0)
            client.ping()
            print("Redis connected successfully!")
            return client
        except redis.ConnectionError as e:
            print(f"Redis not ready (attempt {attempt + 1}/15): {e}")
            time.sleep(3)
    raise Exception("Failed to connect to Redis after multiple attempts")

redis_client = get_redis_client()

# === THREAD POOL ===
executor = ThreadPoolExecutor(max_workers=10)

# === AGENT ===
deep_agent = DeepAgents()

# === PYDANTIC MODELS ===
class ChatRequest(BaseModel):
    message: str
    thread_id: str

# Renamed to avoid any conflict with other modules
class TaskSubmitResponse(BaseModel):
    task_id: str
    status: str = "pending"
    message: str

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    result: str | None = None
    error: str | None = None


# === BACKGROUND TASK ===
def process_chat_task(task_id: str, message: str, thread_id: str):
    try:
        redis_client.hset(f"task:{task_id}", mapping={"status": "processing"})
        print(f"Task {task_id} started processing: {message[:50]}...")

        result = deep_agent.invoke(message, thread_id=thread_id)
        print("=="*100)
        print(result)
        print("=="*100)
        response_content = result["messages"][-1].content

        redis_client.hset(f"task:{task_id}", mapping={
            "status": "completed",
            "result": response_content
        })
        redis_client.expire(f"task:{task_id}", 3600)
        print(f"Task {task_id} completed successfully")

    except Exception as e:
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        print(f"Task {task_id} failed: {error_detail}")
        redis_client.hset(f"task:{task_id}", mapping={
            "status": "failed",
            "error": error_detail
        })
        redis_client.expire(f"task:{task_id}", 3600)


# === ENDPOINTS ===
@app.post("/chat", response_model=TaskSubmitResponse)
async def chat_endpoint(request: ChatRequest):
    task_id = str(uuid.uuid4())

    redis_client.hset(f"task:{task_id}", mapping={
        "status": "pending",
        "message": request.message,
        "thread_id": request.thread_id
    })
    redis_client.expire(f"task:{task_id}", 3600)

    executor.submit(process_chat_task, task_id, request.message, request.thread_id)

    return TaskSubmitResponse(
        task_id=task_id,
        message="Your request is being processed in the background..."
    )


@app.get("/status/{task_id}", response_model=TaskStatusResponse)
def get_task_status(task_id: str):
    key = f"task:{task_id}"
    if not redis_client.exists(key):
        raise HTTPException(status_code=404, detail="Task not found or expired")

    data = redis_client.hgetall(key)

    return TaskStatusResponse(
        task_id=task_id,
        status=data.get("status", "unknown"),
        result=data.get("result"),
        error=data.get("error")
    )


@app.get("/")
def health_check():
    return {"status": "ok", "message": "Research Assistant backend is running"}


@app.on_event("shutdown")
def shutdown_event():
    print("Shutting down thread pool...")
    executor.shutdown(wait=True)
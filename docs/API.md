# API Documentation

## Backend API Reference

The Research Assistant backend provides a RESTful API for submitting research queries and polling task status.

### Base URL

```
http://localhost:8000
```

---

## Endpoints

### 1. Health Check

**Endpoint**: `GET /`

**Description**: Verify backend service is running

**Response** (200 OK):
```json
{
  "status": "ok",
  "message": "Research Assistant backend is running"
}
```

**Example**:
```bash
curl http://localhost:8000/
```

---

### 2. Submit Chat Request

**Endpoint**: `POST /chat`

**Description**: Submit a research query for asynchronous processing

**Request Body**:
```json
{
  "message": "Research query string",
  "thread_id": "unique-conversation-identifier"
}
```

**Request Parameters**:
- `message` (string, required): The user's research query or chat message
- `thread_id` (string, required): Unique identifier for conversation continuity. Can be any string (UUID recommended)

**Response** (200 OK):
```json
{
  "task_id": "generated-task-uuid",
  "status": "pending",
  "message": "Your request is being processed in the background..."
}
```

**Response Fields**:
- `task_id` (string): Unique task identifier for polling status
- `status` (string): Initial status, always "pending"
- `message` (string): Human-readable confirmation message

**Errors**:
- 422: Validation error (missing/invalid fields)

**Example**:
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the latest developments in quantum computing?",
    "thread_id": "user-123-session-456"
  }'

# Response:
# {
#   "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
#   "status": "pending",
#   "message": "Your request is being processed in the background..."
# }
```

**Notes**:
- The endpoint returns immediately; processing happens asynchronously
- Use the returned `task_id` to poll for results
- Same `thread_id` maintains conversation context across multiple requests

---

### 3. Get Task Status

**Endpoint**: `GET /status/{task_id}`

**Description**: Check the status and retrieve results of a submitted task

**Path Parameters**:
- `task_id` (string, required): Task ID returned from `/chat` endpoint

**Response** (200 OK):
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "result": "## Research Results\n\nDetailed markdown-formatted response...",
  "error": null
}
```

**Response Fields**:
- `task_id` (string): Echo of requested task ID
- `status` (string): Current status ("pending", "processing", "completed", "failed")
- `result` (string | null): Markdown-formatted research results if completed; null otherwise
- `error` (string | null): Error details if failed; null otherwise

**Status Values**:
| Status | Meaning | Action |
|--------|---------|--------|
| pending | Queued but not yet started | Continue polling |
| processing | Currently being processed | Continue polling |
| completed | Finished successfully | Read `result` field |
| failed | Encountered an error | Read `error` field |

**Errors**:
- 404: Task not found or expired (expires after 1 hour)

**Example**:
```bash
curl http://localhost:8000/status/a1b2c3d4-e5f6-7890-abcd-ef1234567890

# Response (pending):
# {
#   "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
#   "status": "processing",
#   "result": null,
#   "error": null
# }

# Response (completed):
# {
#   "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
#   "status": "completed",
#   "result": "## Quantum Computing Advances\n\nRecent developments...",
#   "error": null
# }
```

**Notes**:
- Tasks are cached in Redis for 1 hour
- Polling interval of 5 seconds recommended
- Results contain full markdown-formatted research output

---

## Task Processing Flow

```
1. Client submits query to POST /chat
   ↓
2. Backend returns task_id immediately (status: pending)
   ↓
3. Task is queued in Redis and ThreadPoolExecutor
   ↓
4. DeepAgents begins processing (status: processing)
   ├─ Query analysis
   ├─ Optional human interrupt
   ├─ Web research delegation
   └─ Report synthesis
   ↓
5. Client polls GET /status/{task_id}
   ├─ If pending/processing → Continue polling in 5 seconds
   ├─ If completed → Display result field
   └─ If failed → Display error field
```

---

## Polling Strategy

### Recommended Client Implementation

```python
import requests
import time

def submit_research_query(message: str, thread_id: str):
    """Submit a research query and wait for completion."""
    
    # Submit query
    response = requests.post(
        "http://localhost:8000/chat",
        json={"message": message, "thread_id": thread_id}
    )
    task_id = response.json()["task_id"]
    print(f"Task submitted: {task_id}")
    
    # Poll for completion
    max_wait = 3600  # 1 hour timeout
    elapsed = 0
    poll_interval = 5  # seconds
    
    while elapsed < max_wait:
        status_response = requests.get(f"http://localhost:8000/status/{task_id}")
        data = status_response.json()
        
        if data["status"] == "completed":
            print("Research complete!")
            return data["result"]
        
        elif data["status"] == "failed":
            print(f"Task failed: {data['error']}")
            return None
        
        print(f"Status: {data['status']}... (elapsed: {elapsed}s)")
        time.sleep(poll_interval)
        elapsed += poll_interval
    
    print("Timeout: Research took too long")
    return None

# Usage
result = submit_research_query(
    "Latest developments in AI safety",
    "user-123-session-456"
)
print(result)
```

### JavaScript/TypeScript Implementation

```typescript
async function submitResearchQuery(message: string, threadId: string): Promise<string | null> {
  const baseUrl = "http://localhost:8000";
  
  // Submit query
  const submitResponse = await fetch(`${baseUrl}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, thread_id: threadId })
  });
  
  const { task_id } = await submitResponse.json();
  console.log(`Task submitted: ${task_id}`);
  
  // Poll for completion
  const maxWait = 3600000; // 1 hour in ms
  const pollInterval = 5000; // 5 seconds
  let elapsed = 0;
  
  while (elapsed < maxWait) {
    const statusResponse = await fetch(`${baseUrl}/status/${task_id}`);
    const data = await statusResponse.json();
    
    if (data.status === "completed") {
      console.log("Research complete!");
      return data.result;
    } else if (data.status === "failed") {
      console.error(`Task failed: ${data.error}`);
      return null;
    }
    
    console.log(`Status: ${data.status}...`);
    await new Promise(resolve => setTimeout(resolve, pollInterval));
    elapsed += pollInterval;
  }
  
  console.error("Timeout: Research took too long");
  return null;
}

// Usage
const result = await submitResearchQuery(
  "Latest developments in AI safety",
  "user-123-session-456"
);
console.log(result);
```

---

## Error Handling

### HTTP Status Codes

| Code | Scenario | Action |
|------|----------|--------|
| 200 | Success | Process response |
| 404 | Task not found | Task expired, resubmit |
| 422 | Invalid request | Check request format |
| 500 | Server error | Retry with backoff |

### Error Response Example

**Failed Task Response** (200 OK, but status="failed"):
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "failed",
  "result": null,
  "error": "Traceback (most recent call last):\n  ...\nException: Failed to process query\n..."
}
```

### Common Issues

**Issue**: Task expires before completion
- **Cause**: Processing took longer than 1 hour
- **Solution**: Increase Redis expiry time in `app.py` (line ~130)
- **Prevention**: Break complex queries into simpler sub-queries

**Issue**: Task not found (404)
- **Cause**: Task ID is invalid or expired
- **Solution**: Resubmit the query to get new task_id
- **Prevention**: Implement polling within 1-hour window

**Issue**: Backend connection refused
- **Cause**: Backend service not running
- **Solution**: Start backend: `uvicorn app:app --reload`
- **Prevention**: Check backend logs for startup errors

---

## Performance Characteristics

### Typical Response Times

| Query Type | Time Range | Notes |
|------------|-----------|-------|
| Simple fact | 10-30s | Direct API queries |
| Moderate research | 30-120s | 1-2 web searches |
| Complex research | 2-10 min | Multiple searches, synthesis |

### Resource Usage

- **Memory**: ~500MB baseline + ~100MB per concurrent task
- **Redis**: ~1KB per task (expires after 1 hour)
- **CPU**: Scales with concurrent requests

### Rate Limits

No built-in rate limiting, but consider:
- Tavily API rate limits (check documentation)
- NVIDIA NeMo Guard rate limits
- Anthropic Claude rate limits

---

## Thread ID Conventions

While `thread_id` can be any string, recommended patterns:

```
# User + Session based
format: {user_id}-{session_id}
example: user-12345-sess-67890

# UUID based
format: {uuid4}
example: a1b2c3d4-e5f6-7890-abcd-ef1234567890

# Custom context
format: {app}-{user}-{context}
example: web-app-user-42-research-session-1
```

**Benefits of thread_id continuity**:
- Maintains conversation context across requests
- Allows resuming interrupted research
- Enables multi-turn interactions
- Improves agent reasoning with history

---

## Authentication

Currently, the API has **no authentication**. For production deployment, add:

```python
# Example: Bearer token authentication
from fastapi import Security, HTTPException
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.post("/chat")
async def chat_endpoint(request: ChatRequest, credentials = Security(security)):
    token = credentials.credentials
    # Validate token...
    # Process request...
```

---

## Integration Examples

### Curl

```bash
# Submit
TASK_ID=$(curl -s -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"Research quantum computing","thread_id":"test-1"}' \
  | jq -r '.task_id')

# Poll
curl http://localhost:8000/status/$TASK_ID
```

### Python Requests

```python
import requests

# Submit
resp = requests.post("http://localhost:8000/chat", json={
    "message": "Research quantum computing",
    "thread_id": "test-1"
})
task_id = resp.json()["task_id"]

# Check status
status_resp = requests.get(f"http://localhost:8000/status/{task_id}")
print(status_resp.json())
```

### FastAPI Client

```python
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

# Submit
response = client.post("/chat", json={
    "message": "Research quantum computing",
    "thread_id": "test-1"
})
assert response.status_code == 200

# Check status
task_id = response.json()["task_id"]
status_response = client.get(f"/status/{task_id}")
assert status_response.status_code == 200
```

---

## Data Models

### ChatRequest

```python
class ChatRequest(BaseModel):
    message: str       # Research query
    thread_id: str     # Conversation identifier
```

### TaskSubmitResponse

```python
class TaskSubmitResponse(BaseModel):
    task_id: str = "uuid"          # Unique task identifier
    status: str = "pending"        # Initial status
    message: str = "confirmation"  # Human-readable message
```

### TaskStatusResponse

```python
class TaskStatusResponse(BaseModel):
    task_id: str          # Task identifier
    status: str           # pending | processing | completed | failed
    result: str | None    # Markdown-formatted result
    error: str | None     # Error details if failed
```

---

## Monitoring

### Redis CLI Commands

```bash
# List all tasks
redis-cli keys "task:*"

# Get task details
redis-cli hgetall task:{task_id}

# Monitor task updates
redis-cli monitor

# Clear expired tasks
redis-cli scan 0 MATCH "task:*" | xargs redis-cli del
```

### Health Monitoring

```python
import requests

def health_check():
    try:
        resp = requests.get("http://localhost:8000/", timeout=5)
        return resp.status_code == 200
    except:
        return False

# Implement in monitoring system
if not health_check():
    alert("Research Assistant backend is down!")
```

---

## Version History

| Version | Changes |
|---------|---------|
| 1.0 | Initial API release with chat and status endpoints |

---

## Support

For API issues:
1. Check backend logs: Docker logs or console output
2. Verify Redis connectivity: `redis-cli ping`
3. Test with simple queries before complex ones
4. Review error messages in task response

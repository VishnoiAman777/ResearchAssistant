# Research Assistant

A sophisticated multi-agent AI system for conducting comprehensive internet research and generating high-quality reports. The system orchestrates multiple specialized AI agents to analyze user queries, conduct web research, and synthesize findings into professional research documents.

## Things I could have done better(didn't had the time):
- Call the middleware tools in parallel
- Add Perplexity metric using GPT-2 score and create a custom heuristic to prevent GCG Attacks
- U can still embed harful content in the URL and exhaust the tavily search api usage, so a check is missing there
- Make middleware non block to research assistance to optimize for latency
- Stream the output back to the UI
- Add sequential thinking directly in the UI instead of langsmith
- Create a router for simple queries as deepagents take a lot of time
- Learned a lot thanks Repello team(first time thought from adversarial perspective)

## Overview

The Research Assistant is built on a multi-tier architecture combining:
- **Frontend**: Streamlit-based chat interface for user interaction
- **Backend**: FastAPI service with asynchronous task processing via Redis
- **Agent System**: DeepAgents orchestrator with specialized sub-agents for query analysis and research
- **Safety Layers**: Multiple security guardrails including content safety checks, jailbreak detection, and prompt injection prevention
- **Sequential Thinking**: U can see the sequential thinking of the model in langsmith

## Architecture

### System Components

```
Frontend (Streamlit)
         ↓
Backend (FastAPI)
    ├─ Task Queue (Redis)
    └─ DeepAgents Orchestrator
           ├─ Query Analyzer Sub-Agent
           └─ Research Sub-Agent(s)
                ├─ Tools: tavily_search, think_tool
                └─ Safety Middleware
                     ├─ Content Safety (NeMo)
                     ├─ Jailbreak Detection (NeMo)
                     ├─ Prompt Injection Detection
                     └─ Human-in-the-Loop Interrupts
```

## Quick Start

### Prerequisites

- Python 3.11
- Conda/Anaconda
- Docker (for Redis container)
- API Keys:
  - `TAVILY_API_KEY`: Tavily search service
  - `NVIDIA_NEMO_API`: NVIDIA NeMo Guard API
  - `NVIDIA_NEMO_CONTENT_SAFETY_URL`: NeMo content safety endpoint
  - `NVIDIA_NEMO_JAILBREAK_URL`: NeMo jailbreak detection endpoint

### Installation

1. **Set up environment**:
   ```bash
   conda env create -f environment.yml
   conda activate research_assistant
   ```

2. **Configure environment variables**: How to create env file
   ```bash
   TAVILY_API_KEY="tvly-"
    ANTHROPIC_API_KEY="sk-ant"
    NVIDIA_NEMO_CONTENT_SAFETY_URL="https://integrate.api.nvidia.com/v1"
    NVIDIA_NEMO_JAILBREAK_URL="https://ai.api.nvidia.com/v1/security/nvidia/nemoguard-jailbreak-detect"
    NVIDIA_NEMO_API="nvapi-"
    LANGSMITH_API_KEY="lsv2_"
    LANGSMITH_PROJECT="pr-"
    LANGSMITH_TRACING="true"
    LANGSMITH_ENDPOINT="https://api.smith.langchain.com"

   ```

3. **Start Redis**:
   ```bash
   docker-compose -f backend/docker-compose.yaml up -d
   ```

4. **Start backend** (in `/backend` directory):
   ```bash
   python app.py
   # or with uvicorn
   uvicorn app:app --reload --host 0.0.0.0 --port 8000
   ```

5. **Start frontend** (in `/frontend` directory):
   ```bash
   streamlit run app.py
   ```

The frontend will be available at `http://localhost:8501`

## Project Structure

```
ResearchAssistant/
├── backend/
│   ├── app.py                          # FastAPI server, task management
│   ├── docker-compose.yaml             # Redis container configuration
│   └── agents/
│       ├── deep_agent.py               # DeepAgents orchestrator
│       ├── middleware/
│       │   ├── content_safety.py       # Content safety middleware
│       │   ├── jailbreak.py            # Jailbreak detection middleware
│       │   ├── prompt_injection.py     # Prompt injection middleware
│       │   └── query_analyzer.py       # Query analysis interrupts
│       ├── guardrails/
│       │   ├── content_safety_check_nemo.py    # NeMo safety checks
│       │   ├── jailbreak_check_nemo.py         # NeMo jailbreak checks
│       │   └── prompt_injection_custom.py      # Custom LLM-based checks
│       ├── tools/
│       │   ├── tool.py                 # Research tools (search, reflect)
│       │   └── utils.py                # Utility functions
│       └── prompts/
│           └── PROMPTS.py              # System prompts for all agents
├── frontend/
│   └── app.py                          # Streamlit chat interface
└── environment.yml                     # Conda dependencies
```

## Core Modules

### Backend API (`backend/app.py`)

FastAPI application providing:
- **POST `/chat`**: Submit a research query
  - Input: `ChatRequest` (message, thread_id)
  - Output: `TaskSubmitResponse` (task_id, status)
- **GET `/status/{task_id}`**: Check task status and retrieve results
  - Output: `TaskStatusResponse` (status, result, error)
- **GET `/`**: Health check endpoint

**Task Processing Flow**:
1. Client submits query to `/chat` endpoint
2. Request is stored in Redis with "pending" status
3. Task is submitted to ThreadPoolExecutor for background processing
4. DeepAgents processes the query
5. Results stored back in Redis
6. Client polls `/status` endpoint until completion

### DeepAgents Orchestrator (`backend/agents/deep_agent.py`)

The main coordination system that:

1. **Initializes Agents**: Sets up query analyzer and research sub-agents
2. **Manages State**: Uses MemorySaver for conversation continuity via FilesystemBackend
3. **Applies Middleware**: Enforces safety policies before and after agent execution
4. **Invokes Agents**: Processes queries through the agentic workflow

**Key Methods**:
- `create_agents()`: Initializes all sub-agents with their configurations
- `invoke(query, thread_id)`: Processes a user query with conversation context

**Configuration Parameters**:
- `max_concurrent_research_units`: Max parallel research agents (default: 3)
- `max_researcher_iterations`: Max search iterations per agent (default: 5)
- `memory_path`: Directory for persistent agent memory

### Tools (`backend/agents/tools/tool.py`)

**tavily_search(query, max_results=1, topic="general")**
- Searches the web using Tavily API
- Fetches full webpage content and converts to Markdown
- Performs profanity filtering on results
- Returns formatted search results with citations

**think_tool(reflection)**
- Enables strategic reflection during research
- Helps agents pause, analyze gaps, and plan next steps
- Maintains transparent chain-of-thought reasoning

**Helper Function**:
- `fetch_webpage_content(url, timeout=10)`: Uses httpx to fetch pages and markdownify for conversion

### Middleware (`backend/agents/middleware/`)

**content_safety.py**
- `content_safety_user_middleware`: Checks incoming user messages for safety violations
- `content_safety_assistant_middleware`: Checks outgoing assistant responses
- Uses NVIDIA NeMo Guard for content safety classification
- Can jump to "end" node to stop processing if unsafe

**jailbreak.py**
- `jailbreak_middleware`: Detects jailbreak attempts in user messages
- Analyzes last 10 messages for patterns
- Integrates with NVIDIA NeMo jailbreak detection API
- Prevents adversarial manipulation attempts

**prompt_injection.py**
- `prompt_injection_middleware`: Custom detection for prompt injection attempts
- Analyzes last 5 human messages
- Uses Claude Haiku with structured output for classification
- Detects obfuscation, role-playing tricks, and system prompt leaks

**query_analyzer.py**
- `query_analyzer_human_interrupt_middleware`: Implements human-in-the-loop confirmation
- Parses JSON output from query-analyzer sub-agent
- Raises interrupt with proposed query and classification
- Allows user approval before proceeding with research

### Guardrails (`backend/agents/guardrails/`)

**content_safety_check_nemo.py**
- Uses NVIDIA NeMo Guard's content safety model
- Checks for both "User Safety" and "Response Safety"
- Returns boolean indicating if content is safe

**jailbreak_check_nemo.py**
- Calls NVIDIA NeMo jailbreak detection endpoint
- Uses Bearer token authentication
- Returns jailbreak classification

**prompt_injection_custom.py**
- Custom implementation using Claude Haiku
- Structured output with `SafeUnsafeDetection` Pydantic model
- Detects 10+ jailbreak/injection patterns
- Provides detailed explanations for classifications

### Prompts (`backend/agents/prompts/PROMPTS.py`)

System prompts for different agents:

**RESEARCH_WORKFLOW_INSTRUCTIONS**
- Main orchestrator workflow (8-step process)
- Emphasizes query analysis, delegation, synthesis, and verification
- Guides professional report generation

**QUERY_ANALYZER_INSTRUCTIONS**
- Query classification (simple, complex, rubbish, multitopic)
- JSON output format specification
- Handles ambiguous/rambling queries
- Determines if human interrupts needed

**RESEARCHER_INSTRUCTIONS**
- Guidelines for autonomous research sub-agents
- Tool usage patterns and reflection requirements
- Hard limits on search iterations (max 5 total calls)
- Quality evaluation and gap analysis framework

**SUBAGENT_DELEGATION_INSTRUCTIONS**
- Rules for single vs. parallel agent dispatch
- Explains when to use multiple agents (explicit comparisons only)
- Sets concurrency limits and iteration boundaries

**REPORT_WRITING_GUIDELINES**
- Professional formatting standards
- Structure templates for different query types
- Citation format and source documentation
- Emphasis on prose over bullet points

**SAFETY_CHECK_INSTRUCTIONS**
- Detailed prompt injection/jailbreak patterns (10+ categories)
- Examples of unsafe vs. safe inputs
- Guidance for Claude to make strict classifications

### Frontend (`frontend/app.py`)

Streamlit-based chat interface with:

**Session State Management**:
- `history`: Chat message history
- `processing_task`: Current task ID being processed
- `thread_id`: Unique identifier for conversation continuity

**Chat Flow**:
1. User submits query via `st.chat_input()`
2. Message displayed immediately
3. Request sent to backend `/chat` endpoint
4. Task ID received and stored in session state
5. Polling loop checks `/status` every 5 seconds
6. Response displayed when completed or error shown if failed

**Features**:
- Real-time chat history display
- Disabled input during processing
- Status spinner and info messages
- Error handling for connection issues
- Session-based user tracking

## Workflow Example

### User Journey

```
User Input:
"Tell me about the latest developments in quantum computing and also about AI chip leaders"

         ↓

Frontend sends to Backend:
POST /chat {message: "...", thread_id: "user-123"}

         ↓

Backend receives request:
1. Stores task in Redis with status="pending"
2. Submits to ThreadPoolExecutor

         ↓

DeepAgents Orchestrator processes:

Step 1: Query Analysis
  └─ Delegates to query-analyzer sub-agent
  └─ Gets JSON: {type: "multitopic", rewritten_query: "...", needs_interrupt: true}

Step 2: Human Interrupt (if needed)
  └─ Raises interrupt to ask user for confirmation

Step 3: Multi-topic Research
  └─ Delegates to 2 research agents in parallel:
     • Research Agent 1: "Latest developments in quantum computing"
     • Research Agent 2: "AI chip leaders and market analysis"

Step 4: Web Search Execution
  └─ Each agent:
     • Calls tavily_search with refined queries
     • Calls think_tool after each search for reflection
     • Identifies gaps and conducts follow-up searches
     • Performs synthesis with citations

Step 5: Result Aggregation
  └─ Main orchestrator deduplicates citations
  └─ Writes final_report.md with both topics

         ↓

Frontend polls /status endpoint:
GET /status/task-uuid

         ↓

Response received:
{
  "task_id": "task-uuid",
  "status": "completed",
  "result": "## Quantum Computing Developments\n...\n## AI Chip Leaders\n...",
  "error": null
}

         ↓

Display in chat:
Formatted markdown response in assistant message
```

## Safety Architecture

The system implements defense-in-depth with four layers:

### Layer 1: User Input Validation
- **Content Safety**: NVIDIA NeMo checks for harmful content
- **Jailbreak Detection**: NeMo identifies attempt patterns
- **Prompt Injection**: Custom LLM detects manipulation attempts

### Layer 2: Query Analysis
- Human-in-the-loop interrupts for ambiguous/complex queries
- User approval required before research proceeds

### Layer 3: Research Execution
- Sub-agents operate within strict iteration limits
- Tools have built-in profanity filtering

### Layer 4: Response Validation
- Content safety check on final response
- Assistant refusal phrases trigger second safety check
- Prevents unsafe content from reaching user

## Performance Considerations

### Optimization Strategies
- **Parallel Research**: Multiple agents can research different topics simultaneously (limited to 3 by default)
- **Iteration Limits**: Each research agent limited to 5 search iterations to prevent excessive API calls
- **Redis Caching**: Task state persists for 1 hour (3600 seconds)
- **Background Processing**: Long-running research doesn't block frontend

### Scaling Recommendations
- Increase `ThreadPoolExecutor` max_workers for more concurrent requests
- Adjust `max_concurrent_research_units` based on API rate limits
- Use Redis Cluster for distributed deployments
- Add database persistence layer for long-term task history




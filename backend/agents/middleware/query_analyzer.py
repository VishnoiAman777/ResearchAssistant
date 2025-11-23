"""
Query Analyzer Middleware Module

This module implements human-in-the-loop interrupts for the query analysis stage
of the research workflow. It allows the system to pause and ask for user confirmation
when the query analyzer detects ambiguous, multi-topic, or complex queries that
require clarification before proceeding with research.

This middleware sits in the langgraph workflow pipeline and intercepts the
output of the query-analyzer sub-agent to determine if user approval is needed.
"""

from langchain.agents.middleware import AgentState, after_agent
from langgraph.runtime import Runtime
import json
from langgraph.types import interrupt


@after_agent
def query_analyzer_human_interrupt_middleware(state: AgentState, runtime: Runtime):
    """
    Human-in-the-loop interrupt middleware for query analysis validation.

    This middleware function runs after the query-analyzer sub-agent completes
    execution. It intercepts the agent's JSON output to check if the query
    requires human approval before proceeding. If the query-analyzer determined
    that clarification is needed, this middleware raises an interrupt to pause
    the entire workflow and wait for user confirmation.

    The query-analyzer sub-agent produces a JSON response with this structure:
    {
        "type": "simple|complex|rubbish|multitopic",
        "rewritten_query": "Clarified research question",
        "needs_interrupt": true|false,
        "reason": "Explanation of analysis and any changes"
    }

    When needs_interrupt is true, this middleware:
    1. Extracts the proposed rewritten query
    2. Presents it to the user for approval
    3. Waits for user response (APPROVE or REJECT)
    4. Allows the workflow to resume or restart based on feedback

    Args:
        state (AgentState): The current state of the langgraph workflow containing
                           the message history and context. This state object is
                           maintained across the entire research workflow and carries
                           conversation history, configuration, and intermediate results.
                           The last message in state["messages"] should contain the
                           JSON output from the query-analyzer sub-agent.

        runtime (Runtime): The langgraph runtime object that manages workflow
                          execution context. Provides access to workflow metadata
                          and enables control flow operations like interrupts.
                          Not directly used in this middleware but required by
                          the @after_agent decorator signature.

    Returns:
        AgentState: Returns the state unchanged if:
                   - No interrupt is needed (needs_interrupt is false)
                   - JSON parsing fails
                   - Required keys are missing from the JSON response
                   
                   If an interrupt is raised, the function does not return
                   normally; instead, an interrupt is raised that pauses
                   the entire workflow.

    Raises:
        langgraph.types.Interrupt: Raised when needs_interrupt is true.
                                   Pauses the workflow and displays a message
                                   to the user with the proposed query and
                                   classification details. The interrupt includes:
                                   - message: User-facing prompt for approval
                                   - data: Structured context data including
                                           proposed_query, classification, and reason

    Workflow Position:
        This middleware is registered with @after_agent decorator, meaning it
        runs AFTER the query-analyzer sub-agent finishes but BEFORE control
        returns to the main orchestrator agent. This ensures query clarification
        happens early in the workflow before expensive research operations.

    Execution Flow:
        ```
        User Input
            ↓
        Main Orchestrator Agent delegates to query-analyzer
            ↓
        Query Analyzer Sub-Agent (returns JSON)
            ↓
        >>> query_analyzer_human_interrupt_middleware (THIS FUNCTION)
            ├─ Parse JSON from last message
            ├─ Check needs_interrupt flag
            └─ Either: Raise Interrupt OR Return state unchanged
            ↓
        If Interrupt: Workflow pauses, user sees prompt
        If No Interrupt: Control returns to Main Orchestrator
        ```

    Example Query Analysis Scenarios:

        Scenario 1: Simple Query (No Interrupt)
        -----------
        User: "What is the capital of France?"
        Query Analyzer Output: {
            "type": "simple",
            "rewritten_query": "What is the capital of France?",
            "needs_interrupt": false,
            "reason": "Clear, simple factual question"
        }
        → Middleware: Returns state unchanged
        → Workflow: Proceeds directly to research

        Scenario 2: Ambiguous Query (Needs Interrupt)
        -----------
        User: "Tell me about quantum computing and also AI stocks"
        Query Analyzer Output: {
            "type": "multitopic",
            "rewritten_query": "Latest quantum computing developments and top AI stocks 2025",
            "needs_interrupt": true,
            "reason": "Query covers two distinct topics: quantum computing and AI stocks"
        }
        → Middleware: Raises Interrupt
        → User sees:
            "Based on your query we are going to deep dive into the following aspects.
             Proposed query: Latest quantum computing developments and top AI stocks 2025
             Reply with: APPROVE | REJECT"
        → User responds with APPROVE/REJECT
        → Workflow: Resumes with user's decision

        Scenario 3: Rambling Query (Needs Interrupt)
        -----------
        User: "Hey so I'm researching about like quantum stuff and also my cat 
               is cute and also what's the future of AI? Oh and my friend said..."
        Query Analyzer Output: {
            "type": "complex",
            "rewritten_query": "Future developments in quantum computing and artificial intelligence",
            "needs_interrupt": true,
            "reason": "Removed personal statements, merged two research topics, 
                     focusing on substantive questions only"
        }
        → Middleware: Raises Interrupt
        → User confirms the reframed query
        → Workflow: Proceeds with cleaned-up research task

    Implementation Details:
        - Uses @after_agent decorator from langchain.agents.middleware
        - Parses JSON from the last message in state["messages"]
        - Handles both direct string JSON and parsed content
        - Gracefully handles malformed JSON (treats as "no interrupt")
        - Raises langgraph.types.interrupt, not Python's built-in Exception
        - Preserves all state information during interrupt

    Error Handling:
        The function catches three exception types:
        - json.JSONDecodeError: If the message content is not valid JSON
        - KeyError: If required keys are missing from parsed JSON
        - TypeError: If content is not JSON-compatible (e.g., None, numbers)
        
        In all error cases, the function silently continues (returns state unchanged).
        This is intentional: malformed analyzer output should not crash the workflow,
        just skip the interrupt mechanism.

    Integration with Workflow:
        - Part of the @after_agent pipeline in query-analyzer sub-agent
        - Registered in DeepAgents.create_agents() method
        - Enables human-in-the-loop quality control early in workflow
        - Reduces wasted computation on misunderstood queries
        - Improves user satisfaction by confirming intent before research

    User Interaction:
        When an interrupt is raised, the user sees a prompt like:
        ```
        Based on your query we are going to deep dive into the following aspects.
        
        Proposed query: {rewritten_query}
        
        Reply with: APPROVE | REJECT
        ```
        
        User must type either "APPROVE" or "REJECT" (case-insensitive handling
        depends on langgraph framework implementation). The response is captured
        and used to control workflow resumption.

    Performance Notes:
        - This middleware executes immediately after query analysis (~<100ms)
        - JSON parsing is fast for typical queries
        - No external API calls made by this middleware
        - Interrupt wait time depends on user response (seconds to minutes)

    See Also:
        - QUERY_ANALYZER_INSTRUCTIONS: Prompt for query-analyzer sub-agent
        - DeepAgents.create_agents(): Where middleware is registered
        - langgraph.types.interrupt: Framework-level interrupt mechanism
        - AgentState: LangChain state management structure

    Note:
        The commented-out role check (lines 16-17) was a safety measure to
        ensure only assistant messages are processed. It's disabled because
        the query-analyzer always outputs as "assistant", making it redundant.
        Consider re-enabling if agents are modified to produce different message types.
    """
    # The last message from the query-analyzer should be its JSON output
    last_msg = state["messages"][-1]

    # if last_msg.get("role") != "assistant":
    #     return state  # safety

    try:
        content = last_msg.content
        # Handle both direct string JSON and tool calls that contain JSON
        if isinstance(content, str):
            data = json.loads(content)
        else:
            # Sometimes it's already parsed in .tool_calls or .additional_kwargs
            data = content

        if data.get("needs_interrupt") is True:
            # This will pause the ENTIRE graph (including main agent)
            # but the state stays clean — only query-analyzer's local output is in messages
            raise interrupt(
                message=(
                    "Based on your query we are going to deep dive into the following aspects.\n\n"
                    f"Proposed query : {data['rewritten_query']}\n\n"
                    "Reply with: APPROVE | REJECT "
                ),
                data={
                    "proposed_query": data["rewritten_query"],
                    "classification": data["type"],
                    "reason": data["reason"],
                },
            )
    except (json.JSONDecodeError, KeyError, TypeError):
        pass  # Not valid JSON or no interrupt → continue normally

    return state

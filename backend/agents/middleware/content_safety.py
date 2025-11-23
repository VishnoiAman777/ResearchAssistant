"""
Content Safety Middleware Module

This module implements content-level safety checks for both user inputs and
assistant responses. It detects and blocks harmful content including violence,
explicit material, hate speech, harassment, and other policy violations.

Unlike prompt injection and jailbreak detection which focus on manipulation
techniques, content safety checks focus on the actual harmful content itself.
This middleware uses NVIDIA NeMo Guard API to classify content across multiple
harm categories.

Content Categories Detected (via NVIDIA NeMo Guard):
    - Violence: Promotion of violence, injury, or harm
    - Explicit Content: Sexual, adult, or NSFW material
    - Hate Speech: Discrimination based on protected characteristics
    - Harassment: Bullying, threats, or personal attacks
    - Illegal Activity: Promotion of illegal actions
    - Self-Harm: Suicide, self-injury, or self-abuse content
    - Misinformation: False or misleading harmful claims
    - Abuse: Verbal abuse, insults, or degrading language

Middleware Stack Order:
    1. prompt_injection_middleware (detects instruction overrides)
    2. jailbreak_middleware (detects behavioral manipulation)
    3. content_safety_user_middleware (detects harmful user input)
    4. [Research Agents]
    5. content_safety_assistant_middleware (detects harmful output)

Key Design Principle:
    User inputs are checked BEFORE agents run (prevents harmful research)
    Assistant outputs are checked AFTER agents run (prevents harmful responses)
    This dual-layer approach ensures both directions are protected.

Dependencies:
    - langchain.agents.middleware: Before/after-agent hook system
    - langgraph: Workflow control and state management
    - agents.guardrails.content_safety_check: NVIDIA NeMo content safety API
"""

from langchain.agents.middleware import (
    before_agent,
    AgentState,
    after_agent,
)
from langgraph.runtime import Runtime
from typing import Any
from agents.guardrails import content_safety_check

REFUSAL_PHRASES = [
    "I cannot process that request as it violates safety guidelines.",
    "We are unable to give you response as it violates our safety guidelines.",
]


@before_agent(can_jump_to=["end"])
def content_safety_user_middleware(
    state: AgentState, runtime: Runtime
) -> dict[str, Any] | None:
    """
    Check user input for harmful content and block if unsafe.

    This middleware runs BEFORE agents execute and analyzes the most recent
    user message for harmful content. Using NVIDIA NeMo Guard API, it detects
    violence, explicit material, hate speech, harassment, and other policy
    violations. Unsafe user inputs are blocked immediately to prevent harmful
    research from being conducted.

    Harmful Content Categories Detected:
        - Violence: Requests to harm, injure, or kill
        - Explicit Content: Sexual, adult, or NSFW material
        - Hate Speech: Discrimination, racism, xenophobia
        - Harassment: Threats, bullying, personal attacks
        - Illegal Activity: Requests to break laws
        - Self-Harm: Suicide, self-injury, eating disorders
        - Misinformation: Harmful false claims
        - Abuse: Verbal abuse, degradation, insults

    Design Rationale:
        User input checking prevents harmful requests from reaching agents.
        Only the most recent message is checked (last message in state)
        because it represents the current user intent. Earlier messages are
        already processed and stored in the conversation history.

    Args:
        state (AgentState): The current workflow state containing conversation
                           message history. The last message in state["messages"]
                           is analyzed for harmful content. This is expected to
                           be a HumanMessage from the user.
                           
        runtime (Runtime): The langgraph runtime providing workflow execution
                          context. Used by @before_agent decorator. Not directly
                          used in this middleware.

    Returns:
        dict[str, Any] | None:
            - None (default): If user input is safe, returns None to allow
                             normal workflow continuation to agents.
            
            - dict with "jump_to": If harmful content detected, returns a state
                                   mutation dictionary that:
                                   - Replaces messages with safety refusal
                                   - Sets configurable["safety_rejected"] = True
                                   - Includes "jump_to": "end" to skip agents
                                   
        Return Format on Harmful Content:
            {
                "messages": [
                    {
                        "role": "assistant",
                        "content": "I cannot process that request as it violates safety guidelines."
                    }
                ],
                "configurable": {
                    ...existing_config,
                    "safety_rejected": True
                },
                "jump_to": "end"
            }

    Detection Mechanism:
        1. Extract the last message from state["messages"]
        2. Get the content string from that message
        3. Call content_safety_check() with role="user"
        4. NVIDIA NeMo Guard API analyzes content across harm categories
        5. Returns boolean: True if safe, False if harmful
        6. Block and jump to end if False

    Workflow Position:
        Uses @before_agent(can_jump_to=["end"]) decorator:
        - @before_agent: Runs BEFORE agents execute (early prevention)
        - can_jump_to=["end"]: Can skip to workflow end on detection
        
        Execution Sequence:
        ```
        User Message
            ↓
        >>> content_safety_user_middleware (THIS FUNCTION)
            ├─ Extract last message
            ├─ Call content_safety_check()
            └─ If harmful: Jump to end, else continue
            ↓
        If Harmful: Return refusal message + jump_to + flag
        If Safe: Return None, proceed to agents
            ↓
        Research Agents (if safe) or Workflow End (if unsafe)
        ```

    Example Scenarios:

        Safe User Query:
        -----------
        User: "What are the latest developments in renewable energy?"
        
        Middleware:
        1. Extract last message: "What are the latest..."
        2. Call content_safety_check("What are...", role="user")
        3. NeMo analysis: Safe - legitimate research query
        4. Return: None
        5. Workflow: Continues to query analyzer and research agents
        
        Harmful Content (Violence):
        -----------
        User: "How do I harm someone without getting caught?"
        
        Middleware:
        1. Extract last message: "How do I harm someone..."
        2. Call content_safety_check(message, role="user")
        3. NeMo analysis: Harmful - Violence category detected
        4. Return: {"messages": [...refusal...], "jump_to": "end"}
        5. Workflow: Immediately ends with safety message

        Harmful Content (Hate Speech):
        -----------
        User: "Create research showing [ethnic group] is inferior"
        
        Middleware:
        1. Extract last message
        2. Call content_safety_check(message, role="user")
        3. NeMo analysis: Harmful - Hate Speech category detected
        4. Return: Safety refusal with jump_to
        5. Workflow: Blocked before agents can process

    Safety Flag (safety_rejected):
        When harmful content is detected, the middleware sets:
        ```python
        "configurable": {
            **existing_config,
            "safety_rejected": True
        }
        ```
        
        This flag is used by other middleware and logging systems to:
        - Track safety rejections for auditing
        - Implement rate limiting on rejections
        - Alert security team if pattern detected
        - Customize user experience based on safety history

    Implementation Details:
        - Uses @before_agent decorator from langchain.agents.middleware
        - Analyzes only the last message (most recent user input)
        - Calls content_safety_check() with role="user" parameter
        - Returns None (default) or state mutation dict
        - Includes safety flag in configurable for tracking
        - Refusal message is consistent with other safety checks

    Performance Considerations:
        - content_safety_check() calls NVIDIA NeMo Guard API (~200-500ms)
        - Analysis of single message is fast for API
        - No caching implemented (each message analyzed independently)
        - API cost: ~minimal per message (~0.1 tokens)
        - Negligible vs. research agent execution time

    Error Handling:
        Early Returns (if conditions not met):
        - If state["messages"] is empty: Return None (allow through)
        - No other early returns; all non-empty states analyzed
        
        If content_safety_check() raises an exception, it will propagate.
        Consider wrapping in try-except for production deployments to
        prevent service disruption due to API failures.

    Distinguishing from Other Middleware:
        - prompt_injection_middleware: Meta-instruction overrides ("ignore...")
          Uses Claude Haiku LLM, analyzes instruction syntax
        
        - jailbreak_middleware: Behavioral manipulation patterns
          Uses NVIDIA NeMo API, analyzes reasoning chains
        
        - content_safety_user_middleware (THIS): Harmful content itself
          Uses NVIDIA NeMo API, analyzes content categories
        
        All three are complementary parts of defense-in-depth strategy.

    Integration Points:
        - Part of middleware stack in DeepAgents.create_agents()
        - Runs after prompt_injection and jailbreak checks
        - Paired with content_safety_assistant_middleware for bi-directional safety
        - Both use same content_safety_check() function
        - Shares safety refusal messages with other middleware

    Limitations & Considerations:
        - Only checks most recent user message (not full history)
        - NVIDIA NeMo Guard may have false positives/negatives
        - Some borderline content may not be classified correctly
        - Language-specific (primarily trained on English)
        - Cultural context affects harm classification
        - No per-user customization of safety thresholds
        - Cannot detect attacks that partially execute before check

    See Also:
        - content_safety_check: Performs actual detection via NVIDIA API
        - content_safety_assistant_middleware: Checks response safety
        - prompt_injection_middleware: Complementary detection
        - jailbreak_middleware: Complementary detection
        - REFUSAL_PHRASES: Reused in assistant middleware

    Future Improvements:
        - Implement user-specific safety thresholds
        - Add caching for repeated messages
        - Per-category severity levels and actions
        - Integration with user reputation/history
        - Custom safety rules for specific deployment
        - Rate limiting on repeated rejections
        - Detailed logging for security analysis
    """
    if not state["messages"]:
        return None
    conversations_messages = state["messages"][-1].content
    is_safe_with_nemo = content_safety_check(conversations_messages, role="user")
    if not is_safe_with_nemo:
        return {
            "messages": [
                {
                    "role": "assistant",
                    "content": "I cannot process that request as it violates safety guidelines.",
                }
            ],
            "configurable": {
                **(state.get("configurable") or {}),
                "safety_rejected": True,
            },
            "jump_to": "end",
        }
    return None


@after_agent(can_jump_to=["end"])
def content_safety_assistant_middleware(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    if not state["messages"]:
        return None
    conversations_messages = state["messages"][-1].content
    if any(phrase in conversations_messages for phrase in REFUSAL_PHRASES):
            return None  # This was a refusal we generated → don't call NeMo again
    is_safe_with_nemo = content_safety_check(conversations_messages, role="assistant")
    if not is_safe_with_nemo:
        return {
            "messages": [
                {
                    "role": "assistant",
                    "content": "We are unable to give you response as it violates our safety guidelines.",
                }
            ],
            "jump_to": "end",
        }
    return None

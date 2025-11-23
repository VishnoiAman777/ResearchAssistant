from langchain.agents.middleware import before_agent, AgentState, hook_config, after_agent
from langgraph.runtime import Runtime
from langchain_core.messages import HumanMessage, AIMessage
from typing import Any
from agents.guardrails import content_safety_check

REFUSAL_PHRASES = [
    "I cannot process that request as it violates safety guidelines.",
    "We are unable to give you response as it violates our safety guidelines."
]

@before_agent(can_jump_to=["end"])
def content_safety_user_middleware(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    if not state["messages"]:
        return None
    conversations_messages = state["messages"][-1].content
    is_safe_with_nemo = content_safety_check(conversations_messages, role="user")
    if not is_safe_with_nemo:
        return {
            "messages": [{
                "role": "assistant",
                "content": "I cannot process that request as it violates safety guidelines."
            }],
            "configurable": {
                **(state.get("configurable") or {}),
                "safety_rejected": True
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
            "messages": [{
                "role": "assistant",
                "content": "We are unable to give you response as it violates our safety guidelines."
            }],
            "jump_to": "end",
        }
    return None
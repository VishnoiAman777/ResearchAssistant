from langchain.agents.middleware import before_agent, AgentState, after_agent
from langgraph.runtime import Runtime
from langchain_core.messages import HumanMessage, AIMessage
from typing import Any
from agents.guardrails import jailbreak_check


@before_agent(can_jump_to=["end"])
def jailbreak_middleware(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    if not state["messages"]:
        return None
    last_msg = state["messages"][-1]
    # LangChain uses .type, not .role
    if not isinstance(last_msg, HumanMessage):
        return None

    if jailbreak_check(last_msg.content):
        return {
            "messages": [{
                "role": "assistant",
                "content": "I cannot process that request as it's a jailbreak attempt."
            }],
            "jump_to": "end",
        }
    return None

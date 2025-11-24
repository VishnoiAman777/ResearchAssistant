import concurrent.futures
from typing import Any, Callable, Dict, List, Optional
from langchain.agents.middleware import before_agent, after_agent
from langgraph.runtime import Runtime
from langchain.agents.middleware import AgentState
from langchain_core.messages import HumanMessage
from langgraph.types import interrupt
import json
from agents.guardrails import jailbreak_check
from .base_middleware import BaseMiddleware

class JailbreakMiddleware(BaseMiddleware):
    """
    Jailbreak detection middleware (before agent).
    """
    def __init__(self):
        super().__init__()

    def before_agent_logic(self, state: AgentState, runtime: Runtime) -> Optional[Dict[str, Any]]:
        if not state.get("messages"):
            return None
        human_messages = [msg.content for msg in state["messages"] if isinstance(msg, HumanMessage)]
        if not human_messages:
            return None
        last_human_messages = human_messages[-10:]
        combined_msg = "\n".join(last_human_messages)
        if jailbreak_check(combined_msg):
            return {
                "messages": [
                    {
                        "role": "assistant",
                        "content": self.refusal_phrases[0],
                    }
                ],
                "jump_to": "end",
            }
        return None


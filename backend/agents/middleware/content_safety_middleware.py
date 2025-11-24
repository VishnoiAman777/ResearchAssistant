import concurrent.futures
from typing import Any, Callable, Dict, List, Optional
from langchain.agents.middleware import before_agent, after_agent
from langgraph.runtime import Runtime
from langchain.agents.middleware import AgentState
from langchain_core.messages import HumanMessage
from langgraph.types import interrupt
import json
from agents.guardrails import content_safety_check
from .base_middleware import BaseMiddleware

class ContentSafetyUserMiddleware(BaseMiddleware):
    """
    Content safety middleware for user inputs (before agent).
    """
    def __init__(self):
        super().__init__()

    def before_agent_logic(self, state: AgentState, runtime: Runtime) -> Optional[Dict[str, Any]]:
        if not state.get("messages"):
            return None
        last_message = state["messages"][-1].content
        is_safe = content_safety_check(last_message, role="user")
        if not is_safe:
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


class ContentSafetyAssistantMiddleware(BaseMiddleware):
    """
    Content safety middleware for assistant outputs (after agent).
    """
    def __init__(self):
        super().__init__()

    def after_agent_logic(self, state: AgentState, runtime: Runtime) -> Optional[Dict[str, Any]]:
        if not state.get("messages"):
            return None
        last_message = state["messages"][-1].content
        if any(phrase in last_message for phrase in self.refusal_phrases):
            return None  # Skip check for our own refusals
        is_safe = content_safety_check(last_message, role="assistant")
        if not is_safe:
            return {
                "messages": [
                    {
                        "role": "assistant",
                        "content": self.refusal_phrases[1],
                    }
                ],
                "jump_to": "end",
            }
        return None


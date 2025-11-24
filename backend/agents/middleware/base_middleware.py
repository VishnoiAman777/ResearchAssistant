import concurrent.futures
from typing import Any, Callable, Dict, List, Optional
from langchain.agents.middleware import before_agent, after_agent
from langgraph.runtime import Runtime
from langchain.agents.middleware import AgentState
from langchain_core.messages import HumanMessage
from langgraph.types import interrupt
import json

class BaseMiddleware:
    """
    Base class for all middlewares. Provides common structure.
    Subclasses should implement before_agent_logic and/or after_agent_logic.
    """
    def __init__(self, can_jump_to: List[str] = ["end"]):
        self.can_jump_to = can_jump_to
        self.refusal_phrases = [
            "I cannot process that request as it violates safety guidelines.",
            "We are unable to give you response as it violates our safety guidelines.",
        ]

    def before_agent_logic(self, state: AgentState, runtime: Runtime) -> Optional[Dict[str, Any]]:
        raise NotImplementedError("Subclasses should implement this if using @before_agent")

    def after_agent_logic(self, state: AgentState, runtime: Runtime) -> Optional[Dict[str, Any]]:
        raise NotImplementedError("Subclasses should implement this if using @after_agent")

    @before_agent(can_jump_to=["end"])
    def before_agent_wrapper(self, state: AgentState, runtime: Runtime) -> Optional[Dict[str, Any]]:
        return self.before_agent_logic(state, runtime)

    @after_agent(can_jump_to=["end"])
    def after_agent_wrapper(self, state: AgentState, runtime: Runtime) -> Optional[Dict[str, Any]]:
        return self.after_agent_logic(state, runtime)


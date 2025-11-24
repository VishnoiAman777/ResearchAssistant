import concurrent.futures
from typing import Any, Callable, Dict, List, Optional
from langchain.agents.middleware import before_agent, after_agent
from langgraph.runtime import Runtime
from langchain.agents.middleware import AgentState
from langchain_core.messages import HumanMessage
from langgraph.types import interrupt
import json
from .base_middleware import BaseMiddleware



class QueryAnalyzerHumanInterruptMiddleware(BaseMiddleware):
    """
    Human interrupt middleware for query analyzer (after agent).
    """
    def after_agent_logic(self, state: AgentState, runtime: Runtime) -> AgentState:
        last_msg = state["messages"][-1]
        try:
            content = last_msg.content
            data = json.loads(content) if isinstance(content, str) else content
            if data.get("needs_interrupt"):
                raise interrupt(
                    message=(
                        "Based on your query we are going to deep dive into the following aspects.\n\n"
                        f"Proposed query: {data['rewritten_query']}\n\n"
                        "Reply with: APPROVE | REJECT"
                    ),
                    data={
                        "proposed_query": data["rewritten_query"],
                        "classification": data["type"],
                        "reason": data["reason"],
                    },
                )
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
        return state

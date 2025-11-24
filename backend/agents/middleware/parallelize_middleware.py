import concurrent.futures
from typing import Any, Dict, List, Optional
from langchain.agents.middleware import before_agent
from langgraph.runtime import Runtime
from langchain.agents.middleware import AgentState
from .base_middleware import BaseMiddleware
from langchain.agents.middleware import after_agent, before_agent
from functools import partial



class ParallelBeforeMiddleware:
    """
    Composite middleware to run multiple before_agent middlewares in parallel.
    Runs all provided middlewares concurrently and returns the first non-None result
    (indicating a block). If all return None, returns None.
    """
    def __init__(self, middlewares: List[BaseMiddleware]):
        self.middlewares = middlewares
        @before_agent(can_jump_to=["end"])
        def before_agent_logic(state: AgentState, runtime: Runtime) -> Optional[Dict[str, Any]]:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [
                    executor.submit(mw.before_agent_logic, state, runtime)
                    for mw in self.middlewares
                ]
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result is not None:
                        return result 
            return None
        self.before_agent_wrapper = before_agent_logic



class ParallelAfterMiddleware:
    """
    Composite middleware to run multiple after_agent middlewares in parallel.
    Runs all provided middlewares concurrently and returns the first non-None result
    (indicating a block). If all return None, returns None.
    """
    def __init__(self, middlewares: List[BaseMiddleware]):
        self.middlewares = middlewares
        @after_agent(can_jump_to=["end"])
        def after_agent_logic(state: AgentState, runtime: Runtime) -> Optional[Dict[str, Any]]:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                futures = [
                    executor.submit(mw.after_agent_logic, state, runtime)
                    for mw in self.middlewares
                ]
                for future in concurrent.futures.as_completed(futures):
                    result = future.result()
                    if result is not None:
                        return result
            return None

        self.after_agent_wrapper = after_agent_logic




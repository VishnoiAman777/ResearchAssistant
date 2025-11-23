from typing import Any
from openai import OpenAI
from langchain.agents.middleware import before_agent, AgentState, hook_config, after_agent
from langgraph.runtime import Runtime
import requests
import json


@after_agent
def query_analyzer_human_interrupt_middleware(state: AgentState, runtime: Runtime):
    """
    Runs right after the query-analyzer sub-agent finishes.
    If it decided needs_interrupt: true → raise Interrupt with nice message.
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
        with open("debug_message.txt", "w", encoding="utf-8") as f:
            message.pretty_print(stream=f)        # prints nicely formatted to file
            f.write(message.pretty_repr())        # returns a string you can write


        print("="*100)
        if data.get("needs_interrupt") is True:
            # This will pause the ENTIRE graph (including main agent)
            # but the state stays clean — only query-analyzer's local output is in messages
            raise Interrupt(
                message=(
                    "Based on your query we are going to deep dive into the following aspects.\n\n"
                    f"Proposed query : {data['rewritten_query']}\n\n"
                    "Reply with: APPROVE | REJECT "
                ),
                # Optional: store the proposed data for resume logic
                data={
                    "proposed_query": data["rewritten_query"],
                    "classification": data["type"],
                    "reason": data["reason"]
                }
            )
    except (json.JSONDecodeError, KeyError, TypeError):
        pass  # Not valid JSON or no interrupt → continue normally
    
    return state
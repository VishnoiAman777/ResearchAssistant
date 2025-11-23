from langchain_core.tools import InjectedToolArg, tool
from tavily import TavilyClient
from typing_extensions import Annotated, Literal
import os 
tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])
from agents.tools.utils import fetch_webpage_content


@tool()
def tavily_search(
    query: str,
    max_results: Annotated[int, InjectedToolArg] = 1,
    topic: Annotated[
        Literal["general", "news", "finance"], InjectedToolArg
    ] = "general",
) -> str:
    """Search the web for information on a given query.
    Uses Tavily to discover relevant URLs, then fetches and returns full webpage content as markdown.
    Args:
        query: Search query to execute
        max_results: Maximum number of results to return (default: 1)
        topic: Topic filter - 'general', 'news', or 'finance' (default: 'general')
    Returns:
        Formatted search results with full webpage content
    """
    # Use Tavily to discover URLs
    search_results = tavily_client.search(
        query,
        max_results=max_results,
        topic=topic,
    )
    # Fetch full content for each URL
    result_texts = []
    for result in search_results.get("results", []):
        url = result["url"]
        title = result["title"]

        # Fetch webpage content
        content = fetch_webpage_content(url)

        result_text = f"""## {title}**URL:** {url} \n\n{content}---"""
    result_texts.append(result_text)
    # Format final response
    response = f"""🔍 Found {len(result_texts)} result(s) for '{query}': {chr(10).join(result_texts)}"""
    return response


@tool()
def think_tool(reflection: str) -> str:
    """Enhanced tool for strategic reflection.
    Use after each action to pause, analyze, and plan. Input a verbose reflection string structured as:
    1. Findings: ...
    2. Gaps: ...
    3. Quality: ...
    4. Next: ...
    5. Progress: ...

    Returns a parsed dict for easy use in workflows."""
    return f"Reflection recorded: {reflection}"

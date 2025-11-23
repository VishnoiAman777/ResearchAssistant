"""
Research Agent Tools Module

This module provides specialized tools for research agents to conduct web searches
and strategic reflection during the research process. It includes integration with
the Tavily search API for web discovery and content fetching capabilities.

Tools Exported:
    - tavily_search: Web search with full content fetching
    - think_tool: Strategic reflection and analysis

Module Dependencies:
    - langchain_core: LangChain tool decorators
    - tavily: Web search API client
    - better_profanity: Content filtering library
    - utils: Webpage content fetching utilities

Environment Variables:
    TAVILY_API_KEY (str): API key for Tavily search service
"""

from langchain_core.tools import InjectedToolArg, tool
from tavily import TavilyClient
from typing_extensions import Annotated, Literal
import os
from agents.tools.utils import fetch_webpage_content
from better_profanity import profanity


tavily_client = TavilyClient(api_key=os.environ["TAVILY_API_KEY"])


def detect_bad(query: str) -> str:
    """
    Detect profanity, NSFW content, and inappropriate language in text.

    This function uses the better_profanity library to classify text content
    for policy violations. It returns a simple yes/no classification that is
    used to filter research results before returning to users.

    Args:
        query (str): Text to analyze for inappropriate language or content.
                    Can be any length, typically result text or search output.

    Returns:
        str: Either "yes" if profanity/inappropriate content is detected,
             or "no" if the text passes the safety check.

    Example:
        >>> detect_bad("Hello world")
        'no'
        
        >>> detect_bad("This contains a bad word: [profanity]")
        'yes'

    Note:
        - Uses pre-configured better_profanity library settings
        - May have false positives/negatives depending on library version
        - Used internally by tavily_search to filter results
    """
    if profanity.contains_profanity(query):
        return "yes"
    return "no"


@tool()
def tavily_search(
    query: str,
    max_results: Annotated[int, InjectedToolArg] = 1,
    topic: Annotated[
        Literal["general", "news", "finance"], InjectedToolArg
    ] = "general",
) -> str:
    """
    Search the web and retrieve full webpage content as markdown-formatted text.

    This tool integrates with the Tavily search API to discover relevant URLs
    for a given query, then fetches and converts each webpage to markdown format.
    Results are filtered for content safety before being returned to the agent.

    This is a LangChain tool designed to be used by research agents for autonomous
    web discovery and content retrieval. The tool handles all steps of the search
    process including URL discovery, content fetching, format conversion, and
    safety validation.

    Args:
        query (str): The search query string describing the topic or information
                    to find. Should be specific and detailed for better results.
                    Example: "latest developments in quantum computing 2024"

        max_results (int, optional): Maximum number of search results to process
                    and return. Injected by LangChain framework, not exposed to
                    agent. Defaults to 1. Range: 1-20.
                    Note: Higher values increase API costs and processing time.

        topic (str, optional): Category filter for search results. Injected by
                    LangChain framework, not exposed to agent. Must be one of:
                    - "general": Default broad search across all domains
                    - "news": Filter for recent news articles and press releases
                    - "finance": Filter for financial news and market data
                    Defaults to "general".

    Returns:
        str: Formatted markdown string containing all search results. Format:
            ```
            🔍 Found {N} result(s) for '{query}': 
            ## {Title1}
            **URL:** {URL1}
            {Full markdown content from webpage}
            ---
            ## {Title2}
            **URL:** {URL2}
            {Full markdown content from webpage}
            ---
            ```
            
            If a result violates safety guidelines, the content is replaced with:
            ```
            ## {Title}
            **URL:** {URL}
            Content violates safety guidelines
            ```

    Raises:
        No exceptions raised directly. Errors from API calls or webpage fetching
        are caught and included in output (see fetch_webpage_content for details).

    Process Flow:
        1. Call Tavily API with query, max_results, and topic filter
        2. Extract URLs and titles from search results
        3. For each URL:
           a. Fetch webpage content using fetch_webpage_content()
           b. Convert HTML to markdown
           c. Check content for profanity/safety violations
           d. Include full content or safety message in results
        4. Format all results as a single markdown string
        5. Return formatted results to agent

    Example Usage (as called by agent):
        >>> result = tavily_search("quantum computing breakthroughs")
        >>> print(result)
        🔍 Found 1 result(s) for 'quantum computing breakthroughs':
        ## Google Quantum AI Achieves Breakthrough
        **URL:** https://example.com/article
        # Quantum Computing Breakthrough
        Google's latest quantum computer...
        ---

    Implementation Details:
        - Uses LangChain's @tool() decorator for agent integration
        - max_results and topic are InjectedToolArg (controlled by framework)
        - query is a free argument that agents can set dynamically
        - Content safety check uses detect_bad() function
        - Markdown conversion preserves article structure and formatting

    Performance Considerations:
        - Tavily API call: ~100-500ms
        - Content fetching per URL: ~500-2000ms each
        - Total time scales linearly with max_results
        - Recommended: max_results <= 3 for real-time applications
        - Results cached in Tavily API when possible

    Safety & Limitations:
        - Profanity filter uses better_profanity library (may have false positives)
        - Large webpages may be truncated by httpx timeout (10 seconds default)
        - Some websites may block automated requests (404, 403 errors)
        - JavaScript-rendered content not included (static HTML only)
        - PDF and other non-HTML content handled by browser fallback

    See Also:
        - fetch_webpage_content: Converts HTML to markdown
        - detect_bad: Content safety filtering function
        - think_tool: For reflection after search results

    Note:
        This tool should be called after agents use think_tool to reflect on
        what they need to search for, ensuring targeted and efficient queries.
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

        if detect_bad(result_text) == "yes":
            result_texts.append(
                f"""## {title} **URL: ** {url} \n\n Content violates safety guidelines"""
            )
        else:
            result_texts.append(result_text)
    # Format final response
    response = f"""🔍 Found {len(result_texts)} result(s) for '{query}': {chr(10).join(result_texts)}"""
    return response


@tool()
def think_tool(reflection: str) -> str:
    """
    Strategic reflection tool for research agents to pause and analyze progress.

    This tool enables research agents to pause execution, reflect on findings,
    identify gaps, assess quality, and plan next steps. It provides a checkpoint
    mechanism for transparent reasoning and deliberate strategy formation during
    the research process.

    The think_tool is typically invoked AFTER every research action (search,
    content fetch, etc.) to ensure agents maintain a clear chain-of-thought
    and make intentional decisions rather than blindly iterating.

    Args:
        reflection (str): A structured reflection string capturing the agent's
                         analysis. Should be verbose and detailed, structured
                         according to the five-part reflection framework:
                         
                         1. Findings: Summary of key facts, quotes, or data
                            discovered so far. Include source URLs for traceability.
                            Example: "Found that Tesla has 5-star NHTSA rating
                                     (https://example.com). Rivian has safety
                                     concerns per [URL]."
                         
                         2. Gaps: Specific information that is still missing or
                            unclear. Identifies what additional research is needed.
                            Example: "Missing data on Ford EV safety features.
                                     No information about battery safety testing."
                         
                         3. Quality: Assessment of evidence credibility and
                            source quality. Evaluates timeliness and diversity
                            of sources gathered so far.
                            Example: "Sources are recent (2025), from major
                                     publications, and cover multiple angles.
                                     Credibility: High. Missing expert opinions."
                         
                         4. Next: Clear strategic decision about what to do next.
                            Should specify either a follow-up search query or
                            a decision to proceed to synthesis.
                            Example: "Perform targeted search on 'Ford Mustang
                                     Mach-E safety ratings 2025' to fill gap.
                                     Then synthesize all findings."
                         
                         5. Progress: Estimate of completion percentage and
                            rationale for the estimate. Helps agents assess
                            if they have sufficient information to conclude.
                            Example: "70% complete. Have coverage of 2 brands,
                                     need third brand comparison for complete answer."

    Returns:
        str: A confirmation message indicating the reflection has been recorded.
             Format: "Reflection recorded: {reflection}"
             
             The returned message is meant to be added to the agent's thought
             chain but doesn't affect subsequent actions. The value is in the
             deliberation process, not the return value.

    Example Usage:
        >>> reflect = think_tool(
        ...     "1. Findings: Gathered 3 sources on quantum computing.\n"
        ...     "2. Gaps: Need info on practical applications.\n"
        ...     "3. Quality: All sources post-2024, high credibility.\n"
        ...     "4. Next: Search 'quantum computing applications industry 2025'.\n"
        ...     "5. Progress: 60% - Have theory, need applications."
        ... )
        >>> print(reflect)
        Reflection recorded: 1. Findings: Gathered 3 sources on quantum computing...

    Workflow Integration:
        Typical agent flow with think_tool:
        
        1. Agent receives research task
        2. Agent calls think_tool to plan initial approach
        3. Agent calls tavily_search with refined query
        4. Agent calls think_tool to reflect on results
        5. Loop: If gaps exist, go to step 3; else proceed
        6. Agent calls think_tool to assess readiness for synthesis
        7. Agent synthesizes findings into report
        
    Benefits:
        - Transparent reasoning: All thought processes recorded in conversation
        - Prevents loops: Quality assessment prevents infinite iterations
        - Better queries: Reflection-based refinement improves search effectiveness
        - Verifiable process: Chain-of-thought can be audited by human reviewers
        - Cost control: Explicit "done" decision prevents wasteful API calls

    Best Practices:
        - Always call think_tool after major actions (searches, fetches)
        - Be verbose and specific in reflections
        - Use all five sections even if one is just "N/A"
        - Reference URLs and specific quotes when possible
        - Estimate progress conservatively to avoid premature conclusions

    Implementation Notes:
        - This is a LangChain tool wrapped by @tool() decorator
        - Used by agents in langgraph workflows
        - Returns immediately with confirmation
        - Primary value is in the reflection process itself
        - Enables human monitoring and intervention if needed

    See Also:
        - tavily_search: Companion tool for research execution
        - RESEARCHER_INSTRUCTIONS: Full guidelines on reflection usage
        - think_tool usage in PROMPTS.py for detailed patterns

    Warning:
        This tool doesn't enforce the five-part structure - agents should
        follow the pattern for consistency and clarity. Malformed reflections
        may indicate agent confusion and warrant manual investigation.
    """
    return f"Reflection recorded: {reflection}"

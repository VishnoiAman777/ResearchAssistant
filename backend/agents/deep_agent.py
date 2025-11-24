from langchain_anthropic import ChatAnthropic
from agents.prompts import (
    RESEARCHER_INSTRUCTIONS,
    RESEARCH_WORKFLOW_INSTRUCTIONS,
    SUBAGENT_DELEGATION_INSTRUCTIONS,
    QUERY_ANALYZER_INSTRUCTIONS,
    REPORT_WRITING_GUIDELINES
)
from agents.tools import think_tool, tavily_search
from deepagents.backends import FilesystemBackend
from deepagents import create_deep_agent
import os
from langgraph.checkpoint.memory import MemorySaver
from langsmith import traceable
from agents.middleware import (
    ParallelBeforeMiddleware,
    ParallelAfterMiddleware,
    PromptInjectionMiddleware,
    PromptInjectionSubAgentMiddleware,
    JailbreakMiddleware,
    ContentSafetyUserMiddleware,
    ContentSafetyAssistantMiddleware,
    QueryAnalyzerHumanInterruptMiddleware
)


class DeepAgents:
    """
    DeepAgents: A multi-agent research and query analysis system.
    This class orchestrates multiple AI agents to perform internet research, query analysis,
    and report generation. It uses Claude Sonnet 4.0 as the underlying language model and
    implements various safety middlewares to ensure content policy compliance.
    Attributes:
        final_instruction (str): Combined system instructions including research workflow,
            subagent delegation, and report writing guidelines.
        memory_path (str): File system path for storing agent memory files.
        model (ChatAnthropic): Claude Sonnet 4.0 language model instance.
        checkpointer (MemorySaver): Checkpoint manager for conversation state persistence.
        research_sub_agent (dict): Configuration for the internet research agent with
            tavily_search and think_tool capabilities.
        query_analyzer_sub_agent (dict): Configuration for query analysis and classification
            agent with human-in-the-loop interrupt capability.
        agent: The main deep agent instance created with all subagents and middlewares.
    Args:
        max_concurrent_research_units (int, optional): Maximum number of research units
            that can run concurrently. Defaults to 3.
        max_researcher_iterations (int, optional): Maximum number of iterations a
            researcher agent can perform. Defaults to 5.
        memory_path (str, optional): Path to directory for storing agent memory files.
            Defaults to "./agent_memory_files" in the current working directory.
    Example:
        >>> agent_system = DeepAgents(max_concurrent_research_units=5)
        >>> result = agent_system.invoke("Research climate change impacts", thread_id="user123")
        >>> resumed = agent_system.resume_execution(thread_id="user123")
    Methods:
        create_agents(): Initializes research and query analyzer subagents with their
            respective tools, prompts, and middlewares.
        invoke(query, thread_id): Processes a user query through the agent system.
        resume_execution(thread_id): Resumes execution after a human interrupt with approval.
    Safety Features:
        - Content safety middleware for user and assistant messages
        - Jailbreak detection and prevention
        - Prompt injection detection
        - Human-in-the-loop interrupts for query confirmation
    """
    def __init__(self, max_concurrent_research_units=3, max_researcher_iterations=5, memory_path=os.path.join(os.path.abspath(os.getcwd()), "agent_memory_files")):
        self.final_instruction = (
            RESEARCH_WORKFLOW_INSTRUCTIONS
            + "\n\n" + "="*100 + "\n\n"
            + SUBAGENT_DELEGATION_INSTRUCTIONS.format(
                max_concurrent_research_units=max_concurrent_research_units,
                max_researcher_iterations=max_researcher_iterations,
            )
            + "\n\n" + "="*100 + "\n\n"
            + REPORT_WRITING_GUIDELINES
        )
        self.memory_path = memory_path
        self.model = ChatAnthropic(model="claude-sonnet-4-0")
        self.checkpointer = MemorySaver() # Currently storing checkpoints in memory but can change it
        self.create_agents()


    def create_agents(self):
        self.research_sub_agent = {
            "name": "internet-research-agent",
            "description": "Use this agent if you want to conduct a resarch on a specific topic like temperature/cooking/stocks/research using internet. Only give this researcher one topic at a time.",
            "system_prompt": RESEARCHER_INSTRUCTIONS,
            "tools": [tavily_search, think_tool],
            "middleware": [ParallelAfterMiddleware([PromptInjectionSubAgentMiddleware()]).after_agent_wrapper]
        }
        self.query_analyzer_sub_agent = {
            "name": "query-analyzer",
            "description": "Analyze and rewrite the user's query for clarity, type, and alignment. Classify as: simple (direct fact), complex (needs research/sub-queries), rubbish (nonsensical/irrelevant), or pivot (topic shift). Rewrite if unclear or disaligned, and suggest interrupts for user confirmation.",
            "system_prompt": QUERY_ANALYZER_INSTRUCTIONS,
            "tools": [think_tool],
            "middleware": [ParallelAfterMiddleware([QueryAnalyzerHumanInterruptMiddleware()]).after_agent_wrapper]
        }

        # Group before-agent middlewares for parallelism (prompt injection, jailbreak, content safety user)
        parallel_before = ParallelBeforeMiddleware([
            PromptInjectionMiddleware(),
            JailbreakMiddleware(),
            ContentSafetyUserMiddleware()
        ])

        # Updated: Wrap after-agent middlewares (currently just content safety assistant) for parallelism/future-proofing
        parallel_after = ParallelAfterMiddleware([ContentSafetyAssistantMiddleware()])

        # Updated middleware list: Pass bound methods in the original logical order
        # (all before_agents via the parallel wrapper, then all after_agents via the parallel wrapper)
        self.agent = create_deep_agent(
            model=self.model,
            system_prompt=self.final_instruction,
            subagents=[self.research_sub_agent, self.query_analyzer_sub_agent],
            backend=FilesystemBackend(root_dir=self.memory_path, virtual_mode=True),
            checkpointer=self.checkpointer,
            middleware=[parallel_before.before_agent_wrapper, parallel_after.after_agent_wrapper]
        )

    @traceable
    def invoke(self, query, thread_id):
        config = {"configurable": {"thread_id": thread_id}}
        result = self.agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": query }
                ],
            }, 
            config=config,
        )
        return result
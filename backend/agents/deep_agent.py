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
from langchain_core.messages import HumanMessage, AIMessage
import uuid
from agents.middleware import content_safety_assistant_middleware, content_safety_user_middleware, jailbreak_middleware, query_analyzer_human_interrupt_middleware
from agents.utils import format_message_content
from langsmith import traceable


class DeepAgents:
    def __init__(self, max_concurrent_research_units=3, max_researcher_iterations=5, memory_path=os.path.join(os.path.abspath(os.getcwd()), "agent_memory_files")):
        self.final_instruction = INSTRUCTIONS = (
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
        }

        self.query_analyzer_sub_agent = {
            "name": "query-analyzer",
            "description": "Analyze and rewrite the user's query for clarity, type, and alignment. Classify as: simple (direct fact), complex (needs research/sub-queries), rubbish (nonsensical/irrelevant), or pivot (topic shift). Rewrite if unclear or disaligned, and suggest interrupts for user confirmation.",
            "system_prompt": QUERY_ANALYZER_INSTRUCTIONS,
            "tools": [think_tool],
            "middleware": [query_analyzer_human_interrupt_middleware]
        }
        self.agent = create_deep_agent(
            model=self.model,
            system_prompt=self.final_instruction,
            subagents=[self.research_sub_agent, self.query_analyzer_sub_agent],
            backend=FilesystemBackend(root_dir=self.memory_path, virtual_mode=True),
            checkpointer=self.checkpointer,
            middleware=[content_safety_user_middleware, content_safety_assistant_middleware, jailbreak_middleware]
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
    
    @traceable
    def resume_execution(self, thread_id):
        config = {"configurable": {"thread_id": thread_id}}
        result = self.agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": "APPROVE"  # Or "REJECT" based on your decision
                    }
                ],
            }, 
            config=config,
        )



        
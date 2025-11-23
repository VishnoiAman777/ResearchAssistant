from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from agents.prompts import SAEFTY_CHECK_INSTRUCTIONS


class SafeUnsafeDetection(BaseModel):
    classification: str = Field(
        description="Must be exactly 'safe' or 'unsafe' (lowercase)",
        pattern="^(safe|unsafe)$",
    )
    explanation: str = Field(
        description="Detailed, pedantic explanation citing specific phrases, patterns, and why it matches or doesn't match known jailbreak techniques"
    )


def llm_prompt_check(user_input: str) -> SafeUnsafeDetection:
    """
    Detects whether a user message is a jailbreak/prompt injection attempt.
    Returns a structured Pydantic object with classification and explanation.
    """
    SAFETY_PROMPT = ChatPromptTemplate.from_messages(
        [("system", SAEFTY_CHECK_INSTRUCTIONS), ("human", "{user_input}")]
    )
    llm = ChatAnthropic(
        model="claude-haiku-4-5",
        temperature=0.0,
        max_tokens=1024,
    )

    # This is the modern LangChain way — direct structured output
    structured_llm = llm.with_structured_output(SafeUnsafeDetection)
    chain = SAFETY_PROMPT | structured_llm
    result: SafeUnsafeDetection = chain.invoke({"user_input": user_input})
    return result.classification == "safe"

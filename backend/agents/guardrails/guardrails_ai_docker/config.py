from guardrails import Guard
from guardrails.hub import DetectJailbreak
from guardrails.hub import LLMCritic
from guardrails.hub import ProfanityFree


guard = Guard()
guard.name = 'jailbreak'
guard.use(DetectJailbreak()) 

guard.name = "profanity_detector"
guard.use(ProfanityFree)

guard.name ="llm_judge"
guard.use(LLMCritic(
    llm_callable="claude-sonnet-4-0",
    max_score=100,
    on_fail="exception",
    metrics={
        "informative": {
            "description": "An informative summary captures the main points of the input and is free of irrelevant details.",
            "threshold": 75,
        },
        "coherent": {
            "description": "A coherent summary is logically organized and easy to follow.",
            "threshold": 50,
        },
        "concise": {
            "description": "A concise summary is free of unnecessary repetition and wordiness.",
            "threshold": 50,
        },
        "engaging": {
            "description": "An engaging summary is interesting and holds the reader's attention.",
            "threshold": 50,
        },
    }
))
from openai import OpenAI
import os
import json

nemo_client = OpenAI(
    base_url=os.environ["NVIDIA_NEMO_CONTENT_SAFETY_URL"],
    api_key=os.environ["NVIDIA_NEMO_API"],
)


def content_safety_check(query, role):
    completion = nemo_client.chat.completions.create(
        model="nvidia/llama-3.1-nemoguard-8b-content-safety",
        messages=[
            {"role": role, "content": query},
        ],
        stream=False,
    )
    verdict = json.loads(completion.choices[0].message.content)
    return (verdict.get("User Safety", "safe") == "safe") and (
        verdict.get("Response Safety", "safe") == "safe"
    )

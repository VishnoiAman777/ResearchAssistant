import requests
import json
import os

def jailbreak_check(query):
    invoke_url = os.environ["NVIDIA_NEMO_JAILBREAK_URL"]
    headers = {
        "Authorization": f"Bearer {os.environ['NVIDIA_NEMO_API']}",
        "Accept": "application/json"
    }
    payload = {
        "input": query
    }
    response = requests.post(invoke_url, headers=headers, json=payload)
    return response.json()["jailbreak"]
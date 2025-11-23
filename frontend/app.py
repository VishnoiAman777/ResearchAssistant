import os

import requests
import streamlit as st

st.set_page_config(page_title="Research Assistant Chat", page_icon="💬")
st.title("Research Assistant Chat")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000/chat")

if "history" not in st.session_state:
    # Preserve chat transcript between reruns.
    st.session_state.history = []

for message in st.session_state.history:
    st.chat_message(message["role"]).write(message["content"])

if prompt := st.chat_input("Say something to the backend"):
    st.session_state.history.append({"role": "user", "content": prompt})

    try:
        response = requests.post(BACKEND_URL, json={"message": prompt}, timeout=10)
        response.raise_for_status()
        payload = response.json()
        reply = payload.get("message", "backend running fine")
    except Exception as exc:
        reply = f"Request failed: {exc}"

    st.session_state.history.append({"role": "assistant", "content": reply})
    st.rerun()

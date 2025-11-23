"""
Research Assistant Chat Frontend - Streamlit Application

A real-time chat interface for interacting with a research assistant backend.
This application provides a user-friendly interface for submitting research queries
and receiving AI-generated responses through an asynchronous task processing system.

Features:
    - Interactive chat history display
    - Asynchronous task processing with polling mechanism
    - Session-based user tracking with unique thread IDs
    - Real-time status updates during processing
    - Error handling and connection management

Environment Variables:
    BACKEND_URL (str): Base URL of the backend service. Defaults to "http://localhost:8000"

Workflow:
    1. User submits a query via chat input
    2. Request is sent to the backend's /chat endpoint
    3. Backend returns a task_id for the request
    4. Frontend polls the /status endpoint at regular intervals
    5. Once completed, the result is displayed in chat history
"""

import os
import time
import uuid
import requests
import streamlit as st

st.set_page_config(page_title="Research Assistant Chat", page_icon="💬")
st.title("Research Assistant Chat")

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
CHAT_ENDPOINT = f"{BACKEND_URL}/chat"
STATUS_ENDPOINT = f"{BACKEND_URL}/status"

# ============================================================================
# SESSION STATE INITIALIZATION
# ============================================================================
# Initialize session state
if "history" not in st.session_state:
    st.session_state.history = []
if "processing_task" not in st.session_state:
    st.session_state.processing_task = None
if "thread_id" not in st.session_state:
    st.session_state.thread_id = str(uuid.uuid4())

# ============================================================================
# CHAT HISTORY DISPLAY
# ============================================================================
# Display chat history
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ============================================================================
# BACKGROUND TASK POLLING LOGIC
# ============================================================================
# Poll for task status updates if a task is currently processing
# The polling mechanism checks the status every 5 seconds until completion or failure
if st.session_state.processing_task:
    task_id = st.session_state.processing_task

    with st.chat_message("assistant"):
        status_ph = st.empty()
        spinner = st.spinner("Processing your request... This may take 10–60 seconds.")

        try:
            resp = requests.get(f"{STATUS_ENDPOINT}/{task_id}", timeout=10)
            resp.raise_for_status()
            data = resp.json()

            if data["status"] == "completed":
                result = data.get("result", "No result returned.")
                st.session_state.history.append(
                    {"role": "assistant", "content": result}
                )
                st.session_state.processing_task = None
                st.success("Response ready!")
                st.rerun()

            elif data["status"] == "failed":
                error = data.get("error", "Unknown error")
                st.session_state.history.append(
                    {"role": "assistant", "content": f"**Error:** {error}"}
                )
                st.session_state.processing_task = None
                st.error("Task failed")
                st.rerun()

            elif data["status"] in ["pending", "processing"]:
                # Keep polling every 5 seconds
                time.sleep(5)
                st.rerun()

        except requests.exceptions.RequestException as e:
            st.error(f"Connection lost: {e}")
            st.session_state.processing_task = None
            st.rerun()

# ============================================================================
# CHAT INPUT & REQUEST SUBMISSION
# ============================================================================
# Handle user input and send requests to the backend
if prompt := st.chat_input(
    "Ask anything...", disabled=st.session_state.processing_task is not None
):
    st.session_state.history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Sending request..."):
            try:
                resp = requests.post(
                    CHAT_ENDPOINT,
                    json={"message": prompt, "thread_id": st.session_state.thread_id},
                    timeout=15,
                )
                resp.raise_for_status()
                payload = resp.json()

                task_id = payload["task_id"]
                st.session_state.processing_task = task_id

                st.info("Request accepted! Processing in background...")
                st.rerun()

            except requests.exceptions.RequestException as e:
                st.error(f"Failed to reach backend: {e}")
            except Exception as e:
                st.error(f"Unexpected error: {e}")

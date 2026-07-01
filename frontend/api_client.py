"""
api_client.py · Thin HTTP client for the DocMind FastAPI backend.

Keeps every `requests` call and URL in one place so the Streamlit UI
code never talks HTTP directly — it only calls these functions.
"""

import os
from typing import Optional

import requests

API_BASE_URL = os.environ.get("DOCMIND_API_URL", "http://localhost:8000")
DEFAULT_TIMEOUT = 60  # seconds; LLM calls can be slow


class ApiError(RuntimeError):
    """Raised when the backend returns an error response."""


def _raise_for_status(resp: requests.Response) -> None:
    if resp.ok:
        return
    try:
        detail = resp.json().get("detail", resp.text)
    except ValueError:
        detail = resp.text
    raise ApiError(f"[{resp.status_code}] {detail}")


def health_check() -> bool:
    try:
        resp = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return resp.ok
    except requests.RequestException:
        return False


def send_chat_message(message: str, thread_id: Optional[str] = None) -> dict:
    """POST /chat → {thread_id, reply, tool_calls}"""
    resp = requests.post(
        f"{API_BASE_URL}/chat",
        json={"message": message, "thread_id": thread_id},
        timeout=DEFAULT_TIMEOUT,
    )
    _raise_for_status(resp)
    return resp.json()


def upload_document(file_bytes: bytes, filename: str, thread_id: Optional[str] = None) -> dict:
    """POST /documents/upload → {thread_id, filename, documents, chunks}"""
    files = {"file": (filename, file_bytes, "application/pdf")}
    data = {"thread_id": thread_id} if thread_id else {}
    resp = requests.post(
        f"{API_BASE_URL}/documents/upload",
        files=files,
        data=data,
        timeout=DEFAULT_TIMEOUT,
    )
    _raise_for_status(resp)
    return resp.json()


def list_threads() -> list[dict]:
    """GET /threads → list of {thread_id, has_document, document_metadata}"""
    resp = requests.get(f"{API_BASE_URL}/threads", timeout=DEFAULT_TIMEOUT)
    _raise_for_status(resp)
    return resp.json().get("threads", [])


def get_thread_messages(thread_id: str) -> dict:
    """GET /threads/{thread_id}/messages → {thread_id, messages, document_metadata}"""
    resp = requests.get(
        f"{API_BASE_URL}/threads/{thread_id}/messages",
        timeout=DEFAULT_TIMEOUT,
    )
    _raise_for_status(resp)
    return resp.json()



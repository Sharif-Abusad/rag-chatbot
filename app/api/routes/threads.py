from fastapi import APIRouter, HTTPException
from app.services.retriever import get_document_metadata
from app.models.schemas import (
    ThreadListResponse,
    ThreadSummary, 
    ThreadMessagesResponse,
)
from app.services.thread import (
    retrieve_all_threads,
    thread_document_metadata,
    thread_has_document,
)
from app.services.conversations import get_messages
router = APIRouter(prefix="/threads", tags=["threads"])


@router.get("", response_model=ThreadListResponse)
def list_threads():
    """List all known conversation threads and whether each has a document indexed."""
    threads = [
        ThreadSummary(
            thread_id=tid,
            has_document=thread_has_document(tid),
            document_metadata=thread_document_metadata(tid),
        )
        for tid in retrieve_all_threads()
    ]
    return ThreadListResponse(threads=threads)


@router.get("/{thread_id}/messages", response_model=ThreadMessagesResponse)
def get_thread_messages(thread_id: str):
    # Retrieve the chat history for the thread
    messages = get_messages(thread_id)  # Replace with your implementation

    if messages is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    return ThreadMessagesResponse(
        thread_id=thread_id,
        messages=messages,
        document_metadata=get_document_metadata(thread_id=thread_id)
    )
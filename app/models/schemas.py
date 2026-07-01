import uuid
from typing import Any, Optional

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's message text")
    thread_id: Optional[str] = Field(
        default=None,
        description="Existing conversation thread id. Omit to start a new thread.",
    )

    def resolved_thread_id(self) -> str:
        return self.thread_id or str(uuid.uuid4())


class ToolCallInfo(BaseModel):
    name: str
    args: dict[str, Any]


class ChatResponse(BaseModel):
    thread_id: str
    reply: str
    tool_calls: list[ToolCallInfo] = []


class IngestResponse(BaseModel):
    thread_id: str
    filename: str
    documents: int
    chunks: int


class ThreadSummary(BaseModel):
    thread_id: str
    has_document: bool
    document_metadata: dict[str, Any] = {}


class ThreadListResponse(BaseModel):
    threads: list[ThreadSummary]


class MessageItem(BaseModel):
    role: str  # "user" | "assistant"
    content: str


class ThreadMessagesResponse(BaseModel):
    thread_id: str
    messages: list[MessageItem]
    document_metadata: dict[str, Any] = {}


class HealthResponse(BaseModel):
    status: str = "ok"

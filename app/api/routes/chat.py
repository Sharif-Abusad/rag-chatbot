import logging

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.messages import HumanMessage

from app.api.deps import get_chatbot
from app.models.schemas import ChatRequest, ChatResponse, ToolCallInfo
from app.services.conversations import save_message

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def send_message(payload: ChatRequest, chatbot=Depends(get_chatbot)):
    """
    Send a message to the chatbot for a given thread.

    If `thread_id` is omitted, a new conversation thread is created and
    its id is returned so the client can continue the conversation.
    """
    thread_id = payload.resolved_thread_id()
    config = {"configurable": {"thread_id": thread_id}}

    try:
        result = chatbot.invoke(
            {"messages": [HumanMessage(content=payload.message)]},
            config=config,
        )
        save_message(
            thread_id=thread_id,
            role="user",
            message=payload.message,
        )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Chat invocation failed for thread %s", thread_id)
        raise HTTPException(status_code=502, detail=f"LLM call failed: {exc}") from exc

    last_message = result["messages"][-1]
    tool_calls = [
        ToolCallInfo(name=tc["name"], args=tc.get("args", {}))
        for tc in getattr(last_message, "tool_calls", []) or []
    ]
    save_message(
        thread_id=thread_id,
        role="assistant",
        message=last_message.content,
    )
    return ChatResponse(
        thread_id=thread_id,
        reply=last_message.content,
        tool_calls=tool_calls,
    )

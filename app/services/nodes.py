import logging
import time

from langgraph.prebuilt import ToolNode

from app.core.state import ChatState
from app.services.prompts import get_system_prompt
from app.services.retriever import index_exists
from app.services.tools import llm_with_tools, tools

logger = logging.getLogger(__name__)

MAX_LLM_RETRIES = 3
RETRYABLE_ERRORS = ("Failed to call a function", "failed_generation")


def chat_node(state: ChatState, config=None):
    """Main LLM node. Retries on transient tool-calling failures from the provider."""

    thread_id = None
    if config:
        thread_id = config.get("configurable", {}).get("thread_id")

    has_document = thread_id is not None and index_exists(thread_id)
    system_message = get_system_prompt(has_document=has_document, thread_id=thread_id)
    messages = [system_message, *state["messages"]]

    last_exception = None

    for attempt in range(MAX_LLM_RETRIES):
        try:
            response = llm_with_tools.invoke(messages, config=config)
            return {"messages": [response]}
        except Exception as exc:  # noqa: BLE001
            error = str(exc)
            if any(marker in error for marker in RETRYABLE_ERRORS):
                last_exception = exc
                if attempt < MAX_LLM_RETRIES - 1:
                    logger.warning(
                        "Retryable LLM error (attempt %s/%s): %s",
                        attempt + 1,
                        MAX_LLM_RETRIES,
                        error,
                    )
                    time.sleep(1)
                    continue
            raise

    raise last_exception


tool_node = ToolNode(tools)

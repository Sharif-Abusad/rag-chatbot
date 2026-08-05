import logging
import time

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import ToolNode

from app.core.state import ChatState
from app.services.prompts import get_retry_correction_message, get_system_prompt
from app.services.retriever import index_exists
from app.services.tools import llm_with_tools, tools

logger = logging.getLogger(__name__)

MAX_LLM_RETRIES = 3
RETRYABLE_ERRORS = ("Failed to call a function", "failed_generation", "tool_use_failed")


def chat_node(state: ChatState, config=None):
    """
    Main LLM node.

    On a failed_generation / tool_use_failed error (which Groq raises when the
    model produces a malformed tool call — e.g. passing thread_id to web_search),
    we inject a correction message that spells out the exact tool signatures and
    retry. This prevents the model from repeating the same malformed call.
    """
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

        except Exception as exc:
            error = str(exc)
            is_retryable = any(marker in error for marker in RETRYABLE_ERRORS)

            if not is_retryable:
                raise

            last_exception = exc
            logger.warning(
                "Retryable LLM tool-call error (attempt %d/%d): %s",
                attempt + 1, MAX_LLM_RETRIES, error[:200],
            )

            if attempt < MAX_LLM_RETRIES - 1:
                # Inject a correction message so the LLM understands what
                # it did wrong and uses the correct tool signature on the
                # next attempt — instead of repeating the same broken call.
                correction = HumanMessage(content=get_retry_correction_message())
                messages = messages + [correction]
                time.sleep(1)

    raise last_exception


tool_node = ToolNode(tools)

import logging
from typing import Optional

import requests
from langchain.tools import tool
from langchain_community.tools import DuckDuckGoSearchRun

from app.core.clients import llm
from app.core.config import get_settings
from app.services.retriever import get_retriever
from app.services.retriever_manager import retriever_manager as rm

logger = logging.getLogger(__name__)
settings = get_settings()


@tool
def calculator(first_num: float, second_num: float, operation: str) -> dict:
    """
    Perform basic arithmetic on two numbers.
    Supported operations: add, sub, mul, div.
    Parameters: first_num (float), second_num (float), operation (str).
    Do NOT pass thread_id to this tool.
    """
    try:
        if operation == "add":
            result = first_num + second_num
        elif operation == "sub":
            result = first_num - second_num
        elif operation == "mul":
            result = first_num * second_num
        elif operation == "div":
            if second_num == 0:
                return {"error": "Division by zero is not allowed"}
            result = first_num / second_num
        else:
            return {"error": f"Unsupported operation '{operation}'"}

        return {
            "first_num": first_num,
            "second_num": second_num,
            "operation": operation,
            "result": result,
        }
    except Exception as e:
        return {"error": str(e)}


@tool
def rag_tool(query: str, thread_id: Optional[str] = None) -> dict:
    """
    Retrieve relevant information from the PDF uploaded for this chat thread.
    Use this tool ONLY for questions about the uploaded document.
    Parameters: query (str), thread_id (str).
    You MUST pass thread_id when calling this tool.
    """
    retriever = get_retriever(thread_id=thread_id)
    if retriever is None:
        return {
            "error": "No document indexed for this chat. Upload a PDF first.",
            "query": query,
        }

    result = retriever.invoke(query)
    return {
        "query": query,
        "context": [doc.page_content for doc in result],
        "metadata": [doc.metadata for doc in result],
        "source_file": rm.get_metadata(thread_id).get("filename") if thread_id else None,
    }


@tool
def get_stock_price(symbol: str) -> dict:
    """
    Fetch the latest stock price for a given ticker symbol (e.g. 'AAPL', 'TSLA').
    Parameters: symbol (str) only.
    Do NOT pass thread_id or any other argument to this tool.
    """
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "GLOBAL_QUOTE",
        "symbol": symbol,
        "apikey": settings.alpha_vantage_api_key,
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        logger.warning("get_stock_price failed for %s: %s", symbol, e)
        return {"error": f"Failed to fetch stock price for {symbol}: {e}"}


_ddg = DuckDuckGoSearchRun(region="us-en")


@tool
def web_search(query: str) -> str:
    """
    Search the web for current information using DuckDuckGo.
    Use for news, recent events, or anything requiring up-to-date internet data.
    Parameters: query (str) only.
    Do NOT pass thread_id or any other argument to this tool.
    """
    try:
        return _ddg.run(query)
    except Exception as e:
        return f"Search failed: {e}"


tools = [web_search, get_stock_price, calculator, rag_tool]
llm_with_tools = llm.bind_tools(tools)

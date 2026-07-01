from langgraph.graph import END, START, StateGraph

from app.core.state import ChatState
from app.services.memory import checkpointer
from app.services.nodes import chat_node, tool_node


def build_graph():
    """Build and compile the LangGraph workflow."""

    workflow = StateGraph(ChatState)

    workflow.add_node("chat", chat_node)
    workflow.add_node("tools", tool_node)

    workflow.add_edge(START, "chat")

    workflow.add_conditional_edges(
        "chat",
        lambda state: "tools" if state["messages"][-1].tool_calls else END,
    )

    workflow.add_edge("tools", "chat")

    return workflow.compile(checkpointer=checkpointer)

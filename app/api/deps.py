from fastapi import Request


def get_chatbot(request: Request):
    """Return the compiled LangGraph app stored on application startup."""
    return request.app.state.chatbot

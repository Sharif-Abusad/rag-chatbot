"""
Construction of shared LLM / embedding clients.

Kept separate from `core.config` so importing settings doesn't also
spin up model clients (useful for tests / scripts).
"""

from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import get_settings

settings = get_settings()

llm = ChatGroq(
    model=settings.groq_model,
    temperature=0,
    api_key=settings.groq_api_key,
)

embeddings = HuggingFaceEmbeddings(
    model_name=settings.embedding_model,
)

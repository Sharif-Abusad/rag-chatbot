"""
Construction of shared LLM / embedding clients.

Kept separate from `core.config` so importing settings doesn't also
spin up model clients (useful for tests / scripts).
"""

from langchain_groq import ChatGroq

from app.core.config import get_settings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
settings = get_settings()

llm = ChatGroq(
    model=settings.groq_model,
    temperature=0,
    api_key=settings.groq_api_key,
)

# Embeddings model
embeddings = GoogleGenerativeAIEmbeddings(
    model=settings.embedding_model,
    api_key=settings.google_api_key,
)
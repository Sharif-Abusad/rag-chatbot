"""
Application entry point.

"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import chat, documents, health, threads
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.database.database import initialize_database
from app.services.graph import build_graph

configure_logging()
logger = logging.getLogger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database...")
    initialize_database()

    logger.info("Compiling LangGraph workflow...")
    app.state.chatbot = build_graph()

    logger.info("%s startup complete.", settings.app_name)
    yield
    logger.info("%s shutting down.", settings.app_name)


app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Welcome to my API"}

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(documents.router)
app.include_router(threads.router)

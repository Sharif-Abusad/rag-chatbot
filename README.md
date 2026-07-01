# DocMind API

A production-structured FastAPI service wrapping a LangGraph RAG chatbot
(Groq LLM + tool calling + FAISS-backed PDF retrieval).

## Project structure

```
docmind/
├── app/
│   ├── main.py                 # FastAPI app, CORS, startup/shutdown
│   ├── api/
│   │   ├── deps.py             # shared FastAPI dependencies
│   │   └── routes/
│   │       ├── health.py       # GET /health
│   │       ├── chat.py         # POST /chat
│   │       ├── documents.py    # POST /documents/upload
│   │       └── threads.py      # GET /threads
│   ├── core/
│   │   ├── config.py           # pydantic-settings (env vars)
│   │   ├── clients.py          # LLM + embeddings clients
│   │   ├── logging.py          # logging setup
│   │   └── state.py            # LangGraph ChatState
│   ├── database/
│   │   └── database.py         # SQLite connection management
│   ├── models/
│   │   └── schemas.py          # request/response Pydantic models
│   └── services/
│       ├── graph.py            # LangGraph workflow builder
│       ├── nodes.py            # chat_node / tool_node
│       ├── tools.py            # calculator, web_search, rag_tool, stock price
│       ├── prompts.py          # system prompt builder
│       ├── memory.py           # LangGraph SqliteSaver checkpointer
│       ├── retriever.py        # PDF ingestion -> FAISS
│       ├── retriever_manager.py# in-memory thread -> retriever registry
│       └── thread.py           # thread listing helpers
├── requirements.txt
├── .env.example
└── .gitignore
```

This separates **transport** (FastAPI routes/schemas) from **domain logic**
(LangGraph graph, nodes, tools, retrieval), which is what makes it
testable and reusable outside of an HTTP context (e.g. a CLI or worker).

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env               # then fill in real API keys
```

## Run

```bash
uvicorn app.main:app --reload
```

Docs available at `http://localhost:8000/docs`.

## Endpoints

| Method | Path                  | Description                                  |
|--------|-----------------------|-----------------------------------------------|
| GET    | `/health`              | Liveness check                               |
| POST   | `/chat`                 | Send a message, get a reply (creates/continues a thread) |
| POST   | `/documents/upload`     | Upload a PDF, index it for RAG on a thread   |
| GET    | `/threads`              | List all conversation threads + doc status   |

### Example: start a conversation

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is 12 * 7?"}'
```

### Example: upload a PDF then ask about it

```bash
curl -X POST http://localhost:8000/documents/upload \
  -F "file=@report.pdf" \
  -F "thread_id=my-thread-1"

curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Summarize the report", "thread_id": "my-thread-1"}'
```

## Notes on changes from the original prototype

- **No hardcoded secrets**: the Alpha Vantage key and Groq key are now read
  from environment variables via `app/core/config.py` (`pydantic-settings`),
  not hardcoded in source.
- **Fixed typo**: `retriver_manager` → `retriever_manager`.
- **Network calls are guarded**: `get_stock_price` now uses a timeout and
  catches request errors instead of letting them propagate as 500s.
- **Single source of truth for the compiled graph**: built once at startup
  (`lifespan`) and stored on `app.state`, not rebuilt per request.
- **In-memory `RetrieverManager` caveat**: this resets on restart and isn't
  shared across multiple worker processes. For real production scale-out,
  swap it for a persistent FAISS index per thread on disk, or a vector DB
  (e.g. pgvector, Qdrant) keyed by thread_id.
- **SQLite checkpointer caveat**: `SqliteSaver` with a single shared
  connection works for a single-process deployment. For multi-worker
  production deployments, consider Postgres (`langgraph-checkpoint-postgres`).

## Suggested next steps for production hardening

1. Add authentication (API key or JWT) to the routes.
2. Add request-level rate limiting on `/chat` and `/documents/upload`.
3. Move `RetrieverManager` and checkpointing to shared, persistent backends
   if you plan to run more than one worker/process.
4. Add structured request/response logging and basic metrics (e.g. via
   `prometheus-fastapi-instrumentator`).
5. Add tests for `app/services/*` independent of the HTTP layer.
6. Containerize with a `Dockerfile` + `docker-compose.yml` (app + volume for
   `database/`).

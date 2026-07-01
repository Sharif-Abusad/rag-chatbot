import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.clients import embeddings
from app.core.config import get_settings
from app.services.retriever_manager import retriever_manager as rm

logger = logging.getLogger(__name__)
settings = get_settings()

METADATA_FILENAME = "metadata.json"


def _index_dir(thread_id: str) -> Path:
    return settings.faiss_index_dir / str(thread_id)


def _metadata_path(thread_id: str) -> Path:
    return _index_dir(thread_id) / METADATA_FILENAME


def _save_metadata(thread_id: str, metadata: dict) -> None:
    path = _metadata_path(thread_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata))


def _load_metadata_from_disk(thread_id: str) -> Optional[dict]:
    path = _metadata_path(thread_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read metadata for thread %s: %s", thread_id, exc)
        return None


def index_exists(thread_id: str) -> bool:
    """True if a document index exists for this thread, in memory or on disk."""
    if rm.exists(thread_id):
        return True
    return (_index_dir(thread_id) / "index.faiss").exists()


def get_document_metadata(thread_id: str) -> dict:
    """
    Cheap metadata lookup (filename/page/chunk counts) without loading the
    full FAISS index into memory. Used for thread listings.
    """
    cached = rm.get_metadata(thread_id)
    if cached:
        return cached

    disk_metadata = _load_metadata_from_disk(thread_id)
    if disk_metadata:
        rm.set_metadata(thread_id, disk_metadata)
        return disk_metadata

    return {}


def get_retriever(thread_id: Optional[str]):
    """
    Fetch the retriever for a thread, loading it from disk into the
    in-process cache on first use after a restart if needed.
    """
    if not thread_id:
        return None

    if rm.exists(thread_id):
        return rm.get(thread_id=thread_id)

    index_path = _index_dir(thread_id)
    if not (index_path / "index.faiss").exists():
        return None

    logger.info("Loading FAISS index for thread %s from disk", thread_id)
    vector_store = FAISS.load_local(
        str(index_path),
        embeddings,
        allow_dangerous_deserialization=True,
    )
    retriever = vector_store.as_retriever(search_type="similarity", search_kwargs={"k": 4})

    metadata = _load_metadata_from_disk(thread_id) or {}
    rm.add(thread_id, retriever=retriever, metadata=metadata)

    return retriever


def ingest_pdf(file_bytes: bytes, thread_id: str, filename: Optional[str] = None) -> dict:
    """
    Build a FAISS retriever for the uploaded PDF, persist it to disk, and
    cache it in-process for the thread.

    Persisting to disk means a previous chat that had a document attached
    still has working RAG after a backend restart/redeploy, as long as the
    `database/` directory is on a persistent volume.
    """
    if not file_bytes:
        raise ValueError("No bytes received for ingestion.")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(file_bytes)
        temp_path = temp_file.name

    try:
        loader = PyPDFLoader(temp_path)
        docs = loader.load()

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200, separators=["\n\n", "\n", " ", ""]
        )
        chunks = splitter.split_documents(docs)

        vector_store = FAISS.from_documents(chunks, embeddings)
        retriever = vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 4},
        )

        metadata = {
            "filename": filename or os.path.basename(temp_path),
            "documents": len(docs),
            "chunks": len(chunks),
        }

        index_path = _index_dir(thread_id)
        index_path.mkdir(parents=True, exist_ok=True)
        vector_store.save_local(str(index_path))
        _save_metadata(thread_id, metadata)

        rm.add(thread_id, retriever=retriever, metadata=metadata)

        return metadata
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            pass

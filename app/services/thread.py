from app.services.memory import checkpointer
from app.services.retriever import get_document_metadata, index_exists


def retrieve_all_threads() -> list[str]:
    all_threads = set()
    for checkpoint in checkpointer.list(None):
        all_threads.add(checkpoint.config["configurable"]["thread_id"])
    return list(all_threads)


def thread_has_document(thread_id: str) -> bool:
    """Disk-aware check: true even if the index hasn't been lazy-loaded yet."""
    return index_exists(thread_id)


def thread_document_metadata(thread_id: str) -> dict:
    return get_document_metadata(thread_id)


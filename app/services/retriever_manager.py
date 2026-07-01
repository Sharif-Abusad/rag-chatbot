from __future__ import annotations

from typing import Any, Optional


class RetrieverManager:
    """
    Manages thread-specific retrievers and their metadata.

    Each chat thread can have one active retriever associated with an
    uploaded document. This is an in-process registry: it resets on
    restart. For multi-worker / multi-process deployments, swap this
    for a shared store (e.g. Redis) keyed by thread_id.
    """

    def __init__(self) -> None:
        self._retrievers: dict[str, Any] = {}
        self._metadata: dict[str, dict[str, Any]] = {}

    def add(self, thread_id: str, retriever: Any, metadata: dict[str, Any]) -> None:
        thread_id = str(thread_id)
        self._retrievers[thread_id] = retriever
        self._metadata[thread_id] = metadata

    def get(self, thread_id: str) -> Optional[Any]:
        return self._retrievers.get(str(thread_id))

    def get_metadata(self, thread_id: str) -> dict[str, Any]:
        return self._metadata.get(str(thread_id), {})
    
    def set_metadata(self, thread_id: str, metadata: dict[str, Any]) -> None:
        """Update or cache metadata for a thread without changing the retriever."""
        self._metadata[str(thread_id)] = metadata

    def exists(self, thread_id: str) -> bool:
        return str(thread_id) in self._retrievers

    def remove(self, thread_id: str) -> bool:
        thread_id = str(thread_id)
        removed = False
        if thread_id in self._retrievers:
            del self._retrievers[thread_id]
            removed = True
        if thread_id in self._metadata:
            del self._metadata[thread_id]
            removed = True
        return removed

    def clear(self) -> None:
        self._retrievers.clear()
        self._metadata.clear()

    def list_threads(self) -> list[str]:
        return list(self._retrievers.keys())

    def count(self) -> int:
        return len(self._retrievers)


retriever_manager = RetrieverManager()

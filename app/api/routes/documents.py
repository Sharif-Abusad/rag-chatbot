import logging
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.core.config import get_settings
from app.models.schemas import IngestResponse
from app.services.retriever import ingest_pdf

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])
settings = get_settings()


@router.post("/upload", response_model=IngestResponse)
async def upload_document(
    file: UploadFile = File(...),
    thread_id: str | None = Form(default=None),
):
    """
    Upload a PDF and index it for retrieval-augmented chat.

    If `thread_id` is omitted, a new thread is created for this document.
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    file_bytes = await file.read()

    max_bytes = settings.max_upload_mb * 1024 * 1024
    if len(file_bytes) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {settings.max_upload_mb}MB limit.",
        )

    resolved_thread_id = thread_id or str(uuid.uuid4())

    try:
        metadata = ingest_pdf(
            file_bytes=file_bytes,
            thread_id=resolved_thread_id,
            filename=file.filename,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("PDF ingestion failed for thread %s", resolved_thread_id)
        raise HTTPException(status_code=500, detail=f"Failed to ingest PDF: {exc}") from exc

    return IngestResponse(thread_id=resolved_thread_id, **metadata)

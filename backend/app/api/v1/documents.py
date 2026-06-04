"""Documents API endpoint — handles PDF upload, listing, and deletion."""

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.core.config import get_settings
from app.core.exceptions import DocumentNotFoundError
from app.models.schemas import (
    APIResponse,
    DocumentInfo,
    DocumentListResponse,
    DocumentUploadResponse,
)
from app.services.document_service import DocumentService
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/documents", tags=["Documents"])


def get_services() -> tuple[DocumentService, VectorStoreService]:
    """Get service instances from app state."""
    from app.main import _document_service, _vector_store_service
    return _document_service, _vector_store_service


@router.post(
    "/upload",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF document for processing",
)
async def upload_document(
    file: UploadFile = File(..., description="PDF file to upload"),
) -> DocumentUploadResponse:
    """Upload and process a PDF document.

    The file is validated, saved temporarily, parsed into chunks,
    and stored in the vector database for semantic search.
    """
    doc_service, vector_service = get_services()

    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename is required.",
        )

    content = await file.read()
    file_size = len(content)
    content_type = file.content_type or "application/octet-stream"

    doc_service.validate_file(content_type, file_size)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        record, chunks = doc_service.process_pdf(
            file_path=tmp_path,
            filename=file.filename,
            file_size=file_size,
        )

        vector_service.add_documents(
            chunks=chunks,
            document_id=record.document_id,
        )

        return DocumentUploadResponse(
            document_id=record.document_id,
            filename=record.filename,
            status=record.status,
            chunk_count=record.chunk_count,
            message=f"Successfully processed '{file.filename}' into {record.chunk_count} chunks.",
        )
    finally:
        tmp_path.unlink(missing_ok=True)


@router.get(
    "",
    response_model=DocumentListResponse,
    summary="List all uploaded documents",
)
async def list_documents(
    page: int = 1,
    page_size: int = 20,
) -> DocumentListResponse:
    """Return a paginated list of all uploaded documents."""
    doc_service, _ = get_services()
    all_docs = doc_service.list_documents()

    start = (page - 1) * page_size
    end = start + page_size
    paginated = all_docs[start:end]

    return DocumentListResponse(
        documents=[
            DocumentInfo(
                document_id=d.document_id,
                filename=d.filename,
                status=d.status,
                chunk_count=d.chunk_count,
                file_size_bytes=d.file_size_bytes,
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
            for d in paginated
        ],
        total=len(all_docs),
        page=page,
        page_size=page_size,
    )


@router.delete(
    "/{document_id}",
    response_model=APIResponse,
    summary="Delete a document and its chunks",
)
async def delete_document(document_id: str) -> APIResponse:
    """Delete a document and all its associated vector store chunks."""
    doc_service, vector_service = get_services()

    try:
        deleted_chunks = vector_service.delete_document(document_id)
        return APIResponse(
            success=True,
            message=f"Deleted document with {deleted_chunks} chunks.",
            data={"document_id": document_id, "chunks_deleted": deleted_chunks},
        )
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc.detail),
        ) from exc
"""Chat API endpoint — handles question answering with RAG."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.schemas import ChatRequest, ChatResponse
from app.services.document_service import DocumentService
from app.services.llm_service import LLMService
from app.services.vector_store import VectorStoreService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])


def get_document_service() -> DocumentService:
    """Dependency injection for document service."""
    from app.main import _document_service
    return _document_service


def get_vector_store_service() -> VectorStoreService:
    """Dependency injection for vector store service."""
    from app.main import _vector_store_service
    return _vector_store_service


def get_llm_service() -> LLMService:
    """Dependency injection for LLM service."""
    from app.main import _llm_service
    return _llm_service


@router.post(
    "",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a question about uploaded documents",
    responses={
        200: {"description": "Successful response with answer and sources"},
        400: {"description": "Invalid request body"},
        503: {"description": "LLM service not configured"},
    },
)
async def chat(
    request: ChatRequest,
    doc_service: DocumentService = Depends(get_document_service),
    vector_service: VectorStoreService = Depends(get_vector_store_service),
    llm_service: LLMService = Depends(get_llm_service),
) -> ChatResponse:
    """Process a user question against uploaded documents using RAG.

    The pipeline:
    1. Validate the question
    2. Retrieve relevant chunks from vector store
    3. Generate an AI response using the LLM
    4. Return the answer with source references
    """
    conversation_id = request.conversation_id or str(uuid.uuid4())

    logger.info(
        "Chat request received",
        extra={
            "conversation_id": conversation_id,
            "question_length": len(request.question),
        },
    )

    if vector_service.total_chunks == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No documents have been uploaded yet. Please upload a PDF first.",
        )

    search_results = vector_service.similarity_search(
        query=request.question,
        n_results=5,
        document_ids=request.document_ids,
    )

    response = llm_service.generate_response(
        question=request.question,
        search_results=search_results,
    )

    response.conversation_id = conversation_id

    logger.info(
        "Chat response generated",
        extra={
            "conversation_id": conversation_id,
            "sources_count": len(response.sources),
            "tokens_used": response.tokens_used,
        },
    )

    return response
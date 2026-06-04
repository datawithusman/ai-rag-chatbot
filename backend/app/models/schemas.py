"""Pydantic models for request/response validation."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


# ── Enums ──────────────────────────────────────────────────────────


class MessageRole(str, Enum):
    """Chat message role."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class DocumentStatus(str, Enum):
    """Document processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ── Request Models ─────────────────────────────────────────────────


class ChatRequest(BaseModel):
    """Request payload for chat endpoint."""

    question: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="The question to ask about the uploaded documents.",
    )
    document_ids: list[str] | None = Field(
        default=None,
        description="Optional list of document IDs to restrict search to.",
    )
    conversation_id: str | None = Field(
        default=None,
        description="Optional conversation ID for multi-turn chat.",
    )

    @field_validator("question")
    @classmethod
    def sanitize_question(cls, v: str) -> str:
        """Strip whitespace from the question."""
        return v.strip()


class DocumentUploadResponse(BaseModel):
    """Response after successful document upload."""

    document_id: str
    filename: str
    status: DocumentStatus
    chunk_count: int
    message: str


# ── Response Models ────────────────────────────────────────────────


class SourceReference(BaseModel):
    """A source reference used to generate the answer."""

    content: str
    page_number: int | None = None
    document_name: str
    relevance_score: float


class ChatResponse(BaseModel):
    """Response payload for chat endpoint."""

    answer: str
    sources: list[SourceReference] = Field(default_factory=list)
    conversation_id: str
    tokens_used: int = 0


class DocumentInfo(BaseModel):
    """Metadata about an uploaded document."""

    document_id: str
    filename: str
    status: DocumentStatus
    chunk_count: int
    file_size_bytes: int
    created_at: datetime
    updated_at: datetime


class DocumentListResponse(BaseModel):
    """Paginated list of documents."""

    documents: list[DocumentInfo]
    total: int
    page: int
    page_size: int


class HealthResponse(BaseModel):
    """Health check response."""

    status: str = "healthy"
    version: str
    environment: str
    uptime_seconds: float
    documents_count: int


class APIResponse(BaseModel):
    """Generic API response wrapper."""

    success: bool
    message: str
    data: Any | None = None


# ── Internal Models ────────────────────────────────────────────────


class DocumentRecord(BaseModel):
    """Internal document record stored in the database."""

    document_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    status: DocumentStatus = DocumentStatus.PENDING
    chunk_count: int = 0
    file_size_bytes: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ChatMessage(BaseModel):
    """A single chat message in a conversation."""

    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
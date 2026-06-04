"""FastAPI application entry point with middleware and lifecycle management."""

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import chat, documents
from app.core.config import get_settings
from app.models.schemas import HealthResponse
from app.services.document_service import DocumentService
from app.services.llm_service import LLMService
from app.services.vector_store import VectorStoreService

# ── Logging Configuration ──────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# ── Service Instances (module-level singletons) ────────────────────
_document_service = DocumentService()
_vector_store_service = VectorStoreService()
_llm_service = LLMService()

# ── App Start Time ─────────────────────────────────────────────────
_start_time: float = 0.0
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle — startup and shutdown."""
    global _start_time
    _start_time = time.time()
    logger.info(
        "Starting %s v%s [%s]",
        settings.app_name,
        settings.app_version,
        settings.environment,
    )
    yield
    logger.info("Shutting down %s", settings.app_name)


# ── FastAPI App ─────────────────────────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Production-ready AI RAG Chatbot API. "
        "Upload PDFs and ask questions powered by LLMs."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ── Middleware ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    """Log request details and response time."""
    start = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start) * 1000

    logger.info(
        "%s %s -> %d (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


# ── Exception Handlers ─────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch unhandled exceptions and return structured error."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error. Please try again later."},
    )


# ── Routes ─────────────────────────────────────────────────────────
app.include_router(chat.router, prefix=settings.api_v1_prefix)
app.include_router(documents.router, prefix=settings.api_v1_prefix)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """Application health check endpoint."""
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
        environment=settings.environment,
        uptime_seconds=round(time.time() - _start_time, 2),
        documents_count=_document_service.document_count,
    )


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint redirect to docs."""
    return {
        "message": f"Welcome to {settings.app_name} API",
        "docs": "/docs",
        "health": "/health",
    }
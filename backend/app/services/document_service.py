"""Document processing service — handles PDF ingestion and chunking."""

import logging
import uuid
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document as LCDocument

from app.core.config import get_settings
from app.core.exceptions import (
    DocumentProcessingError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from app.models.schemas import DocumentRecord, DocumentStatus

logger = logging.getLogger(__name__)
settings = get_settings()


class DocumentService:
    """Service for processing and chunking uploaded documents."""

    def __init__(self) -> None:
        self._text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )
        self._documents: dict[str, DocumentRecord] = {}

    def validate_file(self, content_type: str, file_size: int) -> None:
        """Validate uploaded file type and size.

        Args:
            content_type: MIME type of the uploaded file.
            file_size: Size of the file in bytes.

        Raises:
            UnsupportedFileTypeError: If the file type is not allowed.
            FileTooLargeError: If the file exceeds the maximum size.
        """
        if content_type not in settings.allowed_file_types:
            raise UnsupportedFileTypeError(content_type)

        max_size_bytes = settings.max_file_size_mb * 1024 * 1024
        if file_size > max_size_bytes:
            raise FileTooLargeError(settings.max_file_size_mb)

    def process_pdf(
        self,
        file_path: Path,
        filename: str,
        file_size: int,
    ) -> tuple[DocumentRecord, list[LCDocument]]:
        """Process a PDF file into chunks for vector storage.

        Args:
            file_path: Path to the saved PDF file.
            filename: Original filename.
            file_size: Size of the file in bytes.

        Returns:
            Tuple of document record and list of chunked documents.

        Raises:
            DocumentProcessingError: If PDF processing fails.
        """
        document_id = str(uuid.uuid4())
        record = DocumentRecord(
            document_id=document_id,
            filename=filename,
            file_size_bytes=file_size,
            status=DocumentStatus.PROCESSING,
        )
        self._documents[document_id] = record

        try:
            loader = PyPDFLoader(str(file_path))
            pages = loader.load()

            if not pages:
                raise DocumentProcessingError(
                    f"No content extracted from '{filename}'."
                )

            chunks = self._text_splitter.split_documents(pages)

            # Enrich each chunk with document metadata
            for i, chunk in enumerate(chunks):
                chunk.metadata.update(
                    {
                        "document_id": document_id,
                        "document_name": filename,
                        "chunk_index": i,
                        "total_chunks": len(chunks),
                    }
                )

            record.status = DocumentStatus.COMPLETED
            record.chunk_count = len(chunks)
            record.updated_at = __import__("datetime").datetime.utcnow()

            logger.info(
                "Document processed successfully",
                extra={
                    "document_id": document_id,
                    "filename": filename,
                    "chunks": len(chunks),
                },
            )

            return record, chunks

        except DocumentProcessingError:
            record.status = DocumentStatus.FAILED
            raise
        except Exception as exc:
            record.status = DocumentStatus.FAILED
            logger.exception("Failed to process document: %s", filename)
            raise DocumentProcessingError(
                f"Error processing '{filename}': {exc}"
            ) from exc

    def get_document(self, document_id: str) -> DocumentRecord:
        """Retrieve a document record by ID.

        Args:
            document_id: The unique document identifier.

        Returns:
            The document record.

        Raises:
            KeyError: If document is not found.
        """
        if document_id not in self._documents:
            raise KeyError(f"Document '{document_id}' not found.")
        return self._documents[document_id]

    def list_documents(self) -> list[DocumentRecord]:
        """Return all document records."""
        return list(self._documents.values())

    @property
    def document_count(self) -> int:
        """Return the total number of processed documents."""
        return len(self._documents)
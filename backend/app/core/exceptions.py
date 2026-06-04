"""Custom exception hierarchy for the application."""

from fastapi import HTTPException, status


class AppException(HTTPException):
    """Base application exception."""

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(status_code=status_code, detail=detail)


class DocumentNotFoundError(AppException):
    """Raised when a requested document is not found."""

    def __init__(self, document_id: str) -> None:
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document '{document_id}' not found.",
        )


class DocumentProcessingError(AppException):
    """Raised when document processing fails."""

    def __init__(self, detail: str = "Failed to process document.") -> None:
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=detail,
        )


class FileTooLargeError(AppException):
    """Raised when uploaded file exceeds size limit."""

    def __init__(self, max_size_mb: int) -> None:
        super().__init__(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds maximum size of {max_size_mb}MB.",
        )


class UnsupportedFileTypeError(AppException):
    """Raised when uploaded file type is not supported."""

    def __init__(self, content_type: str) -> None:
        super().__init__(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"File type '{content_type}' is not supported.",
        )


class LLMConfigurationError(AppException):
    """Raised when LLM is not properly configured."""

    def __init__(self, provider: str) -> None:
        super().__init__(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM provider '{provider}' is not configured. Check API keys.",
        )
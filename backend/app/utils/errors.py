"""Custom exception classes."""

from fastapi import HTTPException, status


class ReportGeneratorError(Exception):
    """Base exception for report generator errors."""

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class DocumentParsingError(ReportGeneratorError):
    """Error during document parsing."""

    pass


class LLMGenerationError(ReportGeneratorError):
    """Error during LLM content generation."""

    pass


class StorageError(ReportGeneratorError):
    """Error during file storage operations."""

    pass


class RenderingError(ReportGeneratorError):
    """Error during output rendering."""

    pass


def http_error(
    status_code: int,
    message: str,
    headers: dict | None = None,
) -> HTTPException:
    """Create an HTTPException with the given parameters."""
    return HTTPException(
        status_code=status_code,
        detail=message,
        headers=headers,
    )


def not_found(resource: str = "Resource") -> HTTPException:
    """Create a 404 Not Found exception."""
    return http_error(status.HTTP_404_NOT_FOUND, f"{resource} not found")


def bad_request(message: str) -> HTTPException:
    """Create a 400 Bad Request exception."""
    return http_error(status.HTTP_400_BAD_REQUEST, message)


def unauthorized(message: str = "Not authenticated") -> HTTPException:
    """Create a 401 Unauthorized exception."""
    return http_error(
        status.HTTP_401_UNAUTHORIZED,
        message,
        headers={"WWW-Authenticate": "Bearer"},
    )


def forbidden(message: str = "Not authorized") -> HTTPException:
    """Create a 403 Forbidden exception."""
    return http_error(status.HTTP_403_FORBIDDEN, message)


def internal_error(message: str = "Internal server error") -> HTTPException:
    """Create a 500 Internal Server Error exception."""
    return http_error(status.HTTP_500_INTERNAL_SERVER_ERROR, message)

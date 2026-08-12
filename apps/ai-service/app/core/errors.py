"""Domain errors and RFC 7807-style problem detail responses."""

from __future__ import annotations

from typing import Any
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    """Base application error with a stable client-facing code."""

    def __init__(
        self,
        *,
        code: str,
        message: str,
        status_code: int = 400,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class AuthorizationError(AppError):
    def __init__(self, message: str = "You are not allowed to access this resource.") -> None:
        super().__init__(code="FORBIDDEN", message=message, status_code=403)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found.") -> None:
        super().__init__(code="NOT_FOUND", message=message, status_code=404)


class ValidationAppError(AppError):
    def __init__(self, message: str, *, code: str = "VALIDATION_ERROR") -> None:
        super().__init__(code=code, message=message, status_code=400)


class ProviderUnavailableError(AppError):
    def __init__(
        self,
        message: str = "The AI provider is temporarily unavailable. Please try again.",
    ) -> None:
        super().__init__(code="PROVIDER_UNAVAILABLE", message=message, status_code=503)


class ProviderTimeoutError(AppError):
    def __init__(
        self,
        message: str = "The AI provider timed out. Please try again.",
    ) -> None:
        super().__init__(code="PROVIDER_TIMEOUT", message=message, status_code=504)


class ProviderConfigError(AppError):
    def __init__(
        self,
        message: str = "The AI service is not configured correctly.",
    ) -> None:
        super().__init__(code="PROVIDER_CONFIG_ERROR", message=message, status_code=503)


class UnsupportedDocumentError(AppError):
    def __init__(self, message: str = "Only PDF documents are supported.") -> None:
        super().__init__(code="UNSUPPORTED_DOCUMENT", message=message, status_code=415)


class DocumentTooLargeError(AppError):
    def __init__(self, message: str = "The uploaded file exceeds the size limit.") -> None:
        super().__init__(code="DOCUMENT_TOO_LARGE", message=message, status_code=413)


class DocumentProcessingError(AppError):
    def __init__(
        self,
        message: str = "Document processing failed. You can retry indexing.",
    ) -> None:
        super().__init__(code="DOCUMENT_PROCESSING_ERROR", message=message, status_code=422)


class DocumentNotReadyError(AppError):
    def __init__(
        self,
        message: str = (
            "This document is still being indexed. Try again when processing is complete."
        ),
    ) -> None:
        super().__init__(code="DOCUMENT_NOT_READY", message=message, status_code=409)


class InsufficientEvidenceError(AppError):
    def __init__(
        self,
        message: str = (
            "The uploaded documents do not contain enough information to answer that question."
        ),
    ) -> None:
        super().__init__(code="INSUFFICIENT_EVIDENCE", message=message, status_code=422)


class ProjectDocumentLimitError(AppError):
    def __init__(self, message: str = "This project has reached its document limit.") -> None:
        super().__init__(code="DOCUMENT_LIMIT", message=message, status_code=409)


def _request_id(request: Request) -> str:
    existing = request.headers.get("X-Request-Id")
    return existing or str(uuid4())


def problem_detail(
    *,
    code: str,
    message: str,
    request_id: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
        }
    }
    if details:
        body["error"]["details"] = details
    return body


def _json_safe(value: Any) -> Any:
    """Recursively convert values into JSON-serializable structures."""
    if isinstance(value, BaseException):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _json_safe_errors(errors: list[Any]) -> list[dict[str, Any]]:
    """Convert Pydantic error dicts into JSON-serializable structures."""
    safe: list[dict[str, Any]] = []
    for item in errors:
        converted = _json_safe(item)
        if isinstance(converted, dict):
            safe.append(converted)
        else:
            safe.append({"message": str(converted)})
    return safe


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=problem_detail(
                code=exc.code,
                message=exc.message,
                request_id=_request_id(request),
                details=exc.details or None,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=problem_detail(
                code="VALIDATION_ERROR",
                message="Request validation failed.",
                request_id=_request_id(request),
                details={"issues": _json_safe_errors(exc.errors())},
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        detail = exc.detail
        message = detail if isinstance(detail, str) else "Request failed."
        code = "HTTP_ERROR"
        if exc.status_code == 401:
            code = "UNAUTHORIZED"
        elif exc.status_code == 403:
            code = "FORBIDDEN"
        elif exc.status_code == 404:
            code = "NOT_FOUND"
        return JSONResponse(
            status_code=exc.status_code,
            content=problem_detail(
                code=code,
                message=message,
                request_id=_request_id(request),
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        # Never expose stack traces or internal exception text to clients.
        _ = exc
        return JSONResponse(
            status_code=500,
            content=problem_detail(
                code="INTERNAL_ERROR",
                message="An unexpected error occurred. Please try again.",
                request_id=_request_id(request),
            ),
        )

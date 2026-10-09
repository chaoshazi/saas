"""Application-level exceptions and helpers."""
from __future__ import annotations


class AppError(Exception):
    def __init__(self, status_code: int, code: str, message: str, detail: dict | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.detail = detail or {}


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(404, "not_found", message)


class PermissionDeniedError(AppError):
    def __init__(self, message: str = "Permission denied"):
        super().__init__(403, "permission_denied", message)


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(401, "unauthorized", message)


class ConflictError(AppError):
    def __init__(self, message: str = "Resource conflict"):
        super().__init__(409, "conflict", message)


class ValidationError(AppError):
    def __init__(self, message: str = "Validation failed"):
        super().__init__(422, "validation_error", message)

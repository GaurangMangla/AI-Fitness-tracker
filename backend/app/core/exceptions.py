"""Domain exceptions.

Services raise these instead of generic `ValueError`/`HTTPException` so error
handling has exactly one place it happens (the handler in `main.py`), and so
service code stays decoupled from HTTP status codes — useful the moment a
service method is ever called from somewhere that isn't a request handler
(a script, a test, a future background job for re-running the ML model).
"""


class AppException(Exception):
    """Base class for expected, handled errors."""

    status_code: int = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppException):
    status_code = 404


class ValidationError(AppException):
    status_code = 422


class ConflictError(AppException):
    status_code = 409


class UnauthorizedError(AppException):
    status_code = 401

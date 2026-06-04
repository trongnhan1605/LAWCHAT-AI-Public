from fastapi import status


if hasattr(status, "HTTP_422_UNPROCESSABLE_CONTENT"):
    HTTP_422_STATUS = status.HTTP_422_UNPROCESSABLE_CONTENT
else:
    HTTP_422_STATUS = 422


class AppException(Exception):
    def __init__(self, message: str, status_code: int = status.HTTP_400_BAD_REQUEST, data=None) -> None:
        self.message = message
        self.status_code = status_code
        self.data = data
        super().__init__(message)


class AuthenticationException(AppException):
    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, status.HTTP_401_UNAUTHORIZED)


class AuthorizationException(AppException):
    def __init__(self, message: str = "Permission denied") -> None:
        super().__init__(message, status.HTTP_403_FORBIDDEN)


class NotFoundException(AppException):
    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, status.HTTP_404_NOT_FOUND)


class ConflictException(AppException):
    def __init__(self, message: str = "Resource already exists", data=None) -> None:
        super().__init__(message, status.HTTP_409_CONFLICT, data)


class ValidationException(AppException):
    def __init__(self, message: str = "Validation failed") -> None:
        super().__init__(message, HTTP_422_STATUS)

from enum import StrEnum
from typing import Any, Generic, TypeVar

from fastapi import HTTPException, status
from pydantic import BaseModel


class ErrorCode(StrEnum):
    common_error = "common.error"
    common_validation_error = "common.validation_error"
    common_internal_error = "common.internal_error"
    common_not_found = "common.not_found"

    sqlalchemy_getting_bloggers_error = "sqlalchemy.getting_bloggers_error"
    ml_service_getting_generated_text = "ml_service.getting_generated_text"


class APIException(HTTPException):
    def __init__(
        self,
        error_code: ErrorCode,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail: Any = None,
        headers: dict[str, str] | None = None,
    ):
        super().__init__(status_code=status_code, headers=headers)
        self.error_code = error_code
        self.message = message
        self.detail = detail


E = TypeVar("E", bound=ErrorCode)
D = TypeVar("D")


class ErrorResponse(BaseModel, Generic[E, D]):
    """Generic error response"""

    error_code: E
    message: str
    details: D

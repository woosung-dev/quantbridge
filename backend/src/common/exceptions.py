from fastapi import HTTPException, status


class AppException(Exception):
    """베이스 도메인 예외. 하위 클래스에서 status_code/detail 지정."""

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    detail: str = "Internal server error"

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class NotFoundError(AppException):
    status_code = status.HTTP_404_NOT_FOUND
    detail = "Resource not found"


class PermissionDeniedError(AppException):
    status_code = status.HTTP_403_FORBIDDEN
    detail = "Permission denied"


class ValidationError(AppException):
    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    detail = "Validation failed"


class UnsupportedPineScriptError(AppException):
    """ADR-003 결정 2: Pine 스크립트에 미지원 함수가 있으면 부분 실행하지 않고 전체 Unsupported."""

    status_code = status.HTTP_422_UNPROCESSABLE_CONTENT
    detail = "Pine script contains unsupported features"


def to_http_exception(exc: AppException) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)

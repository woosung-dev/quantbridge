"""코드 언어·생성 근거와 격리 실행기의 공통 계약."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.strategy.python_runtime.protocol import PROTOCOL_VERSION, PythonRuntimeError


class CodeLanguage(StrEnum):
    pine = "pine"
    python = "python"
    typescript = "typescript"


class GeneratedCodeArtifact(BaseModel):
    """실행할 원문과 생성 모델을 함께 보존한다. 실행 결과를 추측하지 않는다."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    language: CodeLanguage
    source_code: str = Field(min_length=1, max_length=131_072)
    model: str = Field(min_length=1)
    provenance: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source_code", "model")
    @classmethod
    def reject_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("소스와 생성 모델은 공백일 수 없습니다")
        return value


class CodeRuntimeError(PythonRuntimeError):
    """코드·프로토콜 오류는 부분 실행 성공으로 바꾸지 않는다."""


class CodeTransport(Protocol):
    """컨트롤러는 JSONL 요청·응답만 알고 소스를 직접 실행하지 않는다."""

    def exchange(self, message: dict[str, Any]) -> dict[str, Any]: ...

    def close(self) -> None: ...


def validate_code_intent(value: object) -> dict[str, str]:
    """수량·손익·청산 가격은 신뢰된 공통 리스크 원장이 독점한다."""
    if not isinstance(value, dict) or set(value) != {"action"}:
        raise CodeRuntimeError("전략 출력은 action 하나만 허용합니다")
    action = value["action"]
    if action not in ("hold", "long", "short", "close"):
        raise CodeRuntimeError("전략 action은 hold/long/short/close여야 합니다")
    return {"action": str(action)}


__all__ = [
    "PROTOCOL_VERSION",
    "CodeLanguage",
    "CodeRuntimeError",
    "CodeTransport",
    "GeneratedCodeArtifact",
    "validate_code_intent",
]

"""공통 gVisor 외곽에서 Python·TypeScript 코드를 실행한다."""

from __future__ import annotations

import math
from typing import Any

from src.strategy.code_runtime.models import (
    PROTOCOL_VERSION,
    CodeLanguage,
    CodeRuntimeError,
    validate_code_intent,
)
from src.strategy.python_runtime.protocol import validate_source_and_params
from src.strategy.python_runtime.sandbox import DEFAULT_IMAGE, DockerPythonTransport

TYPESCRIPT_IMAGE = "quantbridge-typescript-runner:local"


class DockerCodeTransport(DockerPythonTransport):
    """기존 자원·출력·기한 제한을 재사용하고 새 action-only 계약을 검사한다."""

    def __init__(self, language: CodeLanguage, timeout: float = 900) -> None:
        if language not in (CodeLanguage.python, CodeLanguage.typescript):
            raise CodeRuntimeError("격리 코드 실행 언어는 python/typescript여야 합니다")
        if not math.isfinite(timeout) or timeout <= 0:
            raise CodeRuntimeError("실행 시간은 유한한 양수여야 합니다")
        self.language = language
        self._ready = False
        super().__init__(
            image=DEFAULT_IMAGE if language == CodeLanguage.python else TYPESCRIPT_IMAGE,
            timeout=timeout,
        )

    def exchange(self, message: dict[str, Any]) -> dict[str, Any]:
        try:
            if not self._ready:
                if message.get("type") != "init" or message.get("protocol") != PROTOCOL_VERSION:
                    raise CodeRuntimeError("첫 메시지는 같은 버전의 init이어야 합니다")
                if message.get("language", self.language) != self.language:
                    raise CodeRuntimeError("요청 언어와 격리 이미지가 다릅니다")
                source, params = message.get("source"), message.get("params")
                if not isinstance(source, str) or not isinstance(params, dict):
                    raise CodeRuntimeError("init은 source 문자열과 params 객체가 필요합니다")
                validate_source_and_params(source, params)
                reply = super().exchange(message)
                if reply != {"ready": PROTOCOL_VERSION}:
                    raise CodeRuntimeError("격리 실행기의 초기 응답이 올바르지 않습니다")
                self._ready = True
                return reply
            if message.get("type") != "bar":
                raise CodeRuntimeError("초기화 후에는 bar 메시지만 허용합니다")
            reply = super().exchange(message)
            if set(reply) != {"intent"}:
                raise CodeRuntimeError("격리 실행기의 응답은 intent 하나여야 합니다")
            return {"intent": validate_code_intent(reply["intent"])}
        except Exception:
            self.close()
            raise


def create_transport(language: CodeLanguage | str, timeout: float = 900) -> DockerCodeTransport:
    """Pine이나 미지 언어를 호스트 코드 실행으로 우회하지 않는다."""
    try:
        selected = CodeLanguage(language)
    except ValueError as exc:
        raise CodeRuntimeError("지원하지 않는 코드 실행 언어입니다") from exc
    return DockerCodeTransport(selected, timeout=timeout)

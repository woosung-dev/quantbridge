"""언어별 격리 실행기의 생성·초기화·의도 검증·회수를 한 수명으로 묶는다."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from types import TracebackType
from typing import Any, Literal, Self

import pandas as pd

from src.strategy.code_runtime.models import (
    PROTOCOL_VERSION,
    CodeLanguage,
    CodeRuntimeError,
    CodeTransport,
    validate_code_intent,
)
from src.strategy.python_runtime.protocol import validate_source_and_params
from src.strategy.python_runtime.serialization import frame_from_payload

CodeBars = pd.DataFrame | Sequence[dict[str, Any]]


class CodeSessionProtocolError(CodeRuntimeError):
    """호출자가 기존 오류 유형을 유지하도록 init과 응답 외형 오류만 구분한다."""

    def __init__(self, phase: Literal["init", "bar"]) -> None:
        self.phase = phase
        super().__init__(
            "코드 실행기 프로토콜 버전이 다릅니다"
            if phase == "init"
            else "코드 실행기 응답에는 intent만 있어야 합니다"
        )


def create_code_transport(
    language: CodeLanguage | str, ohlcv: CodeBars, *, timeout: float = 900
) -> CodeTransport:
    """Pine의 전체 봉 선적재와 Python·TypeScript 이미지 선택을 함께 소유한다."""
    selected = CodeLanguage(language)
    if selected == CodeLanguage.pine:
        from src.strategy.code_runtime.pine import PineSignalTransport

        frame = ohlcv if isinstance(ohlcv, pd.DataFrame) else frame_from_payload(list(ohlcv))
        return PineSignalTransport(frame, timeout=timeout)
    from src.strategy.code_runtime.sandbox import create_transport

    return create_transport(selected, timeout=timeout)


class CodeExecutionSession:
    """생성자는 자원을 만들지 않는다. context 안에서는 action만 반환한다."""

    def __init__(
        self,
        source: str,
        language: CodeLanguage | str,
        params: dict[str, Any],
        ohlcv: CodeBars,
        *,
        timeout: float = 900,
        transport_factory: Callable[[], CodeTransport] | None = None,
    ) -> None:
        self._source = source
        self._language = language
        self._params = dict(params)
        self._ohlcv = ohlcv
        self._timeout = timeout
        self._factory = transport_factory
        self._transport: CodeTransport | None = None

    def __enter__(self) -> Self:
        validate_source_and_params(self._source, self._params)
        try:
            self._transport = (
                self._factory()
                if self._factory is not None
                else create_code_transport(self._language, self._ohlcv, timeout=self._timeout)
            )
            ready = self._transport.exchange(
                {
                    "type": "init",
                    "protocol": PROTOCOL_VERSION,
                    "source": self._source,
                    "params": self._params,
                }
            )
            if ready != {"ready": PROTOCOL_VERSION}:
                raise CodeSessionProtocolError("init")
        except BaseException as error:
            self._close(error)
            raise
        return self

    def action(self, bar: dict[str, Any], position: dict[str, Any]) -> str:
        if self._transport is None:
            raise CodeRuntimeError("코드 실행 session이 열리지 않았습니다")
        reply = self._transport.exchange({"type": "bar", "bar": bar, "position": position})
        if set(reply) != {"intent"}:
            raise CodeSessionProtocolError("bar")
        return validate_code_intent(reply["intent"])["action"]

    def _close(self, error: BaseException | None) -> None:
        transport, self._transport = self._transport, None
        if transport is not None:
            try:
                transport.close()
            except BaseException as cleanup_error:
                if error is None:
                    raise
                error.add_note(f"격리 실행기 회수 실패: {type(cleanup_error).__name__}")

    def __exit__(
        self,
        error_type: type[BaseException] | None,
        error: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        self._close(error)
        return False

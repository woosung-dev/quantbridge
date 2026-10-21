"""신뢰 경계 양쪽이 교환하는 최소 JSON 프로토콜."""

from __future__ import annotations

import json
from collections.abc import Mapping
from decimal import Decimal, InvalidOperation
from typing import Any, Literal, Protocol

PROTOCOL_VERSION = 1
MAX_SOURCE_BYTES = 131_072
MAX_PARAMS_BYTES = 32_768
MAX_FRAME_BYTES = 65_536
MAX_OUTPUT_BYTES = 16_777_216
MAX_BARS = 50_000


class PythonRuntimeError(ValueError):
    """전략·프로토콜 오류. 부분 결과를 성공으로 돌려주지 않는다."""


class PythonRunnerUnavailable(PythonRuntimeError):
    """격리 실행기를 사용할 수 없다. 호스트 실행으로 대체하지 않는다."""


class PythonRunnerTimeout(PythonRuntimeError):
    """격리 실행기의 전체 시간 예산 초과."""


class PythonTransport(Protocol):
    """컨트롤러에는 요청/응답만 노출한다. 구현은 사용자 코드를 격리한다."""

    def exchange(self, message: dict[str, Any]) -> dict[str, Any]: ...

    def close(self) -> None: ...


def validate_source_and_params(source: str, params: Mapping[str, Any]) -> None:
    if not source.strip() or len(source.encode()) > MAX_SOURCE_BYTES:
        raise PythonRuntimeError("Python 소스는 1~131072 bytes 여야 합니다")
    try:
        encoded = json.dumps(params, allow_nan=False).encode()
    except (TypeError, ValueError) as exc:
        raise PythonRuntimeError("파라미터는 유한 JSON 값이어야 합니다") from exc
    if len(encoded) > MAX_PARAMS_BYTES:
        raise PythonRuntimeError("파라미터 크기가 32768 bytes 를 초과했습니다")


def validate_intent(value: object) -> dict[str, str]:
    """손익·수량·다른 임의 필드를 전략이 권한 밖에서 지정하지 못하게 한다."""
    if not isinstance(value, dict) or set(value) - {"action", "stop_loss", "take_profit"}:
        raise PythonRuntimeError("전략 출력은 action/stop_loss/take_profit 만 허용합니다")
    action = value.get("action")
    if action not in ("hold", "long", "short", "close"):
        raise PythonRuntimeError("전략 action 이 올바르지 않습니다")
    result: dict[str, str] = {"action": action}
    for key in ("stop_loss", "take_profit"):
        if key not in value or value[key] is None:
            continue
        raw = value[key]
        if not isinstance(raw, str):
            raise PythonRuntimeError(f"{key} 는 절대 가격 문자열이어야 합니다")
        try:
            price = Decimal(raw)
        except InvalidOperation as exc:
            raise PythonRuntimeError(f"{key} 가격이 올바르지 않습니다") from exc
        if not price.is_finite() or price <= 0 or price > Decimal("1e18"):
            raise PythonRuntimeError(f"{key} 가격은 유한 양수여야 합니다")
        result[key] = str(price)
    return result


Action = Literal["hold", "long", "short", "close"]

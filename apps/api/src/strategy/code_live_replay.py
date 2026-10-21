"""관찰된 봉별 포지션으로만 상태를 복원한다. 전략 코드는 격리 transport가 실행한다."""

from collections.abc import Callable, Sequence
from typing import Any

from src.strategy.code_contract import CodeSnapshot
from src.strategy.code_runtime.models import (
    PROTOCOL_VERSION,
    CodeRuntimeError,
    CodeTransport,
    validate_code_intent,
)
from src.strategy.python_runtime.serialization import digest, frame_from_payload
from src.trading.code_checkpoints import LiveCodeBar


def input_hash(
    execution_hash: str,
    bar: dict[str, Any],
    position: dict[str, Any],
    *,
    is_warmup: bool,
    delivery_args: dict[str, Any] | None = None,
) -> str:
    return digest(
        {
            "execution_hash": execution_hash,
            "bar": bar,
            "position": position,
            "is_warmup": is_warmup,
            "delivery_args": delivery_args or {},
        }
    )


def replay_code_intents(
    code: CodeSnapshot,
    records: Sequence[LiveCodeBar],
    *,
    transport_factory: Callable[[], CodeTransport] | None = None,
) -> list[str]:
    """저장된 입력 전체를 재실행한다. 기존 intent가 달라지면 차단한다."""
    if not records or len(records) > 50000:
        raise CodeRuntimeError("코드 재실행 입력은 1~50000봉이어야 합니다")
    for index, row in enumerate(records):
        if row.sequence != index or row.execution_hash != code.execution_hash:
            raise CodeRuntimeError("코드 버전·입력 순서가 변경되었습니다")
        if row.input_hash != input_hash(
            code.execution_hash,
            row.bar,
            row.position,
            is_warmup=row.is_warmup,
            delivery_args=row.delivery_args,
        ):
            raise CodeRuntimeError("저장된 코드 실행 입력 해시가 다릅니다")
    if transport_factory is not None:
        transport = transport_factory()
    elif code.language.value == "pine":
        from src.strategy.code_runtime.pine import PineSignalTransport

        transport = PineSignalTransport(
            frame_from_payload([row.bar for row in records]), timeout=30
        )
    else:
        from src.strategy.code_runtime.sandbox import create_transport

        transport = create_transport(code.language, timeout=30)
    try:
        if transport.exchange(
            {
                "type": "init",
                "protocol": PROTOCOL_VERSION,
                "source": code.source_code,
                "params": code.params,
            }
        ) != {"ready": PROTOCOL_VERSION}:
            raise CodeRuntimeError("코드 실행기 프로토콜이 다릅니다")
        actions = []
        for row in records:
            reply = transport.exchange({"type": "bar", "bar": row.bar, "position": row.position})
            if set(reply) != {"intent"}:
                raise CodeRuntimeError("코드 실행기 응답 필드가 다릅니다")
            action = validate_code_intent(reply["intent"])["action"]
            if row.intent and row.intent != action:
                raise CodeRuntimeError("동일 입력 재실행 의도가 변경되었습니다")
            actions.append(action)
        return actions
    finally:
        transport.close()

"""관찰된 봉별 포지션으로만 상태를 복원한다. 전략 코드는 격리 transport가 실행한다."""

from collections.abc import Callable, Sequence
from typing import Any

from src.strategy.code_contract import CodeSnapshot
from src.strategy.code_runtime.models import (
    CodeRuntimeError,
    CodeTransport,
)
from src.strategy.code_runtime.session import CodeExecutionSession, CodeSessionProtocolError
from src.strategy.python_runtime.serialization import digest
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
    try:
        with CodeExecutionSession(
            code.source_code,
            code.language,
            code.params,
            [row.bar for row in records],
            timeout=30,
            transport_factory=transport_factory,
        ) as session:
            actions = []
            for row in records:
                action = session.action(row.bar, row.position)
                if row.intent and row.intent != action:
                    raise CodeRuntimeError("동일 입력 재실행 의도가 변경되었습니다")
                actions.append(action)
            return actions
    except CodeSessionProtocolError as error:
        message = (
            "코드 실행기 프로토콜이 다릅니다"
            if error.phase == "init"
            else "코드 실행기 응답 필드가 다릅니다"
        )
        raise CodeRuntimeError(message) from error

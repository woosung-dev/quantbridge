"""확정 입력 재생 → 의도 체크포인트 → idempotent 리스크 coordinator. 거래 권한은 없다."""

import asyncio
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import pairwise
from typing import Any, Protocol, cast
from uuid import UUID

from src.strategy.code_contract import CodeSnapshot
from src.strategy.code_live_replay import input_hash, replay_code_intents
from src.strategy.code_runtime.models import CodeRuntimeError, CodeTransport
from src.strategy.python_runtime.protocol import Action
from src.strategy.python_runtime.serialization import json_value
from src.trading.code_checkpoints import LiveCodeBar
from src.trading.repositories.code_checkpoint_repository import CodeCheckpointRepository

FLAT = {"direction": "flat", "size": "0", "average_price": "0"}


class IntentCoordinator(Protocol):
    async def on_intent(
        self,
        session_id: UUID,
        action: Action,
        *,
        intent_key: str | None = None,
        estimated_entry: Decimal | None = None,
        quantity: Decimal | None = None,
        previous_bars: Sequence[Mapping[str, Decimal]] | None = None,
        qty_step: Decimal | None = None,
        min_qty: Decimal | None = None,
    ) -> None: ...


def canonical_bar(value: Mapping[str, Any], sequence: int) -> dict[str, Any]:
    timestamp = datetime.fromisoformat(str(value["timestamp"]))
    if timestamp.tzinfo is None:
        raise CodeRuntimeError("코드 입력 봉 시각은 tz-aware여야 합니다")
    prices = {key: Decimal(str(value[key])) for key in ("open", "high", "low", "close", "volume")}
    if any(not number.is_finite() for number in prices.values()) or not (
        0
        < prices["low"]
        <= min(prices["open"], prices["close"])
        <= max(prices["open"], prices["close"])
        <= prices["high"]
        and prices["volume"] >= 0
    ):
        raise CodeRuntimeError("유효한 확정 OHLCV가 필요합니다")
    return {
        "index": sequence,
        "timestamp": timestamp.astimezone(UTC).isoformat(),
        **{key: str(number) for key, number in prices.items()},
    }


def checked_position(value: Mapping[str, Any]) -> dict[str, Any]:
    if set(value) != {"direction", "size", "average_price"}:
        raise CodeRuntimeError("관찰 포지션 필드가 다릅니다")
    direction = value["direction"]
    size, price = Decimal(str(value["size"])), Decimal(str(value["average_price"]))
    if not size.is_finite() or not price.is_finite() or direction not in ("flat", "long", "short"):
        raise CodeRuntimeError("관찰 포지션이 유효하지 않습니다")
    if (direction == "flat" and (size != 0 or price != 0)) or (
        direction != "flat" and (size <= 0 or price <= 0)
    ):
        raise CodeRuntimeError("관찰 포지션 수량·평균가가 다릅니다")
    return (
        dict(FLAT)
        if direction == "flat"
        else {"direction": direction, "size": str(size), "average_price": str(price)}
    )


class CodeEvaluationService:
    def __init__(
        self,
        repo: CodeCheckpointRepository,
        coordinator: IntentCoordinator,
        *,
        transport_factory: Callable[[], CodeTransport] | None = None,
    ) -> None:
        self.repo, self.coordinator, self.transport_factory = repo, coordinator, transport_factory

    async def evaluate(
        self,
        *,
        session_id: UUID,
        code: CodeSnapshot,
        bars: Sequence[Mapping[str, Any]],
        position: Mapping[str, Any],
        activated_at: datetime,
        now: datetime,
        interval_seconds: int,
        execution_args: dict[str, Any] | None = None,
    ) -> str:
        if now.tzinfo is None or activated_at.tzinfo is None or interval_seconds <= 0 or not bars:
            raise CodeRuntimeError("확정 봉·활성화 시각·양수 주기가 필요합니다")
        width = timedelta(seconds=interval_seconds)
        incoming = [canonical_bar(bar, index) for index, bar in enumerate(bars)]
        times = [datetime.fromisoformat(bar["timestamp"]) for bar in incoming]
        if any(right - left != width for left, right in pairwise(times)) or times[-1] + width > now:
            raise CodeRuntimeError("입력 봉 공백 또는 미완료 봉을 실행하지 않습니다")
        if any(int(time.timestamp()) % interval_seconds for time in times):
            raise CodeRuntimeError("입력 봉이 UTC 주기 경계와 다릅니다")
        await self.repo.acquire(session_id)
        records = await self.repo.history(session_id)
        if any(row.status == "blocked" for row in records):
            raise CodeRuntimeError("재시작 정합성 확인이 필요한 세션입니다")
        if records and any(row.execution_hash != code.execution_hash for row in records):
            raise CodeRuntimeError("실행 버전은 세션 중 변경할 수 없습니다")
        # 제공된 과거 봉이 저장된 입력과 달라졌으면 덮어쓰지 않는다.
        by_time = {row.bar_time: row for row in records}
        for bar, time in zip(incoming, times, strict=True):
            previous = by_time.get(time)
            if previous is not None and {
                key: value for key, value in bar.items() if key != "index"
            } != {key: value for key, value in previous.bar.items() if key != "index"}:
                raise CodeRuntimeError("기록된 확정 봉이 변경되었습니다")
        pending = [row for row in records if row.status == "prepared"]
        if pending:
            if len(pending) != 1 or pending[0] != records[-1]:
                raise CodeRuntimeError("미전달 의도 순서가 다릅니다")
            # 재시도에서는 새 포지션이나 새 수량을 과거 의도에 주입하지 않는다.
            await asyncio.to_thread(
                replay_code_intents, code, records, transport_factory=self.transport_factory
            )
            return await self._deliver(pending[0])
        if records and times[-1] <= records[-1].bar_time:
            return "no_new_bar"
        current = checked_position(position)
        new_rows: list[LiveCodeBar] = []
        if not records:
            if times[-1] + width <= activated_at:
                return "awaiting_first_close"
            if (
                times[-1].timestamp() // interval_seconds
                != activated_at.timestamp() // interval_seconds
            ):
                raise CodeRuntimeError("활성화 후 관찰하지 못한 과거 포지션을 추측하지 않습니다")
            if len(incoming) < code.warmup_bars + 1 or current != FLAT:
                raise CodeRuntimeError("최초 실행은 flat 포지션과 전체 워밍업이 필요합니다")
            incoming, times = incoming[-code.warmup_bars - 1 :], times[-code.warmup_bars - 1 :]
            for index, (bar, time) in enumerate(zip(incoming, times, strict=True)):
                bar["index"] = index
                warmup = index < code.warmup_bars
                observed = dict(FLAT) if warmup else current
                new_rows.append(
                    self._row(
                        session_id,
                        code,
                        bar,
                        time,
                        observed,
                        warmup,
                        {} if warmup else execution_args or {},
                    )
                )
        else:
            if times[-1] - records[-1].bar_time != width:
                raise CodeRuntimeError("관찰하지 못한 포지션이 있는 봉 공백입니다")
            bar = incoming[-1]
            bar["index"] = len(records)
            new_rows.append(
                self._row(session_id, code, bar, times[-1], current, False, execution_args or {})
            )
        all_rows = [*records, *new_rows]
        actions = await asyncio.to_thread(
            replay_code_intents, code, all_rows, transport_factory=self.transport_factory
        )
        for row, action in zip(new_rows, actions[len(records) :], strict=True):
            row.intent = action
            await self.repo.add(row)
        # 외부 주문 전 불변 입력·의도를 먼저 보존한다. ACK 유실은 같은 intent_key로 복구한다.
        await self.repo.commit()
        return await self._deliver(new_rows[-1])

    @staticmethod
    def _row(
        session_id: UUID,
        code: CodeSnapshot,
        bar: dict[str, Any],
        time: datetime,
        position: dict[str, Any],
        warmup: bool,
        arguments: dict[str, Any],
    ) -> LiveCodeBar:
        delivery = json_value(arguments)
        return LiveCodeBar(
            session_id=session_id,
            bar_time=time,
            sequence=bar["index"],
            execution_hash=code.execution_hash,
            input_hash=input_hash(
                code.execution_hash, bar, position, is_warmup=warmup, delivery_args=delivery
            ),
            bar=bar,
            position=position,
            delivery_args=delivery,
            intent="",
            status="warmup" if warmup else "prepared",
            is_warmup=warmup,
        )

    async def _deliver(self, row: LiveCodeBar) -> str:
        arguments: dict[str, Any] = dict(row.delivery_args)
        for key in ("estimated_entry", "quantity", "qty_step", "min_qty"):
            if key in arguments and arguments[key] is not None:
                arguments[key] = Decimal(str(arguments[key]))
        if "previous_bars" in arguments:
            arguments["previous_bars"] = [
                {key: Decimal(str(value)) for key, value in bar.items()}
                for bar in arguments["previous_bars"]
            ]
        await self.coordinator.on_intent(
            row.session_id, cast(Action, row.intent), intent_key=str(row.id), **arguments
        )
        await self.repo.delivered(row.id)
        await self.repo.record_evaluated(row.session_id, row.bar_time)
        await self.repo.commit()
        return row.intent

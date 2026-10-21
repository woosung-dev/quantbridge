"""신호 비교용 단순 선물 어댑터. 1배·고정 1수량·비용 0·다음 봉 시가다."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any

import pandas as pd

from scripts.pine_validation.models import (
    Direction,
    EventInput,
    SignalEvent,
    coerce_events,
    utc_time,
)


@dataclass(frozen=True)
class FuturesTrade:
    direction: str
    entry_time: datetime
    entry_price: Decimal
    exit_time: datetime | None = None
    exit_price: Decimal | None = None
    qty: Decimal = Decimal("1")

    @property
    def pnl(self) -> Decimal | None:
        if self.exit_price is None:
            return None
        sign = Decimal("1") if self.direction == "long" else Decimal("-1")
        return (self.exit_price - self.entry_price) * self.qty * sign

    def to_dict(self) -> dict[str, Any]:
        return {
            "direction": self.direction,
            "entry_time": self.entry_time.isoformat(),
            "entry_price": str(self.entry_price),
            "exit_time": self.exit_time.isoformat() if self.exit_time else None,
            "exit_price": str(self.exit_price) if self.exit_price is not None else None,
            "qty": str(self.qty),
            "pnl": str(self.pnl) if self.pnl is not None else None,
        }


@dataclass
class FuturesResult:
    trades: list[FuturesTrade] = field(default_factory=list)
    open_position: FuturesTrade | None = None
    pending_events: list[SignalEvent] = field(default_factory=list)

    @property
    def realized_pnl(self) -> Decimal:
        return sum((trade.pnl or Decimal("0") for trade in self.trades), Decimal("0"))

    def to_dict(self) -> dict[str, Any]:
        return {
            "trades": [trade.to_dict() for trade in self.trades],
            "open_position": self.open_position.to_dict() if self.open_position else None,
            "pending_events": [event.to_dict() for event in self.pending_events],
            "realized_pnl": str(self.realized_pnl),
            "assumptions": {
                "leverage": 1,
                "qty": "1",
                "fees": "0",
                "slippage": "0",
                "fill_timing": "next_bar_open",
                "position_limit": 1,
            },
        }


def simulate_futures(ohlcv: pd.DataFrame, events: EventInput) -> FuturesResult:
    """마지막 봉 신호는 미체결로 남긴다. 반대 진입은 기존 청산 뒤 신규 진입이다."""
    if not isinstance(ohlcv.index, pd.DatetimeIndex) or ohlcv.index.tz is None:
        raise ValueError("OHLCV index는 시간대가 있는 DatetimeIndex여야 합니다")
    if not ohlcv.index.is_monotonic_increasing or ohlcv.index.has_duplicates:
        raise ValueError("OHLCV 봉은 중복 없이 시간순이어야 합니다")
    times = [utc_time(value) for value in ohlcv.index]
    positions = {value: i for i, value in enumerate(times)}
    grouped: dict[datetime, set[Direction]] = defaultdict(set)
    raw = coerce_events(events)
    for event in raw:
        if event.bar_time not in positions:
            raise ValueError(f"OHLCV에 신호 봉이 없습니다: {event.bar_time.isoformat()}")
        grouped[event.bar_time].add(event.direction)
    for directions in grouped.values():
        if {"long", "short"} <= directions:
            raise ValueError("동일 봉 매수·매도 신호가 충돌합니다")
    result = FuturesResult()

    def close(at: datetime, price: Decimal) -> None:
        position = result.open_position
        if position is not None:
            result.trades.append(
                FuturesTrade(
                    position.direction, position.entry_time, position.entry_price, at, price
                )
            )
            result.open_position = None

    for bar_time in sorted(grouped):
        index = positions[bar_time]
        if index + 1 == len(times):
            result.pending_events.extend(event for event in raw if event.bar_time == bar_time)
            continue
        price = Decimal(str(ohlcv.iloc[index + 1]["open"]))
        if not price.is_finite() or price <= 0:
            raise ValueError("체결 시가는 유한한 양수여야 합니다")
        fill_time, directions = times[index + 1], grouped[bar_time]
        if any(
            event.confirmed_at is not None and event.confirmed_at > fill_time
            for event in raw
            if event.bar_time == bar_time
        ):
            raise ValueError("신호가 확정되기 전에 다음 봉에서 체결할 수 없습니다")
        position = result.open_position
        if position is not None and f"{position.direction}_exit" in directions:
            close(fill_time, price)
        entry = "long" if "long" in directions else "short" if "short" in directions else None
        if entry is not None:
            position = result.open_position
            if position is not None and position.direction != entry:
                close(fill_time, price)
            if result.open_position is None:
                result.open_position = FuturesTrade(entry, fill_time, price)
    return result


def compare_futures(left: FuturesResult, right: FuturesResult) -> dict[str, Any]:
    """체결 순서·가격·열린 포지션·마지막 미체결 의도까지 비교한다."""
    same = (
        left.trades == right.trades
        and left.open_position == right.open_position
        and Counter((event.bar_time, event.direction) for event in left.pending_events)
        == Counter((event.bar_time, event.direction) for event in right.pending_events)
    )
    no_trades = (
        not left.trades
        and not right.trades
        and left.open_position is None
        and right.open_position is None
    )
    return {
        "status": "no_signal"
        if same and no_trades and not left.pending_events
        else "no_fills"
        if same and no_trades
        else "exact_match"
        if same
        else "mismatch",
        "left": left.to_dict(),
        "right": right.to_dict(),
    }

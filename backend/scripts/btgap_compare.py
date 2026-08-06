#!/usr/bin/env python
# btgap — 같은 구간의 백테스트 시뮬과 라이브 원장을 4단으로 분해해 대조한다
"""소크(데모 라이브) 원장과 같은 구간 백테스트를 처음으로 나란히 놓는다.

## 서브커맨드 셋

| 명령     | 하는 일                                                                  |
| -------- | ------------------------------------------------------------------------ |
| `run`    | 얼린 OHLCV 로 엔진을 직접 재실행해 `trades.json` + digest 를 만든다      |
| `match`  | `trades.json` × 라이브 원장을 **4단 분해**해 `report.json` 을 만든다     |
| `s1diff` | 스팟/perp 두 `trades.json` 의 같은 신호봉 진입가 차 분포를 낸다          |

## 대조가 서 있는 세 개의 못 (전부 코드가 정본이다)

1. ★**엔진 `RawTrade.pnl` 은 net 이다** (`v2_adapter._build_raw_trades` 3단 계약 1/3).
   그래서 기대 gross 는 `pnl + fees` 로 **복원**한다. 이 항등식을 뒤집으면
   (`pnl - fees`) 워터폴 1단이 통째로 두 배 틀린다.
2. ★**라이브 진입은 idempotency key 로 판별한다** — `parse_live_entry_key` 가 그 유일한
   자리다. `Order.filled_at` 으로 시각 매칭을 하면 안 된다: 그 값은 거래소 체결시각이
   아니라 **우리 관측시각**이라(`LedgerFill` docstring) 관측 지연만큼 늦은 봉을 고른다.
   key 에는 **신호봉 epoch** 이 실려 있으므로 그것이 봉 귀속의 정본이다.
3. ★**한쪽에만 있는 거래(존재 격차)를 양쪽에 있는 거래의 가격 격차에 접지 않는다.**
   접으면 "엔진이 낸 신호가 라이브에선 아예 안 났다" 가 "체결가가 조금 달랐다" 로
   둔갑한다. `summarize_parity` 의 buckets 규약이 이걸 위해 존재한다 — 재발명하지 않고
   그대로 쓴다.

## ★`--leverage 2.0` 은 거래를 0 건으로 만들 수 있다 (2026-08-06 실측)

`leverage > 1` 이면 `strategy_state._can_afford_entry` 의 **격리 증거금 게이트**가 켜진다.
기본 사이징은 `qty=1.0`(=1 BTC)이고 `init_cash` 는 10,000 이라, BTC 가격에서는
`required_margin = price / leverage` 가 자본을 넘어 **모든 진입이 거절**된다. 실측:
`s1_pbr.pine` × `BTCUSDT_1h.csv` 가 `leverage=1.0` 에서 **950 거래**, `leverage=2.0` 에서
**0 거래**(경고 950건 전부 "증거금 부족으로 진입 skip")였다. `status` 는 양쪽 다 `"ok"` 다.

그래서 `run` 은 **거래 0 건이면 파일을 쓰지 않고 종료 코드 1** 로 끝난다
(`--allow-empty-trades` 로만 관통). 0 건짜리 `trades.json` 을 그대로 넘기면 `match` 가
"라이브에만 있다" 를 잔뜩 보고하고, 그것은 진짜 발견처럼 읽힌다.

## 입력 JSON 스키마 (CONTROL 이 덤프하는 모양 — 동결)

- `orders.json` — `[{id, idempotency_key, side, quantity, price, filled_price,
  filled_quantity, realized_pnl, realized_pnl_synced_at, filled_at, state, reduce_only}]`
- `exits.json` — `[{id, order_link_id, matched_order_id, side, closed_pnl, closed_size,
  avg_entry_price, avg_exit_price, exchange_created_at, classification,
  attribution_confidence}]`
- `session.json` — `{id, strategy_id, symbol, interval, created_at, deactivated_at}`
  **또는 그 객체들의 배열** (세션이 여럿이면 경계 회계가 필요하다 — §세션 경계 참조)

숫자는 전부 문자열/숫자/`null` 을 받아 `Decimal` 로 올린다. float 공간 합산은 없다.

## ★입력에 대해 실측으로 못박힌 것 넷 (전부 조용히 틀리는 자리)

1. **`exits.json` 은 event 하나가 2행으로 온다.** 각 `order_link_id` 가 정확히 2행이고
   payload 는 같고 `classification` 만 `ours`/`unknown` 으로 갈린다. 순진한 Σ 는 손익을
   **정확히 2배** 계상한다(−289.13 vs 진값 −144.57). `match` 는 합산 전에 반드시
   `dedupe_ledger_rows` 를 통과시키고 dedup 전/후 행 수를 report 에 남긴다.
2. **매칭에 가격을 쓰면 안 된다.** 0.1% 창 안에 다른 체결가가 84/84 전건에서 2개 이상
   들어오고, 최근접-가격 그리디는 29.8% 에서 남의 체결가를 고른다. 1차 키는
   `(bar_epoch, direction, trade_id)` + 수량이고, 가격은 매칭 **뒤** 잔차로만 본다.
3. **key 의 `quantity` 는 표기가 4가지**(`'0.058'`/`'0.05800000'`…)다. 문자열 비교 금지 —
   항상 `Decimal` 로 비교한다.
4. **exits→orders 는 `order_link_id == CAST(order.id AS text)`** 직결이다(82/82 실증).

## 세션 경계 — 반전 전략이라 진입창 ≠ 청산창이 실재한다

창을 가로지르는 포지션이 실측 6건이고 그중 1건은 세션 사이 **2.74h 무세션 구간**을
통과했다(보유 211분). 그래서 `match` 는 `unattributed` / `gap_exit` / `cross_window` /
경계 carry 를 **총계에 접지 않고 버킷으로 병기**한다. 귀속 기본값은 **청산시각**이고,
진입시각 귀속과의 차(세션 단위 ±7 USDT 실측)를 함께 낸다.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any
from uuid import UUID

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.trading.outcome_parity import (  # noqa: E402
    ParityBuckets,
    ParityObservation,
    ParitySummary,
    summarize_parity,
)
from src.trading.services.conditional_entry_planner import (  # noqa: E402
    parse_live_entry_key,
)

# 세션 interval → 봉 길이(초). 여기 없는 값은 거부한다 — 추측하면 봉 허용창이 틀린다.
INTERVAL_SECONDS: dict[str, int] = {
    "1m": 60,
    "3m": 180,
    "5m": 300,
    "15m": 900,
    "30m": 1800,
    "1h": 3600,
    "2h": 7200,
    "4h": 14400,
}

# 1차 키가 실패했을 때 보조 후보가 허용하는 봉 거리 (±N봉).
ENTRY_BAR_TOLERANCE_BARS = 3
# ★가격 근접은 **매칭 술어가 아니다** (R7 실측). 이 값은 매칭 뒤 잔차를 「크다」고
# 표시하는 문턱으로만 쓴다 — 0.1% 창(±64.6 USDT) 안에 다른 체결가가 84/84 전건에서
# 2개 이상 들어오므로 판별력이 없다.
TRIGGER_RELATIVE_TOLERANCE = Decimal("0.001")


# --------------------------------------------------------------------------
# 순수 값 — JSON 경계에서 Decimal/datetime 으로 올리는 자리
# --------------------------------------------------------------------------


def to_decimal(value: Any) -> Decimal | None:
    """JSON 값 하나를 `Decimal` 로. 빈 값은 `None` 이지 0 이 아니다."""
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"숫자로 읽을 수 없다: {value!r}") from exc


def to_datetime(value: Any) -> datetime | None:
    """ISO8601 문자열 하나를 tz-aware UTC `datetime` 으로."""
    if value is None or value == "":
        return None
    moment = datetime.fromisoformat(str(value))
    if moment.tzinfo is None:
        raise ValueError(f"tz 없는 시각은 받지 않는다: {value!r}")
    return moment.astimezone(UTC)


def interval_seconds(interval: str) -> int:
    try:
        return INTERVAL_SECONDS[interval]
    except KeyError:
        raise ValueError(f"지원하지 않는 interval: {interval!r}") from None


def decimal_text(value: Decimal | None) -> str | None:
    """지수 표기 없는 고정 소수점 문자열. digest 가 표현에 민감하기 때문이다."""
    return None if value is None else format(value, "f")


def sum_decimals(values: Sequence[Decimal]) -> Decimal:
    """금융 합산을 Decimal 영역에서만 한다 (레포 규칙)."""
    total = Decimal("0")
    for value in values:
        total = Decimal(str(total)) + Decimal(str(value))
    return total


def _iso(moment: datetime | None) -> str | None:
    return None if moment is None else moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


# --------------------------------------------------------------------------
# 백테스트 쪽 — `run` 이 낸 trades.json 을 다시 읽는 자리
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BacktestTrade:
    """`run` 이 낸 trades.json 의 한 행. `pnl` 은 **net** 이다."""

    trade_index: int
    direction: str
    status: str
    entry_time: datetime
    exit_time: datetime | None
    entry_price: Decimal
    exit_price: Decimal | None
    size: Decimal
    pnl: Decimal
    fees: Decimal
    fee_paid: Decimal | None
    slippage_paid: Decimal | None
    comment: str | None
    exit_kind: str | None

    @property
    def expected_gross(self) -> Decimal:
        """엔진 기대 gross = net + 결합 비용. ★`pnl - fees` 가 아니다."""
        return Decimal(str(self.pnl)) + Decimal(str(self.fees))

    @property
    def backtest_cost(self) -> Decimal:
        """백테스트가 뺀 비용. 분해 필드가 없으면 결합 필드를 쓴다."""
        if self.fee_paid is None or self.slippage_paid is None:
            return Decimal(str(self.fees))
        return Decimal(str(self.fee_paid)) + Decimal(str(self.slippage_paid))


def parse_backtest_trades(rows: Sequence[Mapping[str, Any]]) -> list[BacktestTrade]:
    """trades.json 의 `trades` 배열을 `BacktestTrade` 로 올린다."""
    trades: list[BacktestTrade] = []
    for row in rows:
        entry_time = to_datetime(row.get("entry_time"))
        entry_price = to_decimal(row.get("entry_price"))
        size = to_decimal(row.get("size"))
        pnl = to_decimal(row.get("pnl"))
        fees = to_decimal(row.get("fees"))
        if entry_time is None or entry_price is None or size is None:
            raise ValueError(f"백테스트 거래에 진입 정보가 없다: {row!r}")
        if pnl is None or fees is None:
            raise ValueError(f"백테스트 거래에 pnl/fees 가 없다: {row!r}")
        trades.append(
            BacktestTrade(
                trade_index=int(row["trade_index"]),
                direction=str(row["direction"]),
                status=str(row.get("status", "closed")),
                entry_time=entry_time,
                exit_time=to_datetime(row.get("exit_time")),
                entry_price=entry_price,
                exit_price=to_decimal(row.get("exit_price")),
                size=size,
                pnl=pnl,
                fees=fees,
                fee_paid=to_decimal(row.get("fee_paid")),
                slippage_paid=to_decimal(row.get("slippage_paid")),
                comment=row.get("comment"),
                exit_kind=row.get("exit_kind"),
            )
        )
    return sorted(trades, key=lambda trade: (trade.entry_time, trade.trade_index))


# --------------------------------------------------------------------------
# 라이브 쪽 — 주문 / 원장
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class LiveEntry:
    """우리 key 로 판별된 라이브 진입 주문 1건 (체결분이 있는 것만)."""

    order_id: str
    idempotency_key: str
    kind: str
    trade_id: str
    bar_epoch: int | None
    direction: str
    trigger: Decimal | None
    # key 에 실린 **요청** 수량. 표기가 `'0.058'`/`'0.05800000'` 로 갈리므로
    # ★문자열 비교 금지 — 항상 Decimal 로 비교한다 (R7).
    key_quantity: Decimal | None
    filled_price: Decimal | None
    filled_quantity: Decimal | None
    filled_at: datetime | None

    @property
    def partially_filled(self) -> bool:
        """체결분이 요청 수량에 못 미쳤나. 매칭을 막지 않고 **따로 센다**."""
        if self.key_quantity is None or self.filled_quantity is None:
            return False
        return self.filled_quantity < self.key_quantity


@dataclass(frozen=True, slots=True)
class LiveOrder:
    """orders.json 한 행의 최소 스냅샷."""

    order_id: str
    side: str
    state: str
    reduce_only: bool
    idempotency_key: str | None
    quantity: Decimal | None
    filled_quantity: Decimal | None
    filled_price: Decimal | None
    realized_pnl: Decimal | None
    filled_at: datetime | None

    @property
    def signed_fill(self) -> Decimal:
        """원장 순포지션 산술 — buy `+`, sell `−`. 체결분이 없으면 0."""
        quantity = self.filled_quantity or Decimal("0")
        return quantity if self.side.lower() == "buy" else -Decimal(str(quantity))

    @property
    def is_manual_flatten(self) -> bool:
        """빈 idempotency_key + reduce_only = 사람이 손으로 정리한 주문."""
        return not self.idempotency_key and self.reduce_only


@dataclass(frozen=True, slots=True)
class LedgerRow:
    """exits.json 한 행 = 거래소가 확정한 왕복 청산 1건.

    ★`side` 는 거래소 원본(`Buy`/`Sell`)이다 — ccxt 가 뒤집기 전 값
    (`models.ExchangeExit.side` 주석). `Sell` = 롱을 닫았다.
    """

    exit_id: str
    order_link_id: str | None
    matched_order_id: str | None
    side: str | None
    closed_pnl: Decimal
    closed_size: Decimal | None
    avg_entry_price: Decimal | None
    avg_exit_price: Decimal | None
    exchange_created_at: datetime
    classification: str
    attribution_confidence: str


@dataclass(frozen=True, slots=True)
class OrderCorpus:
    """orders.json 을 셋으로 가른 결과. 어디에도 안 들어간 행은 `other` 다."""

    entries: list[LiveEntry]
    manual_flatten: list[LiveOrder]
    other: list[LiveOrder]
    by_id: dict[str, LiveOrder]
    all_orders: list[LiveOrder]


def order_has_fill(order: LiveOrder) -> bool:
    """이 행이 **실제로 포지션을 만들었나**.

    ★`state == 'filled'` 로 판정하면 안 된다 — 레포 정본은
    `entry_completeness.attempt_has_fill` 이고, 그것은 `filled_quantity > 0` 만 본다.
    `cancelled` 인데 체결분이 남은 행이 실재하고, `filled` 인데 수량이 NULL 인 행은
    판독 불가이지 성공이 아니다.
    """
    return order.filled_quantity is not None and order.filled_quantity > Decimal("0")


def _side_direction(side: str) -> str:
    return "long" if side.lower() == "buy" else "short"


def parse_orders(
    rows: Sequence[Mapping[str, Any]], *, session_ids: Collection[UUID]
) -> OrderCorpus:
    """orders.json 을 진입 / 수동 정리 / 그 외로 가른다.

    진입 판별은 오로지 `parse_live_entry_key` 다. 청산 key·웹훅·수동 주문은 전부
    `None` 으로 떨어지고, 그것을 조용히 버리지 않고 `other`/`manual_flatten` 에 남긴다.
    """
    wanted = set(session_ids)
    entries: list[LiveEntry] = []
    manual_flatten: list[LiveOrder] = []
    other: list[LiveOrder] = []
    by_id: dict[str, LiveOrder] = {}
    all_orders: list[LiveOrder] = []

    for row in rows:
        order = LiveOrder(
            order_id=str(row["id"]),
            side=str(row.get("side", "")),
            state=str(row.get("state", "")),
            reduce_only=bool(row.get("reduce_only", False)),
            idempotency_key=row.get("idempotency_key"),
            quantity=to_decimal(row.get("quantity")),
            filled_quantity=to_decimal(row.get("filled_quantity")),
            filled_price=to_decimal(row.get("filled_price")),
            realized_pnl=to_decimal(row.get("realized_pnl")),
            filled_at=to_datetime(row.get("filled_at")),
        )
        by_id[order.order_id] = order
        all_orders.append(order)

        parsed = parse_live_entry_key(order.idempotency_key)
        if parsed is not None and parsed.session_id in wanted and order_has_fill(order):
            entries.append(
                LiveEntry(
                    order_id=order.order_id,
                    idempotency_key=str(order.idempotency_key),
                    kind=str(parsed.kind),
                    trade_id=parsed.trade_id,
                    bar_epoch=parsed.bar_epoch,
                    direction=_side_direction(order.side),
                    trigger=to_decimal(parsed.trigger),
                    key_quantity=to_decimal(parsed.quantity),
                    filled_price=order.filled_price,
                    filled_quantity=order.filled_quantity,
                    filled_at=order.filled_at,
                )
            )
            continue
        if order.is_manual_flatten:
            manual_flatten.append(order)
            continue
        other.append(order)

    entries.sort(key=lambda entry: (entry.bar_epoch or 0, entry.order_id))
    return OrderCorpus(
        entries=entries,
        manual_flatten=manual_flatten,
        other=other,
        by_id=by_id,
        all_orders=all_orders,
    )


def parse_ledger_rows(rows: Sequence[Mapping[str, Any]]) -> list[LedgerRow]:
    """exits.json 을 `LedgerRow` 로 올린다 (시간 오름차순)."""
    ledger: list[LedgerRow] = []
    for row in rows:
        closed_pnl = to_decimal(row.get("closed_pnl"))
        exchange_created_at = to_datetime(row.get("exchange_created_at"))
        if closed_pnl is None:
            raise ValueError(f"원장 행에 closed_pnl 이 없다: {row!r}")
        if exchange_created_at is None:
            raise ValueError(f"원장 행에 exchange_created_at 이 없다: {row!r}")
        ledger.append(
            LedgerRow(
                exit_id=str(row["id"]),
                order_link_id=(
                    None if row.get("order_link_id") is None else str(row["order_link_id"])
                ),
                matched_order_id=(
                    None if row.get("matched_order_id") is None else str(row["matched_order_id"])
                ),
                side=None if row.get("side") is None else str(row["side"]),
                closed_pnl=closed_pnl,
                closed_size=to_decimal(row.get("closed_size")),
                avg_entry_price=to_decimal(row.get("avg_entry_price")),
                avg_exit_price=to_decimal(row.get("avg_exit_price")),
                exchange_created_at=exchange_created_at,
                classification=str(row.get("classification", "unknown")),
                attribution_confidence=str(row.get("attribution_confidence", "none")),
            )
        )
    return sorted(ledger, key=lambda entry: (entry.exchange_created_at, entry.exit_id))


# --------------------------------------------------------------------------
# ★원장 dedup — 한 청산이 두 행으로 온다 (R6)
# --------------------------------------------------------------------------

# 같은 event 의 두 행 중 어느 것을 대표로 삼나. 값이 작을수록 우선.
_CLASSIFICATION_PREFERENCE = {"ours": 0}


@dataclass(frozen=True, slots=True)
class LedgerDedup:
    """dedup 전/후를 **둘 다** 들고 다닌다 — 순진한 Σ 가 2배가 되는 자리이기 때문이다."""

    events: list[LedgerRow]
    rows_in: int
    rows_dropped: int
    duplicate_groups: int


def _ledger_group_key(row: LedgerRow) -> tuple[str, ...]:
    """같은 청산 event 를 가리키는 키. `order_link_id` 가 있으면 그것이 정본이다."""
    if row.order_link_id:
        return ("link", row.order_link_id)
    # link 가 없으면 payload 동등성으로 묶는다 — `id` 는 행마다 다르므로 쓸 수 없다.
    return (
        "payload",
        _iso(row.exchange_created_at) or "",
        decimal_text(row.closed_pnl) or "",
        decimal_text(row.closed_size) or "",
        decimal_text(row.avg_entry_price) or "",
        decimal_text(row.avg_exit_price) or "",
        row.side or "",
    )


def dedupe_ledger_rows(rows: Sequence[LedgerRow]) -> LedgerDedup:
    """★`order_link_id` 당 **1 event** 로 접는다.

    실측(eval2): `exits.json` 은 각 `order_link_id` 가 **정확히 2행**이고 payload 는 같고
    `classification` 만 `ours`/`unknown` 으로 갈린다. 순진한 Σ 는 손익을 **정확히 2배**
    계상한다(−289.13 vs 진값 −144.57). 그래서 합산 전에 여기를 반드시 통과시킨다.

    대표 행은 `classification == "ours"` 를 우선하고, 동률이면 `id` 오름차순으로 골라
    **결정적**이게 둔다.
    """
    grouped: dict[tuple[str, ...], list[LedgerRow]] = {}
    for row in rows:
        grouped.setdefault(_ledger_group_key(row), []).append(row)

    events: list[LedgerRow] = []
    duplicate_groups = 0
    for group in grouped.values():
        if len(group) > 1:
            duplicate_groups += 1
        events.append(
            sorted(
                group,
                key=lambda row: (
                    _CLASSIFICATION_PREFERENCE.get(row.classification, 1),
                    row.exit_id,
                ),
            )[0]
        )
    events.sort(key=lambda row: (row.exchange_created_at, row.exit_id))
    return LedgerDedup(
        events=events,
        rows_in=len(rows),
        rows_dropped=len(rows) - len(events),
        duplicate_groups=duplicate_groups,
    )


def derive_ledger_values(row: LedgerRow) -> tuple[Decimal | None, Decimal | None]:
    """원장 행 하나에서 gross 와 왕복 notional 을 분해한다.

    `parity_repository._derive_ledger_values` 와 **같은 의미론**이되 방향 부호를
    원장 자신의 `side` 에서 가져온다(R10). 그 전에는 청산 주문을 되짚어 side 를 얻었는데,
    덤프에 `side` 가 실리면서 그 우회와 「청산 주문 조회 실패 → 분해 포기」 경로가 함께
    사라졌다.

    가격 셋 중 하나라도 없으면 분해하지 않는다 — 0 으로 메우면 비용이 없는 주문처럼 보인다.
    """
    if (
        row.side is None
        or row.closed_size is None
        or row.avg_entry_price is None
        or row.avg_exit_price is None
    ):
        return None, None

    closed_size = Decimal(str(row.closed_size))
    avg_entry_price = Decimal(str(row.avg_entry_price))
    avg_exit_price = Decimal(str(row.avg_exit_price))
    side = row.side.lower()
    if side == "sell":
        # 청산이 매도 = 롱을 닫았다.
        actual_gross = (avg_exit_price - avg_entry_price) * closed_size
    elif side == "buy":
        actual_gross = (avg_entry_price - avg_exit_price) * closed_size
    else:
        return None, None
    return actual_gross, (avg_entry_price + avg_exit_price) * closed_size


def link_ledger_to_orders(
    events: Sequence[LedgerRow], by_id: Mapping[str, LiveOrder]
) -> dict[str, LiveOrder]:
    """`order_link_id == CAST(order.id AS text)` 직결 (R7 — 82/82 가격 일치 실증).

    되짚지 못한 event 는 **빠진다** — 호출부가 그것을 「orders 에 없는 청산」으로 센다.
    """
    linked: dict[str, LiveOrder] = {}
    for event in events:
        if event.order_link_id is None:
            continue
        order = by_id.get(event.order_link_id)
        if order is not None:
            linked[event.exit_id] = order
    return linked


def attribute_ledger_rows(
    entries: Sequence[LiveEntry],
    events: Sequence[LedgerRow],
) -> tuple[dict[str, LedgerRow], list[LedgerRow]]:
    """원장 event 를 라이브 진입에 **시간순 FIFO** 로 붙인다.

    ★`Order.filled_at` 을 쓰지 않는다 — 그건 우리 관측시각이라 귀속을 늦춘다. 진입 쪽
    시각은 key 의 `bar_epoch`(신호봉), 원장 쪽은 거래소가 찍은 `exchange_created_at` 이다.

    이 전략은 한 번에 한 포지션만 든다(반전 전략). 겹치는 포지션이 생겨 가정이 깨지면
    남는 event 가 `ledger_only` 로 **보이게** 떨어진다 — 조용히 섞이지 않는다.
    """
    ordered_entries = [entry for entry in entries if entry.bar_epoch is not None]
    assigned: dict[str, LedgerRow] = {}
    unassigned: list[LedgerRow] = []
    cursor = 0
    for event in events:
        event_epoch = int(event.exchange_created_at.timestamp())
        entry = ordered_entries[cursor] if cursor < len(ordered_entries) else None
        if entry is not None and entry.bar_epoch is not None and entry.bar_epoch <= event_epoch:
            assigned[entry.order_id] = event
            cursor += 1
        else:
            unassigned.append(event)
    return assigned, unassigned


# --------------------------------------------------------------------------
# 세션 창 — 경계 회계 (R5 · R8)
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SessionWindow:
    session_id: str
    start: datetime
    end: datetime | None  # None = 아직 살아 있다


def parse_sessions(payload: Any) -> list[SessionWindow]:
    """`session.json` 은 객체 하나여도 되고 배열이어도 된다."""
    rows = payload if isinstance(payload, list) else [payload]
    windows: list[SessionWindow] = []
    for row in rows:
        start = to_datetime(row.get("created_at"))
        if start is None:
            raise ValueError(f"세션에 created_at 이 없다: {row!r}")
        windows.append(
            SessionWindow(
                session_id=str(row["id"]),
                start=start,
                end=to_datetime(row.get("deactivated_at")),
            )
        )
    return sorted(windows, key=lambda window: (window.start, window.session_id))


def window_of(moment: datetime, windows: Sequence[SessionWindow]) -> str | None:
    """이 시각을 품는 세션. 어느 창에도 없으면 `None`."""
    for window in windows:
        if window.start <= moment and (window.end is None or moment < window.end):
            return window.session_id
    return None


def is_between_windows(moment: datetime, windows: Sequence[SessionWindow]) -> bool:
    """세션 **사이**의 무세션 구간인가 (첫 창 시작 뒤 · 마지막 창 끝 앞 · 어느 창에도 없음).

    첫 창 앞이나 마지막 창 뒤는 「갭」이 아니라 그냥 범위 밖이다 — 둘을 섞지 않는다.
    """
    if not windows or window_of(moment, windows) is not None:
        return False
    last_end = windows[-1].end
    if last_end is None:
        return moment >= windows[0].start
    return windows[0].start <= moment < last_end


def net_position_at(orders: Sequence[LiveOrder], moment: datetime) -> Decimal:
    """이 시각까지 체결된 주문의 부호합 = 라이브 순포지션.

    ★여기서는 `filled_at` 을 쓴다. 매칭에는 금지지만(관측시각이라 봉을 늦춘다) 경계
    회계에는 다른 시각이 없다 — 그래서 이 값은 **관측 지연만큼 늦다**고 읽어야 한다.
    """
    return sum_decimals(
        [
            order.signed_fill
            for order in orders
            if order.filled_at is not None and order.filled_at <= moment
        ]
    )


def open_backtest_position_at(trades: Sequence[BacktestTrade], moment: datetime) -> Decimal:
    """이 시각에 열려 있던 백테스트 포지션의 부호합."""
    return sum_decimals(
        [
            Decimal(str(trade.size))
            * (Decimal("1") if trade.direction == "long" else Decimal("-1"))
            for trade in trades
            if trade.entry_time <= moment and (trade.exit_time is None or trade.exit_time > moment)
        ]
    )


# --------------------------------------------------------------------------
# 매칭 — 1차 키는 신호봉 + 방향 + trade_id + 수량 (R1 · R7)
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MatchedPair:
    entry: LiveEntry
    trade: BacktestTrade
    grade: str  # "strict" | "loose"


@dataclass(frozen=True, slots=True)
class AmbiguousEntry:
    entry: LiveEntry
    reason: str
    candidate_trade_indexes: list[int]


@dataclass(frozen=True, slots=True)
class MatchResult:
    pairs: list[MatchedPair]
    live_only: list[LiveEntry]
    backtest_only: list[BacktestTrade]
    ambiguous: list[AmbiguousEntry]

    @property
    def strict_pairs(self) -> list[MatchedPair]:
        return [pair for pair in self.pairs if pair.grade == "strict"]

    @property
    def loose_pairs(self) -> list[MatchedPair]:
        return [pair for pair in self.pairs if pair.grade == "loose"]


def trade_bar_epoch(trade: BacktestTrade, *, bar_seconds: int) -> int:
    return (int(trade.entry_time.timestamp()) // bar_seconds) * bar_seconds


def strict_key_matches(trade: BacktestTrade, entry: LiveEntry, *, bar_seconds: int) -> bool:
    """1차 키 — `(bar_epoch, direction, trade_id)` 정확 일치 + 수량 Decimal 동등.

    ★가격은 보지 않는다. 실측(eval2)에서 0.1% 창(±64.6 USDT) 안에 다른 체결가가
    **84/84 전건에서 2개 이상** 들어왔고, 최근접-가격 그리디는 **29.8% 에서 남의 체결가**
    를 골랐다 — 가격은 판별자가 아니라 매칭 **후** 잔차로 보고할 값이다.

    `trade_id` 는 Pine 진입 규칙 이름이고 엔진 쪽 대응 필드는 `RawTrade.comment` 다
    (`strategy.entry("PivRevLE", …, comment="PivRevLE")`). comment 가 없으면 1차 키를
    세울 수 없으므로 **strict 가 아니다** — 없는 술어를 통과로 치지 않는다.
    """
    if entry.bar_epoch is None or entry.key_quantity is None:
        return False
    if trade.direction != entry.direction:
        return False
    if trade.comment is None or trade.comment != entry.trade_id:
        return False
    if trade_bar_epoch(trade, bar_seconds=bar_seconds) != entry.bar_epoch:
        return False
    # 표기가 `'0.058'`/`'0.05800000'` 로 갈리므로 문자열이 아니라 Decimal 로 본다.
    return Decimal(str(trade.size)) == Decimal(str(entry.key_quantity))


def loose_key_matches(
    trade: BacktestTrade,
    entry: LiveEntry,
    *,
    bar_seconds: int,
    bar_tolerance: int = ENTRY_BAR_TOLERANCE_BARS,
) -> bool:
    """보조 후보 — `bar_epoch ±N봉` + 방향 + `trade_id`. **가격 근접은 쓰지 않는다**(R7)."""
    if entry.bar_epoch is None:
        return False
    if trade.direction != entry.direction:
        return False
    if trade.comment is None or trade.comment != entry.trade_id:
        return False
    delta = trade_bar_epoch(trade, bar_seconds=bar_seconds) - entry.bar_epoch
    return abs(delta) <= bar_tolerance * bar_seconds


def match_entries(
    trades: Sequence[BacktestTrade],
    entries: Sequence[LiveEntry],
    *,
    bar_seconds: int,
    bar_tolerance: int = ENTRY_BAR_TOLERANCE_BARS,
) -> MatchResult:
    """2단 매칭. **strict 를 전부 붙인 뒤** 남은 것만 loose 로 본다.

    한 번에 훑으면 loose 후보가 strict 쌍이 쓸 거래를 먼저 집어갈 수 있다 —
    그러면 판정 표본(strict)이 매칭 순서에 흔들린다.

    ★과잉 매칭은 fail-**open** 이다. 같은 `(bar_epoch, direction)` 에 후보가 둘 이상이면
    **붙이지 않고** `ambiguous` 로 센다. 억지로 하나 고르면 격차가 조용히 줄어든다.
    """
    ordered_trades = sorted(trades, key=lambda trade: (trade.entry_time, trade.trade_index))
    ordered_entries = sorted(entries, key=lambda entry: (entry.bar_epoch or 0, entry.order_id))

    ambiguous: list[AmbiguousEntry] = []
    pairs: list[MatchedPair] = []
    used: set[int] = set()

    # ① 라이브 쪽 자체 충돌 — 같은 신호봉·방향에 진입이 둘이면 어느 쪽에 붙일지 모른다.
    live_groups: dict[tuple[int | None, str], list[LiveEntry]] = {}
    for entry in ordered_entries:
        live_groups.setdefault((entry.bar_epoch, entry.direction), []).append(entry)
    candidates: list[LiveEntry] = []
    for group in live_groups.values():
        if len(group) > 1:
            ambiguous.extend(
                AmbiguousEntry(entry=entry, reason="live_key_collision", candidate_trade_indexes=[])
                for entry in group
            )
            continue
        candidates.extend(group)
    candidates.sort(key=lambda entry: (entry.bar_epoch or 0, entry.order_id))

    def _resolve(
        entry: LiveEntry, predicate: Any, reason: str
    ) -> tuple[MatchedPair | None, AmbiguousEntry | None]:
        hits = [
            index
            for index, trade in enumerate(ordered_trades)
            if index not in used and predicate(trade, entry)
        ]
        if len(hits) > 1:
            return None, AmbiguousEntry(
                entry=entry,
                reason=reason,
                candidate_trade_indexes=[ordered_trades[i].trade_index for i in hits],
            )
        if len(hits) == 1:
            used.add(hits[0])
            return MatchedPair(
                entry=entry,
                trade=ordered_trades[hits[0]],
                grade="strict" if reason == "multiple_strict" else "loose",
            ), None
        return None, None

    # ② strict 전량
    remaining: list[LiveEntry] = []
    for entry in candidates:
        pair, conflict = _resolve(
            entry,
            lambda trade, e: strict_key_matches(trade, e, bar_seconds=bar_seconds),
            "multiple_strict",
        )
        if conflict is not None:
            ambiguous.append(conflict)
            continue
        if pair is not None:
            pairs.append(pair)
            continue
        remaining.append(entry)

    # ③ 남은 것만 loose
    live_only: list[LiveEntry] = []
    for entry in remaining:
        pair, conflict = _resolve(
            entry,
            lambda trade, e: loose_key_matches(
                trade, e, bar_seconds=bar_seconds, bar_tolerance=bar_tolerance
            ),
            "multiple_loose",
        )
        if conflict is not None:
            ambiguous.append(conflict)
            continue
        if pair is not None:
            pairs.append(pair)
            continue
        live_only.append(entry)

    pairs.sort(key=lambda pair: (pair.entry.bar_epoch or 0, pair.entry.order_id))
    backtest_only = [trade for index, trade in enumerate(ordered_trades) if index not in used]
    return MatchResult(
        pairs=pairs, live_only=live_only, backtest_only=backtest_only, ambiguous=ambiguous
    )


def price_residuals(pairs: Sequence[MatchedPair]) -> dict[str, Any]:
    """★가격은 매칭 **후** 검증용이다 (R7). 트리거 대비 진입가 상대 잔차 분포.

    표본이 없으면 「미판정」이다 — 0% 로 내면 "완벽히 맞았다" 로 읽힌다.
    """
    residuals = [
        (Decimal(str(pair.trade.entry_price)) - Decimal(str(pair.entry.trigger)))
        / abs(Decimal(str(pair.entry.trigger)))
        * Decimal("100")
        for pair in pairs
        if pair.entry.trigger is not None and pair.entry.trigger != Decimal("0")
    ]
    threshold = TRIGGER_RELATIVE_TOLERANCE * Decimal("100")
    return {
        "n": len(residuals),
        "verdict": "measured" if residuals else "undetermined",
        "median_pct": decimal_text(median_decimal(residuals)),
        "min_pct": decimal_text(min(residuals)) if residuals else None,
        "max_pct": decimal_text(max(residuals)) if residuals else None,
        "beyond_tolerance": sum(1 for value in residuals if abs(value) > threshold),
        "tolerance_pct": decimal_text(threshold),
    }


# --------------------------------------------------------------------------
# 4단 분해 — 조립은 summarize_parity 재사용
# --------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ObservationSet:
    """`ParityObservation` 목록 + R3 비율이 필요로 하는 행별 원자값."""

    observations: list[ParityObservation]
    unrealized: int
    cost_terms: list[Decimal]  # actual_net − actual_gross
    gap_terms: list[Decimal]  # expected_gross − actual_net


def build_observations(
    pairs: Sequence[MatchedPair],
    assigned: Mapping[str, LedgerRow],
) -> ObservationSet:
    """매칭 쌍 + 귀속된 원장 event → parity 관측.

    ★`actual_net` 은 **원장 순수 산술**(`closed_pnl`)이다 — `Order.realized_pnl` 이
    아니다(R2). 매칭됐지만 아직 청산이 없는 쌍은 관측이 **아니다**: `ParityObservation` 은
    확정 net 을 결측으로 표현할 수 없으므로 0 으로 메우는 대신 따로 센다.
    """
    observations: list[ParityObservation] = []
    cost_terms: list[Decimal] = []
    gap_terms: list[Decimal] = []
    unrealized = 0
    for pair in pairs:
        event = assigned.get(pair.entry.order_id)
        if event is None:
            unrealized += 1
            continue
        actual_gross, round_trip_notional = derive_ledger_values(event)
        actual_net = Decimal(str(event.closed_pnl))
        observations.append(
            ParityObservation(
                expected_gross=pair.trade.expected_gross,
                actual_net=actual_net,
                actual_gross=actual_gross,
                round_trip_notional=round_trip_notional,
            )
        )
        if actual_gross is not None:
            cost_terms.append(actual_net - Decimal(str(actual_gross)))
            gap_terms.append(pair.trade.expected_gross - actual_net)
    return ObservationSet(
        observations=observations,
        unrealized=unrealized,
        cost_terms=cost_terms,
        gap_terms=gap_terms,
    )


def cancellation_index(values: Sequence[Decimal]) -> Decimal | None:
    """`1 − |Σx| / Σ|x|`. 0 = 상쇄 없음, 1 로 갈수록 부호가 서로를 지운다.

    Σ|x| 가 0 이면 정의되지 않는다 — 0 으로 내면 "상쇄가 없다" 로 읽힌다.
    """
    absolute_total = sum_decimals([abs(value) for value in values])
    if absolute_total == Decimal("0"):
        return None
    return Decimal("1") - (abs(sum_decimals(list(values))) / absolute_total)


def _ratio(numerator: Decimal, denominator: Decimal) -> Decimal | None:
    return None if denominator == Decimal("0") else numerator / denominator


def cost_explanation(observation_set: ObservationSet) -> dict[str, Any]:
    """③ 을 **두 정의로** 낸다 (R3).

    ★합계를 먼저 낸 뒤 절대값을 씌우면(`preregistered`) 부호 상쇄가 분모를 0 쪽으로
    끌어당겨 비율이 폭발한다. 행별 절대값(`row_abs`)은 그 폭발이 없다. 그런데 판정은
    **사전등록 원문으로 한다** — 표본을 보고 정의를 갈아 끼우는 것이 곧 래칫 위반이다.
    상쇄 정도는 `cancellation_index` 로 옆에 병기해 판단 재료로 남긴다.
    """
    cost_terms = observation_set.cost_terms
    gap_terms = observation_set.gap_terms
    return {
        "n": len(cost_terms),
        "preregistered": decimal_text(
            _ratio(abs(sum_decimals(cost_terms)), abs(sum_decimals(gap_terms)))
        ),
        "row_abs": decimal_text(
            _ratio(
                sum_decimals([abs(value) for value in cost_terms]),
                sum_decimals([abs(value) for value in gap_terms]),
            )
        ),
        "cancellation_index": {
            "numerator": decimal_text(cancellation_index(cost_terms)),
            "denominator": decimal_text(cancellation_index(gap_terms)),
        },
        "verdict_definition": "preregistered",
    }


@dataclass(frozen=True, slots=True)
class Decomposition:
    """`match` 가 내는 전부. 워터폴은 여기서 파생만 한다."""

    summary: ParitySummary
    observation_set: ObservationSet
    loose_summary: ParitySummary | None
    loose_observation_set: ObservationSet | None
    strict_pairs: int
    loose_pairs: int
    ambiguous: int
    backtest_only_expected_gross: Decimal
    live_only_actual_net: Decimal
    ledger_only_net: Decimal
    backtest_cost_matched: Decimal
    backtest_fee_paid: Decimal | None
    backtest_slippage_paid: Decimal | None
    flatten_events: list[LedgerRow]
    flatten_from_order: int
    flatten_orphan: int
    ledger_only_count: int
    ledger_quantity_mismatch: int
    partial_fill_count: int


def _optional_sum(values: Sequence[Decimal | None]) -> Decimal | None:
    """한 건이라도 결측이면 합계를 만들지 않는다 — 0 으로 메우면 비용이 준다."""
    if not values or any(value is None for value in values):
        return None
    return sum_decimals([value for value in values if value is not None])


def decompose(
    match: MatchResult,
    *,
    corpus: OrderCorpus,
    dedup: LedgerDedup,
) -> Decomposition:
    """매칭 결과 + dedup 된 원장을 `ParitySummary` 와 워터폴 입력으로 접는다.

    판정 표본은 **strict 쌍만**이다. loose 는 같은 조립을 한 번 더 돌려 감도로 병기한다.
    """
    events = dedup.events
    assigned, unassigned = attribute_ledger_rows(corpus.entries, events)
    linked = link_ledger_to_orders(events, corpus.by_id)

    strict_set = build_observations(match.strict_pairs, assigned)
    loose_set = build_observations(match.pairs, assigned) if match.loose_pairs else None

    live_only_events = [
        assigned[entry.order_id] for entry in match.live_only if entry.order_id in assigned
    ]
    ambiguous_events = [
        assigned[item.entry.order_id] for item in match.ambiguous if item.entry.order_id in assigned
    ]
    backtest_only_expected_gross = sum_decimals(
        [trade.expected_gross for trade in match.backtest_only]
    )
    live_only_actual_net = sum_decimals(
        [event.closed_pnl for event in live_only_events + ambiguous_events]
    )
    ledger_only_net = sum_decimals([event.closed_pnl for event in unassigned])

    # ★flatten 계상은 orders 가 아니라 exits(dedup) 기준이다 (R8) — 실측에서 3 event 중
    #   2 건이 orders 에 아예 없었다.
    flatten_order_ids = {order.order_id for order in corpus.manual_flatten}
    flatten_events: list[LedgerRow] = []
    flatten_from_order = 0
    flatten_orphan = 0
    for event in events:
        order = linked.get(event.exit_id)
        if order is not None and order.order_id in flatten_order_ids:
            flatten_events.append(event)
            flatten_from_order += 1
        elif order is None and event.order_link_id is not None:
            # link 는 있는데 orders 에 없다 = 우리가 기록하지 못한 청산.
            flatten_events.append(event)
            flatten_orphan += 1

    ledger_quantity_mismatch = sum(
        1
        for event in events
        if (order := linked.get(event.exit_id)) is not None
        and event.closed_size is not None
        and order.filled_quantity is not None
        and Decimal(str(event.closed_size)) != Decimal(str(order.filled_quantity))
    )

    buckets = ParityBuckets(
        expected_only_count=len(match.backtest_only),
        expected_only_gross=backtest_only_expected_gross,
        # 이 셋은 라이브 **이벤트** 상태 축이라 백테스트 대조에는 모집단이 없다.
        # 0 은 "없다" 가 아니라 "이 축을 재지 않는다" 이므로 보고서에 그렇게 적는다.
        expected_only_pending_count=0,
        expected_only_failed_count=0,
        expected_only_dispatched_count=0,
        actual_only_count=len(live_only_events) + len(ambiguous_events),
        actual_only_net=live_only_actual_net,
        ledger_only_count=len(unassigned),
        ledger_only_net=ledger_only_net,
        inferred_attribution_count=sum(
            1 for event in events if event.attribution_confidence == "inferred"
        ),
    )
    summary = summarize_parity(strict_set.observations, buckets)
    loose_summary = summarize_parity(loose_set.observations, buckets) if loose_set else None

    matched_trades = [pair.trade for pair in match.strict_pairs]
    return Decomposition(
        summary=summary,
        observation_set=strict_set,
        loose_summary=loose_summary,
        loose_observation_set=loose_set,
        strict_pairs=len(match.strict_pairs),
        loose_pairs=len(match.loose_pairs),
        ambiguous=len(match.ambiguous),
        backtest_only_expected_gross=backtest_only_expected_gross,
        live_only_actual_net=live_only_actual_net,
        ledger_only_net=ledger_only_net,
        backtest_cost_matched=sum_decimals([trade.backtest_cost for trade in matched_trades]),
        backtest_fee_paid=_optional_sum([trade.fee_paid for trade in matched_trades]),
        backtest_slippage_paid=_optional_sum([trade.slippage_paid for trade in matched_trades]),
        flatten_events=flatten_events,
        flatten_from_order=flatten_from_order,
        flatten_orphan=flatten_orphan,
        ledger_only_count=len(unassigned),
        ledger_quantity_mismatch=ledger_quantity_mismatch,
        partial_fill_count=sum(1 for entry in corpus.entries if entry.partially_filled),
    )


# --------------------------------------------------------------------------
# 세션 경계 회계 (R5 · R8)
# --------------------------------------------------------------------------


def session_boundary_accounting(
    windows: Sequence[SessionWindow],
    *,
    corpus: OrderCorpus,
    dedup: LedgerDedup,
    trades: Sequence[BacktestTrade],
    match: MatchResult,
    assigned: Mapping[str, LedgerRow],
) -> dict[str, Any]:
    """세션 경계에서 새는 것들을 **총계에 접지 않고** 버킷으로 병기한다.

    ★귀속 기본값은 **청산시각**이다. 반전 전략이라 진입창과 청산창이 갈리는 event 가
    실재하고(실측 6건, 그중 1건은 세션 사이 2.74h 무세션 구간을 통과했다), 어느 쪽으로
    귀속하느냐로 세션 단위 합계가 흔들린다 — 그 차이를 숨기지 않고 함께 낸다.
    """
    carry = [
        {
            "session_id": window.session_id,
            "start": _iso(window.start),
            "end": _iso(window.end),
            "live_net_at_start": decimal_text(net_position_at(corpus.all_orders, window.start)),
            "live_net_at_end": (
                decimal_text(net_position_at(corpus.all_orders, window.end))
                if window.end is not None
                else None
            ),
            "backtest_open_at_start": decimal_text(open_backtest_position_at(trades, window.start)),
            "backtest_open_at_end": (
                decimal_text(open_backtest_position_at(trades, window.end))
                if window.end is not None
                else None
            ),
        }
        for window in windows
    ]

    unattributed_orders = [
        order
        for order in corpus.all_orders
        if order.filled_at is not None and window_of(order.filled_at, windows) is None
    ]
    unattributed_events = [
        event for event in dedup.events if window_of(event.exchange_created_at, windows) is None
    ]
    gap_events = [
        event for event in dedup.events if is_between_windows(event.exchange_created_at, windows)
    ]

    cross_window: list[dict[str, Any]] = []
    by_exit_window: dict[str, Decimal] = {}
    by_entry_window: dict[str, Decimal] = {}
    for pair in match.pairs:
        event = assigned.get(pair.entry.order_id)
        if event is None or pair.entry.bar_epoch is None:
            continue
        entry_moment = datetime.fromtimestamp(pair.entry.bar_epoch, tz=UTC)
        entry_window = window_of(entry_moment, windows)
        exit_window = window_of(event.exchange_created_at, windows)
        net = Decimal(str(event.closed_pnl))
        # 기본 귀속 = 청산시각.
        exit_key = exit_window or "__outside__"
        entry_key = entry_window or "__outside__"
        by_exit_window[exit_key] = Decimal(str(by_exit_window.get(exit_key, Decimal("0")))) + net
        by_entry_window[entry_key] = (
            Decimal(str(by_entry_window.get(entry_key, Decimal("0")))) + net
        )
        if entry_window != exit_window:
            cross_window.append(
                {
                    "order_id": pair.entry.order_id,
                    "entry_session": entry_window,
                    "exit_session": exit_window,
                    "held_seconds": int((event.exchange_created_at - entry_moment).total_seconds()),
                    "closed_pnl": decimal_text(net),
                }
            )

    session_keys = sorted(set(by_exit_window) | set(by_entry_window))
    deltas = [
        abs(
            Decimal(str(by_exit_window.get(key, Decimal("0"))))
            - Decimal(str(by_entry_window.get(key, Decimal("0"))))
        )
        for key in session_keys
    ]
    return {
        "attribution_rule": "exit_time",
        "sessions": len(windows),
        "carry": carry,
        "unattributed": {
            "orders": len(unattributed_orders),
            "ledger_events": len(unattributed_events),
            "ledger_net": decimal_text(
                sum_decimals([event.closed_pnl for event in unattributed_events])
            ),
        },
        "gap_exit": {
            "count": len(gap_events),
            "net": decimal_text(sum_decimals([event.closed_pnl for event in gap_events])),
            "exit_ids": [event.exit_id for event in gap_events],
        },
        "cross_window": {
            "count": len(cross_window),
            "events": cross_window,
        },
        "attribution_sensitivity": {
            "by_exit_window": {key: decimal_text(value) for key, value in by_exit_window.items()},
            "by_entry_window": {key: decimal_text(value) for key, value in by_entry_window.items()},
            "max_abs_session_delta": decimal_text(max(deltas)) if deltas else None,
        },
    }


def _sample_payload(summary: ParitySummary) -> dict[str, Any]:
    return {
        "n": summary.sample.n,
        "mean_net": decimal_text(summary.sample.mean_net),
        "sd_net": decimal_text(summary.sample.sd_net),
        "required_n": summary.sample.required_n,
        "sufficient": summary.sample.sufficient,
    }


def coverage_payload(decomposition: Decomposition) -> dict[str, Any]:
    """분해 가능 관측이 매칭 전체에서 차지하는 비중 (R4) — 건수와 금액 양쪽.

    ★금액은 **절대값 합** 기준이다. 부호합으로 재면 서로 지워 분모가 0 근처로 가고
    커버리지가 폭발한다 (R3 이 비율에서 지적한 것과 같은 함정).
    """
    summary = decomposition.summary
    observations = decomposition.observation_set.observations
    matched_abs = sum_decimals([abs(item.actual_net) for item in observations])
    decomposable_abs = sum_decimals(
        [abs(item.actual_net) for item in observations if item.actual_gross is not None]
    )
    count_pct = (
        None
        if summary.matched_count == 0
        else Decimal(summary.decomposable_count) / Decimal(summary.matched_count) * Decimal("100")
    )
    return {
        "matched_count": summary.matched_count,
        "decomposable_count": summary.decomposable_count,
        "decomposable_count_pct": decimal_text(count_pct),
        "matched_abs_net": decimal_text(matched_abs),
        "decomposable_abs_net": decimal_text(decomposable_abs),
        "decomposable_abs_net_pct": decimal_text(
            _ratio(decomposable_abs * Decimal("100"), matched_abs)
        ),
    }


def build_report(
    decomposition: Decomposition,
    match: MatchResult,
    *,
    windows: Sequence[SessionWindow],
    sessions_raw: Any,
    corpus: OrderCorpus,
    dedup: LedgerDedup,
    trades: Sequence[BacktestTrade],
) -> dict[str, Any]:
    """report.json 본문. 표본 N · 시각 범위 · 버킷 계상 · 4단 워터폴을 모두 싣는다."""
    summary = decomposition.summary
    assigned, _ = attribute_ledger_rows(corpus.entries, dedup.events)
    entry_times = [trade.entry_time for trade in trades]
    ledger_times = [event.exchange_created_at for event in dedup.events]
    live_entries = [pair.entry for pair in match.pairs] + list(match.live_only)
    live_bar_epochs = [entry.bar_epoch for entry in live_entries if entry.bar_epoch is not None]

    return {
        "sessions": [
            {"id": window.session_id, "start": _iso(window.start), "end": _iso(window.end)}
            for window in windows
        ],
        "session_raw": sessions_raw,
        "inputs": {
            # ★dedup 전/후를 둘 다 남긴다 — 순진한 Σ 가 2배가 되는 자리다 (R6).
            "ledger_rows_in": dedup.rows_in,
            "ledger_events": len(dedup.events),
            "ledger_rows_dropped": dedup.rows_dropped,
            "ledger_duplicate_groups": dedup.duplicate_groups,
            "orders_in": len(corpus.all_orders),
            "live_entries": len(corpus.entries),
            "entry_kinds": {
                kind: sum(1 for entry in corpus.entries if entry.kind == kind)
                for kind in sorted({entry.kind for entry in corpus.entries})
            },
            "manual_flatten_orders": len(corpus.manual_flatten),
            "backtest_trades": len(trades),
        },
        "sample": {
            "strict_pairs": decomposition.strict_pairs,
            "loose_pairs": decomposition.loose_pairs,
            "ambiguous": decomposition.ambiguous,
            "realized_observations": summary.matched_count,
            "unrealized_pairs": decomposition.observation_set.unrealized,
            "decomposable_observations": summary.decomposable_count,
            "undecomposed_observations": summary.undecomposed_count,
            "partial_fill_entries": decomposition.partial_fill_count,
            "ledger_quantity_mismatch": decomposition.ledger_quantity_mismatch,
            "match_coverage_pct": decimal_text(summary.match_coverage_pct),
            "net_sample": _sample_payload(summary),
        },
        "time_range": {
            "backtest_first_entry": _iso(min(entry_times)) if entry_times else None,
            "backtest_last_entry": _iso(max(entry_times)) if entry_times else None,
            "live_first_signal_bar": (
                _iso(datetime.fromtimestamp(min(live_bar_epochs), tz=UTC))
                if live_bar_epochs
                else None
            ),
            "live_last_signal_bar": (
                _iso(datetime.fromtimestamp(max(live_bar_epochs), tz=UTC))
                if live_bar_epochs
                else None
            ),
            "ledger_first": _iso(min(ledger_times)) if ledger_times else None,
            "ledger_last": _iso(max(ledger_times)) if ledger_times else None,
        },
        "matching": {
            "grade": {"strict": decomposition.strict_pairs, "loose": decomposition.loose_pairs},
            "ambiguous": [
                {
                    "order_id": item.entry.order_id,
                    "reason": item.reason,
                    "candidate_trade_indexes": item.candidate_trade_indexes,
                }
                for item in match.ambiguous
            ],
            # ★가격은 판별자가 아니라 매칭 뒤 잔차다 (R7).
            "price_residual": price_residuals(match.pairs),
        },
        "buckets": {
            "matched": {
                "strict": decomposition.strict_pairs,
                "loose": decomposition.loose_pairs,
                "realized": summary.matched_count,
                "unrealized": decomposition.observation_set.unrealized,
                "expected_gross": decimal_text(summary.expected_gross),
                "actual_net": decimal_text(summary.actual_net),
            },
            "backtest_only": {
                "count": len(match.backtest_only),
                "expected_gross": decimal_text(decomposition.backtest_only_expected_gross),
                "trade_indexes": [trade.trade_index for trade in match.backtest_only],
            },
            "live_only": {
                "count": len(match.live_only),
                "realized_count": summary.buckets.actual_only_count,
                "actual_net": decimal_text(decomposition.live_only_actual_net),
                "order_ids": [entry.order_id for entry in match.live_only],
            },
            "manual_flatten": {
                # ★orders 가 아니라 exits(dedup) 기준이다 (R8).
                "count": len(decomposition.flatten_events),
                "from_order": decomposition.flatten_from_order,
                "orphan_in_exits_only": decomposition.flatten_orphan,
                "net": decimal_text(
                    sum_decimals([event.closed_pnl for event in decomposition.flatten_events])
                ),
            },
            "ledger_only": {
                "count": decomposition.ledger_only_count,
                "net": decimal_text(decomposition.ledger_only_net),
                "inferred_attribution_count": summary.buckets.inferred_attribution_count,
            },
        },
        "session_accounting": session_boundary_accounting(
            windows,
            corpus=corpus,
            dedup=dedup,
            trades=trades,
            match=match,
            assigned=assigned,
        ),
        "waterfall": {
            "note": (
                "1단→4단은 **strict 매칭 중 분해 가능한 관측**만으로 닫힌다. 존재 격차와 "
                "세션 경계 버킷은 별도 항목이며 가격 격차에 더하지 않는다."
            ),
            "stage_1_expected_gross": decimal_text(summary.decomposable_expected_gross),
            "stage_2_execution_gap": {
                "price_gap": decimal_text(summary.execution_gap),
                "existence_gap": {
                    "backtest_only_expected_gross": decimal_text(
                        decomposition.backtest_only_expected_gross
                    ),
                    "live_only_actual_net": decimal_text(decomposition.live_only_actual_net),
                    "ledger_only_net": decimal_text(decomposition.ledger_only_net),
                },
            },
            "stage_3_cost": {
                "backtest_cost_matched": decimal_text(decomposition.backtest_cost_matched),
                "backtest_fee_paid": decimal_text(decomposition.backtest_fee_paid),
                "backtest_slippage_paid": decimal_text(decomposition.backtest_slippage_paid),
                "live_derived_cost": decimal_text(summary.cost),
                "effective_cost_pct_round_trip": decimal_text(
                    summary.effective_cost_pct_round_trip
                ),
                "explanation_ratio": cost_explanation(decomposition.observation_set),
            },
            "stage_4_actual_net": decimal_text(summary.decomposable_actual_net),
            "undecomposed_net": decimal_text(summary.undecomposed_net),
        },
        "coverage": coverage_payload(decomposition),
        "loose_sensitivity": (
            None
            if decomposition.loose_summary is None or decomposition.loose_observation_set is None
            else {
                "note": "판정은 strict 만으로 한다. 이 블록은 loose 를 넣었을 때의 감도다.",
                "matched_count": decomposition.loose_summary.matched_count,
                "stage_1_expected_gross": decimal_text(
                    decomposition.loose_summary.decomposable_expected_gross
                ),
                "price_gap": decimal_text(decomposition.loose_summary.execution_gap),
                "live_derived_cost": decimal_text(decomposition.loose_summary.cost),
                "stage_4_actual_net": decimal_text(
                    decomposition.loose_summary.decomposable_actual_net
                ),
                "explanation_ratio": cost_explanation(decomposition.loose_observation_set),
            }
        ),
    }


# --------------------------------------------------------------------------
# `run` — 엔진 직접 재실행
# --------------------------------------------------------------------------

# trades.json 에 싣는 RawTrade 필드 전부 (bar_index 는 시각과 함께 보존한다).
_RAW_TRADE_DECIMAL_FIELDS = (
    "entry_price",
    "exit_price",
    "size",
    "pnl",
    "return_pct",
    "fees",
    "fee_paid",
    "slippage_paid",
    "runup_abs",
    "runup_pct",
    "drawdown_abs",
    "drawdown_pct",
    "cumulative_pnl",
)


def _enum_text(value: Any) -> str | None:
    if value is None:
        return None
    return str(getattr(value, "value", value))


def trades_digest(trades: Sequence[Mapping[str, Any]]) -> str:
    """거래 목록의 sha256. 키 정렬 + 구분자 고정이라 표현에 흔들리지 않는다."""
    blob = json.dumps(trades, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


# `strategy_state._can_afford_entry` 가 거절할 때 남기는 경고의 표지.
MARGIN_SKIP_MARKER = "증거금 부족"


def summarize_warnings(warnings: Sequence[str]) -> dict[str, Any]:
    """엔진 경고를 세어 둔다 — 특히 증거금 거절은 **거짓 0** 의 원인이다.

    ★`leverage > 1` 이면 `strategy_state` 의 격리 증거금 게이트가 켜진다
    (`is_leverage_active`). 기본 사이징은 `qty=1.0`(=1 BTC)이고 `init_cash` 는 10,000
    이라, BTC 가격에서는 `required_margin = price / leverage` 가 자본을 넘어 **모든 진입이
    거절된다**. 엔진은 `status="ok"` 에 `trades=[]` 를 돌려주므로 겉보기엔 정상이다.
    """
    margin_skips = sum(1 for warning in warnings if MARGIN_SKIP_MARKER in warning)
    return {
        "total": len(warnings),
        "margin_insufficient": margin_skips,
        "sample": sorted(set(warnings))[:5],
    }


def _run_backtest(
    *,
    source: str,
    ohlcv_csv: Path,
    freq: str,
    leverage: float,
    start: datetime | None,
    end: datetime | None,
    init_cash: Decimal | None = None,
    live_position_size_pct: float | None = None,
) -> dict[str, Any]:
    """엔진을 돌려 trades.json 본문을 만든다 (무거운 import 는 여기서만).

    ★사이징은 라이브 미러 tier 로 준다 (R9). `live_position_size_pct` 를 넘기면
    `compat.parse_and_run_v2` 가 `("strategy.percent_of_equity", pct)` 로
    `configure_sizing` 을 호출한다. `sizing_source`/`sizing_basis` 는 `config_mapper` 의
    라이브 미러 조합과 같은 값을 쓴다 — leverage 는 수량이 아니라 증거금 게이트에만 든다
    (레포의 「Nx reject · leverage_basis 1.0」 규약).
    """
    import pandas as pd

    from src.backtest.engine.types import BacktestConfig
    from src.backtest.engine.v2_adapter import run_backtest_v2

    frame = pd.read_csv(ohlcv_csv, parse_dates=["timestamp"])
    ohlcv = frame.set_index("timestamp")
    # ★tz 를 여기서 못박는다. naive index 를 그대로 두면 `_iso` 의 `astimezone` 이 그것을
    #   **로컬 시각**으로 해석해 봉 귀속이 통째로 시간대만큼 밀린다.
    if getattr(ohlcv.index, "tz", None) is None:
        ohlcv.index = pd.DatetimeIndex(ohlcv.index).tz_localize("UTC")
    config = BacktestConfig(freq=freq, leverage=leverage)
    if init_cash is not None:
        config = replace(config, init_cash=init_cash)
    if live_position_size_pct is not None:
        config = replace(
            config,
            live_position_size_pct=live_position_size_pct,
            sizing_source="live",
            sizing_basis="live_available_balance_approx_equity",
        )
    outcome = run_backtest_v2(source, ohlcv, config=config)
    if outcome.status != "ok" or outcome.result is None:
        raise RuntimeError(f"백테스트 실패: status={outcome.status} error={outcome.error}")

    index = list(ohlcv.index)

    def _bar_time(bar_index: int | None) -> str | None:
        if bar_index is None or bar_index < 0 or bar_index >= len(index):
            return None
        return _iso(index[bar_index].to_pydatetime())

    rows: list[dict[str, Any]] = []
    for trade in outcome.result.trades:
        row: dict[str, Any] = {
            "trade_index": trade.trade_index,
            "direction": trade.direction,
            "status": trade.status,
            "entry_bar_index": trade.entry_bar_index,
            "exit_bar_index": trade.exit_bar_index,
            "entry_time": _bar_time(trade.entry_bar_index),
            "exit_time": _bar_time(trade.exit_bar_index),
            "bars_in_trade": trade.bars_in_trade,
            "comment": trade.comment,
            "exit_kind": _enum_text(trade.exit_kind),
            "liquidated": trade.liquidated,
        }
        for field_name in _RAW_TRADE_DECIMAL_FIELDS:
            row[field_name] = decimal_text(getattr(trade, field_name, None))
        rows.append(row)

    total_rows = len(rows)
    if start is not None or end is not None:
        rows = [
            row
            for row in rows
            if row["entry_time"] is not None
            and (start is None or datetime.fromisoformat(row["entry_time"]) >= start)
            and (end is None or datetime.fromisoformat(row["entry_time"]) < end)
        ]

    metrics = outcome.result.metrics
    metrics_summary = {
        name: decimal_text(value) if isinstance(value, Decimal) else value
        for name, value in (
            ("num_trades", metrics.num_trades),
            ("total_return", metrics.total_return),
            ("net_profit_abs", metrics.net_profit_abs),
            ("total_fees", metrics.total_fees),
            ("total_slippage", metrics.total_slippage),
            ("max_drawdown", metrics.max_drawdown),
            ("win_rate", metrics.win_rate),
            ("profit_factor", metrics.profit_factor),
            ("sharpe_ratio", metrics.sharpe_ratio),
        )
    }
    return {
        "ohlcv_csv": str(ohlcv_csv),
        "freq": freq,
        "leverage": leverage,
        "sizing": {
            "init_cash": decimal_text(Decimal(str(config.init_cash))),
            "live_position_size_pct": config.live_position_size_pct,
            "sizing_source": config.sizing_source,
            "sizing_basis": config.sizing_basis,
        },
        "bars": len(index),
        "bar_first": _iso(index[0].to_pydatetime()) if index else None,
        "bar_last": _iso(index[-1].to_pydatetime()) if index else None,
        "scoring_window": {"start": _iso(start), "end": _iso(end)},
        # ★`leverage > 1` 은 격리 증거금 게이트를 켠다 — 0 건이면 여기를 먼저 봐라.
        "warnings": summarize_warnings(list(getattr(outcome.parse, "warnings", []) or [])),
        "trades_total": total_rows,
        "trades_in_window": len(rows),
        # ★metrics 는 **전 구간** 실행 결과다. `trades` 는 채점 창으로 잘린다 —
        #   둘을 합산해 비교하지 마라.
        "metrics": metrics_summary,
        "trades": rows,
        "trades_digest": trades_digest(rows),
    }


# --------------------------------------------------------------------------
# `s1diff` — 스팟/perp 진입가 차
# --------------------------------------------------------------------------


def median_decimal(values: Sequence[Decimal]) -> Decimal | None:
    """짝수 개면 가운데 둘의 평균. Decimal 영역에서만 계산한다."""
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[middle]
    return (Decimal(str(ordered[middle - 1])) + Decimal(str(ordered[middle]))) / Decimal("2")


def _bar_epoch_of(trade: BacktestTrade, *, bar_seconds: int) -> int:
    epoch = int(trade.entry_time.timestamp())
    return (epoch // bar_seconds) * bar_seconds


def pair_by_signal_bar(
    spot: Sequence[BacktestTrade],
    perp: Sequence[BacktestTrade],
    *,
    bar_seconds: int,
) -> list[tuple[BacktestTrade, BacktestTrade]]:
    """같은 신호봉에 양쪽 다 진입한 쌍. 한 봉에 여러 건이면 순서대로 짝짓는다."""
    spot_by_bar: dict[int, list[BacktestTrade]] = {}
    for trade in sorted(spot, key=lambda t: (t.entry_time, t.trade_index)):
        spot_by_bar.setdefault(_bar_epoch_of(trade, bar_seconds=bar_seconds), []).append(trade)
    perp_by_bar: dict[int, list[BacktestTrade]] = {}
    for trade in sorted(perp, key=lambda t: (t.entry_time, t.trade_index)):
        perp_by_bar.setdefault(_bar_epoch_of(trade, bar_seconds=bar_seconds), []).append(trade)

    pairs: list[tuple[BacktestTrade, BacktestTrade]] = []
    for bar in sorted(set(spot_by_bar) & set(perp_by_bar)):
        pairs.extend(zip(spot_by_bar[bar], perp_by_bar[bar], strict=False))
    return pairs


def instrument_stats(trades: Sequence[BacktestTrade]) -> dict[str, Any]:
    """계기 하나의 진입 수 · net_profit_abs · 비용 합."""
    fee_values = [t.fee_paid for t in trades]
    slip_values = [t.slippage_paid for t in trades]
    return {
        "entries": len(trades),
        "net_profit_abs": decimal_text(sum_decimals([t.pnl for t in trades])),
        "cost_total": decimal_text(sum_decimals([t.fees for t in trades])),
        "fee_paid_total": (
            decimal_text(sum_decimals([v for v in fee_values if v is not None]))
            if trades and all(v is not None for v in fee_values)
            else None
        ),
        "slippage_paid_total": (
            decimal_text(sum_decimals([v for v in slip_values if v is not None]))
            if trades and all(v is not None for v in slip_values)
            else None
        ),
    }


def build_s1diff(
    spot: Sequence[BacktestTrade],
    perp: Sequence[BacktestTrade],
    *,
    bar_seconds: int,
) -> dict[str, Any]:
    """`spot_entry − perp_entry` 분포 + 계기별 요약.

    ★쌍이 0 이면 `undetermined` 다. 격차 0 으로 출력하면 "차이가 없다" 로 읽히는데
    실제로는 "잴 표본이 없다" 이다 — 그 둘은 다르다.
    """
    pairs = pair_by_signal_bar(spot, perp, bar_seconds=bar_seconds)
    diffs = [
        Decimal(str(spot_trade.entry_price)) - Decimal(str(perp_trade.entry_price))
        for spot_trade, perp_trade in pairs
    ]
    payload: dict[str, Any] = {
        "bar_seconds": bar_seconds,
        "pairs": {
            "n": len(diffs),
            "verdict": "measured" if diffs else "undetermined",
            "median_spot_minus_perp": decimal_text(median_decimal(diffs)),
            "min_spot_minus_perp": decimal_text(min(diffs)) if diffs else None,
            "max_spot_minus_perp": decimal_text(max(diffs)) if diffs else None,
            "sign": {
                "positive": sum(1 for d in diffs if d > 0),
                "negative": sum(1 for d in diffs if d < 0),
                "zero": sum(1 for d in diffs if d == 0),
            },
        },
        "instruments": {
            "spot": instrument_stats(spot),
            "perp": instrument_stats(perp),
        },
    }
    return payload


# --------------------------------------------------------------------------
# CLI — 얇게. 로직은 위의 순수 함수가 전부 갖는다.
# --------------------------------------------------------------------------


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _trades_of(payload: Any) -> list[BacktestTrade]:
    """`run` 산출 파일 또는 거래 배열 어느 쪽이든 받는다."""
    rows = payload["trades"] if isinstance(payload, dict) else payload
    return parse_backtest_trades(rows)


def _cmd_run(args: argparse.Namespace) -> int:
    source = Path(args.pine_source).read_text(encoding="utf-8")
    payload = _run_backtest(
        source=source,
        ohlcv_csv=Path(args.ohlcv_csv),
        freq=args.freq,
        leverage=args.leverage,
        start=to_datetime(args.start),
        end=to_datetime(args.end),
        init_cash=args.init_cash,
        live_position_size_pct=args.live_position_size_pct,
    )
    if payload["trades_total"] == 0 and not args.allow_empty_trades:
        # ★거래 0 건짜리 trades.json 을 쓰면 뒤의 `match` 가 "라이브에만 있다" 를 잔뜩
        #   보고하고, 그건 진짜 발견처럼 읽힌다. 그러니 여기서 파일을 안 쓴다.
        sys.stderr.write("REFUSED — 거래 0 건이라 파일을 쓰지 않는다.\n")
        margin_skips = int(payload["warnings"]["margin_insufficient"])
        if margin_skips:
            sys.stderr.write(
                f"  원인: 격리 증거금 게이트가 진입 {margin_skips}건을 거절했다"
                f" (leverage={payload['leverage']}).\n"
                "  leverage > 1 이면 `strategy_state._can_afford_entry` 가 켜지는데,\n"
                "  기본 사이징은 qty=1.0 (=1 BTC) 이고 init_cash 는 10,000 이라\n"
                "  required_margin = price / leverage 가 자본을 넘어 전건 거절된다.\n"
                "  → 라이브 미러로 돌려라:"
                " --init-cash <세션 baseline> --live-position-size-pct 1.0\n"
            )
        sys.stderr.write("  의도한 0 건이면 --allow-empty-trades 를 붙여라.\n")
        return 1
    _write_json(Path(args.out), payload)
    print(
        f"[run] trades={payload['trades_in_window']}/{payload['trades_total']} "
        f"digest={payload['trades_digest']}"
    )
    return 0


def _session_interval(sessions_raw: Any) -> str:
    """세션들이 같은 봉 간격이어야 한다 — 다르면 봉 창을 하나로 못 잡는다."""
    rows = sessions_raw if isinstance(sessions_raw, list) else [sessions_raw]
    intervals = {str(row["interval"]) for row in rows}
    if len(intervals) != 1:
        raise ValueError(f"세션들의 interval 이 갈린다: {sorted(intervals)}")
    return intervals.pop()


def _cmd_match(args: argparse.Namespace) -> int:
    sessions_raw = _read_json(Path(args.session))
    windows = parse_sessions(sessions_raw)
    trades = _trades_of(_read_json(Path(args.trades)))
    corpus = parse_orders(
        _read_json(Path(args.orders)),
        session_ids=[UUID(window.session_id) for window in windows],
    )
    # ★합산 전에 dedup — 한 청산이 2행으로 온다 (R6).
    dedup = dedupe_ledger_rows(parse_ledger_rows(_read_json(Path(args.exits))))
    bar_seconds = interval_seconds(_session_interval(sessions_raw))

    match = match_entries(trades, corpus.entries, bar_seconds=bar_seconds)
    decomposition = decompose(match, corpus=corpus, dedup=dedup)
    report = build_report(
        decomposition,
        match,
        windows=windows,
        sessions_raw=sessions_raw,
        corpus=corpus,
        dedup=dedup,
        trades=trades,
    )
    _write_json(Path(args.out), report)
    print(
        f"[match] strict={decomposition.strict_pairs} loose={decomposition.loose_pairs} "
        f"ambiguous={decomposition.ambiguous} "
        f"backtest_only={len(match.backtest_only)} live_only={len(match.live_only)} "
        f"ledger_events={len(dedup.events)}/{dedup.rows_in}"
    )
    return 0


def _cmd_s1diff(args: argparse.Namespace) -> int:
    spot = _trades_of(_read_json(Path(args.spot)))
    perp = _trades_of(_read_json(Path(args.perp)))
    payload = build_s1diff(spot, perp, bar_seconds=args.bar_seconds)
    _write_json(Path(args.out), payload)
    print(f"[s1diff] n={payload['pairs']['n']} verdict={payload['pairs']['verdict']}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="백테스트↔라이브 4단 대조 (btgap).")
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="엔진 재실행 → trades.json")
    run_parser.add_argument("--pine-source", required=True)
    run_parser.add_argument("--ohlcv-csv", required=True)
    run_parser.add_argument("--freq", default="1m")
    run_parser.add_argument("--leverage", type=float, default=2.0)
    run_parser.add_argument(
        "--init-cash",
        type=Decimal,
        default=None,
        help="BacktestConfig.init_cash (세션 equity baseline 을 넣어라)",
    )
    run_parser.add_argument(
        "--live-position-size-pct",
        type=float,
        default=None,
        help="라이브 미러 사이징 %% (StrategySettings.position_size_pct 와 같은 값)",
    )
    run_parser.add_argument("--start", default=None, help="채점 창 시작 ISO8601 (포함)")
    run_parser.add_argument("--end", default=None, help="채점 창 끝 ISO8601 (배타)")
    run_parser.add_argument(
        "--allow-empty-trades",
        action="store_true",
        help="거래 0 건도 산출물로 인정한다 (기본은 거부 — 거짓 0 차단)",
    )
    run_parser.add_argument("--out", required=True)
    run_parser.set_defaults(handler=_cmd_run)

    match_parser = sub.add_parser("match", help="4단 분해 → report.json")
    match_parser.add_argument("--trades", required=True)
    match_parser.add_argument("--orders", required=True)
    match_parser.add_argument("--exits", required=True)
    match_parser.add_argument("--session", required=True)
    match_parser.add_argument("--out", required=True)
    match_parser.set_defaults(handler=_cmd_match)

    s1_parser = sub.add_parser("s1diff", help="스팟/perp 진입가 차 → s1.json")
    s1_parser.add_argument("--spot", required=True)
    s1_parser.add_argument("--perp", required=True)
    s1_parser.add_argument("--bar-seconds", type=int, default=60)
    s1_parser.add_argument("--out", required=True)
    s1_parser.set_defaults(handler=_cmd_s1diff)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    handler: Any = args.handler
    result: int = handler(args)
    return result


if __name__ == "__main__":
    sys.exit(main())

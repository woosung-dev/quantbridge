#!/usr/bin/env python
# btgap — 같은 구간의 백테스트 시뮬과 라이브 원장을 4단으로 분해해 대조한다
"""소크(데모 라이브) 원장과 같은 구간 백테스트를 처음으로 나란히 놓는다.

## 서브커맨드 셋

| 명령        | 하는 일                                                                    |
| ----------- | -------------------------------------------------------------------------- |
| `run`       | 얼린 OHLCV 로 엔진을 직접 재실행해 `trades.json` + digest 를 만든다        |
| `match`     | `trades.json` × 라이브 원장을 **4단 분해**해 `report.json` 을 만든다       |
| `replay`    | 롤링 창 × `run_live` 로 **라이브 프로토콜**을 재생해 진입 집합 R 을 낸다   |
| `entrysets` | B · R · L 세 진입 집합 중 **둘**을 정규화해 쌍별로 맞춘다                  |
| `s1diff`    | 스팟/perp 두 `trades.json` 의 같은 신호봉 진입가 차 분포를 낸다            |

## `run` 과 `replay` 는 **같은 엔진을 다른 프로토콜로** 돌린다

`run` 은 전 구간을 한 번에 돌린다(백테스트). `replay` 는 매 봉마다 직전 300봉만 잘라
`run_live` 를 다시 돌린다(라이브). 그 차이 하나가 「롤링 워밍업의 몫」이고, 그것을
재려고 `replay` 가 있다. 그래서 `replay` 는 **원장 인자 4종을 넘기지 않는다** —
넘기면 재는 대상이 「롤링 창」에서 「롤링 창 + 원장 체결 권한」으로 바뀐다.

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

# ★귀속 판별자의 합격선 (%). 근거는 `entry_price_agreement` docstring — 틀린 귀속의
# 실측 신호(median 0.0716%)의 1/7.2 이고, 옳은 귀속은 실측상 정확히 0 이어야 한다.
ATTRIBUTION_AGREEMENT_TOLERANCE_PCT = Decimal("0.01")


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
        """백테스트가 뺀 비용. ★정의는 **하나뿐이다** — 결합 필드 `fees`.

        `fee_paid + slippage_paid` 로 재는 두 번째 정의를 두면 합계 마지막 자리에서
        두 값이 갈리고, 그때 어느 쪽이 정본인지 아무도 모른다. 분해가 필요하면
        `fee_paid`/`slippage_paid` 를 따로 보고 `split_residual` 로 어긋남을 본다.
        """
        return Decimal(str(self.fees))


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


def _assert_duplicates_agree(group: Sequence[LedgerRow]) -> None:
    """같은 `order_link_id` 의 두 행은 payload 가 **같아야** 한다.

    ★그 전제 위에서 「아무 행이나 대표로 올린다」가 성립한다. 검사 없이 승격하면
    payload 가 갈렸을 때 어느 값이 살아남는지가 `classification` 정렬 운에 달린다 —
    조용히 틀린 손익을 고르는 fail-**open** 이다. 그래서 여기서 크게 실패한다.
    """
    first = group[0]
    for other in group[1:]:
        differing = [
            field
            for field in ("closed_pnl", "closed_size", "avg_entry_price", "avg_exit_price", "side")
            if getattr(first, field) != getattr(other, field)
        ]
        if differing:
            raise ValueError(
                f"같은 order_link_id({first.order_link_id!r}) 의 중복 행이 서로 다르다 — "
                f"{first.exit_id} vs {other.exit_id}, 어긋난 필드: {differing}"
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
            _assert_duplicates_agree(group)
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


@dataclass(frozen=True, slots=True)
class LedgerAttribution:
    """원장 event 가 어느 진입의 결과인가 — 그리고 **무엇을 근거로** 그렇게 봤나.

    근거를 값으로 들고 다니는 이유는 하나다: `linked` 와 `inferred` 는 신뢰도가 다르고,
    `inferred` 를 매칭 합계에 넣으면 그 차이가 사라진다.
    """

    linked: dict[str, LedgerRow]  # opener order_id → event (링크의 직전 진입)
    inferred: dict[str, LedgerRow]  # opener order_id → event (FIFO 추정)
    non_entry_linked: list[LedgerRow]  # 사슬에 꽂을 수 없는 주문에 직결된 event
    no_predecessor: list[LedgerRow]  # 사슬에 꽂았는데 앞이 없는 event
    unattributed: list[LedgerRow]  # 어디에도 못 붙은 event
    # exit_id → "linked" | "linked_via_flatten" | "inferred"
    #         | "no_predecessor" | "non_entry" | "none"
    grade_of: dict[str, str]
    link_collisions: int

    @property
    def via_flatten(self) -> int:
        return sum(1 for grade in self.grade_of.values() if grade == "linked_via_flatten")


def _opener_of(
    target: LiveOrder,
    chain: Sequence[LiveEntry],
    index_of: Mapping[str, int],
) -> tuple[LiveEntry | None, str]:
    """링크된 주문이 **닫은** 포지션을 연 진입. 두 번째 값은 근거 등급이다.

    | 등급                 | 뜻                                                     |
    | -------------------- | ------------------------------------------------------ |
    | `linked`             | 링크가 진입이라 사슬에서 직전 진입을 집었다            |
    | `linked_via_flatten` | 링크가 사슬 밖 주문이라 체결 시각으로 꽂아 직전을 찾았다 |
    | `no_predecessor`     | 꽂았는데 앞이 없다 (첫 진입 이전 잔여 포지션)          |
    | `non_entry`          | 꽂을 수조차 없다 (그 주문에 시각이 없다)               |

    ★`filled_at` 은 우리 관측시각이라 **봉 귀속에는 못 쓴다**. 여기서 쓰는 것은 봉
    귀속이 아니라 **사슬 안 순서**뿐이고, key 가 없는 주문에는 다른 시각이 없다.
    """
    position = index_of.get(target.order_id)
    if position is not None:
        return (chain[position - 1], "linked") if position > 0 else (None, "no_predecessor")
    if target.filled_at is None:
        return None, "non_entry"
    moment = int(target.filled_at.timestamp())
    preceding = [
        entry for entry in chain if entry.bar_epoch is not None and entry.bar_epoch <= moment
    ]
    if not preceding:
        return None, "no_predecessor"
    return preceding[-1], "linked_via_flatten"


def attribute_ledger_events(
    corpus: OrderCorpus,
    events: Sequence[LedgerRow],
) -> LedgerAttribution:
    """★링크된 주문은 그 포지션을 **닫은** 쪽이다 — opener 는 그 **직전 진입**이다.

    두 번의 실측이 이 함수를 두 번 고쳤다.

    ⑴ **시간순 FIFO 폐기** — FIFO 는 직결 링크와 86 event 중 **59 건에서 다른 주문**을
       골랐다. 커서 선점 때문이다: 수동 flatten(00:34:10)이 첫 진입의 신호봉(00:34:00)
       뒤라는 이유만으로 커서를 가져가 이후 전부가 한 칸 밀렸다. loose 37쌍 중 28쌍이
       **남의 청산 손익**을 actual 로 썼고 `price_gap` 은 `+19.36 → −0.36` 으로 뒤집혔다.

    ⑵ ★**직결을 그대로 opener 로 쓰면 또 한 칸 밀린다** — 실덤프에서
       `entry_price_agreement` 가 **exact 0/81**(median 0.0716% · max 0.5976%)을 냈고,
       교차 근거로 `linked.filled_price == event.avg_exit_price` 가 **82/82** 였다.
       즉 링크된 주문은 opener 가 아니라 **closer** 다.

    이 전략의 반전 사슬이 그 이유다. 조건부 진입은 `abs(target − current)` 수량의
    **병합 주문 1건**이라(`conditional_entry_planner.py:502`) 반대편 청산과 신규 진입을
    한 장으로 처리한다(`strategy_state.py:1032-1039`, BL-560):

        r_k 가 P_{k-1} 을 닫고 P_k 를 연다  ⇒  event E_{k-1} 은 r_k 에 링크된다
        ⇒ E_{k-1} 의 opener = r_k 의 **직전 진입** r_{k-1}

    그래서 진입을 `bar_epoch` 순 사슬로 세우고 링크 주문의 predecessor 를 집는다.
    수동 정리처럼 사슬 밖 주문에 링크된 event 는 그 주문의 체결 시각으로 사슬에 꽂아
    직전 진입을 찾고 `linked_via_flatten` 으로 **따로 표시**한다.

    앞이 없으면(`no_predecessor`) 조용히 아무 데나 붙이지 않는다 — 세션 첫 진입 이전의
    잔여 포지션이 실재하고, 그걸 첫 진입에 붙이면 그 진입의 손익이 통째로 남의 것이 된다.

    직결이 없는 event 만 FIFO 로 붙이고 `inferred` 로 표시한다. 그 값은 매칭 합계에
    들어가지 않는다 — 추정을 확정과 같은 칸에 넣지 않는다.

    ★**닫힘은 옳음의 증거가 아니다.** 어느 귀속을 쓰든 버킷 합은 dedup Σ 로 닫힌다.
    옳음을 재는 것은 `entry_price_agreement` 하나뿐이고, 그 값이 이 수리를 스스로
    증명해야 한다.
    """
    chain = [entry for entry in corpus.entries if entry.bar_epoch is not None]
    index_of = {entry.order_id: position for position, entry in enumerate(chain)}
    linked: dict[str, LedgerRow] = {}
    non_entry_linked: list[LedgerRow] = []
    no_predecessor: list[LedgerRow] = []
    grade_of: dict[str, str] = {}
    link_collisions = 0
    needs_fallback: list[LedgerRow] = []

    for event in events:
        target = corpus.by_id.get(event.order_link_id) if event.order_link_id is not None else None
        if target is None:
            needs_fallback.append(event)
            continue
        opener, grade = _opener_of(target, chain, index_of)
        if opener is None:
            (non_entry_linked if grade == "non_entry" else no_predecessor).append(event)
            grade_of[event.exit_id] = grade
            continue
        if opener.order_id in linked:
            # 한 진입에 직결 event 가 둘이면 뒤엣것을 추정으로 내리지 않고 세어 둔다.
            link_collisions += 1
            needs_fallback.append(event)
            continue
        linked[opener.order_id] = event
        grade_of[event.exit_id] = grade

    # 직결이 없는 것만 종전 FIFO 로 붙인다 — 신호봉(bar_epoch) vs 거래소 시각.
    # ★`Order.filled_at` 은 여기서도 쓰지 않는다 (우리 관측시각이라 귀속을 늦춘다).
    open_entries = [entry for entry in chain if entry.order_id not in linked]
    inferred: dict[str, LedgerRow] = {}
    unattributed: list[LedgerRow] = []
    cursor = 0
    for event in sorted(needs_fallback, key=lambda row: (row.exchange_created_at, row.exit_id)):
        event_epoch = int(event.exchange_created_at.timestamp())
        entry = open_entries[cursor] if cursor < len(open_entries) else None
        if entry is not None and entry.bar_epoch is not None and entry.bar_epoch <= event_epoch:
            inferred[entry.order_id] = event
            grade_of[event.exit_id] = "inferred"
            cursor += 1
        else:
            unattributed.append(event)
            grade_of[event.exit_id] = "none"

    return LedgerAttribution(
        linked=linked,
        inferred=inferred,
        non_entry_linked=non_entry_linked,
        no_predecessor=no_predecessor,
        unattributed=unattributed,
        grade_of=grade_of,
        link_collisions=link_collisions,
    )


def entry_price_agreement(attribution: LedgerAttribution, corpus: OrderCorpus) -> dict[str, Any]:
    """★귀속이 **맞는지**를 가르는 유일한 행별 검사 — 그리고 이 도구의 자기 증명.

    귀속된 event 의 `avg_entry_price` 는 그 opener 주문의 `filled_price` 와 같아야 한다.
    귀속이 한 칸 밀리면 이 값이 **다른 진입의 체결가**와 붙는다.

    ★합계로는 이걸 못 잡는다. `price_gap` 은 합이라 actual 계열을 통째로 한 칸 밀어도
    양 끝만 바뀐다(telescoping) — 그래서 "합이 0 에 가깝다" 는 귀속의 증거가 아니다.
    실제로 그 함정이 한 번 발동했다: 직결 귀속의 `price_gap` 은 −0.36 으로 예뻤는데
    이 검사는 **exact 0/81** 이었다.

    ★★**판정 문턱 `ATTRIBUTION_AGREEMENT_TOLERANCE_PCT = 0.01%` 의 근거** — 두 실측 사이에
    잡았다. 위쪽: 틀린 귀속의 신호가 median **0.0716%**(문턱의 **7.2배**) · max 0.5976%.
    아래쪽: 옳은 귀속은 **정확히 0** 이어야 한다 — 같은 덤프에서 청산 쪽 대조
    (`linked.filled_price == avg_exit_price`)가 **82/82 exact** 였으므로 진입 쪽도 표현
    오차가 없다. 문턱은 부분체결·수수료 반올림 여유만 남긴 값이고, 틀린 귀속을 통과시킬
    만큼 넓지 않다.
    """
    entries = {entry.order_id: entry for entry in corpus.entries}
    residuals: list[Decimal] = []
    unknown = 0
    for order_id, event in attribution.linked.items():
        entry = entries.get(order_id)
        if entry is None or entry.filled_price is None or event.avg_entry_price is None:
            unknown += 1
            continue
        filled_price = Decimal(str(entry.filled_price))
        if filled_price == Decimal("0"):
            unknown += 1
            continue
        residuals.append(
            (Decimal(str(event.avg_entry_price)) - filled_price)
            / abs(filled_price)
            * Decimal("100")
        )
    exact = sum(1 for value in residuals if value == Decimal("0"))
    absolute = [abs(value) for value in residuals]
    median = median_decimal(absolute)
    tolerance = ATTRIBUTION_AGREEMENT_TOLERANCE_PCT
    return {
        "n": len(residuals),
        # ★표본이 없으면 "일치한다" 가 아니라 "잴 것이 없다" 다.
        "verdict": (
            "undetermined"
            if not residuals or median is None
            else ("agrees" if median <= tolerance else "disagrees")
        ),
        "tolerance_pct": decimal_text(tolerance),
        "unmeasurable": unknown,
        "exact_matches": exact,
        "beyond_tolerance": sum(1 for value in absolute if value > tolerance),
        "median_pct": decimal_text(median),
        "max_abs_pct": decimal_text(max(absolute)) if absolute else None,
    }


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
    """매칭 쌍 + **직결 귀속된** 원장 event → parity 관측.

    ★`actual_net` 은 **원장 순수 산술**(`closed_pnl`)이다 — `Order.realized_pnl` 이
    아니다(R2). 매칭됐지만 아직 청산이 없는 쌍은 관측이 **아니다**: `ParityObservation` 은
    확정 net 을 결측으로 표현할 수 없으므로 0 으로 메우는 대신 따로 센다.

    ★호출부는 `attribution.linked` 만 넘긴다 (R11). FIFO 추정(`inferred`)을 여기 넣으면
    추정이 확정과 같은 칸에 합산되어, 신뢰도 차이가 숫자에서 사라진다.
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


def cost_explanation(observation_set: ObservationSet, *, verdict: bool = True) -> dict[str, Any]:
    """③ 을 **두 정의로** 낸다 (R3).

    ★합계를 먼저 낸 뒤 절대값을 씌우면(`preregistered`) 부호 상쇄가 분모를 0 쪽으로
    끌어당겨 비율이 폭발한다. 행별 절대값(`row_abs`)은 그 폭발이 없다. 그런데 판정은
    **사전등록 원문으로 한다** — 표본을 보고 정의를 갈아 끼우는 것이 곧 래칫 위반이다.
    상쇄 정도는 `cancellation_index` 로 옆에 병기해 판단 재료로 남긴다.

    ★`verdict=False` (감도 블록) 이면 `verdict_definition` 자체를 **싣지 않는다** (R12).
    같은 모양의 숫자가 옆에 있으면 소비자는 그것도 판정값으로 읽는다.
    """
    cost_terms = observation_set.cost_terms
    gap_terms = observation_set.gap_terms
    payload: dict[str, Any] = {
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
    }
    if verdict:
        payload["verdict_definition"] = "preregistered"
    else:
        payload["not_a_verdict"] = True
    return payload


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
    attribution: LedgerAttribution
    partition: dict[str, list[LedgerRow]]


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
    attribution = attribute_ledger_events(corpus, events)
    linked_orders = link_ledger_to_orders(events, corpus.by_id)

    # ★직결 귀속만 관측이 된다 (R11).
    strict_set = build_observations(match.strict_pairs, attribution.linked)
    loose_set = build_observations(match.pairs, attribution.linked) if match.loose_pairs else None

    matched_entry_ids = {pair.entry.order_id for pair in match.pairs}
    live_only_ids = {entry.order_id for entry in match.live_only}
    ambiguous_ids = {item.entry.order_id for item in match.ambiguous}
    entry_of_event = {event.exit_id: order_id for order_id, event in attribution.linked.items()}

    # ★진짜 파티션 — 모든 dedup event 가 정확히 하나에 들어간다 (R13).
    partition: dict[str, list[LedgerRow]] = {
        "matched": [],
        "live_only": [],
        "ambiguous": [],
        "inferred": [],
        "non_entry_linked": [],
        "no_predecessor": [],
        "ledger_only": [],
    }
    for event in events:
        grade = attribution.grade_of.get(event.exit_id, "none")
        if grade == "inferred":
            partition["inferred"].append(event)
        elif grade == "non_entry":
            partition["non_entry_linked"].append(event)
        elif grade == "no_predecessor":
            # ★사슬에 앞이 없다 = 세션 첫 진입 이전의 잔여 포지션. 첫 진입에 붙이면
            #   그 진입의 손익이 통째로 남의 것이 되므로 **보이게** 남긴다.
            partition["no_predecessor"].append(event)
        elif grade in ("linked", "linked_via_flatten"):
            order_id = entry_of_event.get(event.exit_id)
            if order_id in matched_entry_ids:
                partition["matched"].append(event)
            elif order_id in live_only_ids:
                partition["live_only"].append(event)
            elif order_id in ambiguous_ids:
                partition["ambiguous"].append(event)
            else:
                partition["ledger_only"].append(event)
        else:
            partition["ledger_only"].append(event)

    backtest_only_expected_gross = sum_decimals(
        [trade.expected_gross for trade in match.backtest_only]
    )
    live_only_actual_net = sum_decimals(
        [event.closed_pnl for event in partition["live_only"] + partition["ambiguous"]]
    )
    ledger_only_net = sum_decimals([event.closed_pnl for event in partition["ledger_only"]])
    unassigned = partition["ledger_only"]

    # ★flatten 계상은 orders 가 아니라 exits(dedup) 기준이다 (R8) — 실측에서 3 event 중
    #   2 건이 orders 에 아예 없었다.
    flatten_order_ids = {order.order_id for order in corpus.manual_flatten}
    flatten_events: list[LedgerRow] = []
    flatten_from_order = 0
    flatten_orphan = 0
    for event in events:
        order = linked_orders.get(event.exit_id)
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
        if (order := linked_orders.get(event.exit_id)) is not None
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
        actual_only_count=len(partition["live_only"]) + len(partition["ambiguous"]),
        actual_only_net=live_only_actual_net,
        ledger_only_count=len(unassigned),
        ledger_only_net=ledger_only_net,
        inferred_attribution_count=len(partition["inferred"]),
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
        attribution=attribution,
        partition=partition,
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
    flatten_events: Sequence[LedgerRow],
) -> dict[str, Any]:
    """세션 경계에서 새는 것들을 **총계에 접지 않고** 버킷으로 병기한다.

    ★귀속 기본값은 **청산시각**이다. 반전 전략이라 진입창과 청산창이 갈리는 event 가
    실재하고(실측 6건, 그중 1건은 세션 사이 2.74h 무세션 구간을 통과했다), 어느 쪽으로
    귀속하느냐로 세션 단위 합계가 흔들린다 — 그 차이를 숨기지 않고 함께 낸다.

    ★★**이 블록은 파티션이 아니라 「세션 축 뷰」다** (R13). 같은 event 가
    `unattributed` · `gap_exit` · `cross_window` 에 **동시에** 들어갈 수 있다(실측 5건).
    합이 닫히는 파티션은 `buckets.partition` 쪽이고, 여기 숫자를 서로 더하면 이중계상이
    된다. 그래서 `overlay: true` 와 **어느 event 가 몇 개 뷰에 걸쳤는지**를 함께 낸다.
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
                    "exit_id": event.exit_id,
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
    # ★멀티뷰 event 를 이름으로 남긴다 — 안 남기면 "합쳐도 되나?" 를 아무도 못 답한다.
    views_of: dict[str, list[str]] = {}
    for event in unattributed_events:
        views_of.setdefault(event.exit_id, []).append("unattributed")
    for event in gap_events:
        views_of.setdefault(event.exit_id, []).append("gap_exit")
    for row in cross_window:
        views_of.setdefault(str(row["exit_id"]), []).append("cross_window")
    for event in flatten_events:
        views_of.setdefault(event.exit_id, []).append("manual_flatten")

    return {
        "overlay": True,
        "overlay_note": (
            "이 네 뷰는 파티션이 아니다 — 같은 event 가 여러 뷰에 들어간다. "
            "합이 닫히는 파티션은 buckets.partition 이다."
        ),
        "multi_view_events": [
            {"exit_id": exit_id, "views": sorted(views)}
            for exit_id, views in sorted(views_of.items())
            if len(views) > 1
        ],
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


def _partition_payload(
    partition: Mapping[str, Sequence[LedgerRow]], dedup: LedgerDedup
) -> dict[str, Any]:
    """★합이 닫히는 파티션. 모든 dedup event 가 정확히 하나의 칸에 들어간다 (R13).

    닫힘 자체는 귀속이 옳다는 증거가 **아니다** — 어느 귀속을 쓰든 파티션이면 닫힌다.
    여기서 닫힘을 재는 이유는 event 를 흘리거나 이중계상하지 않았음을 보이기 위해서다.
    """
    counted = sum(len(rows) for rows in partition.values())
    total = sum_decimals([event.closed_pnl for event in dedup.events])
    partition_total = sum_decimals(
        [event.closed_pnl for rows in partition.values() for event in rows]
    )
    return {
        "definition": (
            "matched(strict+loose) + live_only + ambiguous + inferred "
            "+ non_entry_linked + no_predecessor + ledger_only"
        ),
        "note": "세션 축 뷰(session_accounting)는 파티션이 아니다 — 여기 숫자와 더하지 마라.",
        "counts": {name: len(rows) for name, rows in partition.items()},
        "nets": {
            name: decimal_text(sum_decimals([event.closed_pnl for event in rows]))
            for name, rows in partition.items()
        },
        "event_total": len(dedup.events),
        "counted_total": counted,
        "ledger_net_total": decimal_text(total),
        "partition_net_total": decimal_text(partition_total),
        "closes": counted == len(dedup.events) and partition_total == total,
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
    attribution = decomposition.attribution
    partition = decomposition.partition
    # 판정 자격 = strict 쌍에서 **분해 가능한** 관측이 하나라도 있나 (R12).
    eligible_for_verdict = summary.decomposable_count > 0
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
            # ★strict 분해 관측이 0 이면 워터폴·비율은 **판정이 아니다** (R12).
            "eligible_for_verdict": eligible_for_verdict,
            "verdict_blocked_reason": (
                None if eligible_for_verdict else "strict 매칭에서 분해 가능한 관측이 0 건"
            ),
        },
        "attribution": {
            # ★귀속 근거를 값으로 남긴다 — `linked` 와 `inferred` 는 신뢰도가 다르다 (R11).
            "rule": "predecessor of order_link_id target, fifo fallback",
            "rule_note": (
                "링크된 주문은 그 포지션을 **닫은** 쪽이다 — opener 는 사슬에서 그 직전 진입."
            ),
            "linked": len(attribution.linked),
            "linked_via_flatten": attribution.via_flatten,
            "inferred": len(attribution.inferred),
            "non_entry_linked": len(attribution.non_entry_linked),
            "no_predecessor": len(attribution.no_predecessor),
            "unattributed": len(attribution.unattributed),
            "link_collisions": attribution.link_collisions,
            "inferred_net": decimal_text(
                sum_decimals([event.closed_pnl for event in partition["inferred"]])
            ),
            "inferred_note": "추정 귀속은 매칭 합계에 넣지 않는다 — 별도 버킷으로만 센다.",
            # 귀속이 한 칸 밀렸는지 가르는 **행별** 검사. 합계로는 절대 안 잡힌다.
            "entry_price_agreement": entry_price_agreement(attribution, corpus),
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
            # ★여기가 **합이 닫히는 유일한 파티션**이다 (R13). 세션 축 뷰
            #   (`session_accounting`) 와 섞어 더하면 이중계상이 된다.
            "partition": _partition_payload(partition, dedup),
        },
        "session_accounting": session_boundary_accounting(
            windows,
            corpus=corpus,
            dedup=dedup,
            trades=trades,
            match=match,
            assigned=attribution.linked,
            flatten_events=decomposition.flatten_events,
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
                "explanation_ratio": cost_explanation(
                    decomposition.observation_set, verdict=eligible_for_verdict
                ),
            },
            "stage_4_actual_net": decimal_text(summary.decomposable_actual_net),
            "undecomposed_net": decimal_text(summary.undecomposed_net),
        },
        "coverage": coverage_payload(decomposition),
        "loose_sensitivity": (
            None
            if decomposition.loose_summary is None or decomposition.loose_observation_set is None
            else {
                # ★R12 — 같은 모양의 숫자가 옆에 있으면 소비자는 그것도 판정으로 읽는다.
                "note": (
                    "★판정값이 아니다. 판정은 strict 만으로 한다 — 이 블록은 loose 를 "
                    "넣었을 때 숫자가 얼마나 움직이는지 보는 감도 분석이다."
                ),
                "is_verdict": False,
                "matched_count": decomposition.loose_summary.matched_count,
                "stage_1_expected_gross": decimal_text(
                    decomposition.loose_summary.decomposable_expected_gross
                ),
                "price_gap": decimal_text(decomposition.loose_summary.execution_gap),
                "live_derived_cost": decimal_text(decomposition.loose_summary.cost),
                "stage_4_actual_net": decimal_text(
                    decomposition.loose_summary.decomposable_actual_net
                ),
                "explanation_ratio": cost_explanation(
                    decomposition.loose_observation_set, verdict=False
                ),
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
# `replay` — 라이브 프로토콜 재생 (롤링 창 × `run_live`)
# --------------------------------------------------------------------------

# 라이브가 매 tick 가져오는 봉 수. `tasks/live_signal._fetch_evaluation_bars` 의
# `limit_bars=300` 이 정본이다 (perp 강제). 이 값이 곧 「엔진이 볼 수 있는 과거」다.
REPLAY_WINDOW_BARS = 300

# R 의 채널 셋. **셋은 서로 다른 단계를 잰다** — 섞어 세면 안 된다.
#
# | kind    | 무엇                                   | 봉의 의미        | 대응하는 L/B      |
# | ------- | -------------------------------------- | ---------------- | ----------------- |
# | `cond`  | 엔진이 장전한 조건부 진입 (재장전 포함) | **장전봉**       | L 의 `cond` key   |
# | `entry` | 마지막 봉에서 나온 시장가 진입 signal   | **장전봉**       | L 의 `entry` key  |
# | `fill`  | 마지막 봉에서 엔진이 **연** 포지션      | **체결봉**       | B 의 `entry_time` |
#
# ★`cond`/`entry` 는 L 과 같은 단계이고(둘 다 `ctx.bar_time` = 창의 마지막 봉),
# `fill` 은 B 와 같은 단계다(둘 다 엔진 진입 봉). 그래서 R↔L 은 앞의 둘로,
# B↔R(사전등록 ②의 `|B| − |R|`)은 `fill` 로 재야 분모의 뜻이 같다.
REPLAY_KINDS: tuple[str, ...] = ("cond", "entry", "fill")

# 거래소 눈금. 라이브는 `_reconcile_market_precision` 이 ccxt 로 읽지만 재생은 네트워크를
# 타지 않으므로 인자로 받는다. 기본값은 **이 실험의 원장 덤프에서 실측한 값**이다 —
# `cond` key 의 수량 표기가 `0.029`/`0.058` 뿐(3자리)이고 트리거는 `64105.5` 꼴(1자리)이라
# BTCUSDT linear 의 `(qty_step, price_tick) = (0.001, 0.1)` 이다. 다른 심볼이면 바꿔라.
REPLAY_QTY_STEP = Decimal("0.001")
REPLAY_PRICE_TICK = Decimal("0.1")


def _replay_frame(ohlcv_csv: Path) -> Any:
    """CSV → **라이브가 `run_live` 에 넘기는 것과 같은 모양**의 프레임.

    ★`_run_backtest` 와 다르다. 저쪽은 `timestamp` 를 **인덱스**로 세우지만
    (`ohlcv.set_index`), 라이브는 `_ohlcv_rows_to_dataframe` 가 RangeIndex + tz-aware
    `timestamp` **컬럼**을 준다. 그 차이는 관상용이 아니다 — `run_historical` 은
    `ohlcv.index` 가 `DatetimeIndex` 일 때만 `BarContext(timestamps=...)` 를 채우므로
    (`event_loop.py:125-130`), 인덱스로 세우면 세션 게이트가 보는 시각이 있고 없고가
    갈린다. R 은 **라이브를 재생하는 것**이므로 라이브 쪽을 그대로 베낀다.
    """
    import pandas as pd

    frame = pd.read_csv(ohlcv_csv, parse_dates=["timestamp"])
    timestamps = pd.DatetimeIndex(frame["timestamp"])
    if timestamps.tz is None:
        timestamps = timestamps.tz_localize("UTC")
    else:
        timestamps = timestamps.tz_convert("UTC")
    frame["timestamp"] = timestamps
    return frame.reset_index(drop=True)


def _engine_position(result: Any) -> Decimal:
    """마지막 봉을 처리한 뒤의 엔진 순 포지션 (long +, short −).

    ★`position_size` 는 엔진 안에서 float 로 누적된 값이다(실측 오염
    `0.058998579999999995`). 여기서 Decimal 로 올리는 것은 **이후 산술**을 float 공간에서
    하지 않기 위해서지, 누적 오차를 되돌리지는 못한다.
    """
    raw = result.strategy_state_report.get("position_size")
    return Decimal(str(raw or 0))


def _replay_conditional_rows(
    result: Any,
    *,
    bar_epoch: int,
    bar_time: str,
    qty_step: Decimal,
    price_tick: Decimal,
) -> list[dict[str, Any]]:
    """이 tick 에 라이브가 **거래소에 낼** 조건부 진입 = `pending_orders` 의 상.

    `plan_reconcile` 의 산식을 **그대로** 쓴다 (`conditional_entry_planner.py:502-540`):

    1. `수량 = _normalize(|target_position − 현재 포지션|, qty_step)`. 엔진의 leg 수량
       (`entry_qty`)을 그대로 쓰면 같은 id 재발행(순 변화 0)이 주문 1건으로 둔갑하고
       반전(청산+진입 병합)의 크기가 절반으로 계상된다.
    2. **수량이 0 이면 낼 주문이 없다.** 절삭 전에는 0 이 아니어도 절삭 후 0 이면
       라이브는 취소만 하고 등재하지 않는다. 실측으로 이 갈래가 흔하다 — 같은 id
       재발행의 잔차가 `0.000044…` 로 남아 절삭 전 검사만으로는 안 걸린다.
    3. **side 불일치도 등재하지 않는다.** 목표가 포지션의 반대편에 있으면
       (`planner:526-540`) 라이브는 발산으로 기록하고 넘어간다.

    ★재생은 거래소 상태를 모른다. 그래서 「현재 포지션」에 **엔진 포지션**을 넣는다 —
    라이브의 reconciler 는 거래소 실포지션을 쓰고 그 값은 체결 때 이미 눈금으로 절삭돼
    있다(실측: 엔진 `0.0297` ↔ 거래소 `0.029`). 그래서 **반전 수량이 한 눈금 어긋난다**
    (재생 `0.059` ↔ 실측 key `0.058`). 그 어긋남과 「거래소가 엔진을 못 따라온 tick」이
    바로 이 실험이 R↔L 잔차로 재려는 대상이다.

    ★**재현하지 않는 게이트가 있다** — `trigger_already_breached` / 시장가 전환 /
    breach cap / overshoot cap. 넷 다 **거래소 기준가와 resting 주문 상태**를 봐야 하고
    그 둘은 얼린 입력에 없다. 그래서 R 의 `cond` 는 라이브가 실제로 등재한 것의
    **상계**다 — 라이브가 드롭한 레그가 R 에는 남아 있을 수 있다.
    """
    from src.trading.services.conditional_entry_planner import _normalize

    engine_position = _engine_position(result)
    rows: list[dict[str, Any]] = []
    for order in result.pending_orders:
        target = Decimal(str(order.target_position))
        place_qty = _normalize(abs(target - engine_position), qty_step)
        if place_qty == 0:
            continue
        side = "buy" if target > engine_position else "sell"
        if side != ("buy" if str(order.direction) == "long" else "sell"):
            continue
        rows.append(
            {
                "kind": "cond",
                "bar_epoch": bar_epoch,
                "bar_time": bar_time,
                "direction": str(order.direction),
                "trade_id": str(order.trade_id),
                "trigger": decimal_text(_normalize(Decimal(str(order.stop_price)), price_tick)),
                "qty": decimal_text(place_qty),
                "entry_qty": decimal_text(Decimal(str(order.entry_qty))),
                "target_position": decimal_text(target),
                "engine_position": decimal_text(engine_position),
            }
        )
    return rows


def _replay_signal_rows(result: Any, *, bar_epoch: int, bar_time: str) -> list[dict[str, Any]]:
    """마지막 봉의 **시장가 진입** signal. `run_live` 가 이미 마지막 봉으로 잘라 준다."""
    rows: list[dict[str, Any]] = []
    for signal in result.signals:
        if signal.action != "entry":
            continue
        rows.append(
            {
                "kind": "entry",
                "bar_epoch": bar_epoch,
                "bar_time": bar_time,
                "direction": str(signal.direction),
                "trade_id": str(signal.trade_id),
                "trigger": None,
                "qty": decimal_text(Decimal(str(signal.qty))),
                "entry_qty": decimal_text(Decimal(str(signal.qty))),
                "target_position": None,
                "engine_position": decimal_text(_engine_position(result)),
            }
        )
    return rows


def _replay_fill_rows(
    result: Any, *, bar_epoch: int, bar_time: str, last_bar_index: int
) -> list[dict[str, Any]]:
    """마지막 봉에서 엔진이 **연** 포지션 = B 와 같은 단계의 진입.

    ★`run_live().signals` 로는 못 구한다. 조건부 진입의 체결은 `broker_filled` 라
    signal 변환에서 빠지므로(`event_loop.py:580`), signal 만 세면 stop 진입 전략의
    체결이 통째로 0 이 된다. 그래서 상태 리포트의 거래 목록에서 진입 봉으로 고른다.

    `trade_id` 는 **`comment`** 를 우선한다 — 매칭의 1차 키가 보는 백테스트 쪽 필드가
    `RawTrade.comment` 이기 때문이다(`strict_key_matches` docstring). 비어 있으면 Pine
    진입 id 로 떨어진다.
    """
    report = result.strategy_state_report
    rows: list[dict[str, Any]] = []
    trades = list(report.get("open_trades", [])) + list(report.get("closed_trades", []))
    for trade in trades:
        if trade.get("entry_bar") != last_bar_index:
            continue
        comment = str(trade.get("comment") or "").strip()
        rows.append(
            {
                "kind": "fill",
                "bar_epoch": bar_epoch,
                "bar_time": bar_time,
                "direction": str(trade["direction"]),
                "trade_id": comment or str(trade["id"]),
                "trigger": decimal_text(Decimal(str(trade["entry_price"]))),
                "qty": decimal_text(Decimal(str(trade["qty"]))),
                "entry_qty": decimal_text(Decimal(str(trade["qty"]))),
                "target_position": None,
                "engine_position": decimal_text(_engine_position(result)),
            }
        )
    return rows


def _rearm_key(row: Mapping[str, Any]) -> tuple[str, str, str, str]:
    """라이브가 **재등재**를 결정할 때 보는 튜플.

    `plan_reconcile` 은 resting 주문과 `(side, 수량, 트리거, 트리거 방향)` 을 비교해
    다르면 취소 후 재등재한다(`conditional_entry_planner.py:600-`). 재생은 거래소
    resting 을 모르므로 **직전 봉의 desired** 와 비교한다 — 같은 규칙의 최선 근사다.
    """
    return (
        str(row["trade_id"]),
        str(row["direction"]),
        str(row["trigger"]),
        str(row["qty"]),
    )


def replay_live_protocol(
    *,
    source: str,
    frame: Any,
    window_bars: int,
    start: datetime | None,
    end: datetime | None,
    initial_capital: float | None,
    live_position_size_pct: float | None,
    leverage: float,
    pyramiding: int | None,
    fill_timing: str,
    qty_step: Decimal = REPLAY_QTY_STEP,
    price_tick: Decimal = REPLAY_PRICE_TICK,
) -> dict[str, Any]:
    """채점 창의 매 봉에서 **직전 `window_bars` 봉**으로 `run_live` 를 다시 돌린다.

    ★**원장 인자 4종(`ledger_seed_legs` · `ledger_conditional_fills` ·
    `position_epoch` · `emit_from_bar_time`)은 넘기지 않는다.** 이것이 실험의 통제다 —
    넘기지 않으면 `conditional_fill_authority` 가 `None` 이라 조건부 체결이 백테스트와
    같은 시뮬로 판정되고(`event_loop.py:508-513`), 마지막 봉 이벤트만 발행된다.
    넣는 순간 R 은 「롤링 창의 몫」이 아니라 「롤링 창 + 원장 권한의 몫」이 된다.

    ★`sessions_allowed` 도 넘기지 않는다. 라이브는 `strategy.trading_sessions` 를
    싣지만 그 값은 이 실험의 입력(얼린 CSV·원장 덤프)에 **없다**. 비어 있지 않은
    전략이면 R 이 라이브보다 많이 진입한다 — report 에 적을 [확인 필요] 항목이다.
    """
    from src.strategy.pine_v2.event_loop import run_live

    if window_bars < 1:
        raise ValueError(f"--window-bars 는 1 이상이어야 한다: {window_bars}")

    bar_times: list[datetime] = [
        moment.to_pydatetime()
        for moment in list(frame["timestamp"])  # tz-aware UTC
    ]
    entries: list[dict[str, Any]] = []
    previous_pending: dict[str, tuple[str, str, str, str]] = {}
    bars_evaluated = 0
    bars_skipped_short_window = 0
    bars_outside_window = 0

    for index in range(len(frame)):
        if index < window_bars - 1:
            # 창이 안 차면 라이브가 볼 과거보다 **적게** 보게 된다 — 평가하지 않는다.
            bars_skipped_short_window += 1
            continue
        bar_time = bar_times[index]
        if (start is not None and bar_time < start) or (end is not None and bar_time >= end):
            bars_outside_window += 1
            # ★건너뛴 봉에서도 재장전 기억을 비우지 않는다. 채점 창 밖은 「평가하지
            #   않는다」이지 「엔진이 없다」가 아니다 — 여기서 비우면 창 첫 봉이 항상
            #   재장전으로 계상된다.
            continue
        window = frame.iloc[index - window_bars + 1 : index + 1].reset_index(drop=True)
        result = run_live(
            source,
            window,
            initial_capital=initial_capital,
            live_position_size_pct=live_position_size_pct,
            leverage=leverage,
            pyramiding=pyramiding,
            fill_timing=fill_timing,
        )
        bars_evaluated += 1
        bar_epoch = int(bar_time.timestamp())
        bar_time_iso = _iso(bar_time) or ""
        conditional = _replay_conditional_rows(
            result,
            bar_epoch=bar_epoch,
            bar_time=bar_time_iso,
            qty_step=qty_step,
            price_tick=price_tick,
        )
        # 재장전만 남긴다 — 대기 주문은 트리거될 때까지 매 tick 다시 보이고, 라이브는
        # 튜플이 같으면 재등재하지 않는다. 전부 실으면 R 이 「주문 수」가 아니라
        # 「tick 수」가 된다.
        current_pending: dict[str, tuple[str, str, str, str]] = {}
        for row in conditional:
            key = _rearm_key(row)
            current_pending[str(row["trade_id"])] = key
            if previous_pending.get(str(row["trade_id"])) != key:
                entries.append(row)
        previous_pending = current_pending
        entries.extend(_replay_signal_rows(result, bar_epoch=bar_epoch, bar_time=bar_time_iso))
        entries.extend(
            _replay_fill_rows(
                result,
                bar_epoch=bar_epoch,
                bar_time=bar_time_iso,
                last_bar_index=len(window) - 1,
            )
        )

    entries.sort(key=lambda row: (row["bar_epoch"], row["kind"], row["trade_id"]))
    by_kind = {kind: sum(1 for row in entries if row["kind"] == kind) for kind in REPLAY_KINDS}
    return {
        "params": {
            "window_bars": window_bars,
            "initial_capital": initial_capital,
            "live_position_size_pct": live_position_size_pct,
            "leverage": leverage,
            "pyramiding": pyramiding,
            "fill_timing": fill_timing,
            "qty_step": decimal_text(qty_step),
            "price_tick": decimal_text(price_tick),
            "scoring_window": {"start": _iso(start), "end": _iso(end)},
            # ★넘기지 **않은** 인자를 이름으로 남긴다. 「안 넣었다」는 사후에 파일만
            #   보고는 확인할 수 없고, 이 실험의 통제가 바로 그 미주입이다.
            "ledger_arguments_omitted": [
                "ledger_seed_legs",
                "ledger_conditional_fills",
                "position_epoch",
                "emit_from_bar_time",
            ],
            "sessions_allowed_omitted": True,
        },
        "bars_total": len(frame),
        "bars_evaluated": bars_evaluated,
        "bars_skipped_short_window": bars_skipped_short_window,
        "bars_outside_scoring_window": bars_outside_window,
        "bar_first": _iso(bar_times[0]) if bar_times else None,
        "bar_last": _iso(bar_times[-1]) if bar_times else None,
        "entries_by_kind": by_kind,
        "entries": entries,
        "digest": trades_digest(entries),
    }


# --------------------------------------------------------------------------
# `entrysets` — 진입 집합 정규화 + 쌍별 매칭
# --------------------------------------------------------------------------

ENTRY_SET_KINDS: tuple[str, ...] = ("trades", "replay", "orders")


@dataclass(frozen=True, slots=True)
class NormalizedEntry:
    """세 산출물(B · R · L)을 하나의 축으로 올린 진입 1건.

    ★`bar_epoch` 의 **뜻은 출처마다 다르다** — B/R`fill` 은 엔진 진입 봉,
    L/R`cond`/R`entry` 는 장전봉이다. 그래서 이 타입은 단계를 통일하지 **않고**
    `stage` 로 표시만 한다. 통일했다고 적으면 ±1~2봉 오프셋이 숫자 뒤로 숨는다.
    """

    source_id: str
    bar_epoch: int
    direction: str
    trade_id: str
    qty: Decimal | None
    trigger: Decimal | None
    stage: str  # "entry_bar" | "staged_bar"


def normalize_trades(trades: Sequence[BacktestTrade], *, bar_seconds: int) -> list[NormalizedEntry]:
    """B — `run` 산출 trades.json. 봉은 **엔진 진입 봉**이다.

    `entry_time` 은 `_run_backtest` 가 `entry_bar_index` 를 봉 시각으로 되돌린 값이라
    이미 봉 경계에 있지만, floor 는 `trade_bar_epoch` 와 **같은 함수**를 쓴다 — 여기서
    다른 산식을 쓰면 기존 `match` 와 R 의 봉 귀속이 조용히 갈린다.
    """
    return [
        NormalizedEntry(
            source_id=f"trade:{trade.trade_index}",
            bar_epoch=trade_bar_epoch(trade, bar_seconds=bar_seconds),
            direction=trade.direction,
            trade_id=trade.comment or "",
            qty=Decimal(str(trade.size)),
            trigger=Decimal(str(trade.entry_price)),
            stage="entry_bar",
        )
        for trade in trades
    ]


def normalize_replay(payload: Any, *, kinds: Sequence[str]) -> list[NormalizedEntry]:
    """R — `replay` 산출. `kinds` 로 채널을 고른다 (§REPLAY_KINDS 표)."""
    wanted = set(kinds)
    unknown = wanted - set(REPLAY_KINDS)
    if unknown:
        raise ValueError(f"모르는 replay kind: {sorted(unknown)}")
    rows = payload["entries"] if isinstance(payload, dict) else payload
    entries: list[NormalizedEntry] = []
    for index, row in enumerate(rows):
        kind = str(row["kind"])
        if kind not in wanted:
            continue
        entries.append(
            NormalizedEntry(
                source_id=f"replay:{kind}:{index}",
                bar_epoch=int(row["bar_epoch"]),
                direction=str(row["direction"]),
                trade_id=str(row["trade_id"]),
                qty=to_decimal(row.get("qty")),
                trigger=to_decimal(row.get("trigger")),
                stage="entry_bar" if kind == "fill" else "staged_bar",
            )
        )
    return entries


@dataclass(frozen=True, slots=True)
class NormalizedOrders:
    entries: list[NormalizedEntry]
    unparsable: int
    no_bar_epoch: int


def normalize_orders(
    rows: Sequence[Mapping[str, Any]], *, session_ids: Sequence[UUID]
) -> NormalizedOrders:
    """L — orders.json. 판별은 `parse_live_entry_key` 하나뿐이다 (`parse_orders` 재사용).

    되짚지 못한 행(수동 flatten · 청산 key · 웹훅)은 **버리지 않고 센다**.
    """
    corpus = parse_orders(rows, session_ids=session_ids)
    entries: list[NormalizedEntry] = []
    no_bar_epoch = 0
    for entry in corpus.entries:
        if entry.bar_epoch is None:
            # key 는 우리 것인데 봉을 못 읽었다 = 봉 축에 세울 수 없다.
            no_bar_epoch += 1
            continue
        entries.append(
            NormalizedEntry(
                source_id=f"order:{entry.order_id}",
                bar_epoch=entry.bar_epoch,
                direction=entry.direction,
                trade_id=entry.trade_id,
                qty=entry.key_quantity,
                trigger=entry.trigger,
                stage="staged_bar",
            )
        )
    return NormalizedOrders(
        entries=entries,
        unparsable=len(corpus.manual_flatten) + len(corpus.other),
        no_bar_epoch=no_bar_epoch,
    )


def _as_synthetic_trade(entry: NormalizedEntry) -> BacktestTrade:
    """왼쪽 집합을 `match_entries` 의 「백테스트 쪽」 모양으로 올린다.

    ★매칭 규칙을 새로 쓰지 않기 위한 어댑터다. `match_entries` 가 보는 필드는
    `direction`/`comment`/`entry_time`/`size` 넷뿐이고, 나머지는 리포트에 안 실린다.
    `trade_index` 는 원본 id 를 못 담으므로(정수) `source_id` 를 별도 맵으로 들고 간다.
    """
    return BacktestTrade(
        trade_index=0,
        direction=entry.direction,
        status="closed",
        entry_time=datetime.fromtimestamp(entry.bar_epoch, tz=UTC),
        exit_time=None,
        entry_price=entry.trigger if entry.trigger is not None else Decimal("0"),
        exit_price=None,
        size=entry.qty if entry.qty is not None else Decimal("0"),
        pnl=Decimal("0"),
        fees=Decimal("0"),
        fee_paid=None,
        slippage_paid=None,
        comment=entry.trade_id or None,
        exit_kind=None,
    )


def _as_synthetic_live_entry(entry: NormalizedEntry) -> LiveEntry:
    """오른쪽 집합을 `match_entries` 의 「라이브 쪽」 모양으로 올린다."""
    return LiveEntry(
        order_id=entry.source_id,
        idempotency_key="",
        kind="normalized",
        trade_id=entry.trade_id,
        bar_epoch=entry.bar_epoch,
        direction=entry.direction,
        trigger=entry.trigger,
        key_quantity=entry.qty,
        filled_price=None,
        filled_quantity=None,
        filled_at=None,
    )


def filter_by_sessions(
    entries: Sequence[NormalizedEntry], windows: Sequence[SessionWindow]
) -> tuple[list[NormalizedEntry], list[NormalizedEntry]]:
    """세션 창 **안**과 **밖**으로 가른다 (실험 B — 사전등록 ③).

    창 판정은 `window_of` 그대로다 — `created_at <= t < deactivated_at`.
    """
    kept: list[NormalizedEntry] = []
    removed: list[NormalizedEntry] = []
    for entry in entries:
        moment = datetime.fromtimestamp(entry.bar_epoch, tz=UTC)
        (kept if window_of(moment, windows) is not None else removed).append(entry)
    return kept, removed


def _pair_row(
    pair: MatchedPair, *, left_by_key: Mapping[tuple[int, str, str], str]
) -> dict[str, Any]:
    trade_epoch = int(pair.trade.entry_time.timestamp())
    key = (trade_epoch, pair.trade.direction, pair.trade.comment or "")
    return {
        "grade": pair.grade,
        "left_id": left_by_key.get(key),
        "right_id": pair.entry.order_id,
        "left_bar_epoch": trade_epoch,
        "right_bar_epoch": pair.entry.bar_epoch,
        "delta_bars_left_minus_right": trade_epoch - (pair.entry.bar_epoch or 0),
        "direction": pair.trade.direction,
        "trade_id": pair.trade.comment,
    }


def compare_entry_sets(
    left: Sequence[NormalizedEntry],
    right: Sequence[NormalizedEntry],
    *,
    bar_seconds: int,
    bar_tolerance: int = ENTRY_BAR_TOLERANCE_BARS,
) -> dict[str, Any]:
    """두 진입 집합을 **기존 `match_entries` 로** 맞춘다 — 새 규칙을 만들지 않는다.

    ★비대칭이다. `match_entries` 는 오른쪽에서 같은 `(bar_epoch, direction)` 이 둘이면
    **양쪽 다 ambiguous** 로 버리고, 왼쪽은 후보가 둘일 때만 버린다. 그러니 어느 쪽을
    오른쪽에 두느냐가 숫자를 바꾼다 — 라이브(L)를 오른쪽에 두는 것이 기존 `match` 의
    배치이고, 이 함수도 호출자가 그렇게 부르는 것을 전제로 리포트를 낸다.

    ★분모를 하나로 정하지 않는다. 사전등록은 X↔L 을 `|L|` 로 재지만 B↔R 은 `|B|` 를
    병기하라고 적혀 있다 — 둘 다 이름과 함께 낸다.
    """
    left_by_key: dict[tuple[int, str, str], str] = {}
    synthetic_trades: list[BacktestTrade] = []
    for index, entry in enumerate(left):
        trade = replace(_as_synthetic_trade(entry), trade_index=index)
        synthetic_trades.append(trade)
        left_by_key[(entry.bar_epoch, entry.direction, entry.trade_id or "")] = entry.source_id
    synthetic_entries = [_as_synthetic_live_entry(entry) for entry in right]

    match = match_entries(
        synthetic_trades, synthetic_entries, bar_seconds=bar_seconds, bar_tolerance=bar_tolerance
    )
    pairs = len(match.pairs)
    return {
        "left_count": len(left),
        "right_count": len(right),
        "strict_pairs": len(match.strict_pairs),
        "loose_pairs": len(match.loose_pairs),
        "pairs": pairs,
        "ambiguous": len(match.ambiguous),
        "left_only": len(match.backtest_only),
        "right_only": len(match.live_only),
        "match_rate": {
            "vs_left": {
                "denominator": "left_count",
                "n": len(left),
                "value": decimal_text(_ratio(Decimal(pairs), Decimal(len(left)))),
            },
            "vs_right": {
                "denominator": "right_count",
                "n": len(right),
                "value": decimal_text(_ratio(Decimal(pairs), Decimal(len(right)))),
            },
        },
        "matched_rows": [_pair_row(pair, left_by_key=left_by_key) for pair in match.pairs],
        "left_only_rows": [
            {
                "bar_epoch": int(trade.entry_time.timestamp()),
                "direction": trade.direction,
                "trade_id": trade.comment,
                "qty": decimal_text(trade.size),
            }
            for trade in match.backtest_only
        ],
        "right_only_rows": [
            {
                "id": entry.order_id,
                "bar_epoch": entry.bar_epoch,
                "direction": entry.direction,
                "trade_id": entry.trade_id,
                "qty": decimal_text(entry.key_quantity),
            }
            for entry in match.live_only
        ],
        "ambiguous_rows": [
            {"id": item.entry.order_id, "reason": item.reason} for item in match.ambiguous
        ],
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
    """계기 하나의 진입 수 · net_profit_abs · 비용 합.

    ★`cost_total` 의 정의는 **하나뿐이다 — `Σ fees`**(결합 필드). `fee_paid` 와
    `slippage_paid` 는 그 분해일 뿐이고, 따로 합산해서 비교하면 마지막 자리에서 어긋날
    수 있다(`fee_paid + slippage_paid == fees` 는 거래 **한 건**의 불변식이지 합계의
    불변식이 아니다). 두 벌을 나란히 headline 으로 내면 어느 쪽이 정본인지 사라지므로,
    정본은 `cost_total` 하나로 두고 분해 합계의 어긋남은 `split_residual` 로 **보이게**
    남긴다.
    """
    fee_values = [t.fee_paid for t in trades]
    slip_values = [t.slippage_paid for t in trades]
    fee_total = _optional_sum(fee_values)
    slip_total = _optional_sum(slip_values)
    cost_total = sum_decimals([t.fees for t in trades])
    return {
        "entries": len(trades),
        "net_profit_abs": decimal_text(sum_decimals([t.pnl for t in trades])),
        "cost_total": decimal_text(cost_total),
        "cost_total_definition": "sum(RawTrade.fees)",
        "fee_paid_total": decimal_text(fee_total),
        "slippage_paid_total": decimal_text(slip_total),
        "split_residual": (
            None
            if fee_total is None or slip_total is None
            else decimal_text(
                Decimal(str(fee_total)) + Decimal(str(slip_total)) - Decimal(str(cost_total))
            )
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

    ★★**짝지어지지 못한 쪽을 함께 센다** (R14). 실측에서 144쌍은 spot 193 의 75% ·
    perp 210 의 69% 다 — 나머지 25~31% 가 무보고로 빠지면 "짝지어진 것들끼리는 비슷하다"
    가 **선택 편향인지 아닌지**를 아무도 검증할 수 없다.
    """
    pairs = pair_by_signal_bar(spot, perp, bar_seconds=bar_seconds)
    diffs = [
        Decimal(str(spot_trade.entry_price)) - Decimal(str(perp_trade.entry_price))
        for spot_trade, perp_trade in pairs
    ]
    paired_spot = {id(trade) for trade, _ in pairs}
    paired_perp = {id(trade) for _, trade in pairs}
    unpaired_spot = [trade for trade in spot if id(trade) not in paired_spot]
    unpaired_perp = [trade for trade in perp if id(trade) not in paired_perp]
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
            # ★탈락분 — 무보고면 선택 편향 검증이 불가능하다 (R14).
            "unpaired_spot": len(unpaired_spot),
            "unpaired_perp": len(unpaired_perp),
            "unpaired_spot_net": decimal_text(sum_decimals([trade.pnl for trade in unpaired_spot])),
            "unpaired_perp_net": decimal_text(sum_decimals([trade.pnl for trade in unpaired_perp])),
            "spot_pair_coverage_pct": decimal_text(
                _ratio(Decimal(len(diffs)) * Decimal("100"), Decimal(len(spot)))
            ),
            "perp_pair_coverage_pct": decimal_text(
                _ratio(Decimal(len(diffs)) * Decimal("100"), Decimal(len(perp)))
            ),
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


def _resolve_pyramiding(source: str, override: int | None) -> int | None:
    """라이브와 **같은 자리**에서 읽는다 — `tasks/live_signal._extract_pyramiding`.

    그쪽은 `extract_content(pine_source).declaration.pyramiding` 이고 백테스트
    (`compat.parse_and_run_v2`)도 같은 값을 쓴다. CLI 로 따로 받으면 B·R·라이브 셋이
    서로 다른 cap 으로 돌 수 있으므로 **기본값은 소스에서 뽑고**, 명시 override 만 이긴다.
    """
    if override is not None:
        return override
    from src.strategy.pine_v2.ast_extractor import extract_content

    pyramiding: int | None = extract_content(source).declaration.pyramiding
    return pyramiding


def _cmd_replay(args: argparse.Namespace) -> int:
    source = Path(args.pine_source).read_text(encoding="utf-8")
    payload = replay_live_protocol(
        source=source,
        frame=_replay_frame(Path(args.ohlcv_csv)),
        window_bars=args.window_bars,
        start=to_datetime(args.start),
        end=to_datetime(args.end),
        initial_capital=None if args.init_cash is None else float(args.init_cash),
        live_position_size_pct=args.live_position_size_pct,
        leverage=args.leverage,
        pyramiding=_resolve_pyramiding(source, args.pyramiding),
        fill_timing=args.fill_timing,
        qty_step=args.qty_step,
        price_tick=args.price_tick,
    )
    payload["ohlcv_csv"] = str(args.ohlcv_csv)
    payload["freq"] = args.freq
    _write_json(Path(args.out), payload)
    print(
        f"[replay] bars_evaluated={payload['bars_evaluated']} "
        f"entries={len(payload['entries'])} by_kind={payload['entries_by_kind']} "
        f"digest={payload['digest']}"
    )
    return 0


def _load_entry_set(
    path: Path,
    kind: str,
    *,
    bar_seconds: int,
    replay_kinds: Sequence[str],
    session_ids: Sequence[UUID],
) -> tuple[list[NormalizedEntry], dict[str, Any]]:
    payload = _read_json(path)
    if kind == "trades":
        entries = normalize_trades(_trades_of(payload), bar_seconds=bar_seconds)
        return entries, {"kind": kind, "path": str(path)}
    if kind == "replay":
        entries = normalize_replay(payload, kinds=replay_kinds)
        return entries, {"kind": kind, "path": str(path), "replay_kinds": list(replay_kinds)}
    if kind == "orders":
        if not session_ids:
            raise ValueError("--*-kind orders 는 --session-windows 가 있어야 한다 (세션 id 필요)")
        normalized = normalize_orders(payload, session_ids=session_ids)
        return normalized.entries, {
            "kind": kind,
            "path": str(path),
            "unparsable_rows": normalized.unparsable,
            "parsed_without_bar_epoch": normalized.no_bar_epoch,
        }
    raise ValueError(f"모르는 집합 종류: {kind}")


def _cmd_entrysets(args: argparse.Namespace) -> int:
    windows: list[SessionWindow] = []
    session_ids: list[UUID] = []
    bar_seconds = args.bar_seconds
    if args.session_windows is not None:
        sessions_raw = _read_json(Path(args.session_windows))
        windows = parse_sessions(sessions_raw)
        session_ids = [UUID(window.session_id) for window in windows]
        # ★봉 길이가 세션과 다르면 ±3봉 허용창이 통째로 틀린다 — 조용히 넘기지 않는다.
        session_bar_seconds = interval_seconds(_session_interval(sessions_raw))
        if session_bar_seconds != bar_seconds:
            raise ValueError(
                f"--bar-seconds={bar_seconds} 가 세션 interval ({session_bar_seconds}s) 와 다르다"
            )

    replay_kinds = tuple(part.strip() for part in args.replay_kinds.split(",") if part.strip())
    left, left_meta = _load_entry_set(
        Path(args.left),
        args.left_kind,
        bar_seconds=bar_seconds,
        replay_kinds=replay_kinds,
        session_ids=session_ids,
    )
    right, right_meta = _load_entry_set(
        Path(args.right),
        args.right_kind,
        bar_seconds=bar_seconds,
        replay_kinds=replay_kinds,
        session_ids=session_ids,
    )

    removed: list[NormalizedEntry] = []
    if args.filter_left:
        if not windows:
            raise ValueError("--filter-left 는 --session-windows 가 있어야 한다")
        left, removed = filter_by_sessions(left, windows)

    report = compare_entry_sets(
        left, right, bar_seconds=bar_seconds, bar_tolerance=args.bar_tolerance
    )
    report["left"] = left_meta
    report["right"] = right_meta
    report["bar_seconds"] = bar_seconds
    report["bar_tolerance_bars"] = args.bar_tolerance
    report["session_filter"] = {
        "applied": bool(args.filter_left),
        "windows": len(windows),
        "removed_by_session_filter": len(removed),
        "removed_rows": [
            {"id": entry.source_id, "bar_epoch": entry.bar_epoch, "trade_id": entry.trade_id}
            for entry in removed
        ],
    }
    _write_json(Path(args.out), report)
    print(
        f"[entrysets] left={report['left_count']}({args.left_kind}) "
        f"right={report['right_count']}({args.right_kind}) "
        f"strict={report['strict_pairs']} loose={report['loose_pairs']} "
        f"ambiguous={report['ambiguous']} "
        f"rate_vs_right={report['match_rate']['vs_right']['value']} "
        f"removed_by_session_filter={len(removed)}"
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

    replay_parser = sub.add_parser("replay", help="라이브 프로토콜 재생 → replay.json (R)")
    replay_parser.add_argument("--pine-source", required=True)
    replay_parser.add_argument("--ohlcv-csv", required=True)
    replay_parser.add_argument("--freq", default="1m", help="기록용 라벨 (엔진에 안 들어간다)")
    replay_parser.add_argument("--leverage", type=float, default=2.0)
    replay_parser.add_argument(
        "--init-cash",
        type=Decimal,
        default=None,
        help="run_live(initial_capital=…) — 라이브의 equity baseline + carry PnL",
    )
    replay_parser.add_argument("--live-position-size-pct", type=float, default=None)
    replay_parser.add_argument(
        "--pyramiding",
        type=int,
        default=None,
        help="미지정이면 라이브와 같이 Pine 선언에서 뽑는다 (_extract_pyramiding 과 동일)",
    )
    replay_parser.add_argument(
        "--fill-timing",
        choices=("bar_close", "next_bar_open"),
        default="bar_close",
        help="StrategySettings.fill_timing (기본값이 라이브 기본값과 같다)",
    )
    replay_parser.add_argument(
        "--window-bars",
        type=int,
        default=REPLAY_WINDOW_BARS,
        help="라이브가 매 tick 가져오는 봉 수 (live_signal._fetch_evaluation_bars limit_bars)",
    )
    replay_parser.add_argument(
        "--qty-step",
        type=Decimal,
        default=REPLAY_QTY_STEP,
        help="거래소 수량 눈금 (라이브의 _reconcile_market_precision 대체 — 기본은 실측값)",
    )
    replay_parser.add_argument(
        "--price-tick",
        type=Decimal,
        default=REPLAY_PRICE_TICK,
        help="거래소 가격 눈금 (같은 이유)",
    )
    replay_parser.add_argument("--start", default=None, help="채점 창 시작 ISO8601 (포함)")
    replay_parser.add_argument("--end", default=None, help="채점 창 끝 ISO8601 (배타)")
    replay_parser.add_argument("--out", required=True)
    replay_parser.set_defaults(handler=_cmd_replay)

    entrysets_parser = sub.add_parser("entrysets", help="진입 집합 쌍별 매칭 → entrysets.json")
    entrysets_parser.add_argument("--left", required=True)
    entrysets_parser.add_argument("--left-kind", required=True, choices=ENTRY_SET_KINDS)
    entrysets_parser.add_argument("--right", required=True)
    entrysets_parser.add_argument("--right-kind", required=True, choices=ENTRY_SET_KINDS)
    entrysets_parser.add_argument(
        "--replay-kinds",
        default="cond,entry",
        help="replay 집합에서 쓸 채널 (cond,entry = 장전봉 / fill = 엔진 진입봉)",
    )
    entrysets_parser.add_argument(
        "--session-windows",
        default=None,
        help="sessions.json — orders 파싱의 세션 id 출처이자 --filter-left 의 창",
    )
    entrysets_parser.add_argument(
        "--filter-left",
        action="store_true",
        help="left 에서 세션 창 밖 진입을 제거한다 (실험 B — R′). ★파일만 주면 필터는 꺼져 "
        "있다: 사전등록 ③ 이 R↔L 과 R′↔L 을 **둘 다** 요구하는데 L 파싱에도 같은 파일이 "
        "필요해서다",
    )
    entrysets_parser.add_argument("--bar-seconds", type=int, default=60)
    entrysets_parser.add_argument("--bar-tolerance", type=int, default=ENTRY_BAR_TOLERANCE_BARS)
    entrysets_parser.add_argument("--out", required=True)
    entrysets_parser.set_defaults(handler=_cmd_entrysets)

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

# 주문 원장이 증언하는 **현재 열린 포지션**을 유도한다 — 순수 함수 (BL-591 / ADR-022)
"""원장 → 열린 포지션 유도.

## 왜 `_ledger_gap_seed` 를 재사용할 수 없나 (BL-591 반증 5)

`live_signal._ledger_gap_seed` 는 **공백 창에서 열기만 한 경우**를 위한 함수다. 채택 조건이
「창 안 체결이 **전부 같은 방향**이고 **reduce-only 가 하나도 없다**」라, 상시 유도에 쓰면
`since` 를 어떻게 잡아도 깨진다:

- 세션 시작부터 보면 진입과 청산이 **반드시 섞여** `inadmissible` → legs 빈다.
- 직전 tick 만 보면 체결이 거의 없어 `no_basis` → legs 빈다.

그쪽 함수의 주석이 이유를 직접 적고 있다 — 「열고 (부분)닫은 창을 되돌리려면 **공백 이전
포지션**을 알아야 하는데 이 창에는 그 정보가 없다」. 세션 **전체**를 보면 그 정보가 있다.
그래서 여기서는 다른 방식을 쓴다: **Pine `trade_id` 단위로 진입/청산을 상쇄**한다.

## 왜 상쇄가 가능한가

`_build_idempotency_key` 가 만드는 키는
`live:<sess>:<bar_time ISO>:<seq>:<action>:<trade_id>` 이고 **`action` 이 `entry`/`close`
둘 다 `trade_id` 를 담는다**. 조건부 진입(`cond`/`condmkt`)도 끝에 `trade_id` 가 있다.
⇒ 어느 진입을 어느 청산이 닫았는지 **키만으로 이어붙일 수 있다.**

## ★「모른다」와 「비었다」를 같은 값으로 접지 않는다

`legs is None` = **판정 불가**(fail-closed) · `legs == ()` = **flat 이라고 판정함**.
접으면 판정 불가를 flat 으로 오인해 **엔진이 없는 포지션을 만들거나 있는 포지션을 잃는다.**
`outcome` 은 **항상** 채운다 — 슬라이스 1 계측이 이 분포를 재서 상한 계수를 정하기 때문이다.

## 이 함수가 답하지 않는 것

거래소가 실제로 그 포지션을 들고 있는지는 **모른다.** 브래킷 TP/SL 처럼 우리가 주문을 내지
않은 청산은 원장에 안 남으므로 여기서는 「여전히 열림」으로 보인다. 그 어긋남을 잡는 것은
**호출부의 거래소 대조(veto)** 이며, 그것이 ADR-022 의 설계다. **여기서 거래소를 보면 안 된다** —
보는 순간 그 대조가 동어반복이 된다(`live_signal.py:2248`).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal
from uuid import UUID

from src.strategy.pine_v2.strategy_state import Direction, LedgerSeedLeg
from src.trading.models import OrderSide
from src.trading.repositories.order_repository import LedgerFill
from src.trading.services.conditional_entry_planner import (
    LIVE_ENTRY_KEY_PREFIX,
    parse_live_entry_key,
)

_CLOSE_MARKER = ":close:"

LedgerKeyKind = Literal["open", "close"]


@dataclass(frozen=True, slots=True)
class LedgerKey:
    """원장 주문 키가 가리키는 Pine trade 와 그 방향(연다/닫는다)."""

    kind: LedgerKeyKind
    trade_id: str


def parse_ledger_key(key: str | None, *, session_id: UUID) -> LedgerKey | None:
    """우리 세션의 주문 키를 `(연다|닫는다, trade_id)` 로 되짚는다. 우리 것이 아니면 `None`.

    진입 3형식은 `parse_live_entry_key`(형식 판정의 **유일한 자리**)에 위임한다. 청산 키는
    그쪽이 의도적으로 안 되짚으므로(진입이 아니니까) 여기서 `:close:` 마커로 가른다.

    ★`trade_id` 는 Pine 사용자 입력이라 `:` 를 포함할 수 있다. 그래서 `split` 이 아니라
    **마커 뒤 전부**를 id 로 본다 — 진입 쪽이 쓰는 규칙과 같다.
    """
    parsed = parse_live_entry_key(key)
    if parsed is not None:
        # ★세션 대조는 여기서 한다. 남의 세션 주문을 내 포지션으로 세면 안 된다.
        if parsed.session_id != session_id:
            return None
        return LedgerKey(kind="open", trade_id=parsed.trade_id)

    if not key or not key.startswith(LIVE_ENTRY_KEY_PREFIX):
        return None
    session_part, separator, rest = key[len(LIVE_ENTRY_KEY_PREFIX) :].partition(":")
    if not separator:
        return None
    try:
        if UUID(session_part) != session_id:
            return None
    except (TypeError, ValueError):
        return None
    index = rest.find(_CLOSE_MARKER)
    if index == -1:
        return None
    trade_id = rest[index + len(_CLOSE_MARKER) :]
    if not trade_id:
        return None
    return LedgerKey(kind="close", trade_id=trade_id)


@dataclass(frozen=True, slots=True)
class LedgerPosition:
    """원장 유도 결과.

    `legs is None` 이면 **판정 불가**다 — 호출부는 오늘의 fail-closed 동작으로 떨어져야 하고,
    **flat 으로 취급하면 안 된다.**
    """

    legs: tuple[LedgerSeedLeg, ...] | None
    outcome: str

    @property
    def undecidable(self) -> bool:
        return self.legs is None

    def net_signed_qty(self) -> Decimal | None:
        """부호 있는 순포지션. 판정 불가면 `None`."""
        if self.legs is None:
            return None
        total = Decimal("0")
        for leg in self.legs:
            qty = Decimal(str(leg.qty))
            total += qty if leg.direction == "long" else -qty
        return total


def _undecidable(outcome: str) -> LedgerPosition:
    return LedgerPosition(legs=None, outcome=outcome)


def derive_open_position(
    fills: Sequence[LedgerFill], *, session_id: UUID, overflowed: bool
) -> LedgerPosition:
    """세션 체결 원장 → 아직 열려 있는 포지션. **거래소를 보지 않는다.**

    `fills` 는 `(filled_at, id)` 오름차순이어야 한다(`list_fills_since` 계약). 순서가
    뒤집히면 청산이 진입보다 먼저 와서 `close_without_open` 으로 판정 불가가 된다 —
    조용히 틀린 포지션을 만드는 것보다 낫다.
    """
    if overflowed:
        # 절단된 원장은 부분 원장이다. 부분 원장으로 유도하면 **앞쪽 진입을 못 봐서**
        # 열린 포지션을 놓친다 = flat 으로 오인. 조용한 절단이 가장 위험하다.
        return _undecidable("overflow")

    if not fills:
        return LedgerPosition(legs=(), outcome="no_fills")

    open_legs: dict[str, LedgerSeedLeg] = {}
    for fill in fills:
        parsed = parse_ledger_key(fill.idempotency_key, session_id=session_id)
        if parsed is None:
            # 웹훅·수동 주문·브래킷 등 우리 세션 키가 아닌 체결이 섞였다. 그 체결이
            # 포지션에 미친 영향을 알 수 없으므로 유도 전체를 포기한다.
            return _undecidable("foreign_fill")

        if parsed.kind == "close":
            if open_legs.pop(parsed.trade_id, None) is None:
                # 이 창에서 연 적 없는 trade 를 닫았다 = 원장이 이야기의 일부만 갖고 있다.
                return _undecidable("close_without_open")
            continue

        quantity, price = fill.filled_quantity, fill.filled_price
        if (
            quantity is None
            or price is None
            or not quantity.is_finite()
            or not price.is_finite()
            or quantity <= 0
            or price <= 0
        ):
            return _undecidable("unreadable")
        if parsed.trade_id in open_legs:
            # `open_trades` 는 trade id 가 key 라 중복이면 뒤엣것이 앞엣것을 덮어써
            # 엔진이 실제보다 **작은** 포지션을 갖는다 — 조용한 과소 계상이다.
            return _undecidable("duplicate_open")

        direction: Direction = "long" if fill.side == OrderSide.buy else "short"
        open_legs[parsed.trade_id] = LedgerSeedLeg(
            trade_id=parsed.trade_id,
            direction=direction,
            qty=float(quantity),
            entry_price=float(price),
        )

    if not open_legs:
        return LedgerPosition(legs=(), outcome="flat")
    return LedgerPosition(legs=tuple(open_legs.values()), outcome="open")

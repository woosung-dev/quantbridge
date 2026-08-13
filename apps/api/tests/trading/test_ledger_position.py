# 원장 → 열린 포지션 유도의 계약 검증 (BL-591 슬라이스 1a / ADR-022)
"""`src.trading.ledger_position` 단위 테스트.

★이 모듈은 **순수 함수**라 전량을 여기서 검증한다. 그리고 이 함수의 출력은 곧 엔진에
주입될 포지션이므로, **「판정 불가」와 「flat」이 갈리는 지점**이 가장 중요한 계약이다 —
둘을 접으면 엔진이 없는 포지션을 만들거나 있는 포지션을 잃는다.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from src.trading.ledger_position import (
    LedgerKey,
    derive_open_position,
    parse_ledger_key,
)
from src.trading.models import OrderSide
from src.trading.repositories.order_repository import LedgerFill

SESSION_ID = UUID("4bf679af-e535-402e-ba8e-8b91cebe3b51")
OTHER_SESSION_ID = UUID("11111111-1111-1111-1111-111111111111")
_T0 = datetime(2026, 8, 4, 1, 0, tzinfo=UTC)


def _entry_key(trade_id: str, *, seq: int = 1, session_id: UUID = SESSION_ID) -> str:
    return f"live:{session_id}:{_T0.isoformat()}:{seq}:entry:{trade_id}"


def _close_key(trade_id: str, *, seq: int = 2, session_id: UUID = SESSION_ID) -> str:
    return f"live:{session_id}:{_T0.isoformat()}:{seq}:close:{trade_id}"


def _fill(
    key: str | None,
    *,
    side: OrderSide = OrderSide.buy,
    qty: Decimal | None = Decimal("0.03"),
    price: Decimal | None = Decimal("63000"),
    offset_s: int = 0,
    reduce_only: bool = False,
) -> LedgerFill:
    return LedgerFill(
        order_id=uuid4(),
        idempotency_key=key,
        side=side,
        filled_quantity=qty,
        filled_price=price,
        filled_at=_T0 + timedelta(seconds=offset_s),
        reduce_only=reduce_only,
    )


# ── parse_ledger_key ────────────────────────────────────────────────


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        (_entry_key("t1"), LedgerKey(kind="open", trade_id="t1")),
        (_close_key("t1"), LedgerKey(kind="close", trade_id="t1")),
        (f"live:{SESSION_ID}:cond:1754269200:62811.5:0.03:t9", LedgerKey("open", "t9")),
        (f"live:{SESSION_ID}:condmkt:1754269200:62811.5:0.03:t9", LedgerKey("open", "t9")),
    ],
)
def test_parses_our_keys(key: str, expected: LedgerKey) -> None:
    assert parse_ledger_key(key, session_id=SESSION_ID) == expected


@pytest.mark.parametrize(
    "key",
    [
        None,
        "",
        "tv:webhook:whatever",
        "live:not-a-uuid:2026:1:close:t1",
        _entry_key("t1", session_id=OTHER_SESSION_ID),
        _close_key("t1", session_id=OTHER_SESSION_ID),
        f"live:{SESSION_ID}:{_T0.isoformat()}:1:close:",  # trade_id 없음
    ],
)
def test_rejects_foreign_or_malformed_keys(key: str | None) -> None:
    assert parse_ledger_key(key, session_id=SESSION_ID) is None


def test_trade_id_may_contain_colons() -> None:
    """`trade_id` 는 Pine 사용자 입력이라 `:` 를 포함할 수 있다 — 마커 뒤 전부가 id 다."""
    parsed = parse_ledger_key(_close_key("a:b:c"), session_id=SESSION_ID)
    assert parsed == LedgerKey(kind="close", trade_id="a:b:c")


# ── derive_open_position — 판정되는 경우 ────────────────────────────


def test_no_fills_is_flat_not_undecidable() -> None:
    result = derive_open_position([], session_id=SESSION_ID, overflowed=False)
    assert result.legs == ()
    assert result.undecidable is False
    assert result.outcome == "no_fills"


def test_single_entry_stays_open() -> None:
    result = derive_open_position(
        [_fill(_entry_key("t1"))], session_id=SESSION_ID, overflowed=False
    )
    assert result.legs is not None
    assert len(result.legs) == 1
    assert result.legs[0].trade_id == "t1"
    assert result.legs[0].direction == "long"
    assert result.net_signed_qty() == Decimal("0.03")


def test_sell_entry_is_short() -> None:
    result = derive_open_position(
        [_fill(_entry_key("t1"), side=OrderSide.sell)], session_id=SESSION_ID, overflowed=False
    )
    assert result.legs is not None
    assert result.legs[0].direction == "short"
    assert result.net_signed_qty() == Decimal("-0.03")


def test_entry_then_close_cancels_to_flat() -> None:
    """★`_ledger_gap_seed` 가 `inadmissible` 로 포기하던 창이 바로 이것이다."""
    fills = [
        _fill(_entry_key("t1"), offset_s=0),
        _fill(_close_key("t1"), side=OrderSide.sell, offset_s=1, reduce_only=True),
    ]
    result = derive_open_position(fills, session_id=SESSION_ID, overflowed=False)
    assert result.legs == ()
    assert result.undecidable is False
    assert result.outcome == "flat"


def test_only_unclosed_trades_remain() -> None:
    fills = [
        _fill(_entry_key("t1", seq=1), offset_s=0),
        _fill(_entry_key("t2", seq=2), offset_s=1),
        _fill(_close_key("t1", seq=3), side=OrderSide.sell, offset_s=2, reduce_only=True),
    ]
    result = derive_open_position(fills, session_id=SESSION_ID, overflowed=False)
    assert result.legs is not None
    assert [leg.trade_id for leg in result.legs] == ["t2"]


def test_conditional_entry_is_adopted() -> None:
    key = f"live:{SESSION_ID}:cond:1754269200:62811.5:0.03:t9"
    result = derive_open_position([_fill(key)], session_id=SESSION_ID, overflowed=False)
    assert result.legs is not None
    assert result.legs[0].trade_id == "t9"


# ── derive_open_position — 판정 불가 (fail-closed) ──────────────────


def test_overflow_is_undecidable_not_flat() -> None:
    """★절단된 원장을 flat 으로 읽으면 앞쪽 진입을 통째로 놓친다."""
    result = derive_open_position(
        [_fill(_entry_key("t1"))], session_id=SESSION_ID, overflowed=True
    )
    assert result.legs is None
    assert result.undecidable is True
    assert result.outcome == "overflow"
    assert result.net_signed_qty() is None


def test_foreign_fill_is_undecidable() -> None:
    """웹훅·수동 주문이 섞이면 그 체결의 영향을 알 수 없다."""
    result = derive_open_position(
        [_fill(_entry_key("t1")), _fill("tv:webhook:x", offset_s=1)],
        session_id=SESSION_ID,
        overflowed=False,
    )
    assert result.legs is None
    assert result.outcome == "foreign_fill"


def test_close_without_open_is_undecidable() -> None:
    result = derive_open_position(
        [_fill(_close_key("ghost"), side=OrderSide.sell, reduce_only=True)],
        session_id=SESSION_ID,
        overflowed=False,
    )
    assert result.legs is None
    assert result.outcome == "close_without_open"


def test_duplicate_open_is_undecidable() -> None:
    """★같은 trade id 로 두 번 열면 dict 가 앞엣것을 덮어써 **과소 계상**된다."""
    result = derive_open_position(
        [_fill(_entry_key("t1", seq=1)), _fill(_entry_key("t1", seq=2), offset_s=1)],
        session_id=SESSION_ID,
        overflowed=False,
    )
    assert result.legs is None
    assert result.outcome == "duplicate_open"


@pytest.mark.parametrize(
    ("qty", "price"),
    [
        (None, Decimal("63000")),
        (Decimal("0.03"), None),
        (Decimal("0"), Decimal("63000")),
        (Decimal("-0.03"), Decimal("63000")),
        (Decimal("0.03"), Decimal("0")),
        (Decimal("NaN"), Decimal("63000")),
    ],
)
def test_unreadable_fill_is_undecidable(qty: Decimal | None, price: Decimal | None) -> None:
    result = derive_open_position(
        [_fill(_entry_key("t1"), qty=qty, price=price)],
        session_id=SESSION_ID,
        overflowed=False,
    )
    assert result.legs is None
    assert result.outcome == "unreadable"


def test_undecidable_is_distinguishable_from_flat() -> None:
    """★이 스위트의 존재 이유 — 두 상태를 같은 값으로 접으면 안 된다."""
    flat = derive_open_position([], session_id=SESSION_ID, overflowed=False)
    unknown = derive_open_position([], session_id=SESSION_ID, overflowed=True)
    assert flat.legs == () and flat.undecidable is False
    assert unknown.legs is None and unknown.undecidable is True
    assert flat.legs != unknown.legs

# 라이브 진입 key 형식 판정이 한 자리에만 있다는 계약을 고정한다

"""BL-536 — 파서 SSOT.

이 레포는 같은 사실을 세 곳에서 판정하는 Triple SSOT 안티패턴을 이미 배웠다. 진입 key
형식은 이제 `conditional_entry_planner.parse_live_entry_key` 하나가 판정하고, 기존
소비처 둘(`parse_conditional_entry_key` · `live_signal._pine_trade_id_from_order_key`)이
거기로 위임한다.

★위임하면서 **기존 동작이 한 톨도 바뀌면 안 된다.** 두 함수 모두 머니-패스에 있다 —
전자는 reconcile 의 `actual` 집합과 orphan sweep 대상을 정하고, 후자는 BL-544 의 공백
재개 seed 가 "이 체결이 우리 것인가" 를 판정하는 자리다. 그래서 아래 테스트는 새 기능이
아니라 **옛 계약**을 열거한다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from src.tasks.live_signal import _pine_trade_id_from_order_key
from src.trading.services.conditional_entry_planner import (
    build_conditional_entry_key,
    build_market_converted_entry_key,
    parse_conditional_entry_key,
    parse_live_entry_key,
)

SESSION_ID = UUID("a0861954-1c7c-4a27-bfee-6f6af1a4d440")
BAR_TIME = datetime(2026, 7, 29, 7, 53, tzinfo=UTC)
BAR_EPOCH = int(BAR_TIME.timestamp())


def _market_entry_key(session_id: UUID = SESSION_ID, trade_id: str = "PivRevLE") -> str:
    return f"live:{session_id}:{BAR_TIME.isoformat()}:1:entry:{trade_id}"


def _close_key(session_id: UUID = SESSION_ID, trade_id: str = "PivRevLE") -> str:
    return f"live:{session_id}:{BAR_TIME.isoformat()}:1:close:{trade_id}"


# --- 세 형식 왕복 --------------------------------------------------------------


def test_conditional_key_round_trips_with_all_fields() -> None:
    key = build_conditional_entry_key(
        SESSION_ID, "PivRevSE", BAR_TIME, Decimal("64075.0"), Decimal("0.029")
    )
    parsed = parse_live_entry_key(key)
    assert parsed is not None
    assert (parsed.session_id, parsed.kind, parsed.trade_id) == (SESSION_ID, "cond", "PivRevSE")
    assert parsed.bar_epoch == BAR_EPOCH
    assert (parsed.trigger, parsed.quantity) == ("64075.0", "0.029")


def test_market_converted_key_is_parsed_as_condmkt() -> None:
    """★M4 의 근거 — `condmkt` 를 되짚지 못하면 그 체결이 통째로 남의 것이 된다."""
    key = build_market_converted_entry_key(
        SESSION_ID, "PivRevSE", BAR_TIME, Decimal("64075.0"), Decimal("0.029")
    )
    parsed = parse_live_entry_key(key)
    assert parsed is not None
    assert parsed.kind == "condmkt"
    assert parsed.trade_id == "PivRevSE"
    assert parsed.bar_epoch == BAR_EPOCH


def test_market_entry_key_is_parsed_as_entry() -> None:
    parsed = parse_live_entry_key(_market_entry_key())
    assert parsed is not None
    assert (parsed.kind, parsed.trade_id) == ("entry", "PivRevLE")
    assert parsed.bar_epoch == BAR_EPOCH
    assert (parsed.trigger, parsed.quantity) == (None, None)


def test_trade_id_containing_colons_is_preserved_in_every_format() -> None:
    """`trade_id` 는 Pine 사용자 입력이라 `:` 를 포함할 수 있다."""
    conditional = build_conditional_entry_key(
        SESSION_ID, "entry:leg:one", BAR_TIME, Decimal("100"), Decimal("1")
    )
    assert parse_live_entry_key(conditional) is not None
    assert parse_live_entry_key(conditional).trade_id == "entry:leg:one"  # type: ignore[union-attr]
    assert parse_conditional_entry_key(conditional) == (SESSION_ID, "entry:leg:one")


@pytest.mark.parametrize(
    "key",
    [
        None,
        "",
        "notlive:x",
        f"live:{SESSION_ID}",
        "live:not-a-uuid:cond:1:2:3:LE",
        # 필드가 모자라거나 빈 값 - 되짚지 못하는 key 로는 우리 것을 주장하지 않는다.
        f"live:{SESSION_ID}:cond:1:2:3",
        f"live:{SESSION_ID}:cond:1:2:3:",
        f"live:{SESSION_ID}:cond::2:3:LE",
        # close 는 진입이 아니다.
        _close_key(),
    ],
)
def test_non_entry_keys_are_rejected(key: str | None) -> None:
    assert parse_live_entry_key(key) is None


def test_bar_epoch_is_read_leniently() -> None:
    """★엄격하게 막으면 BL-544 의 공백 재개가 legacy key 앞에서 fail-closed 로 죽는다.

    기존 파서는 epoch 를 아예 검사하지 않았다. 계약은 "논리 정수만 보존" 이고 비정규
    표기(`001`)도 받아들인다 - 문자열 왕복은 보장하지 않는다.
    """
    lenient = parse_live_entry_key(f"live:{SESSION_ID}:cond:001:2:3:LE")
    assert lenient is not None and lenient.bar_epoch == 1
    unreadable = parse_live_entry_key(f"live:{SESSION_ID}:cond:notanint:2:3:LE")
    assert unreadable is not None, "epoch 를 못 읽어도 파싱은 성공해야 한다"
    assert unreadable.bar_epoch is None
    assert unreadable.trade_id == "LE"


# --- 위임 계약: resting 파서는 계속 `condmkt` 를 거부한다 ----------------------


def test_resting_parser_still_rejects_market_converted_keys() -> None:
    """`condmkt` 주문은 `trigger_price` 가 없어 호가창에 남지 않는다.

    이 함수를 넓히면 reconcile 의 `actual` 과 orphan sweep 이 그 주문을 취소 대상으로
    끌어들인다. 파서를 합치면서 **여기만은 넓히지 않았다** 는 계약이다.
    """
    key = build_market_converted_entry_key(
        SESSION_ID, "PivRevSE", BAR_TIME, Decimal("64075.0"), Decimal("0.029")
    )
    assert parse_live_entry_key(key) is not None
    assert parse_conditional_entry_key(key) is None


def test_resting_parser_rejects_market_entry_keys() -> None:
    assert parse_conditional_entry_key(_market_entry_key()) is None


# --- 위임 계약: BL-544 gap seed 파서의 옛 동작이 그대로다 ---------------------


@pytest.mark.parametrize("kind", ["cond", "condmkt"])
def test_gap_seed_parser_reads_both_conditional_kinds(kind: str) -> None:
    builder = build_market_converted_entry_key if kind == "condmkt" else build_conditional_entry_key
    key = builder(SESSION_ID, "PivRevLE", BAR_TIME, Decimal("100"), Decimal("1"))
    assert _pine_trade_id_from_order_key(key, session_id=SESSION_ID) == "PivRevLE"


def test_gap_seed_parser_reads_market_entry_marker() -> None:
    assert _pine_trade_id_from_order_key(_market_entry_key(), session_id=SESSION_ID) == "PivRevLE"


def test_gap_seed_parser_ignores_close_keys() -> None:
    """청산 체결은 포지션을 만들지 않으므로 채택 대상이 아니다."""
    assert _pine_trade_id_from_order_key(_close_key(), session_id=SESSION_ID) is None


def test_gap_seed_parser_rejects_another_session() -> None:
    key = build_conditional_entry_key(uuid4(), "PivRevLE", BAR_TIME, Decimal("100"), Decimal("1"))
    assert _pine_trade_id_from_order_key(key, session_id=SESSION_ID) is None


def test_gap_seed_parser_uses_exact_session_prefix_not_uuid_equality() -> None:
    """★대문자 UUID 표기는 예전에도 "우리 것" 이 아니었다.

    파싱된 UUID 동등으로 바꾸면 계약이 조용히 넓어진다. 접두사 문자열 검사를 함수에
    남긴 이유가 이것이다.
    """
    key = f"live:{str(SESSION_ID).upper()}:cond:{BAR_EPOCH}:100:1:PivRevLE"
    assert _pine_trade_id_from_order_key(key, session_id=SESSION_ID) is None


def test_gap_seed_parser_still_reads_non_integer_epoch() -> None:
    """옛 파서는 epoch 를 검사하지 않았다. 엄격해지면 seed 가 거부되어 세션이 계속 죽는다."""
    key = f"live:{SESSION_ID}:cond:notanint:100:1:PivRevLE"
    assert _pine_trade_id_from_order_key(key, session_id=SESSION_ID) == "PivRevLE"

# 원장 → `run_live` 배선의 계약 — **이건 계측이 아니라 집행이다** (ADR-025 / BL-595)
"""`_conditional_fills_from_ledger` / `_capture_ledger_shadow` / `_count_ledger_fill_census`.

이 스위트가 지키는 계약 넷:

1. ★**「모른다」와 「비었다」를 접지 않는다.** `None` = 원장을 온전히 못 봤다 → 그 tick 만
   현행 시뮬로 되돌린다. `()` = 원장이 답했는데 조건부 체결이 없다 → 엔진은 아무것도
   체결하지 않는다. 접으면 판정 불가가 flat 으로 위장돼 **있는 포지션을 통째로 잃는다.**
2. ★**조건부 진입만 대상이다.** 시장가 진입(`:entry:`)·청산(`:close:`)·남의 세션 주문은
   증언에 넣지 않는다. 넣으면 이 권한이 자기 범위 밖 경로를 조용히 바꾼다.
3. ★**조회 실패는 fail-open** 이다(이 레포가 H8 로 이름 붙인 자리의 거울상 — 여기서는
   집행이 실패를 흡수한다). 다만 **조용히** 되돌리지 않는다 — 카운터로 표면화한다.
4. ★census 는 **엔진이 만든 값을 그대로** 올린다. 모르는 키를 무해 취급하지 않는다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.tasks.live_signal import (
    _capture_ledger_shadow,
    _conditional_fills_from_ledger,
    _count_ledger_fill_census,
)
from src.trading.models import OrderSide

SESSION_ID = UUID("4bf679af-e535-402e-ba8e-8b91cebe3b51")
OTHER_SESSION_ID = UUID("a16aa640-a045-4b5f-9c39-17c77a2dec1c")
_FILLED_AT = datetime(2026, 8, 5, 9, 11, tzinfo=UTC)


def _sess() -> Any:
    return SimpleNamespace(
        id=SESSION_ID,
        symbol="BTC/USDT",
        exchange_account_id=uuid4(),
        strategy_id=uuid4(),
        user_id=uuid4(),
        created_at=datetime(2026, 8, 5, 0, 0, tzinfo=UTC),
        deactivated_at=None,
    )


def _fill(
    *,
    key: str | None,
    quantity: Decimal | None = Decimal("0.058"),
    price: Decimal | None = Decimal("64073.1"),
) -> Any:
    # ★`derive_open_position`(같은 조회를 쓰는 슬라이스 1 계측)이 `side`/`reduce_only` 를
    #   읽는다. 빠뜨리면 `_capture_ledger_shadow` 의 try 블록이 통째로 실패해 이 테스트가
    #   "조회 실패" 를 보게 되고 판별력이 0 이 된다(`test_ledger_shadow.py` 가 적어 둔 함정).
    return SimpleNamespace(
        order_id=uuid4(),
        idempotency_key=key,
        side=OrderSide.buy,
        filled_quantity=quantity,
        filled_price=price,
        filled_at=_FILLED_AT,
        reduce_only=False,
    )


def _cond_key(session_id: UUID = SESSION_ID, *, trade_id: str = "PivRevLE") -> str:
    """실제 원장 키 형식 — `live:<sess>:cond:<bar_epoch>:<트리거>:<수량>:<trade_id>`."""
    return f"live:{session_id}:cond:1785920880:64139.2:0.058:{trade_id}"


# ── _conditional_fills_from_ledger ────────────────────────────────────────────


def test_conditional_entry_fill_is_witnessed() -> None:
    witnessed = _conditional_fills_from_ledger(
        [_fill(key=_cond_key())], session_id=SESSION_ID, overflowed=False
    )

    assert witnessed is not None
    assert [(item.trade_id, item.fill_price) for item in witnessed] == [("PivRevLE", 64073.1)]


def test_market_converted_conditional_entry_is_also_witnessed() -> None:
    """`condmkt` 도 조건부 계열이다 — 엔진 쪽 자리는 여전히 pending stop 이다."""
    key = f"live:{SESSION_ID}:condmkt:1785868560:64282.9:0.058:PivRevSE"
    witnessed = _conditional_fills_from_ledger(
        [_fill(key=key)], session_id=SESSION_ID, overflowed=False
    )

    assert witnessed is not None
    assert [item.trade_id for item in witnessed] == ["PivRevSE"]


@pytest.mark.parametrize(
    "key",
    [
        f"live:{SESSION_ID}:2026-08-05T09:11:00+00:00:0:entry:PivRevLE",  # 시장가 진입
        f"live:{SESSION_ID}:2026-08-05T09:11:00+00:00:1:close:PivRevLE",  # 청산
        "tv:webhook:whatever",  # 웹훅
        None,  # 수동 주문
    ],
)
def test_non_conditional_keys_are_not_witnessed(key: str | None) -> None:
    """★범위를 넘으면 이 권한이 남의 경로를 조용히 바꾼다."""
    assert (
        _conditional_fills_from_ledger([_fill(key=key)], session_id=SESSION_ID, overflowed=False)
        == ()
    )


def test_other_sessions_conditional_fill_is_not_witnessed() -> None:
    """같은 계정·심볼이라도 남의 세션 체결을 내 포지션으로 세면 안 된다."""
    assert (
        _conditional_fills_from_ledger(
            [_fill(key=_cond_key(OTHER_SESSION_ID))], session_id=SESSION_ID, overflowed=False
        )
        == ()
    )


def test_empty_ledger_is_a_verdict_not_ignorance() -> None:
    """★`()` 와 `None` 을 접지 않는다 — 여기가 그 경계다."""
    assert _conditional_fills_from_ledger([], session_id=SESSION_ID, overflowed=False) == ()


def test_overflow_is_undecidable() -> None:
    """부분 원장으로 「증언이 없다」를 말하면 엔진이 있는 포지션을 잃는다."""
    assert (
        _conditional_fills_from_ledger(
            [_fill(key=_cond_key())], session_id=SESSION_ID, overflowed=True
        )
        is None
    )


@pytest.mark.parametrize("price", [None, Decimal("0"), Decimal("-1")])
def test_unreadable_fill_price_is_undecidable(price: Decimal | None) -> None:
    """★그 한 건만 버리면 그 진입이 조용히 사라진다 — 전체를 판정 불가로 떨어뜨린다."""
    assert (
        _conditional_fills_from_ledger(
            [_fill(key=_cond_key(), price=price)], session_id=SESSION_ID, overflowed=False
        )
        is None
    )


@pytest.mark.parametrize("quantity", [None, Decimal("0")])
def test_zero_quantity_row_is_not_a_fill(quantity: Decimal | None) -> None:
    """체결분이 없는 취소·거절 행은 체결이 아니다 — 판정 불가도 아니다."""
    assert (
        _conditional_fills_from_ledger(
            [_fill(key=_cond_key(), quantity=quantity)], session_id=SESSION_ID, overflowed=False
        )
        == ()
    )


# ── _capture_ledger_shadow — 집행 필드 ────────────────────────────────────────


def _patch_exchange(monkeypatch: pytest.MonkeyPatch) -> None:
    import src.trading.services.account_service as account_service_module

    class _Service:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None: ...

        async def get_credentials_for_order(self, _account_id: Any) -> Any:
            return MagicMock()

    monkeypatch.setattr(account_service_module, "ExchangeAccountService", _Service)


@pytest.mark.asyncio
async def test_capture_carries_the_conditional_fills(monkeypatch: pytest.MonkeyPatch) -> None:
    """★정상 경로 — 이게 없으면 아래 실패-흡수 테스트가 「무엇이 실패하든 통과」로 퇴화한다."""
    import src.trading.repositories.order_repository as order_repo_module

    repo = MagicMock()
    repo.list_fills_since = AsyncMock(return_value=[_fill(key=_cond_key())])
    monkeypatch.setattr(order_repo_module, "OrderRepository", lambda _s: repo)
    _patch_exchange(monkeypatch)

    shadow = await _capture_ledger_shadow(_sess(), session=MagicMock(), account_repo=MagicMock())

    assert shadow.conditional_fills is not None
    assert [item.trade_id for item in shadow.conditional_fills] == ["PivRevLE"]


@pytest.mark.asyncio
async def test_capture_falls_back_to_none_when_the_ledger_is_unreadable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★fail-open — 조회가 터지면 `None` 이고, 호출부는 그 tick 만 현행 시뮬로 되돌린다.

    여기서 `()` 를 내면 「원장이 답했는데 체결이 없다」가 되어 **엔진이 포지션을 통째로 잃는다.**
    """
    import src.trading.repositories.order_repository as order_repo_module

    class _Boom:
        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("ledger down")

    monkeypatch.setattr(order_repo_module, "OrderRepository", _Boom)
    shadow = await _capture_ledger_shadow(_sess(), session=MagicMock(), account_repo=MagicMock())

    assert shadow.conditional_fills is None


# ── _count_ledger_fill_census ─────────────────────────────────────────────────


def _counts(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    import src.tasks.live_signal as live_signal_module

    seen: list[str] = []
    monkeypatch.setattr(
        live_signal_module,
        "_count_safely",
        lambda _counter, **labels: seen.append(labels["outcome"]),
    )
    return seen


def test_census_is_counted_once_per_occurrence(monkeypatch: pytest.MonkeyPatch) -> None:
    seen = _counts(monkeypatch)
    _count_ledger_fill_census({"ledger_fill_census": {"agree": 2, "ledger_only_adopted": 1}})

    assert sorted(seen) == ["agree", "agree", "ledger_only_adopted"]


def test_unknown_census_key_is_not_silently_dropped(monkeypatch: pytest.MonkeyPatch) -> None:
    """★[BL-596] 이 게이트에서 등재한 결함(모르는 라벨을 조용히 무해 취급)을 여기 안 만든다."""
    seen = _counts(monkeypatch)
    _count_ledger_fill_census({"ledger_fill_census": {"미래의_새_라벨": 1}})

    assert seen == ["미래의_새_라벨"]


@pytest.mark.parametrize(
    "report",
    [None, "문자열", {}, {"ledger_fill_census": None}, {"ledger_fill_census": {"agree": 0}}],
)
def test_malformed_census_is_absorbed(monkeypatch: pytest.MonkeyPatch, report: object) -> None:
    """계측이 던지면 그 tick 의 claim 이 rollback 되어 매-tick 크래시 루프가 된다."""
    seen = _counts(monkeypatch)
    _count_ledger_fill_census(report)

    assert seen == []

# 확정 손익 refresh 의 **진입 게이트** — 무엇이 들어오고 무엇이 막히는가 ([BL-733]).
"""`_refresh_closed_pnl_with_session` 의 `not_reduce_only` 갈래 회귀.

## ★왜 새 파일인가 — 이 게이트에는 테스트가 **하나도 없었다**

2026-08-15 실측: `not_reduce_only` 를 단언하는 테스트가 레포 전체에 **0건**이었다.
[BL-733] 이 그 게이트에 갈래를 하나 더 여는데, 없애도 아무 테스트가 red 가 되지 않는
상태였다(변이 M4 → 31 passed). 완화하는 쪽만 테스트하고 **막는 쪽을 안 재면**, 다음 사람이
「어차피 안 걸리네」 하고 필터를 지운다. 그것이 이 항목이 경고하는 바로 그 사고다.

## 계약 셋

1. **순수 선물 entry 는 막힌다** — 열면 `closed-pnl` 원장에 대응 행이 없어 `transient`
   4회 재시도 뒤 `_alert_closed_pnl_unbackfilled` 운영자 알림이 난다.
2. **reduce-only 는 들어온다** — 종전 동작. 이 갈래를 깨면 청산 손익이 전부 추정치로 남는다.
3. **반전으로 증명된 leg 는 들어온다** — 반전에는 `reduce_only` 를 걸 수 없으므로(ADR-032)
   `reversal=True` 가 유일한 통로다. 판정은 `_measure_conditional_reversal_with_session` 이
   체결 후 포지션으로 이미 했고 여기서 재조회하지 않는다.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.tasks.test_closed_pnl_refresh_commits import (
    _account,
    _order,
    _patch_crypto,
    _sessionmaker,
)


def _snapshot(value: str = "-4.2") -> Any:
    from src.trading.providers import ClosedPnlSnapshot

    return ClosedPnlSnapshot("bybit-close-1", Decimal(value), None, None, None)


def _provider(snapshot: Any = None) -> MagicMock:
    return MagicMock(fetch_closed_pnl=AsyncMock(return_value=snapshot))


def _install(monkeypatch: pytest.MonkeyPatch, order: Any) -> MagicMock:
    """주문 조회·계정 조회·복호화를 통과시켜 **게이트 판정만** 남긴다."""
    import src.tasks.trading as trading_mod

    repo = MagicMock(
        get_by_id=AsyncMock(return_value=order),
        backfill_exchange_realized_pnl=AsyncMock(return_value=1),
        commit=AsyncMock(),
    )
    monkeypatch.setattr(trading_mod, "OrderRepository", lambda _s: repo)
    _patch_crypto(monkeypatch)
    return repo


@pytest.mark.asyncio
async def test_plain_entry_is_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    """계약 1 — 순수 선물 entry(`reduce_only=False`, 반전 아님)는 **막힌다**.

    ★거래소를 **부르지 않았다는 것**까지 단언한다. `skipped` 문자열만 재면 게이트를 지나
    조회한 뒤 뒤늦게 skip 하는 판본도 통과한다 — 그러면 거짓 알림은 그대로 난다.
    """
    import src.tasks.trading as trading_mod

    order = _order()
    order.reduce_only = False
    _install(monkeypatch, order)
    provider = _provider(_snapshot())
    session = MagicMock()
    session.get = AsyncMock(return_value=_account())

    result = await trading_mod._refresh_closed_pnl_with_session(
        order.id, _sessionmaker([session]), provider=provider
    )

    assert result["skipped"] == "not_reduce_only"
    provider.fetch_closed_pnl.assert_not_awaited()


@pytest.mark.asyncio
async def test_reduce_only_still_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    """계약 2 — reduce-only 는 종전대로 통과한다 (완화가 기존 갈래를 깨지 않았다)."""
    import src.tasks.trading as trading_mod

    order = _order()  # reduce_only=True 가 기본
    _install(monkeypatch, order)
    provider = _provider(_snapshot())
    first, second = MagicMock(), MagicMock()
    first.get = AsyncMock(return_value=_account())
    second.commit = AsyncMock()

    result = await trading_mod._refresh_closed_pnl_with_session(
        order.id, _sessionmaker([first, second]), provider=provider
    )

    assert "skipped" not in result
    provider.fetch_closed_pnl.assert_awaited_once()


@pytest.mark.asyncio
async def test_confirmed_reversal_passes_without_reduce_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """계약 3 — `reversal=True` 면 `reduce_only=False` 여도 통과한다 ([BL-733] 이 연 갈래).

    ★반전에는 `reduce_only` 를 걸 수 없다(ADR-032) — 이 인자가 유일한 통로다.
    """
    import src.tasks.trading as trading_mod

    order = _order()
    order.reduce_only = False
    _install(monkeypatch, order)
    provider = _provider(_snapshot())
    first, second = MagicMock(), MagicMock()
    first.get = AsyncMock(return_value=_account())
    second.commit = AsyncMock()

    result = await trading_mod._refresh_closed_pnl_with_session(
        order.id, _sessionmaker([first, second]), provider=provider, reversal=True
    )

    assert "skipped" not in result
    provider.fetch_closed_pnl.assert_awaited_once()


@pytest.mark.asyncio
async def test_reversal_flag_defaults_to_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """★큐 하위호환 — 인자를 안 주면 종전 동작(reduce-only 만)이다.

    배포 시점에 큐에 남아 있는 옛 메시지는 `reversal` 을 싣지 않는다. 기본값이 True 쪽으로
    새면 그 메시지들이 순수 entry 에 대해 거짓 알림을 낸다.
    """
    import src.tasks.trading as trading_mod

    order = _order()
    order.reduce_only = False
    _install(monkeypatch, order)
    provider = _provider(_snapshot())
    session = MagicMock()
    session.get = AsyncMock(return_value=_account())

    result = await trading_mod._refresh_closed_pnl_with_session(
        order.id, _sessionmaker([session]), provider=provider
    )

    assert result["skipped"] == "not_reduce_only"


@pytest.mark.asyncio
async def test_reversal_without_ledger_row_does_not_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """계약 4 — 반전 경로에서 원장이 비면 **재시도하지 않는다** (2026-08-15 codex Spec-1).

    `_reversal_bucket_at_fill` 는 **알려진 위양성**을 갖는다 — 조건부 주문 등재 뒤 같은 방향
    포지션이 새로 열리고 포지션 조회가 체결 전 스냅샷이면 증량 entry 가 반전으로 잡힌다.
    단일 스냅샷으로는 원리적으로 구별 불가라 그 함수가 고의로 남긴 한계다.

    그 휴리스틱을 `transient` 권한까지 승격하면 **정상 entry 가 4회 재시도 뒤 운영자 알림**을
    낸다 — [BL-733] 이 막으려던 사고 그 자체다. 그래서 반전 경로의 원장 부재는 `skipped` 이고
    5분 스윕이 받는다. **판정이 틀렸을 때의 대가를 「늦음」으로 묶어 두는 것**이 이 계약이다.
    """
    import src.tasks.trading as trading_mod

    order = _order()
    order.reduce_only = False
    _install(monkeypatch, order)
    provider = _provider(None)  # 원장에 대응 행이 없다
    first, second = MagicMock(), MagicMock()
    first.get = AsyncMock(return_value=_account())
    second.commit = AsyncMock()

    result = await trading_mod._refresh_closed_pnl_with_session(
        order.id, _sessionmaker([first, second]), provider=provider, reversal=True
    )

    assert result["skipped"] == "reversal_pending_ledger"
    assert "transient" not in result


@pytest.mark.asyncio
async def test_reduce_only_without_ledger_row_still_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """★음성 대조 — reduce-only 는 종전대로 `transient` 다 (재시도 사다리 보존).

    이것이 없으면 「반전만 예외」가 아니라 「전부 재시도 없음」으로 넓힌 판본도 통과한다.
    reduce-only 청산은 원장에 **반드시** 대응 행이 생기므로, 없으면 그것은 정산 지연이고
    재시도가 옳다.
    """
    import src.tasks.trading as trading_mod

    order = _order()  # reduce_only=True
    _install(monkeypatch, order)
    provider = _provider(None)
    first, second = MagicMock(), MagicMock()
    first.get = AsyncMock(return_value=_account())
    second.commit = AsyncMock()

    result = await trading_mod._refresh_closed_pnl_with_session(
        order.id, _sessionmaker([first, second]), provider=provider
    )

    assert result["transient"] == "closed_pnl_not_yet_available"

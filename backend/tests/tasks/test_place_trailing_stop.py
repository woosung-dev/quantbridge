# STEP B — place_trailing_stop core: stale-position 가드 + set_trading_stop + 실패 분류.
"""체결(fill-transition) 후 native trailing-stop 부착. winner-only enqueue 라 멱등.
money-path: 무방비 방지 — 성공/skip 분류 + network 실패는 raise(상위 retry+alert).
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.trading.exceptions import ProviderError
from src.trading.models import OrderSide
from src.trading.providers import PositionInfo


def _provider(*, pos, set_side_effect=None):
    p = AsyncMock()
    p.fetch_position = AsyncMock(return_value=pos)
    p.set_trading_stop = AsyncMock(side_effect=set_side_effect)
    return p


async def _run(provider, *, entry_side=OrderSide.buy, distance=Decimal("3.0")):
    from src.tasks.trading import _do_place_trailing_stop

    return await _do_place_trailing_stop(
        order_id=uuid4(),
        symbol="BTC/USDT",
        entry_side=entry_side,
        distance=distance,
        creds=object(),
        provider=provider,
    )


async def test_place_happy_long():
    """long 진입(buy) → 포지션 long → exit=sell 로 trailing 부착."""
    p = _provider(pos=PositionInfo(size=Decimal("0.001"), side="long"))
    res = await _run(p, entry_side=OrderSide.buy)
    assert res == {"placed": True}
    # exit_side=sell, qty=현재 포지션 size, distance 전달.
    p.set_trading_stop.assert_awaited_once()
    kw = p.set_trading_stop.await_args.kwargs
    assert kw["symbol"] == "BTC/USDT"
    assert kw["side"] == OrderSide.sell
    assert kw["qty"] == Decimal("0.001")
    assert kw["distance"] == Decimal("3.0")


async def test_place_happy_short():
    """short 진입(sell) → 포지션 short → exit=buy."""
    p = _provider(pos=PositionInfo(size=Decimal("0.5"), side="short"))
    res = await _run(p, entry_side=OrderSide.sell)
    assert res == {"placed": True}
    assert p.set_trading_stop.await_args.kwargs["side"] == OrderSide.buy


async def test_skip_position_flat():
    """EC-2 — 체결→placement 사이 포지션 닫힘(flat) → skip, set_trading_stop 미호출."""
    p = _provider(pos=None)
    res = await _run(p)
    assert res == {"skipped": "position_flat"}
    p.set_trading_stop.assert_not_awaited()


async def test_skip_position_mismatch_flip():
    """EC-2 — long 진입인데 현재 포지션이 short(close+reopen flip) → stale 차단, 미부착."""
    p = _provider(pos=PositionInfo(size=Decimal("0.001"), side="short"))
    res = await _run(p, entry_side=OrderSide.buy)
    assert res == {"skipped": "position_mismatch"}
    p.set_trading_stop.assert_not_awaited()


async def test_position_zero_race_benign():
    """EC-2 — fetch 후 set 전 포지션 0 (retCode 110017) → benign skip, raise 안 함."""
    p = _provider(
        pos=PositionInfo(size=Decimal("0.001"), side="long"),
        set_side_effect=ProviderError("InvalidOrder: 110017 position is zero"),
    )
    res = await _run(p)
    assert res == {"skipped": "position_zero"}


async def test_network_failure_raises_for_retry():
    """network/exchange 실패 = 포지션 무방비 → raise(상위 task 가 retry + critical alert)."""
    p = _provider(
        pos=PositionInfo(size=Decimal("0.001"), side="long"),
        set_side_effect=ProviderError("RequestTimeout: connection lost"),
    )
    with pytest.raises(ProviderError):
        await _run(p)


def test_enqueue_gates_on_trailing_intent(monkeypatch):
    """3 fill winner(동기/WS/watchdog)가 공유하는 enqueue helper — trailing 의도만 발화."""
    from types import SimpleNamespace

    from src.tasks import trading as t

    calls: list[dict] = []
    monkeypatch.setattr(
        t.place_trailing_stop_task, "apply_async", lambda **kw: calls.append(kw)
    )
    t._enqueue_trailing_if_intended(
        SimpleNamespace(id=uuid4(), trailing_stop=Decimal("3.0"))
    )
    assert len(calls) == 1 and calls[0]["countdown"] == 2
    # trailing 의도 없으면(close/reduce-only 등) enqueue 안 함.
    t._enqueue_trailing_if_intended(SimpleNamespace(id=uuid4(), trailing_stop=None))
    assert len(calls) == 1

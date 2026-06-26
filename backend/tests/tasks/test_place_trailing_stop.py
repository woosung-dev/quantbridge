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


class _FakeSession:
    def __init__(self, account):
        self._account = account

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, _model, _id):
        return self._account


def _patch_session_wrapper(monkeypatch, *, order, account):
    from types import SimpleNamespace

    from src.tasks import trading as t

    monkeypatch.setattr(
        t, "OrderRepository", lambda _s: SimpleNamespace(get_by_id=AsyncMock(return_value=order))
    )
    monkeypatch.setattr(
        t, "EncryptionService", lambda _k: SimpleNamespace(decrypt=lambda x: "pt")
    )
    return lambda: _FakeSession(account)


def _order(**kw):
    from types import SimpleNamespace

    base = dict(
        id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        side=OrderSide.buy,
        leverage=5,
        trailing_stop=Decimal("3.0"),
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _account(exchange):
    from types import SimpleNamespace

    from src.trading.models import ExchangeMode

    return SimpleNamespace(
        exchange=exchange,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"x",
        api_secret_encrypted=b"y",
        passphrase_encrypted=None,
    )


async def test_session_wrapper_skips_non_bybit(monkeypatch):
    """P2(codex) — 비-Bybit 계정 주문에 trailing_stop 붙어도 BybitFuturesProvider 발주 차단."""
    from src.tasks.trading import _place_trailing_stop_with_session
    from src.trading.models import ExchangeName

    order = _order()
    sm = _patch_session_wrapper(monkeypatch, order=order, account=_account(ExchangeName.okx))
    provider = _provider(pos=PositionInfo(size=Decimal("0.001"), side="long"))
    res = await _place_trailing_stop_with_session(order.id, sm, provider=provider)
    assert res == {"skipped": "unsupported_exchange"}
    provider.fetch_position.assert_not_awaited()
    provider.set_trading_stop.assert_not_awaited()


async def test_session_wrapper_bybit_futures_proceeds(monkeypatch):
    """Bybit futures(leverage 有) → placement 진행."""
    from src.tasks.trading import _place_trailing_stop_with_session
    from src.trading.models import ExchangeName

    order = _order()
    sm = _patch_session_wrapper(monkeypatch, order=order, account=_account(ExchangeName.bybit))
    provider = _provider(pos=PositionInfo(size=Decimal("0.001"), side="long"))
    res = await _place_trailing_stop_with_session(order.id, sm, provider=provider)
    assert res == {"placed": True}
    provider.set_trading_stop.assert_awaited_once()


async def test_alert_trailing_unprotected_fires_critical(monkeypatch):
    """Opus B/A — 최종 실패 시 critical alert(무신호 차단). 메시지는 고정 SL floor 명시."""
    from src.tasks import trading as t

    sent: list[dict] = []

    async def fake_alert(settings, *, title, message, context):
        sent.append({"title": title, "message": message, "context": context})
        return True

    monkeypatch.setattr(t, "send_critical_alert", fake_alert)
    await t._alert_trailing_unprotected(uuid4(), "RequestTimeout: connection lost")
    assert len(sent) == 1
    assert "TRAILING" in sent[0]["title"]
    assert "RequestTimeout" in sent[0]["message"]
    # P3 — 완전 무방비 아님(고정 bracket SL 유효) 명시.
    assert "SL" in sent[0]["message"]


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

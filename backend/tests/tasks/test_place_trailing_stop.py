# STEP B — place_trailing_stop core: stale-position 가드 + set_trading_stop + 실패 분류.
"""체결(fill-transition) 후 native trailing-stop 부착. winner-only enqueue 라 멱등.
money-path: 무방비 방지 — 성공/skip 분류 + network 실패는 raise(상위 retry+alert).
"""
from __future__ import annotations

import contextlib
from decimal import Decimal
from unittest.mock import AsyncMock, Mock
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


async def test_position_not_visible_returns_transient():
    """STEP B — fetch_position None 은 "2s 내 청산"과 "fill REST 미전파"가 구분 불가 →
    즉시 flat 단정 금지, transient 분류 반환(상위 task 가 bounded 재시도 후 concede)."""
    p = _provider(pos=None)
    res = await _run(p)
    assert res == {"transient": "position_not_visible"}
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

    base = {
        "id": uuid4(),
        "exchange_account_id": uuid4(),
        "symbol": "BTC/USDT",
        "side": OrderSide.buy,
        "leverage": 5,
        "trailing_stop": Decimal("3.0"),
    }
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
        SimpleNamespace(id=uuid4(), trailing_stop=Decimal("3.0"), reduce_only=False)
    )
    assert len(calls) == 1 and calls[0]["countdown"] == 2
    # trailing 의도 없으면 enqueue 안 함.
    t._enqueue_trailing_if_intended(
        SimpleNamespace(id=uuid4(), trailing_stop=None, reduce_only=False)
    )
    assert len(calls) == 1
    # P2(codex/Opus B) — reduce_only(close/manual) 주문은 trailing 있어도 skip.
    t._enqueue_trailing_if_intended(
        SimpleNamespace(id=uuid4(), trailing_stop=Decimal("3.0"), reduce_only=True)
    )
    assert len(calls) == 1


# ---------------------------------------------------------------------------
# place_trailing_stop_task 본문 — retry / backoff / exhaustion→alert / flat-retry concede.
# (qa-P2: 실패-표면화 코어가 무테스트였음 + STEP B fast-fill flat-retry fix 커버)
# ---------------------------------------------------------------------------
def _fake_worker_loop(behaviors):
    """run_in_worker_loop 대체 — 전달된 coroutine 을 닫고 사전 정의 동작을 순서대로 수행."""
    seq = iter(behaviors)

    def _run(coro):
        with contextlib.suppress(Exception):
            coro.close()
        b = next(seq)
        if isinstance(b, BaseException):
            raise b
        return b

    return _run


def _drive_task(monkeypatch, *, retries, behaviors):
    """place_trailing_stop_task 본문을 fake self(request.retries) + fake worker-loop 로 구동.

    반환 = (result_or_None, retry_spy, raised_Retry_or_None).
    """
    from celery.exceptions import Retry

    from src.tasks import _worker_loop as wl
    from src.tasks.trading import place_trailing_stop_task as task

    monkeypatch.setattr(wl, "run_in_worker_loop", _fake_worker_loop(behaviors))
    monkeypatch.setattr(task, "retry", Mock(side_effect=lambda **kw: Retry()))
    task.push_request(retries=retries)
    try:
        try:
            return task.run(str(uuid4())), task.retry, None
        except Retry as r:
            return None, task.retry, r
    finally:
        task.pop_request()


def test_task_premature_flat_retries_within_limit(monkeypatch):
    """STEP B — transient(position_not_visible) + retries<limit → bounded 재시도(backoff 10s)."""
    _res, retry, raised = _drive_task(
        monkeypatch, retries=0, behaviors=[{"transient": "position_not_visible"}]
    )
    assert raised is not None  # Retry 발생(재시도)
    retry.assert_called_once()
    assert retry.call_args.kwargs["countdown"] == 10  # base * 2**0


def test_task_premature_flat_concedes_after_limit(monkeypatch):
    """STEP B — retries>=limit 면 진짜 flat 으로 concede(benign skip, 재시도/alert 없음)."""
    res, retry, raised = _drive_task(
        monkeypatch, retries=2, behaviors=[{"transient": "position_not_visible"}]
    )
    assert raised is None
    assert res["skipped"] == "position_flat"
    retry.assert_not_called()


def test_task_network_failure_retries_with_backoff(monkeypatch):
    """qa-P2 — network 실패 + retries<MAX → self.retry(exc, backoff). retries 1 → countdown 20s."""
    _res, retry, raised = _drive_task(
        monkeypatch, retries=1, behaviors=[ProviderError("RequestTimeout: lost")]
    )
    assert raised is not None
    assert retry.call_args.kwargs["countdown"] == 20  # base * 2**1
    assert retry.call_args.kwargs["exc"] is not None


def test_task_exhaustion_fires_alert_no_retry(monkeypatch):
    """qa-P2 — retries>=MAX → critical alert + {"failed":...} 반환, 재시도 안 함(무신호 차단)."""
    from src.tasks.trading import _TRAILING_MAX_RETRIES

    res, retry, raised = _drive_task(
        monkeypatch,
        retries=_TRAILING_MAX_RETRIES,  # >= MAX
        behaviors=[ProviderError("RequestTimeout: lost"), None],  # place raise, alert 반환
    )
    assert raised is None
    assert res["failed"] == "trailing_unprotected"
    retry.assert_not_called()


def test_task_contract_error_no_retry_immediate_alert(monkeypatch):
    """BL-372 — TrailingContractError(버전/degenerate/hedge)는 재시도 없이 즉시 alert + give up."""
    from src.tasks import trading as t
    from src.trading.exceptions import TrailingContractError

    alert_spy = Mock(return_value=None)
    monkeypatch.setattr(t, "_alert_trailing_unprotected", alert_spy)
    res, retry, raised = _drive_task(
        monkeypatch,
        retries=0,  # 아직 소진 전이지만 contract 에러라 재시도 안 함
        behaviors=[TrailingContractError("ccxt_unvalidated", "ccxt 9.9.9 ..."), None],
    )
    assert raised is None
    assert res["failed"] == "ccxt_unvalidated"
    retry.assert_not_called()
    called_reason = alert_spy.call_args.kwargs.get("reason") or alert_spy.call_args.args[1]
    assert called_reason == "ccxt_unvalidated"


def test_task_exhaustion_alert_classified_taxonomy(monkeypatch):
    """BL-372 #7 — 소진 alert reason 은 정확한 분류 문자열, 원본(누설) 미포함."""
    from src.tasks import trading as t
    from src.tasks.trading import _TRAILING_MAX_RETRIES
    from src.trading.exceptions import ProviderError

    alert_spy = Mock(return_value=None)
    monkeypatch.setattr(t, "_alert_trailing_unprotected", alert_spy)
    # reject 류 — 원본에 secret-ish payload 가 있어도 분류 문자열만 전송.
    _drive_task(
        monkeypatch,
        retries=_TRAILING_MAX_RETRIES,
        behaviors=[ProviderError("InvalidOrder: bybit {secret-ish payload} retCode=10001"), None],
    )
    r1 = alert_spy.call_args.kwargs.get("reason") or alert_spy.call_args.args[1]
    assert r1 == "exchange_rejected"
    assert "secret-ish" not in r1
    # network 류
    _drive_task(
        monkeypatch,
        retries=_TRAILING_MAX_RETRIES,
        behaviors=[ProviderError("RequestTimeout: connection lost"), None],
    )
    r2 = alert_spy.call_args.kwargs.get("reason") or alert_spy.call_args.args[1]
    assert r2 == "network_error"

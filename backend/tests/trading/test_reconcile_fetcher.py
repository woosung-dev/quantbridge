# BL-308 — BybitReconcileFetcher coverage (0% → 커버). reconcile REST snapshot 어댑터 wiring 검증
"""BybitReconcileFetcher 단위 테스트 (Sprint 12 reconcile fetcher, BL-308 coverage gap).

CCXT 인스턴스 + EncryptionService 를 mock — 네트워크/복호화 없이 어댑터의 orchestration
(category 라우팅 / ephemeral client close / account 결박 / 복호화 호출)을 검증한다.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.trading import models
from src.trading.websocket import reconcile_fetcher
from src.trading.websocket.reconcile_fetcher import BybitReconcileFetcher


def _make_account() -> models.ExchangeAccount:
    return models.ExchangeAccount(
        id=uuid4(),
        user_id=uuid4(),
        exchange=models.ExchangeName.bybit,
        mode=models.ExchangeMode.demo,
        api_key_encrypted=b"enc-key",
        api_secret_encrypted=b"enc-secret",
    )


def _patch_ccxt(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    """reconcile_fetcher 의 ccxt_async.bybit 를 mock exchange 로 교체.

    P1-14 (S5-C): has['fetchCanceledOrders']=False 가 default — 기존 closed-only 테스트
    호환. 신규 union 테스트는 explicit 으로 has 와 fetch_canceled_orders 를 설정.
    """
    mock_exchange = MagicMock()
    mock_exchange.fetch_open_orders = AsyncMock(return_value=[{"id": "o1", "status": "open"}])
    mock_exchange.fetch_closed_orders = AsyncMock(return_value=[{"id": "c1", "status": "closed"}])
    mock_exchange.fetch_canceled_orders = AsyncMock(return_value=[])  # 기본은 빈 list
    mock_exchange.has = {"fetchCanceledOrders": False}  # default off
    mock_exchange.close = AsyncMock()
    mock_exchange.enable_demo_trading = MagicMock()  # _apply_bybit_env(demo) 호출
    monkeypatch.setattr(
        reconcile_fetcher.ccxt_async, "bybit", MagicMock(return_value=mock_exchange)
    )
    return mock_exchange


def _make_crypto() -> MagicMock:
    crypto = MagicMock()
    crypto.decrypt = MagicMock(side_effect=lambda b: f"dec:{b.decode()}")
    return crypto


@pytest.mark.asyncio
async def test_fetch_open_orders_routes_category_and_returns_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account = _make_account()
    mock_exchange = _patch_ccxt(monkeypatch)
    fetcher = BybitReconcileFetcher(account=account, crypto=_make_crypto())

    result = await fetcher.fetch_open_orders(account.id)

    assert result == [{"id": "o1", "status": "open"}]
    mock_exchange.fetch_open_orders.assert_awaited_once_with(None, params={"category": "linear"})
    mock_exchange.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_recent_orders_uses_closed_with_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account = _make_account()
    mock_exchange = _patch_ccxt(monkeypatch)
    fetcher = BybitReconcileFetcher(account=account, crypto=_make_crypto())

    result = await fetcher.fetch_recent_orders(account.id, limit=25)

    assert result == [{"id": "c1", "status": "closed"}]
    mock_exchange.fetch_closed_orders.assert_awaited_once_with(
        None, limit=25, params={"category": "linear"}
    )
    mock_exchange.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_build_exchange_decrypts_creds_and_configures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account = _make_account()
    bybit_cls = MagicMock(return_value=_patch_exchange())
    monkeypatch.setattr(reconcile_fetcher.ccxt_async, "bybit", bybit_cls)
    crypto = _make_crypto()
    fetcher = BybitReconcileFetcher(account=account, crypto=crypto, category="spot")

    await fetcher.fetch_open_orders(account.id)

    # 복호화 2회 (key + secret)
    assert crypto.decrypt.call_count == 2
    cfg = bybit_cls.call_args.args[0]
    assert cfg["apiKey"] == "dec:enc-key"
    assert cfg["secret"] == "dec:enc-secret"
    assert cfg["options"]["defaultType"] == "spot"
    assert cfg["options"]["testnet"] is False


@pytest.mark.asyncio
async def test_account_id_mismatch_logs_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account = _make_account()
    _patch_ccxt(monkeypatch)
    # caplog 은 full-suite 의 logging 설정에 영향받아 flaky → logger 직접 patch (deterministic).
    warn = MagicMock()
    monkeypatch.setattr(reconcile_fetcher.logger, "warning", warn)
    fetcher = BybitReconcileFetcher(account=account, crypto=_make_crypto())

    await fetcher.fetch_open_orders(uuid4())  # 다른 account_id

    assert warn.called
    assert "account_mismatch" in warn.call_args.args[0]


@pytest.mark.asyncio
async def test_close_called_even_on_fetch_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account = _make_account()
    mock_exchange = _patch_ccxt(monkeypatch)
    mock_exchange.fetch_open_orders = AsyncMock(side_effect=RuntimeError("ws boom"))
    fetcher = BybitReconcileFetcher(account=account, crypto=_make_crypto())

    with pytest.raises(RuntimeError, match="ws boom"):
        await fetcher.fetch_open_orders(account.id)

    mock_exchange.close.assert_awaited_once()  # finally 보장


@pytest.mark.asyncio
async def test_close_failure_swallowed(monkeypatch: pytest.MonkeyPatch) -> None:
    account = _make_account()
    mock_exchange = _patch_ccxt(monkeypatch)
    mock_exchange.close = AsyncMock(side_effect=RuntimeError("close fail"))
    fetcher = BybitReconcileFetcher(account=account, crypto=_make_crypto())

    # close 실패는 swallow (finally try/except) → fetch 결과 정상 반환
    result = await fetcher.fetch_open_orders(account.id)
    assert result == [{"id": "o1", "status": "open"}]


@pytest.mark.asyncio
async def test_recent_orders_account_id_mismatch_logs_warning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account = _make_account()
    _patch_ccxt(monkeypatch)
    warn = MagicMock()
    monkeypatch.setattr(reconcile_fetcher.logger, "warning", warn)
    fetcher = BybitReconcileFetcher(account=account, crypto=_make_crypto())

    await fetcher.fetch_recent_orders(uuid4())

    assert warn.called
    assert "account_mismatch" in warn.call_args.args[0]


@pytest.mark.asyncio
async def test_recent_orders_close_failure_swallowed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    account = _make_account()
    mock_exchange = _patch_ccxt(monkeypatch)
    mock_exchange.close = AsyncMock(side_effect=RuntimeError("close fail"))
    fetcher = BybitReconcileFetcher(account=account, crypto=_make_crypto())

    result = await fetcher.fetch_recent_orders(account.id)
    assert result == [{"id": "c1", "status": "closed"}]


# ── P1-14 (S5-C, BL-308 후속) — fetch_canceled_orders union ──


@pytest.mark.asyncio
async def test_fetch_recent_orders_unions_closed_and_canceled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P1-14 (S5-C): has['fetchCanceledOrders']=True → closed + canceled union 반환.

    Reconciler._find_match 가 canceled local active order 를 찾을 수 있도록 보장.
    Bybit V5/CCXT 표준 경로 — canceled 는 fetch_closed_orders 가 반환 안 함.
    """
    account = _make_account()
    mock_exchange = _patch_ccxt(monkeypatch)
    mock_exchange.has = {"fetchCanceledOrders": True}
    mock_exchange.fetch_canceled_orders = AsyncMock(
        return_value=[{"id": "x1", "status": "canceled"}]
    )
    fetcher = BybitReconcileFetcher(account=account, crypto=_make_crypto())

    result = await fetcher.fetch_recent_orders(account.id, limit=25)

    assert result == [
        {"id": "c1", "status": "closed"},
        {"id": "x1", "status": "canceled"},
    ]
    mock_exchange.fetch_closed_orders.assert_awaited_once_with(
        None, limit=25, params={"category": "linear"}
    )
    mock_exchange.fetch_canceled_orders.assert_awaited_once_with(
        None, limit=25, params={"category": "linear"}
    )
    mock_exchange.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_fetch_recent_orders_skips_canceled_when_unsupported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P1-14 (S5-C): has['fetchCanceledOrders']=False → fetch_canceled_orders 호출 X."""
    account = _make_account()
    mock_exchange = _patch_ccxt(monkeypatch)
    # 기본값이 False, 명시적으로 확인
    assert mock_exchange.has == {"fetchCanceledOrders": False}
    fetcher = BybitReconcileFetcher(account=account, crypto=_make_crypto())

    result = await fetcher.fetch_recent_orders(account.id)

    assert result == [{"id": "c1", "status": "closed"}]
    mock_exchange.fetch_canceled_orders.assert_not_awaited()


@pytest.mark.asyncio
async def test_fetch_recent_orders_canceled_failure_returns_closed_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """P1-14 (S5-C): fetch_canceled_orders 실패 시 closed-only graceful (silent X)."""
    account = _make_account()
    mock_exchange = _patch_ccxt(monkeypatch)
    mock_exchange.has = {"fetchCanceledOrders": True}
    mock_exchange.fetch_canceled_orders = AsyncMock(
        side_effect=RuntimeError("rate limit")
    )
    fetcher = BybitReconcileFetcher(account=account, crypto=_make_crypto())

    # closed 결과만 반환되어야 함 (RuntimeError 가 caller 까지 전파되지 않음)
    result = await fetcher.fetch_recent_orders(account.id)
    assert result == [{"id": "c1", "status": "closed"}]
    mock_exchange.fetch_canceled_orders.assert_awaited_once()
    mock_exchange.close.assert_awaited_once()


def _patch_exchange() -> MagicMock:
    ex = MagicMock()
    ex.fetch_open_orders = AsyncMock(return_value=[])
    ex.close = AsyncMock()
    ex.enable_demo_trading = MagicMock()
    return ex

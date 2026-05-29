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
    """reconcile_fetcher 의 ccxt_async.bybit 를 mock exchange 로 교체."""
    mock_exchange = MagicMock()
    mock_exchange.fetch_open_orders = AsyncMock(return_value=[{"id": "o1", "status": "open"}])
    mock_exchange.fetch_closed_orders = AsyncMock(return_value=[{"id": "c1", "status": "closed"}])
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


def _patch_exchange() -> MagicMock:
    ex = MagicMock()
    ex.fetch_open_orders = AsyncMock(return_value=[])
    ex.close = AsyncMock()
    ex.enable_demo_trading = MagicMock()
    return ex

# 라이브 세션 등록의 조건부 진입 허용 및 자본 기준선 게이트를 검증한다.
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.common.exceptions import AppException
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.exceptions import ProviderError
from src.trading.models import ExchangeAccount, ExchangeMode, ExchangeName
from src.trading.schemas import RegisterLiveSessionRequest
from src.trading.services.live_session_service import LiveSignalSessionService
from tests.trading.test_live_session_commits import _make_balance_service

_VALID_SETTINGS = {
    "schema_version": 1,
    "leverage": 2,
    "margin_mode": "cross",
    "position_size_pct": 10.0,
}
_STOP_ENTRY_SOURCE = (
    Path(__file__).parents[1] / "fixtures" / "pine_corpus_v2" / "s1_pbr.pine"
).read_text()
_MARKET_ENTRY_SOURCE = (
    Path(__file__).parents[3] / "frontend" / "public" / "samples" / "ema-crossover.pine"
).read_text()


def _svc(*, pine_source: str, balance_service: AsyncMock | None = None, active_count: int = 0):
    user_id = uuid4()
    strategy = Strategy(
        id=uuid4(),
        user_id=user_id,
        name="t",
        pine_source=pine_source,
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
        settings=_VALID_SETTINGS,
    )
    account = ExchangeAccount(
        id=uuid4(),
        user_id=user_id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"x",
        api_secret_encrypted=b"y",
    )
    repo = AsyncMock()
    repo.acquire_quota_lock = AsyncMock(return_value=None)
    repo.count_active_by_user = AsyncMock(return_value=active_count)
    repo.save = AsyncMock(return_value=object())
    account_repo = AsyncMock()
    account_repo.get_by_id = AsyncMock(return_value=account)
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=strategy)
    balance_service = balance_service or _make_balance_service()
    service = LiveSignalSessionService(
        repo=repo,
        account_repo=account_repo,
        strategy_repo=strategy_repo,
        balance_service=balance_service,
    )
    request = RegisterLiveSessionRequest(
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTCUSDT",
        interval="5m",
    )
    return service, repo, balance_service, user_id, request


def _allow_ticker_kick(monkeypatch: pytest.MonkeyPatch) -> None:
    from src.tasks.websocket_task import run_bybit_public_ticker_stream

    monkeypatch.setattr(run_bybit_public_ticker_stream, "delay", MagicMock())


@pytest.mark.asyncio
async def test_register_allows_stop_entry_strategy(monkeypatch: pytest.MonkeyPatch) -> None:
    """stop= 진입 전략도 조건부 주문 등재 경로로 세션을 등록한다."""
    service, repo, balance_service, user_id, request = _svc(pine_source=_STOP_ENTRY_SOURCE)
    _allow_ticker_kick(monkeypatch)

    await service.register(user_id, request)

    repo.save.assert_awaited_once()
    repo.commit.assert_awaited_once()
    balance_service.get_balance.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_allows_market_entry_strategy(monkeypatch: pytest.MonkeyPatch) -> None:
    """음성 대조군은 stop-entry 게이트가 모든 전략을 차단하지 않음을 증명한다."""
    service, repo, _balance_service, user_id, request = _svc(pine_source=_MARKET_ENTRY_SOURCE)
    _allow_ticker_kick(monkeypatch)

    await service.register(user_id, request)

    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.asyncio
async def test_register_rejects_when_balance_total_is_none() -> None:
    """총자본 미확인은 기준선 부재로 fail-closed 한다."""
    service, repo, _balance_service, user_id, request = _svc(
        pine_source=_MARKET_ENTRY_SOURCE,
        balance_service=_make_balance_service(total=None),
    )

    with pytest.raises(AppException) as exc_info:
        await service.register(user_id, request)

    assert exc_info.value.code == "sizing_baseline_unavailable"
    repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_register_rejects_when_balance_unsupported() -> None:
    """지원하지 않는 잔고 응답은 기준선으로 쓰지 않는다."""
    service, repo, _balance_service, user_id, request = _svc(
        pine_source=_MARKET_ENTRY_SOURCE,
        balance_service=_make_balance_service(supported=False, total=None),
    )

    with pytest.raises(AppException) as exc_info:
        await service.register(user_id, request)

    assert exc_info.value.code == "sizing_baseline_unavailable"
    repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_register_rejects_when_balance_is_zero() -> None:
    """0 총자본 경계도 기준선 부재로 거부한다."""
    service, repo, _balance_service, user_id, request = _svc(
        pine_source=_MARKET_ENTRY_SOURCE,
        balance_service=_make_balance_service(total=Decimal("0")),
    )

    with pytest.raises(AppException) as exc_info:
        await service.register(user_id, request)

    assert exc_info.value.code == "sizing_baseline_unavailable"
    repo.save.assert_not_called()


@pytest.mark.asyncio
async def test_register_persists_equity_baseline_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """등록 시 총자본 스냅샷이 세션에 저장된다."""
    service, repo, _balance_service, user_id, request = _svc(
        pine_source=_MARKET_ENTRY_SOURCE,
        balance_service=_make_balance_service(total=Decimal("1234.5")),
    )
    _allow_ticker_kick(monkeypatch)

    await service.register(user_id, request)

    saved_session = repo.save.await_args.args[0]
    assert saved_session.equity_baseline_usdt == Decimal("1234.5")


@pytest.mark.asyncio
async def test_register_snapshots_total_not_free(monkeypatch: pytest.MonkeyPatch) -> None:
    """열린 포지션 증거금이 빠진 free 대신 백테스트 init_cash 대응 total을 저장한다."""
    service, repo, _balance_service, user_id, request = _svc(
        pine_source=_MARKET_ENTRY_SOURCE,
        balance_service=_make_balance_service(total=Decimal("8192"), free=Decimal("4096")),
    )
    _allow_ticker_kick(monkeypatch)

    await service.register(user_id, request)

    saved_session = repo.save.await_args.args[0]
    assert saved_session.equity_baseline_usdt == Decimal("8192")
    assert saved_session.equity_baseline_usdt != Decimal("4096")


@pytest.mark.asyncio
async def test_register_balance_snapshot_awaited_once_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """정상 등록은 잔고 스냅샷을 정확히 한 번만 조회한다."""
    service, _repo, balance_service, user_id, request = _svc(pine_source=_MARKET_ENTRY_SOURCE)
    _allow_ticker_kick(monkeypatch)

    await service.register(user_id, request)

    balance_service.get_balance.assert_awaited_once()


@pytest.mark.asyncio
async def test_register_quota_exceeded_skips_exchange_roundtrip() -> None:
    """사전 quota 초과는 잔고 조회 없이 즉시 거부한다."""
    service, _repo, balance_service, user_id, request = _svc(
        pine_source=_MARKET_ENTRY_SOURCE,
        active_count=5,
    )

    with pytest.raises(AppException) as exc_info:
        await service.register(user_id, request)

    assert exc_info.value.code == "live_session_quota_exceeded"
    balance_service.get_balance.assert_not_awaited()


@pytest.mark.asyncio
async def test_register_maps_provider_error_to_422() -> None:
    """ProviderError는 사용자 조치 가능한 기준선 422로 표면화한다."""
    balance_service = _make_balance_service()
    balance_service.get_balance = AsyncMock(side_effect=ProviderError("CCXT unavailable"))
    service, _repo, _balance_service, user_id, request = _svc(
        pine_source=_MARKET_ENTRY_SOURCE,
        balance_service=balance_service,
    )

    with pytest.raises(AppException) as exc_info:
        await service.register(user_id, request)

    assert exc_info.value.code == "sizing_baseline_unavailable"
    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_register_forces_fresh_balance_not_cached() -> None:
    """BL-479 — 기준선 스냅샷은 15초 캐시를 물려받으면 안 된다.

    이 값은 한 번 찍으면 세션 내내 사이징 분모로 남는다. 입금 직후 세션을 시작하면
    입금 전 잔고로 세션 전체를 사이징하게 되므로 `force_refresh=True` 로 거래소를 직접 친다.
    """
    service, _repo, balance_service, user_id, request = _svc(pine_source=_MARKET_ENTRY_SOURCE)

    await service.register(user_id, request)

    balance_service.get_balance.assert_awaited_once()
    assert balance_service.get_balance.await_args.kwargs.get("force_refresh") is True

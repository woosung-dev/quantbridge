# Wave 0 W4 — 데모 안정화 readiness 게이트 (라이브 경로 한정) 테스트
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.exceptions import AccountModeNotAllowed, DemoAccountNotYetStable
from src.trading.models import ExchangeAccount, ExchangeMode, ExchangeName
from src.trading.schemas import RegisterLiveSessionRequest
from src.trading.services.live_session_service import (
    _MIN_DEMO_STABLE_DAYS,
    LiveSignalSessionService,
)

_VALID_SETTINGS = {
    "schema_version": 1,
    "leverage": 2,
    "margin_mode": "cross",
    "position_size_pct": 10.0,
}


def _strategy(user_id):
    return Strategy(
        id=uuid4(),
        user_id=user_id,
        name="t",
        pine_source="//@version=5\nstrategy('t')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
        settings=_VALID_SETTINGS,
    )


def _account(user_id, *, mode):
    return ExchangeAccount(
        id=uuid4(),
        user_id=user_id,
        exchange=ExchangeName.bybit,
        mode=mode,
        api_key_encrypted=b"x",
        api_secret_encrypted=b"y",
    )


def _req(strategy_id, account_id):
    return RegisterLiveSessionRequest(
        strategy_id=strategy_id,
        exchange_account_id=account_id,
        symbol="BTCUSDT",
        interval="5m",
    )


def _svc(*, strategy, account, created_at):
    repo = AsyncMock()
    repo.acquire_quota_lock = AsyncMock(return_value=None)
    repo.count_active_by_user = AsyncMock(return_value=0)
    account_repo = AsyncMock()
    account_repo.get_by_id = AsyncMock(return_value=account)
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=strategy)
    user_repo = AsyncMock()
    user_repo.get_created_at = AsyncMock(return_value=created_at)
    svc = LiveSignalSessionService(
        repo=repo,
        account_repo=account_repo,
        strategy_repo=strategy_repo,
        user_repo=user_repo,
    )
    return svc, repo, user_repo


@pytest.mark.asyncio
async def test_live_not_yet_stable_raises():
    """라이브 + 경과일 < N → DemoAccountNotYetStable (AccountModeNotAllowed 보다 먼저)."""
    user_id = uuid4()
    created = datetime.now(UTC) - timedelta(days=_MIN_DEMO_STABLE_DAYS - 1, hours=1)
    svc, repo, _ = _svc(
        strategy=_strategy(user_id),
        account=_account(user_id, mode=ExchangeMode.live),
        created_at=created,
    )
    with pytest.raises(DemoAccountNotYetStable) as ei:
        await svc.register(user_id, _req(uuid4(), uuid4()))
    assert ei.value.min_required == _MIN_DEMO_STABLE_DAYS
    assert ei.value.days_elapsed == _MIN_DEMO_STABLE_DAYS - 1
    repo.commit.assert_not_called()


@pytest.mark.asyncio
async def test_live_boundary_exactly_n_days_passes_gate():
    """경계: 정확히 N일 경과 → 게이트 통과 → 라이브 stub(AccountModeNotAllowed) 도달."""
    user_id = uuid4()
    created = datetime.now(UTC) - timedelta(days=_MIN_DEMO_STABLE_DAYS, hours=1)
    svc, repo, _ = _svc(
        strategy=_strategy(user_id),
        account=_account(user_id, mode=ExchangeMode.live),
        created_at=created,
    )
    with pytest.raises(AccountModeNotAllowed):
        await svc.register(user_id, _req(uuid4(), uuid4()))
    repo.commit.assert_not_called()


@pytest.mark.asyncio
async def test_demo_path_skips_gate_no_user_repo_call(monkeypatch: pytest.MonkeyPatch):
    """demo 경로 → readiness 미적용 → user_repo 미호출 → 정상 등록 commit."""
    user_id = uuid4()
    strategy = _strategy(user_id)
    account = _account(user_id, mode=ExchangeMode.demo)
    svc, repo, user_repo = _svc(strategy=strategy, account=account, created_at=None)
    repo.save = AsyncMock(return_value=object())
    from src.tasks.websocket_task import run_bybit_public_ticker_stream

    delay = MagicMock()
    monkeypatch.setattr(run_bybit_public_ticker_stream, "delay", delay)
    await svc.register(user_id, _req(strategy.id, account.id))
    user_repo.get_created_at.assert_not_called()
    repo.commit.assert_awaited_once()
    delay.assert_called_once_with()


@pytest.mark.asyncio
async def test_live_missing_created_at_fails_closed():
    """user.created_at None (조회 실패) → fail-closed → DemoAccountNotYetStable(days=0)."""
    user_id = uuid4()
    svc, repo, _ = _svc(
        strategy=_strategy(user_id),
        account=_account(user_id, mode=ExchangeMode.live),
        created_at=None,
    )
    with pytest.raises(DemoAccountNotYetStable) as ei:
        await svc.register(user_id, _req(uuid4(), uuid4()))
    assert ei.value.days_elapsed == 0
    repo.commit.assert_not_called()

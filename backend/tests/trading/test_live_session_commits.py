"""Sprint 26 — LiveSignalSessionService LESSON-019 commit-spy 회귀 테스트.

Sprint 6 (webhook_secret) → Sprint 13 (OrderService) → Sprint 15-A (ExchangeAccount)
패턴 4번째 재발 방어. AsyncMock spy 가 commit 누락 broken bug 의 본질을 직접 검증.

표준 reference: backend/tests/trading/test_webhook_secret_commits.py + test_strategy_commits.py.
"""

from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from src.strategy.exceptions import StrategyNotFoundError
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.exceptions import (
    AccountModeNotAllowed,
    InvalidStrategySettings,
    LiveSessionQuotaExceeded,
    StrategySettingsRequired,
)
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    LiveSignalInterval,
    LiveSignalSession,
)
from src.trading.schemas import RegisterLiveSessionRequest

_VALID_SETTINGS = {
    "schema_version": 1,
    "leverage": 2,
    "margin_mode": "cross",
    "position_size_pct": 10.0,
}


def _make_strategy(user_id, settings=_VALID_SETTINGS) -> Strategy:
    return Strategy(
        id=uuid4(),
        user_id=user_id,
        name="t",
        pine_source="//@version=5\nstrategy('t')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
        settings=settings,
    )


def _make_account(user_id, *, exchange=ExchangeName.bybit, mode=ExchangeMode.demo) -> ExchangeAccount:
    return ExchangeAccount(
        id=uuid4(),
        user_id=user_id,
        exchange=exchange,
        mode=mode,
        api_key_encrypted=b"x",
        api_secret_encrypted=b"y",
    )


def _make_session(user_id, strategy_id, account_id) -> LiveSignalSession:
    return LiveSignalSession(
        id=uuid4(),
        user_id=user_id,
        strategy_id=strategy_id,
        exchange_account_id=account_id,
        symbol="BTCUSDT",
        interval=LiveSignalInterval.m5,
    )


def _make_req(strategy_id, account_id) -> RegisterLiveSessionRequest:
    return RegisterLiveSessionRequest(
        strategy_id=strategy_id,
        exchange_account_id=account_id,
        symbol="BTCUSDT",
        interval="5m",
    )


@pytest.mark.asyncio
async def test_register_calls_repo_commit() -> None:
    """LESSON-019 spy: register() 정상 path 에서 repo.commit() 호출 강제.

    Sprint 6 (webhook_secret) / 13 (OrderService) / 15-A (ExchangeAccount) 4번째 재발 방어.
    """
    from src.trading.services.live_session_service import LiveSignalSessionService

    user_id = uuid4()
    strategy = _make_strategy(user_id)
    account = _make_account(user_id)
    saved = _make_session(user_id, strategy.id, account.id)

    repo = AsyncMock()
    repo.acquire_quota_lock = AsyncMock(return_value=None)
    repo.count_active_by_user = AsyncMock(return_value=0)
    repo.save = AsyncMock(return_value=saved)

    account_repo = AsyncMock()
    account_repo.get_by_id = AsyncMock(return_value=account)

    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=strategy)

    svc = LiveSignalSessionService(
        repo=repo, account_repo=account_repo, strategy_repo=strategy_repo
    )

    req = _make_req(strategy.id, account.id)
    result = await svc.register(user_id, req)

    repo.save.assert_awaited_once()
    repo.commit.assert_awaited_once()  # ← broken bug 재발 방어
    assert result is saved


@pytest.mark.asyncio
async def test_register_strategy_not_found_does_not_commit() -> None:
    """ownership 위반 / 미존재 → StrategyNotFoundError + commit 0 (의도치 않은 변경 차단)."""
    from src.trading.services.live_session_service import LiveSignalSessionService

    user_id = uuid4()
    repo = AsyncMock()
    account_repo = AsyncMock()
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=None)

    svc = LiveSignalSessionService(
        repo=repo, account_repo=account_repo, strategy_repo=strategy_repo
    )

    req = _make_req(uuid4(), uuid4())
    with pytest.raises(StrategyNotFoundError):
        await svc.register(user_id, req)

    repo.save.assert_not_called()
    repo.commit.assert_not_called()


@pytest.mark.asyncio
async def test_register_settings_required_does_not_commit() -> None:
    """codex G.0 P2 #4: strategy.settings is None → StrategySettingsRequired + commit 0."""
    from src.trading.services.live_session_service import LiveSignalSessionService

    user_id = uuid4()
    strategy = _make_strategy(user_id, settings=None)

    repo = AsyncMock()
    account_repo = AsyncMock()
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=strategy)

    svc = LiveSignalSessionService(
        repo=repo, account_repo=account_repo, strategy_repo=strategy_repo
    )

    req = _make_req(strategy.id, uuid4())
    with pytest.raises(StrategySettingsRequired):
        await svc.register(user_id, req)

    repo.commit.assert_not_called()


@pytest.mark.asyncio
async def test_register_invalid_settings_does_not_commit() -> None:
    """codex G.0 P2 #4: malformed JSONB → InvalidStrategySettings + commit 0."""
    from src.trading.services.live_session_service import LiveSignalSessionService

    user_id = uuid4()
    # leverage 가 string — Pydantic ValidationError
    strategy = _make_strategy(user_id, settings={"leverage": "invalid", "margin_mode": "cross"})

    repo = AsyncMock()
    account_repo = AsyncMock()
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=strategy)

    svc = LiveSignalSessionService(
        repo=repo, account_repo=account_repo, strategy_repo=strategy_repo
    )

    req = _make_req(strategy.id, uuid4())
    with pytest.raises(InvalidStrategySettings):
        await svc.register(user_id, req)

    repo.commit.assert_not_called()


@pytest.mark.asyncio
async def test_register_account_mode_live_rejected() -> None:
    """codex G.0 P2 #1: mode=live → AccountModeNotAllowed (Bybit Demo 한정)."""
    from src.trading.services.live_session_service import LiveSignalSessionService

    user_id = uuid4()
    strategy = _make_strategy(user_id)
    # mode=live → AccountModeNotAllowed
    account = _make_account(user_id, mode=ExchangeMode.live)

    repo = AsyncMock()
    account_repo = AsyncMock()
    account_repo.get_by_id = AsyncMock(return_value=account)
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=strategy)

    svc = LiveSignalSessionService(
        repo=repo, account_repo=account_repo, strategy_repo=strategy_repo
    )

    req = _make_req(strategy.id, account.id)
    with pytest.raises(AccountModeNotAllowed):
        await svc.register(user_id, req)

    repo.commit.assert_not_called()


@pytest.mark.asyncio
async def test_register_exchange_okx_rejected() -> None:
    """codex G.0 P2 #1: exchange=okx → AccountModeNotAllowed (Bybit only)."""
    from src.trading.services.live_session_service import LiveSignalSessionService

    user_id = uuid4()
    strategy = _make_strategy(user_id)
    account = _make_account(user_id, exchange=ExchangeName.okx, mode=ExchangeMode.demo)

    repo = AsyncMock()
    account_repo = AsyncMock()
    account_repo.get_by_id = AsyncMock(return_value=account)
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=strategy)

    svc = LiveSignalSessionService(
        repo=repo, account_repo=account_repo, strategy_repo=strategy_repo
    )

    req = _make_req(strategy.id, account.id)
    with pytest.raises(AccountModeNotAllowed):
        await svc.register(user_id, req)

    repo.commit.assert_not_called()


@pytest.mark.asyncio
async def test_register_quota_exceeded_does_not_commit() -> None:
    """codex G.0 P3 #3: 사용자별 active session ≥ 5 → LiveSessionQuotaExceeded."""
    from src.trading.services.live_session_service import LiveSignalSessionService

    user_id = uuid4()
    strategy = _make_strategy(user_id)
    account = _make_account(user_id)

    repo = AsyncMock()
    repo.acquire_quota_lock = AsyncMock(return_value=None)
    repo.count_active_by_user = AsyncMock(return_value=5)  # 한도 초과

    account_repo = AsyncMock()
    account_repo.get_by_id = AsyncMock(return_value=account)
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=strategy)

    svc = LiveSignalSessionService(
        repo=repo, account_repo=account_repo, strategy_repo=strategy_repo
    )

    req = _make_req(strategy.id, account.id)
    with pytest.raises(LiveSessionQuotaExceeded):
        await svc.register(user_id, req)

    repo.save.assert_not_called()
    repo.commit.assert_not_called()


@pytest.mark.asyncio
async def test_deactivate_calls_repo_commit() -> None:
    """LESSON-019 spy: deactivate() 가 repo.commit() 호출 강제 (rowcount > 0 시)."""
    from src.trading.services.live_session_service import LiveSignalSessionService

    user_id = uuid4()
    sess = _make_session(user_id, uuid4(), uuid4())

    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=sess)
    repo.deactivate = AsyncMock(return_value=1)

    account_repo = AsyncMock()
    strategy_repo = AsyncMock()

    svc = LiveSignalSessionService(
        repo=repo, account_repo=account_repo, strategy_repo=strategy_repo
    )

    await svc.deactivate(user_id, sess.id)

    repo.deactivate.assert_awaited_once()
    repo.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_deactivate_already_inactive_no_commit() -> None:
    """idempotent: rowcount=0 (이미 deactivated) → commit 0. error 도 안 함."""
    from src.trading.services.live_session_service import LiveSignalSessionService

    user_id = uuid4()
    sess = _make_session(user_id, uuid4(), uuid4())
    sess.is_active = False

    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=sess)
    repo.deactivate = AsyncMock(return_value=0)  # 이미 deactivated

    account_repo = AsyncMock()
    strategy_repo = AsyncMock()

    svc = LiveSignalSessionService(
        repo=repo, account_repo=account_repo, strategy_repo=strategy_repo
    )

    await svc.deactivate(user_id, sess.id)

    repo.deactivate.assert_awaited_once()
    repo.commit.assert_not_called()


@pytest.mark.asyncio
async def test_deactivate_ownership_violation_404() -> None:
    """다른 user 의 session deactivate 시도 → StrategyNotFoundError (정보 누설 방어)."""
    from src.trading.services.live_session_service import LiveSignalSessionService

    user_id = uuid4()
    other_user = uuid4()
    sess = _make_session(other_user, uuid4(), uuid4())  # 다른 user 소유

    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=sess)

    account_repo = AsyncMock()
    strategy_repo = AsyncMock()

    svc = LiveSignalSessionService(
        repo=repo, account_repo=account_repo, strategy_repo=strategy_repo
    )

    with pytest.raises(StrategyNotFoundError):
        await svc.deactivate(user_id, sess.id)

    repo.deactivate.assert_not_called()
    repo.commit.assert_not_called()

"""세션 종료 사유가 실제로 DB 에 남는지, 누락이 타입으로 잡히는지 검증한다 (BL-484).

★사유가 없던 시절의 실패 모양 — fail-closed 로 세션이 죽으면 사유는 Slack/Telegram 으로만
나갔고 DB·API·화면에는 아무것도 없었다. 알림을 놓치면 "왜 멈췄나" 를 알 방법이 없었다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from src.auth.models import User
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    LiveSignalInterval,
    LiveSignalSession,
    SessionDeactivationReason,
)
from src.trading.repositories.live_signal_session_repository import (
    LiveSignalSessionRepository,
)


async def _seed_active_session(db_session: AsyncSession) -> LiveSignalSession:
    user = User(
        id=uuid4(),
        clerk_user_id=f"u_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@s.local",
    )
    db_session.add(user)
    await db_session.flush()

    strategy = Strategy(
        user_id=user.id,
        name="deactivation-reason",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    account = ExchangeAccount(
        user_id=user.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"key",
        api_secret_encrypted=b"secret",
    )
    db_session.add_all([strategy, account])
    await db_session.flush()

    session = LiveSignalSession(
        user_id=user.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        interval=LiveSignalInterval.m1,
    )
    db_session.add(session)
    await db_session.flush()
    return session


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", list(SessionDeactivationReason))
async def test_deactivate_persists_every_reason_in_the_set(
    db_session: AsyncSession, reason: SessionDeactivationReason
) -> None:
    """등재된 사유 전건이 컬럼에 그대로 저장된다 (String(64) 절단·enum cast 사고 방어)."""
    session = await _seed_active_session(db_session)
    repo = LiveSignalSessionRepository(db_session)
    at = datetime(2026, 7, 30, 12, tzinfo=UTC)

    rowcount = await repo.deactivate(session.id, at=at, reason=reason)

    assert rowcount == 1
    await db_session.refresh(session)
    assert session.is_active is False
    assert session.deactivated_at == at
    # ★plain str 로 온다 (컬럼이 PG enum 이 아니라 String). `.value` 를 기대하면 안 된다.
    assert session.deactivated_reason == str(reason)


@pytest.mark.asyncio
async def test_deactivate_refuses_to_run_without_a_reason() -> None:
    """★누락을 타입으로 잡는다 — 기본값을 주면 새 종료 경로가 조용히 사유를 빼먹는다."""
    repo = LiveSignalSessionRepository(AsyncMock())

    with pytest.raises(TypeError, match="reason"):
        # 표적 변이: `reason` 기본값을 붙이면 이 단정이 무너진다.
        await repo.deactivate(uuid4(), at=datetime.now(UTC))  # type: ignore[call-arg]


@pytest.mark.asyncio
async def test_deactivate_leaves_reason_untouched_when_already_inactive(
    db_session: AsyncSession,
) -> None:
    """두 번째 호출은 rowcount 0 — 먼저 기록된 사유를 나중 호출이 덮어쓰지 않는다.

    동시 worker 두 기가 같은 세션을 죽이려 할 때 winner-only dedupe 가 사유에도
    적용돼야 한다. 지면 그 갈래의 사유가 진짜 원인을 지운다.
    """
    session = await _seed_active_session(db_session)
    repo = LiveSignalSessionRepository(db_session)
    at = datetime(2026, 7, 30, 12, tzinfo=UTC)

    first = await repo.deactivate(
        session.id, at=at, reason=SessionDeactivationReason.runtime_divergence
    )
    second = await repo.deactivate(
        session.id, at=at, reason=SessionDeactivationReason.user_stopped
    )

    assert (first, second) == (1, 0)
    await db_session.refresh(session)
    assert session.deactivated_reason == "runtime_divergence"


@pytest.mark.asyncio
async def test_user_stop_records_user_stopped_reason() -> None:
    """사람이 Stop 을 누른 것과 안전 점검이 죽인 것을 화면이 구분할 수 있어야 한다."""
    from src.trading.services.live_session_service import LiveSignalSessionService

    user_id = uuid4()
    session_id = uuid4()
    sess = LiveSignalSession(
        id=session_id,
        user_id=user_id,
        strategy_id=uuid4(),
        exchange_account_id=uuid4(),
        symbol="BTC/USDT",
        interval=LiveSignalInterval.m1,
    )

    repo = AsyncMock()
    repo.get_by_id = AsyncMock(return_value=sess)
    repo.deactivate = AsyncMock(return_value=1)

    svc = LiveSignalSessionService(
        repo=repo,
        account_repo=AsyncMock(),
        strategy_repo=AsyncMock(),
        balance_service=AsyncMock(),
    )

    await svc.deactivate(user_id, session_id)

    kwargs = repo.deactivate.await_args.kwargs
    assert kwargs["reason"] == SessionDeactivationReason.user_stopped
    assert isinstance(repo.deactivate.await_args.args[0], UUID)

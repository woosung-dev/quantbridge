"""세션 종료 사유가 실제로 DB 에 남는지, 누락이 타입으로 잡히는지 검증한다 (BL-484).

★사유가 없던 시절의 실패 모양 — fail-closed 로 세션이 죽으면 사유는 Slack/Telegram 으로만
나갔고 DB·API·화면에는 아무것도 없었다. 알림을 놓치면 "왜 멈췄나" 를 알 방법이 없었다.

★BL-571 — 그 다음 실패 모양은 반대였다. 사유가 **있는데 정본 밖 값**이었다
(`soak_closed_by_operator` / `interim_window_stop` / `prefix_w1_window_done`). 코드가 만든
값이 아니라 운영자가 soak 중 psql 로 원장에 직접 써넣은 값이고, 화면은 원문 그대로 보여줬다.
아래 raw SQL 쌍이 그 경로 — ORM 을 건너뛴 직접 쓰기 — 를 그대로 재현한다.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
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
        auth_subject=f"u_{uuid4().hex[:8]}",
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


_WRITE_REASON_DIRECTLY = text(
    "UPDATE trading.live_signal_sessions SET deactivated_reason = :reason WHERE id = :id"
)

# 실제로 원장을 오염시킨 값들. 셋 다 레포 어디에도 없다 — 운영자가 psql 로 직접 써넣었다.
_POLLUTED_REASONS = ("soak_closed_by_operator", "interim_window_stop", "prefix_w1_window_done")


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", [str(member) for member in SessionDeactivationReason])
async def test_ledger_accepts_every_canonical_reason_written_directly(
    db_session: AsyncSession, reason: str
) -> None:
    """대조군 — ORM 을 건너뛴 직접 쓰기라도 정본 9종은 전부 통과한다.

    아래 거절 테스트와 **같은 채널·같은 문장**이다. 이 짝이 없으면 CHECK 가 사유를 전부
    막아도(= 프로덕션에서 세션 종료 실패) 테스트가 초록이다.
    """
    session = await _seed_active_session(db_session)

    await db_session.execute(_WRITE_REASON_DIRECTLY, {"reason": reason, "id": session.id})

    stored = await db_session.execute(
        text("SELECT deactivated_reason FROM trading.live_signal_sessions WHERE id = :id"),
        {"id": session.id},
    )
    assert stored.scalar_one() == reason


@pytest.mark.asyncio
@pytest.mark.parametrize("reason", _POLLUTED_REASONS)
async def test_ledger_rejects_a_reason_outside_the_canonical_set(
    db_session: AsyncSession, reason: str
) -> None:
    """★BL-571 재발 차단 — 정본 밖 값은 원장이 거절한다. 쓰는 주체가 누구든.

    호출부 AST 가드(`tests/tasks/test_deactivation_reason_wiring.py`)는 `src` 의
    `deactivate(...)` 호출부만 훑는다. 그 범위는 옳지만 psql·스크립트·수기 경로는
    구조적으로 시야 밖이라, 실제 오염을 만든 이 채널을 못 본다.
    """
    session = await _seed_active_session(db_session)

    with pytest.raises(IntegrityError, match="ck_live_signal_sessions_deactivated_reason"):
        await db_session.execute(_WRITE_REASON_DIRECTLY, {"reason": reason, "id": session.id})

    # 위반한 트랜잭션은 못 쓴다 — savepoint 로 되감아 fixture teardown 을 살린다.
    await db_session.rollback()


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
    second = await repo.deactivate(session.id, at=at, reason=SessionDeactivationReason.user_stopped)

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
        exclusivity_service=AsyncMock(),
    )

    await svc.deactivate(user_id, session_id)

    kwargs = repo.deactivate.await_args.kwargs
    assert kwargs["reason"] == SessionDeactivationReason.user_stopped
    assert isinstance(repo.deactivate.await_args.args[0], UUID)

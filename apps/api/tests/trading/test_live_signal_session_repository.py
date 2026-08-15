# 활성 라이브 세션 ticker 심볼 조회 repository 쿼리를 검증한다.
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from sqlmodel.ext.asyncio.session import AsyncSession

from src.trading.repositories.live_signal_session_repository import (
    LiveSignalSessionRepository,
)


@pytest.mark.asyncio
async def test_list_distinct_active_symbols_returns_scalar_rows() -> None:
    session = MagicMock()
    scalars = MagicMock()
    scalars.all.return_value = ["BTC/USDT", "ETH/USDT"]
    result = MagicMock()
    result.scalars.return_value = scalars
    session.execute = AsyncMock(return_value=result)

    symbols = await LiveSignalSessionRepository(session).list_distinct_active_symbols()

    assert symbols == ["BTC/USDT", "ETH/USDT"]
    session.execute.assert_awaited_once()


# ── BL-498 계정 스코프 세션 조회 (실DB) ────────────────────────────────


@pytest.mark.asyncio
async def test_list_by_account_includes_inactive_sessions_and_filters_by_user(
    db_session: AsyncSession,
) -> None:
    """★비활성 세션이 나와야 한다. fail-closed 종료가 남기는 게 정확히 그것이다.

    포지션은 남기고 세션만 비활성화하는 것이 설계이므로, 활성만 보면 그 포지션을
    만든 세션을 영영 못 찾는다. 그리고 귀속을 정하는 조회이므로 `user_id` 도 건다 —
    `LiveSignalSession.user_id` 와 `exchange_account_id` 는 독립 FK 라 두 소유자가
    같다는 DB 제약이 없다.
    """
    from src.auth.models import User
    from src.strategy.models import ParseStatus, PineVersion, Strategy
    from src.trading.models import (
        ExchangeAccount,
        ExchangeMode,
        ExchangeName,
        LiveSignalSession,
    )

    async def _make_user() -> User:
        user = User(
            id=uuid4(),
            auth_subject=f"u_{uuid4().hex[:8]}",
            email=f"{uuid4().hex[:8]}@s.local",
        )
        db_session.add(user)
        await db_session.flush()
        return user

    owner = await _make_user()
    stranger = await _make_user()

    strategy = Strategy(
        user_id=owner.id,
        name="account-scope",
        pine_source="//@version=5\nstrategy('s')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    db_session.add(strategy)
    await db_session.flush()

    account = ExchangeAccount(
        user_id=owner.id,
        exchange=ExchangeName.bybit,
        mode=ExchangeMode.demo,
        api_key_encrypted=b"key",
        api_secret_encrypted=b"secret",
        label="account-scope",
    )
    db_session.add(account)
    await db_session.flush()

    inactive = LiveSignalSession(
        user_id=owner.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        interval="1m",
        is_active=False,
    )
    foreign = LiveSignalSession(
        user_id=stranger.id,
        strategy_id=strategy.id,
        exchange_account_id=account.id,
        symbol="BTC/USDT",
        interval="1m",
        is_active=False,
    )
    db_session.add(inactive)
    db_session.add(foreign)
    await db_session.flush()

    repo = LiveSignalSessionRepository(db_session)

    owned = await repo.list_by_account(account.id, user_id=owner.id)
    assert [session.id for session in owned] == [inactive.id]

    # 음성 대조 — 활성 전용 조회는 같은 계정에서 아무것도 못 찾는다(이것이 BL-498).
    assert await repo.list_active_by_account(account.id) == []

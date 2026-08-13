"""GET /api/v1/live-sessions의 활성 및 최근 종료 목록 계약 테스트."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.trading.models import (
    ExchangeAccount,
    ExchangeMode,
    ExchangeName,
    LiveSignalInterval,
    LiveSignalSession,
)

_BASE = datetime(2026, 7, 28, 12, tzinfo=UTC)


async def _seed_session_dependencies(
    db_session: AsyncSession,
    user: User,
) -> tuple[Strategy, ExchangeAccount]:
    strategy = Strategy(
        user_id=user.id,
        name="session-list",
        pine_source="//@version=5\nstrategy('session-list')",
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
    return strategy, account


def _session(
    *,
    user_id,
    strategy_id,
    account_id,
    is_active: bool,
    created_at: datetime,
    deactivated_at: datetime | None = None,
) -> LiveSignalSession:
    return LiveSignalSession(
        user_id=user_id,
        strategy_id=strategy_id,
        exchange_account_id=account_id,
        symbol="BTC/USDT",
        interval=LiveSignalInterval.m1,
        is_active=is_active,
        created_at=created_at,
        deactivated_at=deactivated_at,
    )


@pytest.mark.asyncio
async def test_list_live_sessions_defaults_to_active_only_and_never_leaks_other_users(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth: User,
) -> None:
    strategy, account = await _seed_session_dependencies(db_session, mock_clerk_auth)
    active = _session(
        user_id=mock_clerk_auth.id,
        strategy_id=strategy.id,
        account_id=account.id,
        is_active=True,
        created_at=_BASE,
    )
    inactive = _session(
        user_id=mock_clerk_auth.id,
        strategy_id=strategy.id,
        account_id=account.id,
        is_active=False,
        created_at=_BASE - timedelta(hours=2),
        deactivated_at=_BASE - timedelta(hours=1),
    )
    other_user = User(
        id=uuid4(),
        clerk_user_id=f"u_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
    )
    foreign_inactive = _session(
        user_id=other_user.id,
        strategy_id=strategy.id,
        account_id=account.id,
        is_active=False,
        created_at=_BASE - timedelta(hours=3),
        deactivated_at=_BASE,
    )
    db_session.add_all([active, inactive, other_user, foreign_inactive])
    await db_session.commit()

    default_response = await client.get("/api/v1/live-sessions")
    assert default_response.status_code == 200, default_response.text
    default_body = default_response.json()
    assert default_body["total"] == 1
    assert [item["id"] for item in default_body["items"]] == [str(active.id)]
    assert all(item["is_active"] for item in default_body["items"])

    inclusive_response = await client.get("/api/v1/live-sessions?include_inactive=true")
    assert inclusive_response.status_code == 200, inclusive_response.text
    inclusive_body = inclusive_response.json()
    assert [item["id"] for item in inclusive_body["items"]] == [
        str(active.id),
        str(inactive.id),
    ]
    assert str(foreign_inactive.id) not in {
        item["id"] for item in inclusive_body["items"]
    }


@pytest.mark.asyncio
async def test_list_live_sessions_includes_recent_inactive_after_active_in_deactivation_order(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth: User,
) -> None:
    strategy, account = await _seed_session_dependencies(db_session, mock_clerk_auth)
    active = _session(
        user_id=mock_clerk_auth.id,
        strategy_id=strategy.id,
        account_id=account.id,
        is_active=True,
        created_at=_BASE,
    )
    newest_inactive = _session(
        user_id=mock_clerk_auth.id,
        strategy_id=strategy.id,
        account_id=account.id,
        is_active=False,
        created_at=_BASE - timedelta(hours=3),
        deactivated_at=_BASE - timedelta(hours=1),
    )
    older_inactive = _session(
        user_id=mock_clerk_auth.id,
        strategy_id=strategy.id,
        account_id=account.id,
        is_active=False,
        created_at=_BASE - timedelta(hours=5),
        deactivated_at=_BASE - timedelta(hours=2),
    )
    inactive_without_end_time = _session(
        user_id=mock_clerk_auth.id,
        strategy_id=strategy.id,
        account_id=account.id,
        is_active=False,
        created_at=_BASE - timedelta(hours=6),
    )
    db_session.add_all([active, newest_inactive, older_inactive, inactive_without_end_time])
    await db_session.commit()

    response = await client.get("/api/v1/live-sessions?include_inactive=true")
    assert response.status_code == 200, response.text
    body = response.json()

    assert [item["id"] for item in body["items"]] == [
        str(active.id),
        str(newest_inactive.id),
        str(older_inactive.id),
        str(inactive_without_end_time.id),
    ]


@pytest.mark.asyncio
async def test_list_live_sessions_limits_recent_inactive_to_twenty(
    client: AsyncClient,
    db_session: AsyncSession,
    mock_clerk_auth: User,
) -> None:
    strategy, account = await _seed_session_dependencies(db_session, mock_clerk_auth)
    inactive_sessions = [
        _session(
            user_id=mock_clerk_auth.id,
            strategy_id=strategy.id,
            account_id=account.id,
            is_active=False,
            created_at=_BASE - timedelta(days=1),
            deactivated_at=_BASE + timedelta(minutes=index),
        )
        for index in range(25)
    ]
    db_session.add_all(inactive_sessions)
    await db_session.commit()

    response = await client.get("/api/v1/live-sessions?include_inactive=true")
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["total"] == 20
    assert [item["id"] for item in body["items"]] == [
        str(session.id) for session in reversed(inactive_sessions[5:])
    ]

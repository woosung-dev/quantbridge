# Sprint 41 Worker H — backtest share endpoint 테스트 (create / revoke / view 분기)
"""BacktestService.create_share / revoke_share / view_share — Sprint 41 Worker H.

5+ tests covering:
- create_share: 신규 토큰 발급 (멱등 — 두번째 호출이 동일 토큰)
- revoke_share: share_revoked_at 마킹
- view_share: 200 (active) / 410 (revoked) / 404 (not found)
- create_share after revoke: 새 토큰 발급 (기존 토큰은 영구 dead)
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.backtest.dispatcher import FakeTaskDispatcher
from src.backtest.exceptions import BacktestNotFound, BacktestShareRevoked
from src.backtest.models import Backtest, BacktestStatus
from src.backtest.repository import BacktestRepository
from src.backtest.service import BacktestService
from src.market_data.providers.fixture import FixtureProvider
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.repository import StrategyRepository


async def _seed(session: AsyncSession) -> tuple[User, Backtest]:
    """User + Strategy + completed Backtest 레코드 생성."""
    user = User(
        id=uuid4(),
        clerk_user_id=f"u_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@ex.com",
    )
    session.add(user)
    await session.flush()
    strat = Strategy(
        id=uuid4(),
        user_id=user.id,
        name="EMA",
        pine_source="//@version=5\nstrategy('EMA')\n",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    session.add(strat)
    await session.flush()
    bt = Backtest(
        id=uuid4(),
        user_id=user.id,
        strategy_id=strat.id,
        symbol="BTCUSDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 1, 2, tzinfo=UTC),
        initial_capital=Decimal("10000"),
        status=BacktestStatus.COMPLETED,
        completed_at=datetime(2024, 1, 2, 1, 0, tzinfo=UTC),
    )
    session.add(bt)
    await session.flush()
    return user, bt


def _make_service(session: AsyncSession) -> BacktestService:
    return BacktestService(
        repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=FixtureProvider(root="/tmp/ohlcv-share-test"),
        dispatcher=FakeTaskDispatcher(),
    )


@pytest.mark.asyncio
async def test_create_share_issues_new_token(db_session: AsyncSession) -> None:
    """신규 share — secrets.token_urlsafe(32) 결과 + revoked=False."""
    user, bt = await _seed(db_session)
    service = _make_service(db_session)

    resp = await service.create_share(bt.id, user_id=user.id)

    assert resp.backtest_id == bt.id
    assert resp.share_token  # non-empty
    assert len(resp.share_token) >= 40  # token_urlsafe(32) ≈ 43 chars
    assert resp.share_url_path == f"/share/backtests/{resp.share_token}"
    assert resp.revoked is False


@pytest.mark.asyncio
async def test_create_share_is_idempotent(db_session: AsyncSession) -> None:
    """active token 있을 때 create_share 재호출 → 동일 토큰 반환."""
    user, bt = await _seed(db_session)
    service = _make_service(db_session)

    resp1 = await service.create_share(bt.id, user_id=user.id)
    resp2 = await service.create_share(bt.id, user_id=user.id)

    assert resp1.share_token == resp2.share_token


@pytest.mark.asyncio
async def test_view_share_returns_detail_for_active_token(db_session: AsyncSession) -> None:
    """200 active — BacktestDetail 반환 (error 필드 strip)."""
    user, bt = await _seed(db_session)
    service = _make_service(db_session)

    resp = await service.create_share(bt.id, user_id=user.id)
    detail = await service.view_share(resp.share_token)

    assert detail.id == bt.id
    assert detail.symbol == "BTCUSDT"
    assert detail.error is None  # strip 의무 — 민감 필드 노출 X


@pytest.mark.asyncio
async def test_view_share_revoked_raises_410(db_session: AsyncSession) -> None:
    """revoke 후 view_share → BacktestShareRevoked (HTTP 410)."""
    user, bt = await _seed(db_session)
    service = _make_service(db_session)

    resp = await service.create_share(bt.id, user_id=user.id)
    await service.revoke_share(bt.id, user_id=user.id)

    with pytest.raises(BacktestShareRevoked):
        await service.view_share(resp.share_token)


@pytest.mark.asyncio
async def test_view_share_unknown_token_raises_404(db_session: AsyncSession) -> None:
    """매칭 row 없음 → BacktestNotFound (HTTP 404)."""
    await _seed(db_session)
    service = _make_service(db_session)

    with pytest.raises(BacktestNotFound):
        await service.view_share("not-a-real-token-xxxxxxxxxxxxxxxxxxxxxx")


@pytest.mark.asyncio
async def test_create_share_after_revoke_issues_new_token(
    db_session: AsyncSession,
) -> None:
    """revoke 후 재 create → 새 토큰 발급 (기존 토큰은 영구 dead)."""
    user, bt = await _seed(db_session)
    service = _make_service(db_session)

    first = await service.create_share(bt.id, user_id=user.id)
    await service.revoke_share(bt.id, user_id=user.id)
    second = await service.create_share(bt.id, user_id=user.id)

    assert second.share_token != first.share_token
    # 신규 토큰은 view 가능
    detail = await service.view_share(second.share_token)
    assert detail.id == bt.id
    # 구 토큰은 revoke 상태 — dead.
    # 단 service helper 가 share_revoked_at 을 신규 발급 시 None 으로 reset 하므로
    # 기존 토큰을 lookup 해도 row 가 신규 토큰으로 swap 되어 BacktestNotFound 발생.
    with pytest.raises(BacktestNotFound):
        await service.view_share(first.share_token)

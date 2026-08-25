"""Sprint 31-E (BL-155) — direction count consistency BE vs FE.

Sprint 30 dogfood Day 3 발견:
- 거래분석 카드: "전체 83 / 롱 37 / 숏 46" (BE long_count/short_count, closed only)
- 거래목록 탭: "84 / 84 건" (FE trades 배열 length, open + closed)
- direction breakdown 카드: "롱 38 / 숏 46" (FE computeDirectionBreakdown, open + closed)
- 3-way mismatch.

Root cause: vectorbt `pf.trades.long.count() / pf.trades.short.count()` 가 closed only
만 집계 → metrics.long_count/short_count 가 closed only. 반면 trades 테이블에는
open 포함 모든 trade 가 저장 → FE 거래목록 / breakdown 은 open + closed.

Decision (option A): 사용자 시점 일관성 우선 — service layer 에서 trades 테이블
재집계로 long_count/short_count/num_trades override. 실제 BE 응답이 FE 거래목록 모수와
매치 (37+1=38 long, 46 short, total 84).

Note: storage layer (JSONB metrics) 는 변경 없음. metrics.py 도 변경 없음
(W2 영역). service layer 만 patch — 최소 변경 원칙 + 향후 재계산 정책 변경 가능성.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.backtest.dispatcher import FakeTaskDispatcher
from src.backtest.models import (
    Backtest,
    BacktestStatus,
    BacktestTrade,
    TradeDirection,
    TradeStatus,
)
from src.backtest.repository import BacktestRepository
from src.backtest.service import BacktestService
from src.market_data.providers.fixture import FixtureProvider
from src.strategy.repository import StrategyRepository

# ---------------------------------------------------------------------------
# Fixtures (test_service.py 패턴 재사용 — strategy/provider 는 dummy 로 충분)
# ---------------------------------------------------------------------------


@pytest.fixture
async def service(db_session: AsyncSession, tmp_path) -> BacktestService:  # type: ignore[no-untyped-def]
    """get() 만 검증할거라 strategy/provider 는 사용 안 됨. 최소 조립."""
    backtest_repo = BacktestRepository(db_session)
    strategy_repo = StrategyRepository(db_session)
    # FixtureProvider 는 root 디렉토리만 있으면 OK (실제 OHLCV 안 읽음).
    fix_root = tmp_path / "ohlcv"
    fix_root.mkdir()
    provider = FixtureProvider(root=fix_root)
    dispatcher = FakeTaskDispatcher()
    return BacktestService(
        repo=backtest_repo,
        strategy_repo=strategy_repo,
        ohlcv_provider=provider,
        dispatcher=dispatcher,
    )


async def _seed_completed_bt_with_trades(
    session: AsyncSession,
    *,
    closed_long: int,
    open_long: int,
    closed_short: int,
    open_short: int,
    metrics_long_count: int,
    metrics_short_count: int,
):  # type: ignore[no-untyped-def]
    """COMPLETED Backtest + trades 시드.

    metrics JSONB 는 metrics.py 의 closed-only 출력 모방 — closed 만 카운트한
    값으로 보관. trades 테이블은 open + closed 모두 저장. service.get() 이
    metrics 를 trades 테이블 재집계로 override 하는지 검증.
    """
    from src.auth.models import User
    from src.strategy.models import ParseStatus, PineVersion, Strategy

    user = User(
        id=uuid4(),
        auth_subject=f"u_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@ex.com",
    )
    session.add(user)
    await session.flush()
    strat = Strategy(
        id=uuid4(),
        user_id=user.id,
        name="dummy",
        pine_source="// dummy",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    session.add(strat)
    await session.flush()

    bt_id = uuid4()
    bt = Backtest(
        id=bt_id,
        user_id=user.id,
        strategy_id=strat.id,
        symbol="BTCUSDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 2, 1, tzinfo=UTC),
        initial_capital=Decimal("10000"),
        status=BacktestStatus.COMPLETED,
        metrics={
            "total_return": "0.10",
            "sharpe_ratio": "1.0",
            "max_drawdown": "-0.05",
            "win_rate": "0.5",
            # metrics.py 의 closed-only 카운트 모방
            "num_trades": closed_long + closed_short,
            "long_count": metrics_long_count,
            "short_count": metrics_short_count,
        },
        equity_curve=None,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    session.add(bt)

    # trades 시드 (open + closed 모두)
    idx = 0
    for direction, status, n in [
        (TradeDirection.LONG, TradeStatus.CLOSED, closed_long),
        (TradeDirection.LONG, TradeStatus.OPEN, open_long),
        (TradeDirection.SHORT, TradeStatus.CLOSED, closed_short),
        (TradeDirection.SHORT, TradeStatus.OPEN, open_short),
    ]:
        for _ in range(n):
            trade = BacktestTrade(
                backtest_id=bt_id,
                trade_index=idx,
                direction=direction,
                status=status,
                entry_time=datetime(2024, 1, 1, tzinfo=UTC),
                exit_time=(
                    datetime(2024, 1, 2, tzinfo=UTC) if status == TradeStatus.CLOSED else None
                ),
                entry_price=Decimal("100"),
                exit_price=(Decimal("110") if status == TradeStatus.CLOSED else None),
                size=Decimal("1"),
                pnl=Decimal("10") if status == TradeStatus.CLOSED else Decimal("0"),
                return_pct=Decimal("0.1") if status == TradeStatus.CLOSED else Decimal("0"),
                fees=Decimal("0.1"),
            )
            session.add(trade)
            idx += 1

    await session.flush()
    return user, bt


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_direction_counts_include_open_trades(
    service: BacktestService, db_session: AsyncSession
) -> None:
    """dogfood Day 3 시나리오 재현: BE long_count 37 → 38 (open 1건 포함).

    fixture: 5 closed long + 1 open long + 3 closed short + 1 open short = 10 trades.
    metrics JSONB (closed only) = num_trades 8 / long_count 5 / short_count 3.
    service.get() 후 → num_trades 10 / long_count 6 / short_count 4 (override).
    """
    user, bt = await _seed_completed_bt_with_trades(
        db_session,
        closed_long=5,
        open_long=1,
        closed_short=3,
        open_short=1,
        metrics_long_count=5,  # closed only
        metrics_short_count=3,  # closed only
    )

    detail = await service.get(bt.id, user_id=user.id)

    assert detail.metrics is not None
    # override: trades 테이블 재집계 (open + closed)
    assert detail.metrics.num_trades == 10
    assert detail.metrics.long_count == 6
    assert detail.metrics.short_count == 4
    # PRD parity alias 도 동기화
    assert detail.metrics.total_trades == 10


@pytest.mark.asyncio
async def test_direction_counts_long_short_sum_equals_num_trades(
    service: BacktestService, db_session: AsyncSession
) -> None:
    """invariant: long_count + short_count == num_trades (모든 trade 은 long XOR short)."""
    user, bt = await _seed_completed_bt_with_trades(
        db_session,
        closed_long=10,
        open_long=2,
        closed_short=7,
        open_short=3,
        metrics_long_count=10,
        metrics_short_count=7,
    )

    detail = await service.get(bt.id, user_id=user.id)

    assert detail.metrics is not None
    assert detail.metrics.long_count + detail.metrics.short_count == detail.metrics.num_trades


@pytest.mark.asyncio
async def test_legacy_no_trades_falls_back_to_metrics_jsonb(
    service: BacktestService, db_session: AsyncSession
) -> None:
    """trades 테이블에 0건일 때 (legacy backtest) metrics JSONB 값 그대로 사용.

    backward-compat: Sprint 31-E 이전에 완료된 backtest 는 trades 테이블에
    저장된 거래가 없을 수 있음. override 하지 않고 JSONB num_trades/long/short
    유지 (None 도 허용 → 응답 그대로 None).
    """
    user, bt = await _seed_completed_bt_with_trades(
        db_session,
        closed_long=0,
        open_long=0,
        closed_short=0,
        open_short=0,
        metrics_long_count=12,  # legacy JSONB 의 가짜 값
        metrics_short_count=8,
    )
    # metrics.num_trades 도 legacy 값 (예: 20)
    bt.metrics["num_trades"] = 20  # type: ignore[index]
    await db_session.flush()

    detail = await service.get(bt.id, user_id=user.id)

    assert detail.metrics is not None
    # trades 0건 → JSONB 값 유지
    assert detail.metrics.num_trades == 20
    assert detail.metrics.long_count == 12
    assert detail.metrics.short_count == 8


@pytest.mark.asyncio
async def test_repository_count_trades_by_direction(
    service: BacktestService, db_session: AsyncSession
) -> None:
    """repository helper 직접 검증 — open + closed 모두 카운트."""
    _user, bt = await _seed_completed_bt_with_trades(
        db_session,
        closed_long=4,
        open_long=2,
        closed_short=6,
        open_short=1,
        metrics_long_count=4,
        metrics_short_count=6,
    )

    total, long_n, short_n = await service.repo.count_trades_by_direction(bt.id)

    assert total == 13
    assert long_n == 6
    assert short_n == 7


# ---------------------------------------------------------------------------
# BL-822 — 「거래 수 N」과 「완료 거래 M」을 이름으로 가른다
#
# 위 Sprint 31-E override 는 유지하되(BL-155 의 의도된 결정), 승률의 분모가 무엇인지
# 응답이 스스로 말하게 한다. 그러지 않으면 화면이 「총 거래 수 13 · 승률 16.67%」처럼
# 곱해서 정수가 안 나오는 조합을 인쇄한다 (2026-08-25 qa-sweep 실측, backtest 20128227).
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_completed_trades_is_win_rate_denominator(
    service: BacktestService, db_session: AsyncSession
) -> None:
    """win_rate × completed_trades 는 정수(= 승리 건수)여야 한다. num_trades 로는 안 된다.

    fixture: 5 closed long + 1 open long + 3 closed short + 1 open short = 10 trades.
    JSONB win_rate = 0.375 = 3/8 — **완료 8건** 기준에서만 정수 승수(3)가 나오고
    override 값 10 을 분모로 쓰면 3.75 라 산술이 불가능하다.
    """
    user, bt = await _seed_completed_bt_with_trades(
        db_session,
        closed_long=5,
        open_long=1,
        closed_short=3,
        open_short=1,
        metrics_long_count=5,
        metrics_short_count=3,
    )
    # ★JSONB 는 `Column(JSONB)`(MutableDict 아님)라 **in-place 변경을 unit-of-work 가 못 본다**.
    #   재대입해야 dirty 로 잡혀 flush 가 실제 UPDATE 를 낸다 (in-place 는 identity map
    #   덕에 우연히 통과할 뿐이라 populate_existing/새 세션이면 뒤집힌다).
    bt.metrics = {**(bt.metrics or {}), "win_rate": "0.375"}
    await db_session.flush()

    detail = await service.get(bt.id, user_id=user.id)

    assert detail.metrics is not None
    assert detail.metrics.num_trades == 10  # override 유지 (BL-155)
    assert detail.metrics.completed_trades == 8  # 승률 분모

    wins = detail.metrics.win_rate * detail.metrics.completed_trades
    assert wins == Decimal("3"), f"완료 거래를 분모로 쓰면 정수 승수여야 한다 (got {wins})"
    # 음성 대조 — override 된 num_trades 를 분모로 쓰면 정수가 아니다(그래서 갈라야 했다).
    assert detail.metrics.win_rate * detail.metrics.num_trades != Decimal("3")


@pytest.mark.asyncio
async def test_trade_count_invariant_num_equals_completed_plus_open(
    service: BacktestService, db_session: AsyncSession
) -> None:
    """불변식: num_trades == completed_trades + total_open_trades (override 경로)."""
    user, bt = await _seed_completed_bt_with_trades(
        db_session,
        closed_long=10,
        open_long=2,
        closed_short=7,
        open_short=3,
        metrics_long_count=10,
        metrics_short_count=7,
    )
    bt.metrics = {**(bt.metrics or {}), "total_open_trades": 5}  # engine 이 세는 open 개수
    await db_session.flush()

    detail = await service.get(bt.id, user_id=user.id)

    assert detail.metrics is not None
    assert detail.metrics.completed_trades == 17
    assert detail.metrics.total_open_trades == 5
    assert detail.metrics.num_trades - detail.metrics.completed_trades == 5


@pytest.mark.asyncio
async def test_no_open_trades_means_counts_do_not_split(
    service: BacktestService, db_session: AsyncSession
) -> None:
    """음성 대조 — 미청산 0건이면 두 셈이 갈리지 않는다(갈라짐이 없는 곳에서 갈리면 결함)."""
    user, bt = await _seed_completed_bt_with_trades(
        db_session,
        closed_long=4,
        open_long=0,
        closed_short=2,
        open_short=0,
        metrics_long_count=4,
        metrics_short_count=2,
    )

    detail = await service.get(bt.id, user_id=user.id)

    assert detail.metrics is not None
    assert detail.metrics.num_trades == 6
    assert detail.metrics.completed_trades == 6


@pytest.mark.asyncio
async def test_legacy_fallback_completed_equals_num_trades(
    service: BacktestService, db_session: AsyncSession
) -> None:
    """trades 0건(legacy) 경로 — override 가 안 걸리므로 두 값이 같다.

    ★이 경로가 「FE 가 num_trades − total_open_trades 로 파생시키면 된다」를 반증한다.
      여기서 num_trades 는 이미 closed 라 빼면 M 보다 작아진다.
    """
    user, bt = await _seed_completed_bt_with_trades(
        db_session,
        closed_long=0,
        open_long=0,
        closed_short=0,
        open_short=0,
        metrics_long_count=12,
        metrics_short_count=8,
    )
    # 구 실행의 잔존 값까지 함께 심는다 — 재대입이라 flush 가 실제 UPDATE 를 낸다.
    bt.metrics = {**(bt.metrics or {}), "num_trades": 20, "total_open_trades": 3}
    await db_session.flush()

    detail = await service.get(bt.id, user_id=user.id)

    assert detail.metrics is not None
    assert detail.metrics.num_trades == 20
    assert detail.metrics.completed_trades == 20
    # 빼기 파생이었다면 17 이 나왔을 자리다.
    assert detail.metrics.completed_trades != 17

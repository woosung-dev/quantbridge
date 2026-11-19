# 거래별 OHLCV 조회 범위와 다운샘플링을 검증한다.
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
from src.backtest.dispatcher import FakeTaskDispatcher
from src.backtest.exceptions import BacktestNotFound
from src.backtest.models import Backtest, BacktestStatus, BacktestTrade, TradeDirection, TradeStatus
from src.backtest.repository import BacktestRepository
from src.backtest.service import MAX_BARS, BacktestService
from src.market_data.providers.fixture import FixtureProvider
from src.market_data.repository import OHLCVRepository
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.repository import StrategyRepository


def _time(hour: int = 0, minute: int = 0) -> datetime:
    return datetime(2024, 1, 1, hour, minute, tzinfo=UTC)


async def _seed_backtest(
    session: AsyncSession,
    *,
    period_end: datetime,
    entry_time: datetime,
    exit_time: datetime | None,
    trade_index: int = 7,
    timeframe: str = "1h",
) -> tuple[User, Backtest, BacktestTrade]:
    user = User(
        id=uuid4(),
        auth_subject=f"user_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@example.com",
    )
    strategy = Strategy(
        id=uuid4(),
        user_id=user.id,
        name="OHLCV",
        pine_source="//@version=5\nstrategy('OHLCV')",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    backtest = Backtest(
        id=uuid4(),
        user_id=user.id,
        strategy_id=strategy.id,
        symbol="BTCUSDT",
        timeframe=timeframe,
        period_start=_time(),
        period_end=period_end,
        initial_capital=Decimal("10000"),
        status=BacktestStatus.COMPLETED,
    )
    trade = BacktestTrade(
        backtest_id=backtest.id,
        trade_index=trade_index,
        direction=TradeDirection.LONG,
        status=TradeStatus.CLOSED if exit_time is not None else TradeStatus.OPEN,
        entry_time=entry_time,
        exit_time=exit_time,
        entry_price=Decimal("100"),
        exit_price=Decimal("101") if exit_time is not None else None,
        size=Decimal("1"),
        pnl=Decimal("1"),
        return_pct=Decimal("0.01"),
        fees=Decimal("0"),
    )
    # Backtest 는 strategies/users 로의 ORM relationship 이 없어 UoW 가 INSERT 순서를
    # 보장하지 않는다. FK 위반 회피를 위해 부모 → 자식 순으로 단계적 flush (test_repository 패턴).
    session.add_all([user, strategy])
    await session.flush()
    session.add(backtest)
    await session.flush()
    session.add(trade)
    await session.flush()
    return user, backtest, trade


async def _seed_ohlcv(
    session: AsyncSession, *, start: datetime, count: int, timeframe: str
) -> None:
    await OHLCVRepository(session).insert_bulk(
        [
            {
                "time": start + timedelta(hours=index)
                if timeframe == "1h"
                else start + timedelta(minutes=index),
                "symbol": "BTC/USDT",
                "timeframe": timeframe,
                "exchange": "bybit",
                "open": Decimal("100"),
                "high": Decimal("101"),
                "low": Decimal("99"),
                "close": Decimal("100.5"),
                "volume": Decimal("10"),
            }
            for index in range(count)
        ]
    )
    await session.flush()


def _service(session: AsyncSession, tmp_path: Path) -> BacktestService:
    return BacktestService(
        repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=FixtureProvider(root=tmp_path),
        ohlcv_repo=OHLCVRepository(session),
        dispatcher=FakeTaskDispatcher(),
    )


@pytest.mark.asyncio
async def test_trade_ohlcv_rejects_another_users_backtest(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    _, backtest, _ = await _seed_backtest(
        db_session,
        period_end=_time() + timedelta(hours=24),
        entry_time=_time(5),
        exit_time=_time(10),
    )

    with pytest.raises(BacktestNotFound) as exc_info:
        await _service(db_session, tmp_path).trade_ohlcv(backtest.id, 7, user_id=uuid4())

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_trade_ohlcv_rejects_missing_trade_index(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    user, backtest, _ = await _seed_backtest(
        db_session,
        period_end=_time() + timedelta(hours=24),
        entry_time=_time(5),
        exit_time=_time(10),
    )

    with pytest.raises(BacktestNotFound) as exc_info:
        await _service(db_session, tmp_path).trade_ohlcv(backtest.id, 99, user_id=user.id)

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_trade_ohlcv_uses_padded_closed_trade_window(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    user, backtest, _ = await _seed_backtest(
        db_session,
        period_end=_time() + timedelta(hours=24),
        entry_time=_time(5),
        exit_time=_time(10),
    )
    await _seed_ohlcv(db_session, start=_time(), count=25, timeframe="1h")

    response = await _service(db_session, tmp_path).trade_ohlcv(backtest.id, 7, user_id=user.id)

    assert response.bars[0].time == _time(1)
    assert response.bars[-1].time == _time(14)
    assert response.pad_bars == 4


@pytest.mark.asyncio
async def test_trade_ohlcv_open_trade_uses_backtest_period_end(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    user, backtest, _ = await _seed_backtest(
        db_session,
        period_end=_time() + timedelta(hours=24),
        entry_time=_time(5),
        exit_time=None,
    )
    await _seed_ohlcv(db_session, start=_time(), count=25, timeframe="1h")

    response = await _service(db_session, tmp_path).trade_ohlcv(backtest.id, 7, user_id=user.id)

    assert response.bars[0].time == _time(1)
    assert response.bars[-1].time == _time() + timedelta(hours=24)
    assert response.exit_time is None


@pytest.mark.asyncio
async def test_trade_ohlcv_downsamples_and_preserves_trade_markers(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    period_end = _time() + timedelta(minutes=700)
    entry_time = _time() + timedelta(minutes=11)
    exit_time = _time() + timedelta(minutes=690)
    user, backtest, _ = await _seed_backtest(
        db_session,
        period_end=period_end,
        entry_time=entry_time,
        exit_time=exit_time,
        timeframe="1m",
    )
    await _seed_ohlcv(db_session, start=_time(), count=701, timeframe="1m")

    response = await _service(db_session, tmp_path).trade_ohlcv(backtest.id, 7, user_id=user.id)
    times = {bar.time for bar in response.bars}

    assert response.truncated is True
    assert response.stride > 1
    assert response.bars[0].time == _time() + timedelta(minutes=7)
    assert response.bars[-1].time == _time() + timedelta(minutes=694)
    assert entry_time in times
    assert exit_time in times
    assert len(response.bars) <= MAX_BARS


@pytest.mark.asyncio
async def test_trade_ohlcv_keeps_small_ranges_unchanged(
    db_session: AsyncSession, tmp_path: Path
) -> None:
    user, backtest, _ = await _seed_backtest(
        db_session,
        period_end=_time() + timedelta(hours=24),
        entry_time=_time(5),
        exit_time=_time(10),
    )
    await _seed_ohlcv(db_session, start=_time(), count=25, timeframe="1h")

    response = await _service(db_session, tmp_path).trade_ohlcv(backtest.id, 7, user_id=user.id)

    assert response.stride == 1
    assert response.truncated is False
    assert len(response.bars) <= MAX_BARS


def _legacy_downsample(
    times: list[datetime], entry: datetime, exit_: datetime | None
) -> list[datetime]:
    """SQL 이전의 파이썬 다운샘플 — 새 경로가 같은 봉을 고르는지 대조하는 기준."""

    def closest(target: datetime) -> int:
        return min(range(len(times)), key=lambda index: abs(times[index] - target))

    forced = {0, len(times) - 1, closest(entry)}
    if exit_ is not None:
        forced.add(closest(exit_))
    budget = max(MAX_BARS - len(forced), 1)
    stride = -(-len(times) // budget)
    return [times[index] for index in sorted(set(range(0, len(times), stride)) | forced)]


@pytest.mark.asyncio
@pytest.mark.parametrize("closed", [True, False])
async def test_trade_ohlcv_downsample_matches_legacy_without_loading_whole_range(
    db_session: AsyncSession, tmp_path: Path, closed: bool
) -> None:
    """긴 구간은 DB 에서 솎아 MAX_BARS 근처만 올리되, 고르는 봉은 종전과 같아야 한다."""
    count = 3001
    period_end = _time() + timedelta(minutes=count - 1)
    entry_time = _time() + timedelta(minutes=137)
    exit_time = _time() + timedelta(minutes=2900) if closed else None
    user, backtest, _ = await _seed_backtest(
        db_session,
        period_end=period_end,
        entry_time=entry_time,
        exit_time=exit_time,
        timeframe="1m",
    )
    await _seed_ohlcv(db_session, start=_time(), count=count, timeframe="1m")

    service = _service(db_session, tmp_path)
    loaded: list[int] = []
    assert service.ohlcv_repo is not None
    real_get_range = service.ohlcv_repo.get_range

    async def spy_get_range(*args: object, **kwargs: object) -> list:
        rows = await real_get_range(*args, **kwargs)  # type: ignore[arg-type]
        loaded.append(len(rows))
        return rows

    service.ohlcv_repo.get_range = spy_get_range  # type: ignore[method-assign]

    response = await service.trade_ohlcv(backtest.id, 7, user_id=user.id)

    bar_delta = timedelta(minutes=4)
    window_end = min(period_end, (exit_time or period_end) + bar_delta)
    window = [
        _time() + timedelta(minutes=i)
        for i in range(count)
        if entry_time - bar_delta <= _time() + timedelta(minutes=i) <= window_end
    ]
    assert [bar.time for bar in response.bars] == _legacy_downsample(window, entry_time, exit_time)
    assert response.truncated is True
    assert len(response.bars) <= MAX_BARS
    # 구간 전체(수천 행)를 파이썬으로 올리지 않는다.
    assert all(n <= MAX_BARS for n in loaded)

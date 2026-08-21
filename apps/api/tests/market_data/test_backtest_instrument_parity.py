"""BL-535 — 백테스트가 재생하는 봉은 라이브 주문이 나가는 상품과 같아야 한다.

BL-530 이 라이브 경로 1사이트를 perp 로 정렬했지만 백테스트는 `TimescaleProvider` →
`CCXTProvider`(`defaultType: "spot"`) 경로라 **스팟 이력**으로 돌고 있었다. 즉
백테스트=스팟 / 라이브=perp 로 두 축이 갈려 있었다.

네 가지를 잠근다.

1. **회귀** — 백테스트 실행 경로가 OHLCV 를 **perp 심볼**로 요청한다. ★반드시 실제
   `BacktestService.run` 을 거친다. 테스트가 `to_ccxt_perpetual_symbol` 을 스스로
   호출하면 프로덕션 한 줄을 되돌려도 통과하는 거짓 게이트가 된다 (BL-530 선례).
2. **저장 키** — 새로 받은 봉은 상품 키(`BTC/USDT:USDT`)로 적재되고 canonical 키는
   건드리지 않는다.
3. **기존 데이터 불변** — 스팟 키로 이미 저장된 행은 수정·삭제되지 않고 그대로 읽힌다.
4. **화면 정합** — 거래 상세 차트가 엔진이 재생한 것과 같은 상품을 그린다(perp 우선,
   그 창에 perp 가 없으면 legacy 스팟).

경계 정본: `docs/domain/instrument-symbol-boundary.md`.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.models import User
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
from src.market_data.providers.ccxt import CCXTProvider
from src.market_data.providers.fixture import FixtureProvider
from src.market_data.providers.timescale import TimescaleProvider
from src.market_data.repository import OHLCVRepository
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.strategy.repository import StrategyRepository

CANONICAL = "BTC/USDT"
INSTRUMENT = "BTC/USDT:USDT"

# 스팟 봉과 perp 봉을 종가로 구분한다 — 어느 키에서 읽혔는지가 값으로 드러나야
# "읽히긴 했다" 는 약한 단언에서 벗어난다.
_SPOT_CLOSE = Decimal("63541.7")
_PERP_CLOSE = Decimal("63499.4")

_BASE = datetime(2024, 1, 1, tzinfo=UTC)
_BARS = 25


def _at(hour: int) -> datetime:
    return _BASE + timedelta(hours=hour)


def _db_rows(symbol: str, close: Decimal, *, count: int = _BARS) -> list[dict[str, object]]:
    return [
        {
            "time": _at(index),
            "symbol": symbol,
            "timeframe": "1h",
            "exchange": "bybit",
            "open": close,
            "high": close,
            "low": close,
            "close": close,
            "volume": Decimal("10"),
        }
        for index in range(count)
    ]


def _ccxt_bars(close: float, *, count: int = _BARS) -> list[list[float]]:
    return [
        [float(int(_at(index).timestamp() * 1000)), close, close, close, close, 10.0]
        for index in range(count)
    ]


async def _seed_user_and_strategy(session: AsyncSession) -> tuple[User, Strategy]:
    user = User(
        id=uuid4(),
        auth_subject=f"u_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@ex.com",
    )
    strategy = Strategy(
        id=uuid4(),
        user_id=user.id,
        name="instrument parity",
        pine_source='//@version=5\nstrategy("instrument parity")\n',
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    # Backtest 는 users/strategies 로의 ORM relationship 이 없어 UoW 가 INSERT 순서를
    # 보장하지 않는다 — 부모부터 단계적 flush (test_trade_ohlcv 패턴).
    session.add_all([user, strategy])
    await session.flush()
    return user, strategy


async def _seed_backtest(
    session: AsyncSession,
    *,
    symbol: str = CANONICAL,
    status: BacktestStatus = BacktestStatus.QUEUED,
) -> tuple[User, Backtest]:
    user, strategy = await _seed_user_and_strategy(session)
    backtest = Backtest(
        id=uuid4(),
        user_id=user.id,
        strategy_id=strategy.id,
        symbol=symbol,
        timeframe="1h",
        period_start=_BASE,
        period_end=_at(_BARS - 1),
        initial_capital=Decimal("10000"),
        status=status,
    )
    session.add(backtest)
    await session.flush()
    return user, backtest


def _timescale_service(session: AsyncSession, ccxt: AsyncMock) -> BacktestService:
    return BacktestService(
        repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=TimescaleProvider(OHLCVRepository(session), ccxt, exchange_name="bybit"),
        ohlcv_repo=OHLCVRepository(session),
        dispatcher=FakeTaskDispatcher(),
    )


# ── 1 + 2. 백테스트 실행 경로가 perp 를 물고 perp 키로 적재하는가 ──────────


class TestBacktestFetchesPerpBars:
    @pytest.mark.asyncio
    async def test_run_requests_the_perpetual_symbol(self, db_session: AsyncSession) -> None:
        """`bt.symbol` 을 그대로 넘기면 스팟 봉이 온다 — perp 로 변환돼야 한다.

        ★실제 `BacktestService.run` 을 거친다. provider 를 직접 부르면 백테스트가
        provider 를 canonical 로 부른다는 사실만 재확인할 뿐이다.
        """
        _, backtest = await _seed_backtest(db_session)
        ccxt = AsyncMock(spec=CCXTProvider)
        ccxt.fetch_ohlcv.return_value = _ccxt_bars(float(_PERP_CLOSE))

        service = _timescale_service(db_session, ccxt)
        await service.run(backtest.id)

        ccxt.fetch_ohlcv.assert_awaited()
        requested = ccxt.fetch_ohlcv.await_args.args[0]
        assert requested == INSTRUMENT, (
            "백테스트가 스팟 봉으로 perp 전략을 검증하면 라이브와 다른 신호가 난다 (BL-535)"
        )

        # 조기 return(전략 미발견 / fetch 실패)으로 통과한 것이 아님을 함께 잠근다.
        after = await service.repo.get_by_id(backtest.id)
        assert after is not None
        assert after.status != BacktestStatus.QUEUED
        assert "OHLCV fetch failed" not in (after.error or "")

    @pytest.mark.asyncio
    async def test_already_perpetual_symbol_is_idempotent(self, db_session: AsyncSession) -> None:
        """이미 perp 표기로 저장된 백테스트에 `:USDT` 를 두 번 붙이지 않는다."""
        _, backtest = await _seed_backtest(db_session, symbol=INSTRUMENT)
        ccxt = AsyncMock(spec=CCXTProvider)
        ccxt.fetch_ohlcv.return_value = _ccxt_bars(float(_PERP_CLOSE))

        await _timescale_service(db_session, ccxt).run(backtest.id)

        assert ccxt.fetch_ohlcv.await_args.args[0] == INSTRUMENT

    @pytest.mark.asyncio
    async def test_fetched_bars_land_under_the_instrument_key(
        self, db_session: AsyncSession
    ) -> None:
        """새로 받은 봉은 상품 키로 적재된다 — canonical 키는 비어 있어야 한다."""
        _, backtest = await _seed_backtest(db_session)
        ccxt = AsyncMock(spec=CCXTProvider)
        ccxt.fetch_ohlcv.return_value = _ccxt_bars(float(_PERP_CLOSE))

        await _timescale_service(db_session, ccxt).run(backtest.id)

        repo = OHLCVRepository(db_session)
        perp_rows = await repo.get_range(INSTRUMENT, "1h", _BASE, _at(_BARS - 1))
        spot_rows = await repo.get_range(CANONICAL, "1h", _BASE, _at(_BARS - 1))

        assert len(perp_rows) == _BARS
        assert spot_rows == [], "canonical 키에 perp 봉을 섞으면 한 키에 두 상품이 된다"


# ── 3. 기존 스팟 행은 건드리지 않는다 (마이그레이션 0) ─────────────────────


class TestLegacySpotRowsAreUntouched:
    @pytest.mark.asyncio
    async def test_spot_rows_survive_a_perp_fetch_over_the_same_window(
        self, db_session: AsyncSession
    ) -> None:
        """같은 창에 perp 를 채워도 스팟 행은 값까지 그대로 남아 있어야 한다.

        `ts.ohlcv` PK 는 `(time, symbol, timeframe)` 이라 상품 키는 **신규 행**이다.
        UPDATE 도 DELETE 도 없고 알렘빅 리비전도 필요 없다.
        """
        repo = OHLCVRepository(db_session)
        await repo.insert_bulk(_db_rows(CANONICAL, _SPOT_CLOSE))
        await repo.commit()

        ccxt = AsyncMock(spec=CCXTProvider)
        ccxt.fetch_ohlcv.return_value = _ccxt_bars(float(_PERP_CLOSE))
        provider = TimescaleProvider(repo, ccxt, exchange_name="bybit")

        frame = await provider.get_ohlcv(CANONICAL, "1h", _BASE, _at(_BARS - 1))

        # 엔진이 받은 것은 perp 다.
        assert len(frame) == _BARS
        assert set(frame["close"]) == {float(_PERP_CLOSE)}

        # 스팟 행은 개수도 값도 그대로다.
        spot_rows = await repo.get_range(CANONICAL, "1h", _BASE, _at(_BARS - 1))
        assert len(spot_rows) == _BARS
        assert {row.close for row in spot_rows} == {_SPOT_CLOSE}

    @pytest.mark.asyncio
    async def test_a_spot_only_cache_is_not_a_cache_hit(self, db_session: AsyncSession) -> None:
        """★스팟 행이 있다고 perp 를 안 받아오면 계기 정렬이 조용히 무산된다."""
        repo = OHLCVRepository(db_session)
        await repo.insert_bulk(_db_rows(CANONICAL, _SPOT_CLOSE))
        await repo.commit()

        ccxt = AsyncMock(spec=CCXTProvider)
        ccxt.fetch_ohlcv.return_value = _ccxt_bars(float(_PERP_CLOSE))
        provider = TimescaleProvider(repo, ccxt, exchange_name="bybit")

        await provider.get_ohlcv(CANONICAL, "1h", _BASE, _at(_BARS - 1))

        ccxt.fetch_ohlcv.assert_awaited_once()


# ── 4. 거래 상세 차트가 엔진과 같은 상품을 그리는가 ────────────────────────


async def _seed_closed_trade(session: AsyncSession, backtest: Backtest) -> None:
    session.add(
        BacktestTrade(
            backtest_id=backtest.id,
            trade_index=0,
            direction=TradeDirection.LONG,
            status=TradeStatus.CLOSED,
            entry_time=_at(5),
            exit_time=_at(10),
            entry_price=Decimal("100"),
            exit_price=Decimal("101"),
            size=Decimal("1"),
            pnl=Decimal("1"),
            return_pct=Decimal("0.01"),
            fees=Decimal("0"),
        )
    )
    await session.flush()


def _chart_service(session: AsyncSession, tmp_path: Path) -> BacktestService:
    # 차트는 읽기 전용 경로라 provider 를 타지 않는다 — fixture 로 충분하다.
    return BacktestService(
        repo=BacktestRepository(session),
        strategy_repo=StrategyRepository(session),
        ohlcv_provider=FixtureProvider(root=tmp_path),
        ohlcv_repo=OHLCVRepository(session),
        dispatcher=FakeTaskDispatcher(),
    )


class TestTradeChartFollowsTheEngineInstrument:
    @pytest.mark.asyncio
    async def test_chart_prefers_the_instrument_bars(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """★두 키가 다 있으면 perp 를 그린다.

        스팟 봉 위에 perp 체결 마커를 얹으면 스톱이 그려진 봉의 고저 밖에 놓여
        화면이 발산을 은폐한다.
        """
        user, backtest = await _seed_backtest(db_session, status=BacktestStatus.COMPLETED)
        await _seed_closed_trade(db_session, backtest)
        repo = OHLCVRepository(db_session)
        await repo.insert_bulk(_db_rows(CANONICAL, _SPOT_CLOSE))
        await repo.insert_bulk(_db_rows(INSTRUMENT, _PERP_CLOSE))
        await db_session.flush()

        response = await _chart_service(db_session, tmp_path).trade_ohlcv(
            backtest.id, 0, user_id=user.id
        )

        assert response.bars, "차트가 비면 안 된다"
        assert {bar.close for bar in response.bars} == {_PERP_CLOSE}
        # 화면 문자열은 계속 시장 이름이다 — 상품 표기는 저장 계층에만 산다.
        assert response.symbol == CANONICAL

    @pytest.mark.asyncio
    async def test_legacy_backtest_falls_back_to_spot_bars(
        self, db_session: AsyncSession, tmp_path: Path
    ) -> None:
        """★계기 정렬 이전 백테스트의 차트가 통째로 비면 회귀다."""
        user, backtest = await _seed_backtest(db_session, status=BacktestStatus.COMPLETED)
        await _seed_closed_trade(db_session, backtest)
        await OHLCVRepository(db_session).insert_bulk(_db_rows(CANONICAL, _SPOT_CLOSE))
        await db_session.flush()

        response = await _chart_service(db_session, tmp_path).trade_ohlcv(
            backtest.id, 0, user_id=user.id
        )

        assert response.bars, "perp 가 없으면 예전처럼 스팟을 그려야 한다"
        assert {bar.close for bar in response.bars} == {_SPOT_CLOSE}

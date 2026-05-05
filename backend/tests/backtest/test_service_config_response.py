"""Sprint 31 BL-156: BacktestDetail.config 5 가정 응답 활성화 검증.

PRD `backtests.config` JSONB 5 가정 — leverage / fees / slippage /
include_funding (initial_capital 은 detail 최상위). FE AssumptionsCard 가
default 표시 (Sprint 30-α graceful degrade) → BE 응답 graceful upgrade
완성.

현재 Backtest 모델엔 config 컬럼이 없으므로 engine BacktestConfig default
값을 응답에 노출 (Sprint 32+ 모델 확장 hook).

DB 의존 없는 pure unit test — `_to_detail()` 은 Backtest dataclass 만
입력으로 받는 순수 함수.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import MagicMock
from uuid import uuid4

from src.backtest.engine.types import BacktestConfig as EngineBacktestConfig
from src.backtest.models import Backtest, BacktestStatus
from src.backtest.schemas import BacktestConfigOut
from src.backtest.service import BacktestService


def _make_service() -> BacktestService:
    """DB 의존 없는 BacktestService — mock repo / strategy_repo / provider / dispatcher."""
    return BacktestService(
        repo=MagicMock(),
        strategy_repo=MagicMock(),
        ohlcv_provider=MagicMock(),
        dispatcher=MagicMock(),
    )


def _make_completed_bt() -> Backtest:
    """COMPLETED 상태 minimal Backtest fixture — _to_detail 입력용."""
    return Backtest(
        id=uuid4(),
        user_id=uuid4(),
        strategy_id=uuid4(),
        symbol="BTCUSDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 2, 1, tzinfo=UTC),
        initial_capital=Decimal("10000"),
        status=BacktestStatus.COMPLETED,
        metrics={
            "total_return": "0.15",
            "sharpe_ratio": "1.2",
            "max_drawdown": "-0.08",
            "win_rate": "0.55",
            "num_trades": 20,
        },
        equity_curve=None,
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )


# --- Test 1: config 5 가정 응답 포함 ---------------------------------------


def test_to_detail_includes_config_5_fields() -> None:
    """BacktestDetail 응답에 config 5 가정 (leverage/fees/slippage/include_funding) 노출."""
    service = _make_service()
    bt = _make_completed_bt()
    detail = service._to_detail(bt)

    # config 필드 존재 + 모든 4 필드 채워짐 (initial_capital 은 detail 최상위)
    assert detail.config is not None
    assert isinstance(detail.config, BacktestConfigOut)
    # initial_capital 은 BacktestDetail 최상위 필드 — separate
    assert detail.initial_capital == Decimal("10000")


# --- Test 2: default 값 정합 (engine BacktestConfig 기본값과 일치) -------


def test_to_detail_config_defaults_match_engine_defaults() -> None:
    """현재 Backtest 모델엔 config 컬럼 없음 → engine default 노출."""
    service = _make_service()
    bt = _make_completed_bt()
    detail = service._to_detail(bt)

    assert detail.config is not None
    default_cfg = EngineBacktestConfig()

    # leverage default = 1.0 (현물 가정)
    assert detail.config.leverage == default_cfg.leverage == 1.0
    # fees default = 0.001 (0.1%)
    assert detail.config.fees == default_cfg.fees == 0.001
    # slippage default = 0.0005 (0.05%)
    assert detail.config.slippage == default_cfg.slippage == 0.0005
    # include_funding default = False
    assert detail.config.include_funding == default_cfg.include_funding is False


# --- Test 3: config 응답 직렬화 정합 (FE BacktestConfigSchema 정합) -----


def test_to_detail_config_serialization_matches_fe_schema() -> None:
    """FE features/backtest/schemas.ts BacktestConfigSchema 4 키 정합."""
    service = _make_service()
    bt = _make_completed_bt()
    detail = service._to_detail(bt)

    assert detail.config is not None
    dumped = detail.config.model_dump()
    # FE schema: { leverage, fees, slippage, include_funding } 4 키
    assert set(dumped.keys()) == {"leverage", "fees", "slippage", "include_funding"}
    # 타입 정합 — number / boolean
    assert isinstance(dumped["leverage"], float)
    assert isinstance(dumped["fees"], float)
    assert isinstance(dumped["slippage"], float)
    assert isinstance(dumped["include_funding"], bool)


# --- Test 4: non-COMPLETED 상태에도 config 응답 (FE는 항상 표시) -------


def test_to_detail_config_present_for_queued_status() -> None:
    """QUEUED / RUNNING 상태도 config 노출 (가정 박스는 진행 중에도 표시)."""
    service = _make_service()
    bt = _make_completed_bt()
    bt.status = BacktestStatus.QUEUED
    bt.metrics = None
    bt.equity_curve = None
    detail = service._to_detail(bt)
    # metrics 는 None 이지만 config 는 채워짐
    assert detail.metrics is None
    assert detail.config is not None
    assert detail.config.leverage == 1.0

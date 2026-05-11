# Sprint 52 BL-222 P1 — StressTestService 가 parent backtest config 를 cell 마다 보존하는지 검증
"""Sprint 52 BL-222 P1 — `_execute_cost_assumption_sensitivity` + `_execute_param_stability`
가 parent backtest 의 `bt.config` JSONB + `bt.initial_capital` 을 engine 함수에
`backtest_config=` 로 전달하는지 service-level spy 로 검증.

codex G.0 P1 (2026-05-11) 권고: 단순 "cell 결과 차이" 검증 X. spy 로 engine 함수가
받은 `backtest_config` 의 5+ 필드 (init_cash / freq / trading_sessions / sizing 5필드)
보존 검증.

monkeypatch.setattr 로 engine 함수를 spy 로 대체 + Repository 의존성 AsyncMock 으로
mock — DB session 미사용 (unit test). 모든 Backtest field 는 사용자 입력 가정.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pandas as pd
import pytest

from src.backtest.engine.types import BacktestConfig
from src.backtest.models import Backtest, BacktestStatus
from src.strategy.models import ParseStatus, PineVersion, Strategy
from src.stress_test.models import StressTest, StressTestKind, StressTestStatus
from src.stress_test.service import StressTestService


def _make_backtest_with_bl188_v3_config() -> Backtest:
    """BL-188 v3 sizing 5필드 + trading_sessions + fees/slippage 다 채운 Backtest.

    이 config 가 cell 마다 보존되어야 함 (BL-222 P1 fix 검증 대상).
    """
    return Backtest(
        id=uuid4(),
        user_id=uuid4(),
        strategy_id=uuid4(),
        symbol="BTCUSDT",
        timeframe="4h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 1, 7, tzinfo=UTC),
        initial_capital=Decimal("50000"),  # NOT default 10000
        status=BacktestStatus.COMPLETED,
        completed_at=datetime.now(UTC),
        config={
            "fees": 0.002,  # NOT default 0.001
            "slippage": 0.0007,  # NOT default 0.0005
            "leverage": 2.0,
            "include_funding": True,
            "trading_sessions": ["America/New_York"],
            "default_qty_type": "percent_of_equity",
            "default_qty_value": 50.0,
            "live_position_size_pct": 25.0,
            "sizing_source": "form",
            "sizing_basis": "form_equity",
            "leverage_basis": 5.0,
        },
    )


def _make_strategy() -> Strategy:
    return Strategy(
        id=uuid4(),
        user_id=uuid4(),
        name="bl222_test_strategy",
        pine_source="//@version=5\nstrategy('x')\nplot(close)\n",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )


def _make_ohlcv() -> pd.DataFrame:
    idx = pd.date_range(start="2024-01-01", periods=10, freq="4h", tz="UTC")
    return pd.DataFrame(
        {
            "open": [100.0] * 10,
            "high": [101.0] * 10,
            "low": [99.0] * 10,
            "close": [100.5] * 10,
            "volume": [1000.0] * 10,
        },
        index=idx,
    )


def _make_service_with_mocks(
    strategy: Strategy,
    ohlcv: pd.DataFrame,
) -> StressTestService:
    """모든 의존성 AsyncMock — DB 미사용."""
    repo = AsyncMock()
    backtest_repo = AsyncMock()
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=strategy)
    provider = MagicMock()
    provider.get_ohlcv = AsyncMock(return_value=ohlcv)
    dispatcher = MagicMock()
    return StressTestService(
        repo=repo,
        backtest_repo=backtest_repo,
        strategy_repo=strategy_repo,
        ohlcv_provider=provider,
        dispatcher=dispatcher,
    )


@pytest.mark.asyncio
async def test_execute_cost_assumption_propagates_backtest_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BL-222 P1: `_execute_cost_assumption_sensitivity` 가 engine 에 backtest_config 전달."""
    bt = _make_backtest_with_bl188_v3_config()
    strategy = _make_strategy()
    ohlcv = _make_ohlcv()
    service = _make_service_with_mocks(strategy, ohlcv)
    st = StressTest(
        id=uuid4(),
        user_id=bt.user_id,
        backtest_id=bt.id,
        kind=StressTestKind.COST_ASSUMPTION_SENSITIVITY,
        status=StressTestStatus.RUNNING,
        params={"param_grid": {"fees": ["0.001", "0.002"], "slippage": ["0.0005"]}},
    )

    received_kwargs: dict[str, Any] = {}

    def spy_run(*_args: Any, **kwargs: Any) -> Any:
        received_kwargs.update(kwargs)
        return MagicMock(param1_name="fees", param2_name="slippage", cells=[])

    monkeypatch.setattr(
        "src.stress_test.service.run_cost_assumption_sensitivity", spy_run
    )
    monkeypatch.setattr(
        "src.stress_test.service.ca_result_to_jsonb", lambda _r: {}
    )

    await service._execute_cost_assumption_sensitivity(st, bt)

    cfg = received_kwargs.get("backtest_config")
    assert cfg is not None, "engine 가 backtest_config 받지 못함 (BL-222 P1 silent corruption)"
    assert isinstance(cfg, BacktestConfig)
    # 5 필드 보존 검증 — codex G.0 P1 권고 (initial_capital 변화 cell 결과 X, 보존 검증 O)
    assert cfg.init_cash == Decimal("50000"), "initial_capital 보존 실패"
    assert cfg.freq == "4h", "timeframe → freq 매핑 실패"
    assert cfg.trading_sessions == ("America/New_York",), "trading_sessions 보존 실패"
    # BL-188 v3 sizing 5필드
    assert cfg.sizing_source == "form"
    assert cfg.sizing_basis == "form_equity"
    assert cfg.leverage_basis == 5.0
    assert cfg.default_qty_type == "percent_of_equity"
    assert cfg.default_qty_value == 50.0
    assert cfg.live_position_size_pct == 25.0


@pytest.mark.asyncio
async def test_execute_param_stability_propagates_backtest_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BL-222 P1: `_execute_param_stability` 가 engine 에 backtest_config 전달."""
    bt = _make_backtest_with_bl188_v3_config()
    strategy = _make_strategy()
    ohlcv = _make_ohlcv()
    service = _make_service_with_mocks(strategy, ohlcv)
    st = StressTest(
        id=uuid4(),
        user_id=bt.user_id,
        backtest_id=bt.id,
        kind=StressTestKind.PARAM_STABILITY,
        status=StressTestStatus.RUNNING,
        params={"param_grid": {"emaPeriod": ["10", "20"], "stopLossPct": ["0.5"]}},
    )

    received_kwargs: dict[str, Any] = {}

    def spy_run(*_args: Any, **kwargs: Any) -> Any:
        received_kwargs.update(kwargs)
        return MagicMock(
            param1_name="emaPeriod", param2_name="stopLossPct", cells=[]
        )

    monkeypatch.setattr(
        "src.stress_test.service.run_param_stability", spy_run
    )
    monkeypatch.setattr(
        "src.stress_test.service.ps_result_to_jsonb", lambda _r: {}
    )

    await service._execute_param_stability(st, bt)

    cfg = received_kwargs.get("backtest_config")
    assert cfg is not None, "engine 가 backtest_config 받지 못함 (BL-222 P1 silent corruption)"
    assert isinstance(cfg, BacktestConfig)
    # PS 는 fees/slippage 도 보존 (CA 와 달리 input_overrides 만 override)
    assert cfg.init_cash == Decimal("50000")
    assert cfg.freq == "4h"
    assert cfg.fees == 0.002
    assert cfg.slippage == 0.0007
    assert cfg.leverage == 2.0
    assert cfg.include_funding is True
    assert cfg.trading_sessions == ("America/New_York",)
    # BL-188 v3 sizing 5필드
    assert cfg.sizing_source == "form"
    assert cfg.sizing_basis == "form_equity"
    assert cfg.default_qty_type == "percent_of_equity"
    assert cfg.default_qty_value == 50.0
    assert cfg.live_position_size_pct == 25.0


@pytest.mark.asyncio
async def test_execute_cost_assumption_propagates_default_when_bt_config_null(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BL-222 P1: bt.config NULL (legacy Sprint 30 이전) 시 init_cash + freq 만 bt 값 적용."""
    bt = _make_backtest_with_bl188_v3_config()
    bt.config = None  # legacy NULL
    strategy = _make_strategy()
    ohlcv = _make_ohlcv()
    service = _make_service_with_mocks(strategy, ohlcv)
    st = StressTest(
        id=uuid4(),
        user_id=bt.user_id,
        backtest_id=bt.id,
        kind=StressTestKind.COST_ASSUMPTION_SENSITIVITY,
        status=StressTestStatus.RUNNING,
        params={"param_grid": {"fees": ["0.001"], "slippage": ["0.0005"]}},
    )

    received_kwargs: dict[str, Any] = {}

    def spy_run(*_args: Any, **kwargs: Any) -> Any:
        received_kwargs.update(kwargs)
        return MagicMock(param1_name="fees", param2_name="slippage", cells=[])

    monkeypatch.setattr(
        "src.stress_test.service.run_cost_assumption_sensitivity", spy_run
    )
    monkeypatch.setattr(
        "src.stress_test.service.ca_result_to_jsonb", lambda _r: {}
    )

    await service._execute_cost_assumption_sensitivity(st, bt)

    cfg = received_kwargs["backtest_config"]
    assert cfg.init_cash == Decimal("50000")
    assert cfg.freq == "4h"
    # legacy NULL → engine default 사용
    default = BacktestConfig()
    assert cfg.fees == default.fees
    assert cfg.slippage == default.slippage
    assert cfg.sizing_source == "fallback"
    assert cfg.sizing_basis == "fallback_qty1"
    assert cfg.trading_sessions == ()


@pytest.mark.asyncio
async def test_execute_param_stability_propagates_default_when_bt_config_null(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """BL-222 P1: PS legacy NULL config 처리도 동일."""
    bt = _make_backtest_with_bl188_v3_config()
    bt.config = None
    strategy = _make_strategy()
    ohlcv = _make_ohlcv()
    service = _make_service_with_mocks(strategy, ohlcv)
    st = StressTest(
        id=uuid4(),
        user_id=bt.user_id,
        backtest_id=bt.id,
        kind=StressTestKind.PARAM_STABILITY,
        status=StressTestStatus.RUNNING,
        params={"param_grid": {"emaPeriod": ["10"], "stopLossPct": ["0.5"]}},
    )

    received_kwargs: dict[str, Any] = {}

    def spy_run(*_args: Any, **kwargs: Any) -> Any:
        received_kwargs.update(kwargs)
        return MagicMock(
            param1_name="emaPeriod", param2_name="stopLossPct", cells=[]
        )

    monkeypatch.setattr(
        "src.stress_test.service.run_param_stability", spy_run
    )
    monkeypatch.setattr(
        "src.stress_test.service.ps_result_to_jsonb", lambda _r: {}
    )

    await service._execute_param_stability(st, bt)

    cfg = received_kwargs["backtest_config"]
    assert cfg.init_cash == Decimal("50000")
    assert cfg.freq == "4h"
    default = BacktestConfig()
    assert cfg.sizing_source == "fallback"
    assert cfg.input_overrides is None or cfg.input_overrides == default.input_overrides

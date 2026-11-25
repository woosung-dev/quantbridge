# Sprint 52 BL-222 P1 — config_mapper.build_engine_config_from_db unit test
"""Sprint 52 BL-222 P1 — `src/backtest/config_mapper.py` module-level helper unit test.

Sprint 31 BL-162a 진입 시점 매핑이 BacktestService._build_engine_config 에서 추출됐다.
본 unit test 는 추출된 helper 가 동일 매핑 정합성 보존을 검증.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from src.backtest.config_mapper import (
    StoredAssumptions,
    build_engine_config_from_db,
    timeframe_to_freq,
)
from src.backtest.engine.types import BacktestConfig
from src.backtest.models import Backtest, BacktestStatus
from src.backtest.schemas import CreateBacktestRequest
from src.backtest.service import BacktestService
from src.strategy.models import ParseStatus, PineVersion, Strategy, StrategyVersion


def _make_bt(
    *, config: dict | None, initial_capital: Decimal = Decimal("10000"), timeframe: str = "1h"
) -> Backtest:
    return Backtest(
        id=uuid4(),
        user_id=uuid4(),
        strategy_id=uuid4(),
        symbol="BTCUSDT",
        timeframe=timeframe,
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 1, 2, tzinfo=UTC),
        initial_capital=initial_capital,
        status=BacktestStatus.COMPLETED,
        config=config,
    )


def test_build_engine_config_null_config_uses_defaults_with_bt_overrides() -> None:
    """bt.config NULL → engine default 적용. init_cash / freq 만 bt 값."""
    bt = _make_bt(config=None, initial_capital=Decimal("25000"), timeframe="5m")
    cfg = build_engine_config_from_db(bt)

    default = BacktestConfig()
    assert cfg.init_cash == Decimal("25000")
    assert cfg.freq == "5min"
    assert cfg.fees == default.fees
    assert cfg.slippage == default.slippage
    assert cfg.leverage == default.leverage
    assert cfg.include_funding == default.include_funding
    assert cfg.trading_sessions == ()
    assert cfg.sizing_source == "fallback"
    assert cfg.sizing_basis == "fallback_qty1"
    assert cfg.default_qty_type is None
    assert cfg.default_qty_value is None
    assert cfg.live_position_size_pct is None


def test_build_engine_config_with_bl188_v3_sizing_all_5_fields_preserved() -> None:
    """BL-188 v3 sizing 5 필드 + trading_sessions + fees/slippage/leverage 보존."""
    cfg_dict = {
        "fees": 0.002,
        "slippage": 0.0007,
        "leverage": 2.0,
        "include_funding": True,
        "trading_sessions": ["America/New_York", "Europe/London"],
        "default_qty_type": "percent_of_equity",
        "default_qty_value": 50.0,
        "live_position_size_pct": 25.0,
        "sizing_source": "form",
        "sizing_basis": "form_equity",
        "leverage_basis": 5.0,
    }
    bt = _make_bt(config=cfg_dict, initial_capital=Decimal("50000"), timeframe="4h")
    cfg = build_engine_config_from_db(bt)

    assert cfg.init_cash == Decimal("50000")
    assert cfg.freq == "4h"
    assert cfg.fees == 0.002
    assert cfg.slippage == 0.0007
    assert cfg.leverage == 2.0
    assert cfg.include_funding is True
    assert cfg.trading_sessions == ("America/New_York", "Europe/London")
    assert cfg.default_qty_type == "percent_of_equity"
    assert cfg.default_qty_value == 50.0
    assert cfg.live_position_size_pct == 25.0
    assert cfg.sizing_source == "form"
    assert cfg.sizing_basis == "form_equity"
    assert cfg.leverage_basis == 5.0


def test_build_engine_config_invalid_sizing_source_falls_back() -> None:
    """sizing_source 가 4 Literal 외 값이면 'fallback' 으로 강제."""
    bt = _make_bt(config={"sizing_source": "bogus_value"})
    cfg = build_engine_config_from_db(bt)
    assert cfg.sizing_source == "fallback"


def test_build_engine_config_invalid_sizing_basis_falls_back() -> None:
    """sizing_basis 가 4 Literal 외 값이면 'fallback_qty1' 으로 강제."""
    bt = _make_bt(config={"sizing_basis": "bogus_value"})
    cfg = build_engine_config_from_db(bt)
    assert cfg.sizing_basis == "fallback_qty1"


def test_timeframe_to_freq_maps_all_6_supported_timeframes() -> None:
    """6 timeframe Literal 모두 pandas offset alias 매핑 + fallback."""
    assert timeframe_to_freq("1m") == "1min"
    assert timeframe_to_freq("5m") == "5min"
    assert timeframe_to_freq("15m") == "15min"
    assert timeframe_to_freq("1h") == "1h"
    assert timeframe_to_freq("4h") == "4h"
    assert timeframe_to_freq("1d") == "1D"
    assert timeframe_to_freq("invalid_tf") == "1D"


def test_build_engine_config_partial_sizing_fields_omitted() -> None:
    """일부 sizing 필드만 채워진 config (실제 사용자 입력 변형) — None 보존."""
    bt = _make_bt(
        config={
            "fees": 0.001,
            "default_qty_type": "fixed",
            "default_qty_value": 100.0,
            # live_position_size_pct 누락
            # sizing_source / sizing_basis 누락 → fallback
        }
    )
    cfg = build_engine_config_from_db(bt)
    assert cfg.fees == 0.001
    assert cfg.default_qty_type == "fixed"
    assert cfg.default_qty_value == 100.0
    assert cfg.live_position_size_pct is None
    assert cfg.sizing_source == "fallback"
    assert cfg.sizing_basis == "fallback_qty1"


def test_legacy_maker_default_and_explicit_maker_rate_are_preserved() -> None:
    assert build_engine_config_from_db(_make_bt(config={})).maker_fee == BacktestConfig().maker_fee
    assert (
        build_engine_config_from_db(_make_bt(config={"maker_fee": "0.00010"})).maker_fee == 0.00010
    )
    assert build_engine_config_from_db(_make_bt(config={"maker_fee": "0"})).maker_fee == 0


# --- 쓰기 → 읽기 왕복 ---------------------------------------------------------
# 저장 dict 는 손으로 베끼지 않고 실제 쓰기 경로(`BacktestService.submit`)에서 받는다.
# 손 사본을 쓰면 쓰기 쪽 키가 바뀌어도 이 테스트가 못 본다. 요청값은 전부 engine
# 기본값과 다르게 준다 — 같으면 키 이름이 어긋나도 fallback 이 같은 값을 돌려준다.


async def _submit_and_reload(
    strategy: Strategy, version: StrategyVersion, **request: Any
) -> tuple[BacktestService, Backtest]:
    """submit() 이 `repo.create` 에 넘긴 row 를 JSONB 왕복(json dumps/loads)시켜 돌려준다."""
    repo, strategy_repo = AsyncMock(), AsyncMock()
    strategy_repo.find_by_id_and_owner.return_value = strategy
    strategy_repo.get_version_by_id.return_value = version
    dispatcher = Mock()
    dispatcher.dispatch_backtest.return_value = "task-id"
    service = BacktestService(
        repo=repo,
        strategy_repo=strategy_repo,
        ohlcv_provider=AsyncMock(),
        dispatcher=dispatcher,
    )
    await service.submit(
        CreateBacktestRequest.model_validate(
            {
                "strategy_id": strategy.id,
                "symbol": "BTC/USDT",
                "timeframe": "4h",
                "period_start": datetime(2024, 1, 1, tzinfo=UTC),
                "period_end": datetime(2024, 1, 7, tzinfo=UTC),
                "initial_capital": Decimal("25000"),
                "fees_pct": Decimal("0.0008"),
                "slippage_pct": Decimal("0.0002"),
                "include_funding": True,
                "fill_timing": "next_bar_open",
                **request,
            }
        ),
        user_id=strategy.user_id,
    )
    stored: Backtest = repo.create.call_args.args[0]
    stored.config = json.loads(json.dumps(stored.config))
    return service, stored


@pytest.mark.asyncio
async def test_pine_submit_shape_round_trips_through_config_mapper() -> None:
    strategy = Strategy(
        id=uuid4(),
        user_id=uuid4(),
        name="t",
        pine_source="//@version=5\nstrategy('t')\n",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )
    version = StrategyVersion(
        id=uuid4(),
        strategy_id=strategy.id,
        pine_source=strategy.pine_source,
        source_hash="a" * 64,
    )
    strategy.strategy_version_id = version.id

    service, stored = await _submit_and_reload(strategy, version, leverage=Decimal("5"))

    # 쓰기 모양 고정 — maker_fee · default_qty_* · live_position_size_pct ·
    # trading_sessions 는 값이 없으면 키 자체가 없다.
    assert stored.config == {
        "leverage": 5.0,
        "fees": 0.0008,
        "slippage": 0.0002,
        "include_funding": True,
        "fill_timing": "next_bar_open",
        "sizing_source": "fallback",
        "sizing_basis": "fallback_qty1",
        "leverage_basis": 1.0,
    }

    assumptions = StoredAssumptions(stored.config)
    assert (
        assumptions.leverage,
        assumptions.fees,
        assumptions.slippage,
        assumptions.include_funding,
        assumptions.fill_timing,
    ) == (5.0, 0.0008, 0.0002, True, "next_bar_open")
    # Pine 제출은 maker_fee 를 저장하지 않는다 → engine 기본값.
    assert assumptions.maker_fee == BacktestConfig().maker_fee

    engine = build_engine_config_from_db(stored)
    assert engine == BacktestConfig(
        init_cash=Decimal("25000"),
        freq="4h",
        leverage=5.0,
        fees=0.0008,
        slippage=0.0002,
        include_funding=True,
        fill_timing="next_bar_open",
        sizing_source="fallback",
        sizing_basis="fallback_qty1",
        leverage_basis=1.0,
    )

    # 응답(화면에 보이는 가정)이 엔진이 쓴 가정과 같은 값이다. Pine 은 maker_fee 를 숨긴다.
    shown = service._to_detail(stored).config
    assert shown is not None
    assert (
        shown.leverage,
        shown.fees,
        shown.slippage,
        shown.include_funding,
        shown.fill_timing,
    ) == (
        engine.leverage,
        engine.fees,
        engine.slippage,
        engine.include_funding,
        engine.fill_timing,
    )
    assert shown.maker_fee is None


@pytest.mark.asyncio
async def test_code_submit_shape_round_trips_through_config_mapper() -> None:
    from tests.strategy.test_code_strategy_commits import snapshot
    from tests.strategy.test_research_code_contract import pinned

    code = snapshot()
    strategy = Strategy(user_id=uuid4(), name="c", execution_policy=code.execution_policy)
    version = pinned(strategy.id, code)
    strategy.strategy_version_id = version.id

    service, stored = await _submit_and_reload(
        strategy,
        version,
        execution_policy="code_v1",
        strategy_version_id=version.id,
        maker_fee_pct=Decimal("0.00030"),
    )

    # 쓰기 모양 고정 — maker_fee 만 Decimal 문자열이고 나머지 수치는 float 다.
    assert stored.config == {
        "execution_policy": "code_v1",
        "execution_hash": code.execution_hash,
        "language": "python",
        "risk_policy": "swing_two_bar_v1",
        "warmup_bars": 50,
        "fill_timing": "next_bar_open",
        "leverage": 1.0,
        "fees": 0.0008,
        "slippage": 0.0002,
        "include_funding": True,
        "default_qty_type": "strategy.percent_of_equity",
        "default_qty_value": 100.0,
        "sizing_source": "form",
        "sizing_basis": "form_equity",
        "leverage_basis": 1.0,
        "execution_resolution": "1min",
        "maker_fee": "0.00030",
    }
    assert isinstance(stored.config["maker_fee"], str)

    assumptions = StoredAssumptions(stored.config)
    assert (
        assumptions.leverage,
        assumptions.fees,
        assumptions.maker_fee,
        assumptions.slippage,
        assumptions.include_funding,
        assumptions.fill_timing,
    ) == (1.0, 0.0008, 0.0003, 0.0002, True, "next_bar_open")

    engine = build_engine_config_from_db(stored)
    assert engine == BacktestConfig(
        init_cash=Decimal("25000"),
        freq="4h",
        leverage=1.0,
        fees=0.0008,
        maker_fee=0.0003,
        slippage=0.0002,
        include_funding=True,
        fill_timing="next_bar_open",
        default_qty_type="strategy.percent_of_equity",
        default_qty_value=100.0,
        sizing_source="form",
        sizing_basis="form_equity",
        leverage_basis=1.0,
    )

    shown = service._to_detail(stored).config
    assert shown is not None
    assert (
        shown.leverage,
        shown.fees,
        shown.maker_fee,
        shown.slippage,
        shown.include_funding,
        shown.fill_timing,
    ) == (
        engine.leverage,
        engine.fees,
        engine.maker_fee,
        engine.slippage,
        engine.include_funding,
        engine.fill_timing,
    )
    assert (shown.default_qty_type, shown.default_qty_value) == (
        "strategy.percent_of_equity",
        100.0,
    )

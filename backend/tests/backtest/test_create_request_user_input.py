"""Sprint 31 BL-162a — CreateBacktestRequest 사용자 입력 비용/마진 검증.

TradingView strategy 속성 패턴 (수수료 / 슬리피지 / leverage / include_funding)
사용자 입력 활성화. service 가 BacktestConfig 에 매핑 + Backtest.config JSONB
에 저장 → BacktestDetail.config 응답이 default 가 아닌 사용자 입력값.

DB 의존 없는 pure unit test — Pydantic V2 validation + service helper 검증만.
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from src.backtest.engine.types import BacktestConfig as EngineBacktestConfig
from src.backtest.models import Backtest, BacktestStatus
from src.backtest.schemas import BacktestConfigOut, CreateBacktestRequest
from src.backtest.config_mapper import timeframe_to_freq
from src.backtest.service import BacktestService
from src.strategy.models import ParseStatus, PineVersion, Strategy


def _make_request(**overrides: object) -> CreateBacktestRequest:
    """기본 valid CreateBacktestRequest 생성. overrides 로 필드 교체."""
    base: dict[str, object] = {
        "strategy_id": uuid4(),
        "symbol": "BTC/USDT",
        "timeframe": "1h",
        "period_start": datetime(2024, 1, 1, tzinfo=UTC),
        "period_end": datetime(2024, 1, 7, tzinfo=UTC),
        "initial_capital": Decimal("10000"),
    }
    base.update(overrides)
    return CreateBacktestRequest.model_validate(base)


def _make_strategy() -> Strategy:
    return Strategy(
        id=uuid4(),
        user_id=uuid4(),
        name="t",
        pine_source="//@version=5\nstrategy('t')\n",
        pine_version=PineVersion.v5,
        parse_status=ParseStatus.ok,
    )


# --- Test 1: schema default + 명시 override ---------------------------------


def test_create_request_default_values_match_bybit_taker_standard() -> None:
    """Sprint 31 BL-162a: 4 신규 필드 default = Bybit Perpetual taker 표준."""
    req = _make_request()
    assert req.leverage == Decimal("1.0")  # 1x 현물 기본
    assert req.fees_pct == Decimal("0.001")  # 0.10%
    assert req.slippage_pct == Decimal("0.0005")  # 0.05%
    assert req.include_funding is True  # 펀딩비 ON 기본


def test_create_request_accepts_user_overrides() -> None:
    """사용자가 4 신규 필드 override 시 그대로 보존."""
    req = _make_request(
        leverage=Decimal("10.0"),
        fees_pct=Decimal("0.0006"),
        slippage_pct=Decimal("0.0001"),
        include_funding=False,
    )
    assert req.leverage == Decimal("10.0")
    assert req.fees_pct == Decimal("0.0006")
    assert req.slippage_pct == Decimal("0.0001")
    assert req.include_funding is False


# --- Test 2: validation ----------------------------------------------------


def test_create_request_rejects_invalid_leverage() -> None:
    """leverage < 1 (현물도 1.0 가정) 또는 > 125 (Bybit max) 모두 reject."""
    with pytest.raises(ValidationError):
        _make_request(leverage=Decimal("0.5"))  # < 1
    with pytest.raises(ValidationError):
        _make_request(leverage=Decimal("200"))  # > 125 (Bybit max)


def test_create_request_rejects_invalid_fees_pct() -> None:
    """fees_pct < 0 또는 > 1% (절대 상한) 모두 reject."""
    with pytest.raises(ValidationError):
        _make_request(fees_pct=Decimal("-0.01"))  # 음수
    with pytest.raises(ValidationError):
        _make_request(fees_pct=Decimal("0.05"))  # 5% > 1% 상한


def test_create_request_rejects_invalid_slippage_pct() -> None:
    """slippage_pct < 0 또는 > 1% reject."""
    with pytest.raises(ValidationError):
        _make_request(slippage_pct=Decimal("-0.001"))
    with pytest.raises(ValidationError):
        _make_request(slippage_pct=Decimal("0.5"))  # 50% — 상한 초과


# --- Test 3: service.submit 가 사용자 입력을 Backtest.config 에 저장 ----------


@pytest.mark.asyncio
async def test_submit_persists_user_config_to_backtest_row() -> None:
    """submit() 가 사용자 입력 4 필드를 Backtest.config JSONB 에 매핑."""
    repo = AsyncMock()
    captured: dict[str, Backtest] = {}

    async def _capture_create(bt: Backtest) -> None:
        captured["bt"] = bt

    repo.create = _capture_create

    strategy = _make_strategy()
    strategy_repo = AsyncMock()
    strategy_repo.find_by_id_and_owner = AsyncMock(return_value=strategy)

    dispatcher = MagicMock()
    dispatcher.dispatch_backtest = MagicMock(return_value="task-id-xyz")

    svc = BacktestService(
        repo=repo,
        strategy_repo=strategy_repo,
        ohlcv_provider=AsyncMock(),
        dispatcher=dispatcher,
    )

    req = CreateBacktestRequest.model_validate(
        {
            "strategy_id": strategy.id,
            "symbol": "BTC/USDT",
            "timeframe": "1h",
            "period_start": datetime(2024, 1, 1, tzinfo=UTC),
            "period_end": datetime(2024, 1, 7, tzinfo=UTC),
            "initial_capital": Decimal("10000"),
            "leverage": Decimal("5.0"),
            "fees_pct": Decimal("0.0008"),
            "slippage_pct": Decimal("0.0002"),
            "include_funding": False,
        }
    )

    await svc.submit(req, user_id=strategy.user_id, idempotency_key=None)

    bt = captured["bt"]
    assert bt.config is not None
    assert bt.config["leverage"] == 5.0
    assert bt.config["fees"] == 0.0008
    assert bt.config["slippage"] == 0.0002
    assert bt.config["include_funding"] is False


# --- Test 4: _build_engine_config (worker run path) -------------------------


def test_build_engine_config_uses_user_input_from_bt_config() -> None:
    """worker run path 가 Backtest.config 사용자 입력을 BacktestConfig 에 매핑."""
    bt = Backtest(
        id=uuid4(),
        user_id=uuid4(),
        strategy_id=uuid4(),
        symbol="BTC/USDT",
        timeframe="4h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 2, 1, tzinfo=UTC),
        initial_capital=Decimal("50000"),
        status=BacktestStatus.QUEUED,
        config={
            "leverage": 10.0,
            "fees": 0.0002,
            "slippage": 0.0001,
            "include_funding": True,
        },
    )

    svc = BacktestService(
        repo=MagicMock(),
        strategy_repo=MagicMock(),
        ohlcv_provider=MagicMock(),
        dispatcher=MagicMock(),
    )
    cfg = svc._build_engine_config(bt)

    assert cfg.init_cash == Decimal("50000")
    assert cfg.leverage == 10.0
    assert cfg.fees == 0.0002
    assert cfg.slippage == 0.0001
    assert cfg.include_funding is True
    assert cfg.freq == "4h"


def test_build_engine_config_falls_back_to_engine_defaults_when_config_null() -> None:
    """legacy bt.config NULL 시 engine BacktestConfig default 로 fallback."""
    bt = Backtest(
        id=uuid4(),
        user_id=uuid4(),
        strategy_id=uuid4(),
        symbol="BTC/USDT",
        timeframe="1d",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 2, 1, tzinfo=UTC),
        initial_capital=Decimal("10000"),
        status=BacktestStatus.QUEUED,
        config=None,
    )

    svc = BacktestService(
        repo=MagicMock(),
        strategy_repo=MagicMock(),
        ohlcv_provider=MagicMock(),
        dispatcher=MagicMock(),
    )
    cfg = svc._build_engine_config(bt)

    default = EngineBacktestConfig()
    assert cfg.leverage == default.leverage
    assert cfg.fees == default.fees
    assert cfg.slippage == default.slippage
    assert cfg.include_funding == default.include_funding
    assert cfg.freq == "1D"


# --- Test 5: _to_detail() 가 사용자 입력값을 응답에 반영 (graceful upgrade) ---


def test_to_detail_returns_user_config_when_set() -> None:
    """bt.config 가 set 이면 BacktestDetail.config 가 사용자 입력값 응답."""
    bt = Backtest(
        id=uuid4(),
        user_id=uuid4(),
        strategy_id=uuid4(),
        symbol="BTC/USDT",
        timeframe="1h",
        period_start=datetime(2024, 1, 1, tzinfo=UTC),
        period_end=datetime(2024, 2, 1, tzinfo=UTC),
        initial_capital=Decimal("10000"),
        status=BacktestStatus.COMPLETED,
        config={
            "leverage": 3.0,
            "fees": 0.0006,
            "slippage": 0.0003,
            "include_funding": True,
        },
        created_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        metrics={
            "total_return": "0.1",
            "sharpe_ratio": "1.0",
            "max_drawdown": "-0.05",
            "win_rate": "0.5",
            "num_trades": 10,
        },
    )

    svc = BacktestService(
        repo=MagicMock(),
        strategy_repo=MagicMock(),
        ohlcv_provider=MagicMock(),
        dispatcher=MagicMock(),
    )
    detail = svc._to_detail(bt)

    assert detail.config is not None
    assert isinstance(detail.config, BacktestConfigOut)
    assert detail.config.leverage == 3.0
    assert detail.config.fees == 0.0006
    assert detail.config.slippage == 0.0003
    assert detail.config.include_funding is True


# --- Test 6: timeframe → freq 매핑 ------------------------------------------


def test_timeframe_to_freq_maps_all_supported_literals() -> None:
    """CreateBacktestRequest 의 6 timeframe Literal 모두 pandas offset alias 매핑.

    Sprint 52 BL-222 P1 (2026-05-11): `_timeframe_to_freq` 가 `src/backtest/config_mapper.py`
    로 이동. 본 테스트는 신규 module-level helper `timeframe_to_freq` 를 검증.
    """
    assert timeframe_to_freq("1m") == "1min"
    assert timeframe_to_freq("5m") == "5min"
    assert timeframe_to_freq("15m") == "15min"
    assert timeframe_to_freq("1h") == "1h"
    assert timeframe_to_freq("4h") == "4h"
    assert timeframe_to_freq("1d") == "1D"
    # 미매핑 fallback
    assert timeframe_to_freq("30m") == "1D"

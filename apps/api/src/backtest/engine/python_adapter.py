"""격리 Python 의 신호를 기존 Pine 브로커·비용·통계 모델에 연결한다."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping
from dataclasses import replace
from decimal import Decimal
from typing import Any, cast

import pandas as pd

from src.backtest.engine.types import BacktestConfig, BacktestResult
from src.backtest.engine.v2_adapter import (
    _build_raw_trades,
    _compute_equity_curve,
    _compute_equity_extremes,
    _compute_metrics,
    _funding_cost_by_bar,
)
from src.strategy.pine_v2.strategy_state import MarketIntent, StrategyState
from src.strategy.python_runtime.protocol import (
    MAX_BARS,
    PROTOCOL_VERSION,
    PythonRuntimeError,
    PythonTransport,
    validate_intent,
    validate_source_and_params,
)
from src.strategy.python_runtime.sandbox import DockerPythonTransport


def validate_python_data(ohlcv: pd.DataFrame, cfg: BacktestConfig, warmup_bars: int) -> None:
    """누락·중복·비유한 가격을 결과로 위장하지 않는다."""
    if not 0 <= warmup_bars < len(ohlcv) or len(ohlcv) > MAX_BARS:
        raise PythonRuntimeError("봉 수 또는 워밍업 범위가 올바르지 않습니다")
    index = ohlcv.index
    if not isinstance(index, pd.DatetimeIndex) or index.tz is None:
        raise PythonRuntimeError("봉 시간은 UTC 변환 가능한 tz-aware DatetimeIndex 여야 합니다")
    if not index.is_unique or not index.is_monotonic_increasing:
        raise PythonRuntimeError("봉 시간이 중복되거나 정렬되지 않았습니다")
    if len(index) > 1:
        expected = pd.Timedelta(pd.tseries.frequencies.to_offset(cfg.freq).nanos, unit="ns")
        if any(index[1:] - index[:-1] != expected):
            raise PythonRuntimeError("봉 간격이 설정과 다르거나 데이터에 빈 구간이 있습니다")
    for name in ("open", "high", "low", "close", "volume"):
        if name not in ohlcv:
            raise PythonRuntimeError(f"OHLCV 에 {name} 이 없습니다")
        for value in ohlcv[name]:
            number = Decimal(str(value))
            if not number.is_finite() or number < 0 or (name != "volume" and number == 0):
                raise PythonRuntimeError(f"OHLCV {name} 에 잘못된 값이 있습니다")
    for values in zip(*(ohlcv[name] for name in ("open", "high", "low", "close")), strict=True):
        open_, high, low, close = (Decimal(str(v)) for v in values)
        if not low <= min(open_, close) <= max(open_, close) <= high:
            raise PythonRuntimeError("OHLC 가격 관계가 올바르지 않습니다")
    if cfg.leverage != 1 or cfg.leverage_basis != 1:
        raise PythonRuntimeError("Python 전략은 레버리지 1배만 지원합니다")
    if cfg.init_cash <= 0 or not cfg.init_cash.is_finite():
        raise PythonRuntimeError("초기 자본은 유한 양수여야 합니다")
    if any(not math.isfinite(v) or not 0 <= v < 1 for v in (cfg.fees, cfg.slippage, cfg.maker_fee)):
        raise PythonRuntimeError("거래 비용은 0 이상 1 미만이어야 합니다")
    if cfg.default_qty_type not in (
        None,
        "strategy.percent_of_equity",
        "strategy.fixed",
        "strategy.cash",
    ):
        raise PythonRuntimeError("지원하지 않는 포지션 크기 방식입니다")
    if cfg.default_qty_value is not None:
        if not math.isfinite(cfg.default_qty_value) or cfg.default_qty_value <= 0:
            raise PythonRuntimeError("포지션 크기는 유한 양수여야 합니다")
        if cfg.default_qty_type == "strategy.percent_of_equity" and cfg.default_qty_value > 100:
            raise PythonRuntimeError("포지션 비중은 100% 이하여야 합니다")


def _position(state: StrategyState) -> dict[str, str | None]:
    trade = next(iter(state.open_trades.values()), None)
    return {
        "size": str(trade.qty) if trade else "0",
        "direction": trade.direction if trade else "flat",
        "average_price": str(trade.entry_price) if trade else None,
    }


def _place_bracket(state: StrategyState, intent: Mapping[str, str], bar: int) -> None:
    if "stop_loss" in intent or "take_profit" in intent:
        state.place_exit(
            from_entry="python",
            exit_id="python_bracket",
            bar=bar,
            stop=float(intent["stop_loss"]) if "stop_loss" in intent else None,
            limit=float(intent["take_profit"]) if "take_profit" in intent else None,
        )


def run_python_backtest(
    source: str,
    ohlcv: pd.DataFrame,
    config: BacktestConfig | None = None,
    funding_rates: pd.Series | None = None,
    params: dict[str, Any] | None = None,
    warmup_bars: int = 0,
    *,
    transport_factory: Callable[[], PythonTransport] | None = None,
) -> BacktestResult:
    """확정봉 1개씩 전달한다. transport_factory 는 신뢰된 테스트·gateway 주입점이다."""
    cfg = replace(config or BacktestConfig(), fill_timing="next_bar_open")
    parameters = dict(params or {})
    validate_source_and_params(source, parameters)
    validate_python_data(ohlcv, cfg, warmup_bars)
    if cfg.include_funding:
        if funding_rates is None or funding_rates.empty:
            raise PythonRuntimeError("펀딩 반영에 필요한 실제 펀딩 데이터가 없습니다")
        fi = funding_rates.index
        if (
            not isinstance(fi, pd.DatetimeIndex)
            or fi.tz is None
            or not fi.is_unique
            or not fi.is_monotonic_increasing
        ):
            raise PythonRuntimeError("펀딩 시간은 중복 없는 정렬된 tz-aware 인덱스여야 합니다")
        if any(not Decimal(str(v)).is_finite() for v in funding_rates):
            raise PythonRuntimeError("펀딩 비율이 유한하지 않습니다")
    else:
        funding_rates = None
    evaluated = ohlcv.iloc[warmup_bars:]
    state = StrategyState(pyramiding=1, sessions_allowed=cfg.trading_sessions)
    state.configure_sizing(
        initial_capital=float(cfg.init_cash),
        default_qty_type=cfg.default_qty_type or "strategy.percent_of_equity",
        default_qty_value=cfg.default_qty_value if cfg.default_qty_value is not None else 100,
        taker_cost_rate=cfg.fees + cfg.slippage,
    )
    transport = (transport_factory or DockerPythonTransport)()
    pending_bracket: dict[str, str] | None = None
    try:
        ready = transport.exchange(
            {"type": "init", "protocol": PROTOCOL_VERSION, "source": source, "params": parameters}
        )
        if ready != {"ready": PROTOCOL_VERSION}:
            raise PythonRuntimeError("Python 실행기 프로토콜 버전이 다릅니다")
        for absolute_index, (timestamp, row) in enumerate(ohlcv.iterrows()):
            bar_index = absolute_index - warmup_bars
            ts = pd.Timestamp(str(timestamp)).to_pydatetime()
            if bar_index >= 0:
                state.process_market_intents(bar=bar_index, open_=float(row["open"]), bar_ts=ts)
                if pending_bracket is not None and not state.pending_market_intents:
                    _place_bracket(state, pending_bracket, bar_index - 1)
                    pending_bracket = None
                state.check_exit_fills(
                    bar=bar_index,
                    open_=float(row["open"]),
                    high=float(row["high"]),
                    low=float(row["low"]),
                    bar_ts=ts,
                )
            bar: dict[str, Any] = {
                "index": absolute_index,
                "timestamp": pd.Timestamp(str(timestamp)).tz_convert("UTC").isoformat(),
                **{name: str(row[name]) for name in ("open", "high", "low", "close", "volume")},
            }
            reply = transport.exchange({"type": "bar", "bar": bar, "position": _position(state)})
            if set(reply) != {"intent"}:
                raise PythonRuntimeError("Python 실행기 응답 형식이 다릅니다")
            intent = validate_intent(reply["intent"])
            if bar_index < 0:
                continue
            action = intent["action"]
            if action == "close":
                state.queue_market_intent(
                    MarketIntent(kind="close_all", trade_id="python", placed_bar=bar_index)
                )
            elif action in ("long", "short"):
                current = next(iter(state.open_trades.values()), None)
                if current is None or current.direction != action:
                    state.queue_market_intent(
                        MarketIntent(
                            kind="entry",
                            trade_id="python",
                            direction=cast(Any, action),
                            placed_bar=bar_index,
                        )
                    )
                    pending_bracket = intent
                else:
                    _place_bracket(state, intent, bar_index)
            else:
                _place_bracket(state, intent, bar_index)
    finally:
        transport.close()
    trades = _build_raw_trades(state, cfg, ohlcv=evaluated)
    funding_costs, incomplete = (
        _funding_cost_by_bar(trades, evaluated, funding_rates, freq=cfg.freq)
        if funding_rates is not None
        else (None, None)
    )
    if incomplete:
        raise PythonRuntimeError(
            "봉 내부 체결과 펀딩 정산의 선후를 확정할 수 없습니다. "
            "확정 봉 신호의 다음 봉 청산 등 체결 시각이 알려진 규칙이 필요합니다"
        )
    total_funding = sum(funding_costs, start=Decimal("0")) if funding_costs is not None else None
    equity = _compute_equity_curve(
        trades, evaluated, cfg, funding_rates=funding_rates, funding_costs=funding_costs
    )
    extremes = (
        _compute_equity_extremes(
            trades, evaluated, cfg, close_equity=equity, funding_costs=funding_costs
        )
        if trades
        else None
    )
    metrics = _compute_metrics(
        trades,
        equity,
        cfg,
        evaluated,
        funding_data_incomplete=incomplete,
        total_funding=total_funding,
        equity_extremes=extremes,
    )
    return BacktestResult(metrics=metrics, equity_curve=equity, trades=trades, config_used=cfg)

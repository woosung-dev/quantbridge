"""세 언어의 실행 신호를 동일한 고정 R 원장·비용·펀딩·통계에 연결한다."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import replace
from decimal import Decimal
from typing import Any, cast

import pandas as pd

from src.backtest.engine.python_adapter import validate_python_data
from src.backtest.engine.swing_risk_adapter import Direction, _Ledger, _raw_episode
from src.backtest.engine.types import BacktestConfig, BacktestResult
from src.backtest.engine.v2_adapter import _compute_metrics
from src.strategy.code_runtime.models import (
    PROTOCOL_VERSION,
    CodeLanguage,
    CodeRuntimeError,
    CodeTransport,
    validate_code_intent,
)
from src.strategy.python_runtime.protocol import validate_source_and_params
from src.strategy.python_runtime.serialization import json_value
from src.strategy.python_runtime.swing_risk import RiskEvent, apply_event, replay_candle

_ZERO = Decimal("0")


def _funding_rates(
    funding: pd.Series | None, ohlcv: pd.DataFrame, config: BacktestConfig
) -> dict[int, Decimal]:
    if not config.include_funding:
        return {}
    if funding is None or funding.empty:
        raise CodeRuntimeError("펀딩 반영에는 실제 펀딩 데이터가 필요합니다")
    index = funding.index
    if (
        not isinstance(index, pd.DatetimeIndex)
        or index.tz is None
        or not index.is_unique
        or not index.is_monotonic_increasing
    ):
        raise CodeRuntimeError("펀딩 시각은 중복 없는 정렬된 tz-aware 인덱스여야 합니다")
    width = pd.tseries.frequencies.to_offset(config.freq).nanos
    bar_times = {ts.value for ts in ohlcv.index}
    start, end = ohlcv.index[0].value, ohlcv.index[-1].value + width
    result: dict[int, Decimal] = {}
    for timestamp, value in funding.items():
        rate = Decimal(str(value))
        time_ns = pd.Timestamp(str(timestamp)).value
        if not rate.is_finite():
            raise CodeRuntimeError("펀딩 비율은 유한한 숫자여야 합니다")
        if start <= time_ns < end and time_ns not in bar_times:
            raise CodeRuntimeError(
                "봉 내부 펀딩 선후를 확정할 수 없습니다. 정산 시각의 실행 봉이 필요합니다"
            )
        result[time_ns] = rate
    return result


def run_code_backtest(
    source: str,
    language: CodeLanguage | str,
    ohlcv: pd.DataFrame,
    config: BacktestConfig | None = None,
    funding_rates: pd.Series | None = None,
    params: dict[str, Any] | None = None,
    warmup_bars: int = 0,
    *,
    transport_factory: Callable[[], CodeTransport] | None = None,
    trace: list[dict[str, Any]] | None = None,
) -> BacktestResult:
    """완료 봉 신호를 다음 시가에 체결하고 같은 봉부터 공통 SL을 적용한다.

    trace는 관찰 산출물이며 체결 결정에 다시 입력하지 않는다. OHLC 내부 경로는 기존
    swing_risk의 두 시나리오 중 낮은 손익을 선택하며 실제 틱 순서라고 주장하지 않는다.
    """
    selected = CodeLanguage(language)
    cfg = replace(config or BacktestConfig(), fill_timing="next_bar_open")
    parameters = dict(params or {})
    validate_source_and_params(source, parameters)
    validate_python_data(ohlcv, cfg, warmup_bars)
    if cfg.trading_sessions or cfg.input_overrides is not None:
        raise CodeRuntimeError(
            "공통 실행기는 거래 시간 필터·별도 Pine override를 지원하지 않습니다"
        )
    if cfg.live_position_size_pct not in (None, 100):
        raise CodeRuntimeError("공통 실행기는 별도 라이브 수량 설정을 지원하지 않습니다")
    rates = _funding_rates(funding_rates, ohlcv, cfg)
    ledger = _Ledger(cfg, cfg.init_cash)
    values: list[Decimal] = []
    pending: tuple[str, list[dict[str, Decimal]]] | None = None
    history: list[dict[str, Decimal]] = []
    transport: CodeTransport
    if transport_factory is not None:
        transport = transport_factory()
    elif selected == CodeLanguage.pine:
        from src.strategy.code_runtime.pine import PineSignalTransport

        transport = PineSignalTransport(ohlcv)
    else:
        from src.strategy.code_runtime.sandbox import create_transport

        transport = create_transport(selected.value)
    try:
        if transport.exchange(
            {"type": "init", "protocol": PROTOCOL_VERSION, "source": source, "params": parameters}
        ) != {"ready": PROTOCOL_VERSION}:
            raise CodeRuntimeError("코드 실행기 프로토콜 버전이 다릅니다")
        for index, (timestamp, row) in enumerate(ohlcv.iterrows()):
            bar_index = index - warmup_bars
            timestamp_str = pd.Timestamp(str(timestamp)).tz_convert("UTC").isoformat()
            prices = {name: Decimal(str(row[name])) for name in ("open", "high", "low", "close")}
            fills_before = len(ledger.fills)
            ambiguous = False
            if bar_index >= 0:
                rate = rates.get(pd.Timestamp(str(timestamp)).value)
                if rate is not None and ledger.current is not None:
                    sign = Decimal(1) if ledger.current.direction == "long" else Decimal(-1)
                    funding = prices["open"] * ledger.remaining_qty * rate * sign
                    ledger.cash -= funding
                    ledger.current.funding += funding
                    if trace is not None:
                        trace.append(
                            {"type": "funding", "bar_index": index, "amount": str(funding)}
                        )
                if pending is not None:
                    action, references = pending
                    if action == "close":
                        if ledger.current is not None:
                            ledger.exit(
                                RiskEvent(
                                    ledger.generation, "close", prices["open"], ledger.remaining_qty
                                ),
                                bar_index,
                                timestamp_str,
                                "bar_open",
                            )
                    else:
                        ledger.market(
                            cast(Direction, action),
                            prices["open"],
                            bar_index,
                            timestamp_str,
                            "bar_open",
                            references,
                        )
                    pending = None
                if ledger.state is not None:
                    outcome = replay_candle(
                        ledger.state,
                        open_=prices["open"],
                        high=prices["high"],
                        low=prices["low"],
                        close=prices["close"],
                    )
                    ambiguous = outcome.ambiguous
                    for event in outcome.events:
                        assert ledger.state is not None
                        ledger.state = apply_event(ledger.state, event)
                        ledger.exit(event, bar_index, timestamp_str, "intrabar_scenario")
                    if ledger.state is not None:
                        ledger.state = outcome.state
                values.append(ledger.mark(prices["close"]))
            if trace is not None:
                trace.extend(
                    {"type": "fill", **json_value(fill)} for fill in ledger.fills[fills_before:]
                )
            bar = {
                "index": index,
                "timestamp": timestamp_str,
                **{name: str(row[name]) for name in ("open", "high", "low", "close", "volume")},
            }
            reply = transport.exchange({"type": "bar", "bar": bar, "position": ledger.position()})
            if set(reply) != {"intent"}:
                raise CodeRuntimeError("코드 실행기 응답에는 intent만 있어야 합니다")
            action = validate_code_intent(reply["intent"])["action"]
            history.append(prices)
            disposition = "hold"
            if bar_index < 0:
                disposition = "warmup"
            elif action == "close":
                pending = action, []
                disposition = "queued"
            elif action in ("long", "short"):
                if ledger.current is not None and ledger.current.direction == action:
                    disposition = "same_direction_ignored"
                elif len(history) < 2:
                    disposition = "insufficient_history"
                else:
                    pending = action, history[-2:]
                    disposition = "queued"
            if trace is not None:
                trace.append(
                    {
                        "type": "intent",
                        "bar_index": index,
                        "timestamp": timestamp_str,
                        "action": action,
                        "disposition": disposition,
                        "position": ledger.position(),
                        "risk_state": json_value(ledger.state),
                        "ambiguous": ambiguous,
                    }
                )
    finally:
        transport.close()
    evaluated = ohlcv.iloc[warmup_bars:]
    equity = pd.Series(values, index=evaluated.index, dtype=object)
    exit_phases = {
        fill["generation"]: "bar_open" if fill["phase"] == "bar_open" else "intrabar_unknown"
        for fill in ledger.fills
        if fill["kind"] != "entry"
    }
    trades = [
        replace(
            _raw_episode(episode),
            entry_phase="bar_open",
            exit_phase=cast(Any, exit_phases.get(episode.generation, "intrabar_unknown")),
        )
        for episode in ledger.episodes
    ]
    total_funding = (
        sum((episode.funding for episode in ledger.episodes), _ZERO)
        if cfg.include_funding
        else None
    )
    metrics = _compute_metrics(
        trades,
        equity,
        cfg,
        evaluated,
        funding_data_incomplete=None if trades else False,
        total_funding=total_funding,
    )
    closed_net = sum((trade.pnl for trade in trades if trade.status == "closed"), _ZERO)
    metrics = replace(metrics, open_pnl=values[-1] - cfg.init_cash - closed_net)
    return BacktestResult(metrics=metrics, equity_curve=equity, trades=trades, config_used=cfg)

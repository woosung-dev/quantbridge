"""세 언어의 실행 신호를 명시적 청산 정책·공통 원장·비용·펀딩에 연결한다."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from contextlib import nullcontext
from dataclasses import replace
from decimal import Decimal
from typing import Any, cast

import pandas as pd

from src.backtest.engine.python_adapter import validate_python_data
from src.backtest.engine.swing_risk_adapter import Direction, _execution_data, _Ledger, _raw_episode
from src.backtest.engine.types import BacktestConfig, BacktestResult
from src.backtest.engine.v2_adapter import _compute_metrics
from src.strategy.code_runtime.models import (
    CodeLanguage,
    CodeRuntimeError,
    CodeTransport,
    validate_code_intent,
)
from src.strategy.code_runtime.session import CodeExecutionSession, CodeSessionProtocolError
from src.strategy.python_runtime.protocol import validate_source_and_params
from src.strategy.python_runtime.serialization import json_value
from src.strategy.python_runtime.swing_risk import RiskEvent, apply_event, replay_candle
from src.strategy.research_contract import ResearchExecution

_ZERO = Decimal("0")
_Pending = tuple[str, list[dict[str, Decimal]], str | None]


def _hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _signal_record(
    identity: dict[str, Any],
    bar: dict[str, Any],
    action: str,
    position: dict[str, Any] | None,
) -> dict[str, Any]:
    input_hash = _hash({**identity, "bar": bar, "position": position})
    return {
        "index": bar["index"],
        "timestamp": bar["timestamp"],
        "action": action,
        "event_id": _hash([input_hash, action, 0]) if action != "hold" else None,
        "input_hash": input_hash,
    }


def _execute_bar(
    ledger: _Ledger,
    prices: dict[str, Decimal],
    index: int,
    timestamp: str,
    rate: Decimal | None,
    pending: _Pending | None,
    trace: list[dict[str, Any]] | None,
    *,
    research: bool = False,
) -> bool:
    """실행 시계의 확정 순서: 보유 펀딩 → 대기 시장가 → 보호 → 평가."""
    fills_before = len(ledger.fills)
    if rate is not None and ledger.current is not None:
        sign = Decimal(1) if ledger.current.direction == "long" else Decimal(-1)
        funding = prices["open"] * ledger.remaining_qty * rate * sign
        ledger.cash -= funding
        ledger.current.funding += funding
        if trace is not None:
            trace.append(
                {
                    "type": "funding",
                    "bar_index": index,
                    "timestamp": timestamp,
                    "amount": str(funding),
                }
            )
    if pending is not None:
        action, references, event_id = pending
        disposition = "flat_close_ignored"
        if action == "close":
            if ledger.current is not None:
                ledger.exit(
                    RiskEvent(ledger.generation, "close", prices["open"], ledger.remaining_qty),
                    index,
                    timestamp,
                    "bar_open",
                    signal_event_id=event_id,
                    exit_reason="source_close" if research else None,
                )
                disposition = "close"
        else:
            disposition = ledger.market(
                cast(Direction, action),
                prices["open"],
                index,
                timestamp,
                "bar_open",
                references,
                reenter_same_direction=research,
                signal_event_id=event_id,
            )
        if research and trace is not None:
            trace.append(
                {
                    "type": "execution",
                    "timestamp": timestamp,
                    "event_id": event_id,
                    "disposition": disposition,
                }
            )
    ambiguous = False
    if ledger.state is not None:
        previous_state = ledger.state
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
            ledger.exit(event, index, timestamp, "intrabar_scenario")
        if ledger.state is not None:
            ledger.state = outcome.state
        if research and trace is not None and ledger.state != previous_state:
            trace.append(
                {
                    "type": "risk_state",
                    "timestamp": timestamp,
                    "episode_id": ledger.generation,
                    "state": json_value(ledger.state),
                }
            )
    if trace is not None:
        trace.extend({"type": "fill", **json_value(fill)} for fill in ledger.fills[fills_before:])
    return ambiguous


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
    execution_ohlcv: pd.DataFrame | None = None,
    research_policy: ResearchExecution | None = None,
    signal_tape: Sequence[Mapping[str, Any]] | None = None,
    signal_output: list[dict[str, Any]] | None = None,
) -> BacktestResult:
    """완료 봉 신호를 다음 시가에 체결하고 같은 봉부터 공통 SL을 적용한다.

    trace는 관찰 산출물이며 체결 결정에 다시 입력하지 않는다. OHLC 내부 경로는 기존
    swing_risk의 두 시나리오 중 낮은 손익을 선택하며 실제 틱 순서라고 주장하지 않는다.
    shared_events는 포지션 독립성이 검토된 소스에만 선택한다. 신호 tape는 준비 봉을
    포함하며 원문·입력·전체 봉을 확인한 뒤 재생한다. 피드백 모드는 매 정책 코드를 실행한다.
    """
    selected = CodeLanguage(language)
    cfg = replace(config or BacktestConfig(), fill_timing="next_bar_open")
    parameters = dict(params or {})
    validate_source_and_params(source, parameters)
    validate_python_data(ohlcv, cfg, warmup_bars)
    if signal_tape is not None and (
        research_policy is None or research_policy.signal_mode != "shared_events"
    ):
        raise CodeRuntimeError("신호 tape 재생은 shared_events 연구 정책에서만 허용합니다")
    if signal_output is not None and research_policy is None:
        raise CodeRuntimeError("신호 tape 출력에는 연구 정책이 필요합니다")
    if signal_tape is not None and len(signal_tape) != len(ohlcv):
        raise CodeRuntimeError("신호 tape가 준비 봉을 포함한 전체 입력과 다릅니다")
    identity = {
        "source_hash": hashlib.sha256(source.encode()).hexdigest(),
        "language": selected.value,
        "params": parameters,
        "timeframe": cfg.freq,
        "warmup_bars": warmup_bars,
        "mapping_hash": research_policy.signal_mapping_hash if research_policy else None,
    }
    if cfg.trading_sessions or cfg.input_overrides is not None:
        raise CodeRuntimeError(
            "공통 실행기는 거래 시간 필터·별도 Pine override를 지원하지 않습니다"
        )
    if cfg.live_position_size_pct not in (None, 100):
        raise CodeRuntimeError("공통 실행기는 별도 라이브 수량 설정을 지원하지 않습니다")
    minutes, child_prices, child_index = 1, None, None
    if execution_ohlcv is not None:
        minutes, child_prices, child_index = _execution_data(
            ohlcv, execution_ohlcv, cfg, warmup_bars
        )
    rates = _funding_rates(
        funding_rates,
        execution_ohlcv if execution_ohlcv is not None else ohlcv,
        replace(cfg, freq="1min") if execution_ohlcv is not None else cfg,
    )
    ledger = _Ledger(cfg, cfg.init_cash)
    if research_policy is not None and research_policy.exit_policy == "signal_only_v1":
        ledger.exit_policy = "source"
    values: list[Decimal] = []
    pending: _Pending | None = None
    history: list[dict[str, Decimal]] = []
    signals: list[dict[str, Any]] = []
    seen_events: set[str] = set()
    try:
        context = (
            CodeExecutionSession(
                source, selected, parameters, ohlcv, transport_factory=transport_factory
            )
            if signal_tape is None
            else nullcontext(None)
        )
        with context as session:
            for index, (timestamp, row) in enumerate(ohlcv.iterrows()):
                bar_index = index - warmup_bars
                timestamp_str = pd.Timestamp(str(timestamp)).tz_convert("UTC").isoformat()
                prices = {
                    name: Decimal(str(row[name])) for name in ("open", "high", "low", "close")
                }
                ambiguous = False
                if bar_index >= 0:
                    if child_prices is None or child_index is None:
                        ambiguous = _execute_bar(
                            ledger,
                            prices,
                            bar_index,
                            timestamp_str,
                            rates.get(pd.Timestamp(str(timestamp)).value),
                            pending,
                            trace,
                            research=research_policy is not None,
                        )
                        values.append(ledger.mark(prices["close"]))
                    else:
                        left = bar_index * minutes
                        for child in range(left, left + minutes):
                            current = {
                                name: child_prices[name][child]
                                for name in ("open", "high", "low", "close")
                            }
                            ambiguous |= _execute_bar(
                                ledger,
                                current,
                                child,
                                child_index[child].isoformat(),
                                rates.get(child_index[child].value),
                                pending if child == left else None,
                                trace,
                                research=research_policy is not None,
                            )
                            values.append(ledger.mark(current["close"]))
                    pending = None
                bar = {
                    "index": index,
                    "timestamp": timestamp_str,
                    **{name: str(row[name]) for name in ("open", "high", "low", "close", "volume")},
                }
                position = ledger.position()
                if research_policy is not None and research_policy.signal_mode == "shared_events":
                    position = {"size": "0", "direction": "flat", "average_price": None}
                if signal_tape is None:
                    assert session is not None
                    action = session.action(bar, position)
                else:
                    action = validate_code_intent({"action": signal_tape[index].get("action")})[
                        "action"
                    ]
                event_id = None
                record = None
                if research_policy is not None:
                    record = _signal_record(
                        identity,
                        bar,
                        action,
                        position if research_policy.signal_mode == "position_feedback" else None,
                    )
                    if signal_tape is not None and dict(signal_tape[index]) != record:
                        raise CodeRuntimeError("신호 tape의 원문·입력·봉·이벤트 hash가 다릅니다")
                    signals.append(record)
                    if signal_output is not None:
                        signal_output.append(dict(record))
                    event_id = record["event_id"]
                history.append(prices)
                disposition = "hold"
                if bar_index < 0:
                    disposition = "warmup"
                elif event_id is not None and event_id in seen_events:
                    disposition = "duplicate_signal_ignored"
                elif action == "close":
                    pending = action, [], event_id
                    disposition = "queued"
                elif action in ("long", "short"):
                    if (
                        research_policy is None
                        and ledger.current is not None
                        and ledger.current.direction == action
                    ):
                        disposition = "same_direction_ignored"
                    elif ledger.exit_policy == "swing" and len(history) < 2:
                        disposition = "insufficient_history"
                    else:
                        pending = action, history[-2:], event_id
                        disposition = "queued"
                if event_id is not None:
                    seen_events.add(event_id)
                if research_policy is not None and index == len(ohlcv) - 1 and pending is not None:
                    disposition = "queued_unfilled"
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
                    if record is not None:
                        assert research_policy is not None
                        trace[-1].update(
                            event_id=event_id,
                            signal_input_hash=record["input_hash"],
                            signal_mode=research_policy.signal_mode,
                        )
    except CodeSessionProtocolError as error:
        raise CodeRuntimeError(str(error)) from error
    evaluated = ohlcv.iloc[warmup_bars:]
    equity = pd.Series(
        values, index=child_index if child_index is not None else evaluated.index, dtype=object
    )
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
        replace(cfg, freq="1min") if child_index is not None else cfg,
        execution_ohlcv if child_index is not None else evaluated,
        funding_data_incomplete=None if trades else False,
        total_funding=total_funding,
    )
    closed_net = sum((trade.pnl for trade in trades if trade.status == "closed"), _ZERO)
    metrics = replace(metrics, open_pnl=values[-1] - cfg.init_cash - closed_net)
    if research_policy is not None and trace is not None:
        trace.append(
            {
                "type": "research_summary",
                "policy": research_policy.model_dump(mode="json"),
                "signal_hash": _hash(signals),
                "counters": dict(ledger.counters),
                "episodes": json_value(ledger.episodes),
            }
        )
    return BacktestResult(metrics=metrics, equity_curve=equity, trades=trades, config_used=cfg)

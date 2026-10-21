"""부모봉 신호와 분봉 청산을 분리한 선택형 연구 실행기. 거래소 권한은 없다."""

from __future__ import annotations

import hashlib
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal, cast

import numpy as np
import pandas as pd

from src.backtest.engine.python_adapter import validate_python_data
from src.backtest.engine.types import BacktestConfig, RawTrade
from src.backtest.engine.v2_adapter import _compute_metrics, _leg_cost, _max_drawdown
from src.strategy.python_runtime.protocol import (
    PROTOCOL_VERSION,
    PythonRuntimeError,
    PythonTransport,
    validate_intent,
    validate_source_and_params,
)
from src.strategy.python_runtime.sandbox import DockerPythonTransport
from src.strategy.python_runtime.serialization import digest, engine_digest, json_value
from src.strategy.python_runtime.swing_risk import (
    POLICY,
    RiskEvent,
    RiskState,
    apply_event,
    create_plan,
    initial_state,
    replay_candle,
)

ZERO = Decimal("0")
ONE = Decimal("1")
MINUTE_NS = 60_000_000_000
Direction = Literal["long", "short"]


@dataclass
class _Episode:
    generation: int
    direction: Direction
    entry_index: int
    entry_price: Decimal
    quantity: Decimal
    entry_time: str
    entry_phase: str
    realized: Decimal = ZERO
    fees: Decimal = ZERO
    slippage: Decimal = ZERO
    funding: Decimal = ZERO
    exit_notional: Decimal = ZERO
    exit_index: int | None = None
    exit_time: str | None = None


@dataclass
class _Ledger:
    cfg: BacktestConfig
    cash: Decimal
    exit_policy: Literal["swing", "source"] = "swing"
    remaining_qty: Decimal = ZERO
    state: RiskState | None = None
    current: _Episode | None = None
    episodes: list[_Episode] = field(default_factory=list)
    fills: list[dict[str, Any]] = field(default_factory=list)
    counters: Counter[str] = field(default_factory=Counter)
    generation: int = 0

    def position(self) -> dict[str, str | None]:
        if self.current is None:
            return {"size": "0", "direction": "flat", "average_price": None}
        return {
            "size": str(self.remaining_qty),
            "direction": self.current.direction,
            "average_price": str(self.current.entry_price),
        }

    def mark(self, price: Decimal) -> Decimal:
        if self.current is None:
            return self.cash
        sign = ONE if self.current.direction == "long" else -ONE
        return self.cash + (price - self.current.entry_price) * self.remaining_qty * sign

    def costs(self, notional: Decimal, *, maker: bool = False) -> tuple[Decimal, Decimal]:
        return _leg_cost(
            notional,
            fill_type="maker" if maker else "taker",
            taker_fee=Decimal(str(self.cfg.fees)),
            slippage=Decimal(str(self.cfg.slippage)),
            maker_fee=Decimal(str(self.cfg.maker_fee)),
        )

    def exit(self, event: RiskEvent, index: int, timestamp: str, phase: str) -> None:
        episode = self.current
        assert episode is not None
        sign = ONE if episode.direction == "long" else -ONE
        gross = (event.price - episode.entry_price) * event.qty * sign
        fee, slip = self.costs(event.price * event.qty, maker=event.kind == "partial_tp")
        self.cash += gross - fee - slip
        episode.realized += gross
        episode.fees += fee
        episode.slippage += slip
        episode.exit_notional += event.price * event.qty
        self.remaining_qty -= event.qty
        self.counters[event.kind] += 1
        self.fills.append(
            {
                "generation": event.generation,
                "timestamp": timestamp,
                "phase": phase,
                "kind": event.kind,
                "price": event.price,
                "quantity": event.qty,
                "fee": fee,
                "slippage": slip,
                "gross_pnl": gross,
            }
        )
        if self.remaining_qty == ZERO:
            episode.exit_index, episode.exit_time = index, timestamp
            self.current, self.state = None, None

    def market(
        self,
        direction: Direction,
        price: Decimal,
        index: int,
        timestamp: str,
        phase: str,
        previous_bars: Sequence[Mapping[str, Decimal]],
    ) -> str:
        if self.current is not None and self.current.direction == direction:
            self.counters["same_direction_ignored"] += 1
            return "same_direction_ignored"
        if self.current is not None:
            event = RiskEvent(self.generation, "close", price, self.remaining_qty)
            self.exit(event, index, timestamp, phase)
            self.counters["reversal"] += 1
        if self.cash <= ZERO:
            self.counters["nonpositive_equity"] += 1
            return "nonpositive_equity"
        value = Decimal(str(self.cfg.default_qty_value or 100))
        if self.cfg.default_qty_type == "strategy.fixed":
            quantity = value
        elif self.cfg.default_qty_type == "strategy.cash":
            quantity = value / price
        else:
            quantity = self.cash * value / Decimal("100") / price
        if (self.cfg.default_qty_type == "strategy.fixed" and quantity * price > self.cash) or (
            self.cfg.default_qty_type == "strategy.cash" and value > self.cash
        ):
            self.counters["insufficient_capital"] += 1
            return "insufficient_capital"
        plan = None
        if self.exit_policy == "swing":
            try:
                plan = create_plan(
                    entry_price=price,
                    qty=quantity,
                    direction=direction,
                    previous_bars=previous_bars,
                    generation=self.generation + 1,
                )
            except ValueError:
                self.counters["invalid_swing"] += 1
                return "invalid_swing"
        self.generation += 1
        self.state = initial_state(plan) if plan is not None else None
        self.remaining_qty = quantity
        fee, slip = self.costs(price * quantity)
        self.cash -= fee + slip
        self.current = _Episode(
            self.generation,
            direction,
            index,
            price,
            quantity,
            timestamp,
            phase,
            fees=fee,
            slippage=slip,
        )
        self.episodes.append(self.current)
        self.counters["entry"] += 1
        self.fills.append(
            {
                "generation": self.generation,
                "timestamp": timestamp,
                "phase": phase,
                "kind": "entry",
                "direction": direction,
                "price": price,
                "quantity": quantity,
                "fee": fee,
                "slippage": slip,
                "plan": json_value(plan),
            }
        )
        return "entry"


def _execution_data(
    parent: pd.DataFrame, execution: pd.DataFrame, cfg: BacktestConfig, warmup: int
) -> tuple[int, dict[str, list[Decimal]], pd.DatetimeIndex]:
    width = pd.tseries.frequencies.to_offset(cfg.freq).nanos
    if width not in (3_600_000_000_000, 14_400_000_000_000, 86_400_000_000_000):
        raise PythonRuntimeError("swing 연구의 부모봉은 1h/4h/1d만 지원합니다")
    if np.any(parent.index.to_numpy(dtype="datetime64[ns]").astype(np.int64) % width):
        raise PythonRuntimeError("부모봉은 UTC 봉 경계에 맞아야 합니다")
    index = execution.index
    if not isinstance(index, pd.DatetimeIndex) or index.tz is None:
        raise PythonRuntimeError("실행 분봉은 tz-aware DatetimeIndex여야 합니다")
    expected = (len(parent) - warmup) * (width // MINUTE_NS)
    start, end = parent.index[warmup].value, parent.index[-1].value + width
    if (
        len(index) != expected
        or len(index) == 0
        or index[0].value != start
        or index[-1].value + MINUTE_NS != end
        or np.any(np.diff(index.to_numpy(dtype="datetime64[ns]").astype(np.int64)) != MINUTE_NS)
    ):
        raise PythonRuntimeError("실행 1분봉이 요청 구간을 정확히 덮지 않거나 빈 구간이 있습니다")
    columns: dict[str, list[Decimal]] = {}
    for name in ("open", "high", "low", "close", "volume"):
        if name not in execution:
            raise PythonRuntimeError(f"실행 분봉에 {name}이 없습니다")
        values = execution[name].tolist()
        columns[name] = [v if isinstance(v, Decimal) else Decimal(str(v)) for v in values]
    numeric = execution[["open", "high", "low", "close", "volume"]].to_numpy(dtype=float)
    if not np.isfinite(numeric).all() or (numeric[:, :4] <= 0).any() or (numeric[:, 4] < 0).any():
        raise PythonRuntimeError("실행 분봉 가격·거래량이 유한 양수/비음수여야 합니다")
    o, h, low, c = (numeric[:, i] for i in range(4))
    if ((low > np.minimum(o, c)) | (h < np.maximum(o, c))).any():
        raise PythonRuntimeError("실행 분봉 OHLC 가격 관계가 올바르지 않습니다")
    count = width // MINUTE_NS
    for offset, (_, row) in enumerate(parent.iloc[warmup:].iterrows()):
        left, right = offset * count, (offset + 1) * count
        aggregated = (
            columns["open"][left],
            max(columns["high"][left:right]),
            min(columns["low"][left:right]),
            columns["close"][right - 1],
        )
        if aggregated != tuple(
            Decimal(str(row[name])) for name in ("open", "high", "low", "close")
        ):
            raise PythonRuntimeError("부모봉 OHLC와 실행 분봉 집계가 다릅니다")
    return int(count), columns, index


def _raw_episode(episode: _Episode) -> RawTrade:
    closed = episode.exit_index is not None
    net = episode.realized - episode.fees - episode.slippage - episode.funding
    return RawTrade(
        trade_index=episode.generation - 1,
        direction=episode.direction,
        status="closed" if closed else "open",
        entry_bar_index=episode.entry_index,
        exit_bar_index=episode.exit_index,
        entry_price=episode.entry_price,
        exit_price=episode.exit_notional / episode.quantity if closed else None,
        size=episode.quantity,
        pnl=net,
        return_pct=net / (episode.entry_price * episode.quantity),
        fees=episode.fees + episode.slippage,
        fee_paid=episode.fees,
        slippage_paid=episode.slippage,
        bars_in_trade=episode.exit_index - episode.entry_index
        if episode.exit_index is not None
        else None,
    )


def run_swing_risk_backtest(
    source: str,
    parent_ohlcv: pd.DataFrame,
    execution_ohlcv: pd.DataFrame,
    config: BacktestConfig | None = None,
    funding_rates: pd.Series | None = None,
    params: dict[str, Any] | None = None,
    warmup_bars: int = 0,
    *,
    transport_factory: Callable[[], PythonTransport] | None = None,
    exit_policy: Literal["swing", "source"] = "swing",
) -> dict[str, Any]:
    """부모봉만 격리 코드에 전달하고 신뢰된 컨트롤러가 1분봉을 순서대로 재생한다."""
    cfg = config or replace(BacktestConfig(), fill_timing="next_bar_open")
    if exit_policy not in ("swing", "source"):
        raise PythonRuntimeError("청산 정책은 swing/source여야 합니다")
    if cfg.trading_sessions:
        raise PythonRuntimeError("swing 연구 실행기는 trading_sessions 필터를 지원하지 않습니다")
    if cfg.input_overrides is not None:
        raise PythonRuntimeError("swing 연구 실행기는 Pine input_overrides를 지원하지 않습니다")
    if cfg.live_position_size_pct not in (None, 100):
        raise PythonRuntimeError(
            "swing 연구 실행기의 live_position_size_pct는 None/100만 허용합니다"
        )
    parameters = dict(params or {})
    validate_source_and_params(source, parameters)
    validate_python_data(parent_ohlcv, cfg, warmup_bars)
    minutes, prices, index = _execution_data(parent_ohlcv, execution_ohlcv, cfg, warmup_bars)
    rates: dict[int, Decimal] = {}
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
            raise PythonRuntimeError("펀딩 시각은 중복 없는 정렬된 tz-aware 인덱스여야 합니다")
        for ts, raw in funding_rates.items():
            rate = Decimal(str(raw))
            if not rate.is_finite() or pd.Timestamp(str(ts)).value % MINUTE_NS:
                raise PythonRuntimeError("펀딩 비율 또는 분봉 경계가 올바르지 않습니다")
            rates[pd.Timestamp(str(ts)).value] = rate
    ledger = _Ledger(cfg, cfg.init_cash, exit_policy)
    equity_values: list[Decimal] = []
    signals: list[dict[str, Any]] = []
    ambiguous: list[dict[str, str]] = []
    parents = parent_ohlcv.to_dict("records")
    parent_timestamps = parent_ohlcv.index
    pending: tuple[str, list[dict[str, Decimal]], dict[str, Any]] | None = None
    transport = (transport_factory or DockerPythonTransport)()
    try:
        ready = transport.exchange(
            {"type": "init", "protocol": PROTOCOL_VERSION, "source": source, "params": parameters}
        )
        if ready != {"ready": PROTOCOL_VERSION}:
            raise PythonRuntimeError("Python 실행기 프로토콜 버전이 다릅니다")
        for parent_index, row in enumerate(parents):
            if parent_index >= warmup_bars:
                left = (parent_index - warmup_bars) * minutes
                right = left + minutes
                child = left
                while child < right:
                    if ledger.current is None and (pending is None or child > left):
                        equity_values.extend([ledger.cash] * (right - child))
                        break
                    timestamp = index[child].isoformat()
                    current_rate = rates.get(index[child].value)
                    if current_rate is not None and ledger.current is not None:
                        sign = ONE if ledger.current.direction == "long" else -ONE
                        funding = prices["open"][child] * ledger.remaining_qty * current_rate * sign
                        ledger.cash -= funding
                        ledger.current.funding += funding
                    if child == left and pending is not None:
                        direction, references, signal = pending
                        if direction == "close":
                            if ledger.current is not None:
                                ledger.exit(
                                    RiskEvent(
                                        ledger.generation,
                                        "close",
                                        prices["open"][child],
                                        ledger.remaining_qty,
                                    ),
                                    child,
                                    timestamp,
                                    "minute_open",
                                )
                            signal["disposition"] = "close"
                        else:
                            signal["disposition"] = ledger.market(
                                cast(Direction, direction),
                                prices["open"][child],
                                child,
                                timestamp,
                                "minute_open",
                                references,
                            )
                        pending = None
                    if ledger.state is not None:
                        was_active = ledger.state.trailing_active
                        outcome = replay_candle(
                            ledger.state,
                            open_=prices["open"][child],
                            high=prices["high"][child],
                            low=prices["low"][child],
                            close=prices["close"][child],
                        )
                        if outcome.state.trailing_active and not was_active:
                            ledger.counters["trailing_activation"] += 1
                        if outcome.ambiguous:
                            ambiguous.append(
                                {"timestamp": timestamp, "selected_path": outcome.path}
                            )
                        for event in outcome.events:
                            assert ledger.state is not None
                            ledger.state = apply_event(ledger.state, event)
                            ledger.exit(event, child, timestamp, "minute_path")
                        if ledger.state is not None:
                            ledger.state = outcome.state
                    equity_values.append(ledger.mark(prices["close"][child]))
                    child += 1
            bar = {
                "index": parent_index,
                "timestamp": parent_timestamps[parent_index].isoformat(),
                **{name: str(row[name]) for name in ("open", "high", "low", "close", "volume")},
            }
            reply = transport.exchange({"type": "bar", "bar": bar, "position": ledger.position()})
            if set(reply) != {"intent"}:
                raise PythonRuntimeError("Python 실행기 응답 형식이 다릅니다")
            intent = validate_intent(reply["intent"])
            if parent_index < warmup_bars:
                continue
            action = intent["action"]
            if exit_policy == "source" and len(intent) > 1:
                raise PythonRuntimeError(
                    "source 비교 정책은 close 신호만 지원하며 SL/TP 출력은 지원하지 않습니다"
                )
            if exit_policy == "swing" and (action == "close" or len(intent) > 1):
                ledger.counters["source_exit_ignored"] += 1
            if action not in ("long", "short") and not (
                exit_policy == "source" and action == "close"
            ):
                continue
            signal = {
                "parent_index": parent_index,
                "timestamp": parent_timestamps[parent_index].isoformat(),
                "available_at": (
                    parent_timestamps[parent_index] + pd.Timedelta(minutes=minutes)
                ).isoformat(),
                "direction": action,
            }
            signals.append(signal)
            ledger.counters["signal_opportunity"] += 1
            if ledger.current is not None and ledger.current.direction == action:
                signal["disposition"] = "same_direction_ignored"
                ledger.counters["same_direction_ignored"] += 1
                continue
            if exit_policy == "swing" and parent_index < 1:
                signal["disposition"] = "insufficient_history"
                ledger.counters["insufficient_history"] += 1
                continue
            references = [
                {name: Decimal(str(parents[j][name])) for name in ("open", "high", "low", "close")}
                for j in (parent_index - 1, parent_index)
                if j >= 0
            ]
            if cfg.fill_timing == "next_bar_open":
                signal["disposition"] = "queued_unfilled"
                pending = action, references, signal
            else:
                last = right - 1
                close_timestamp = (index[last] + pd.Timedelta(minutes=1)).isoformat()
                if action == "close":
                    if ledger.current is not None:
                        ledger.exit(
                            RiskEvent(
                                ledger.generation,
                                "close",
                                prices["close"][last],
                                ledger.remaining_qty,
                            ),
                            last,
                            close_timestamp,
                            "parent_close",
                        )
                    signal["disposition"] = "close"
                else:
                    signal["disposition"] = ledger.market(
                        cast(Direction, action),
                        prices["close"][last],
                        last,
                        close_timestamp,
                        "parent_close",
                        references,
                    )
                equity_values[-1] = ledger.mark(prices["close"][last])
    finally:
        transport.close()
    trades = [_raw_episode(episode) for episode in ledger.episodes]
    equity = pd.Series(equity_values, index=index, dtype=object)
    total_funding = (
        sum((episode.funding for episode in ledger.episodes), ZERO) if cfg.include_funding else None
    )
    metrics = _compute_metrics(
        trades,
        equity,
        replace(cfg, freq="1min"),
        execution_ohlcv,
        funding_data_incomplete=None if trades else False,
        total_funding=total_funding,
    )
    closed_net = sum((trade.pnl for trade in trades if trade.status == "closed"), ZERO)
    metrics = replace(
        metrics,
        open_pnl=equity_values[-1] - cfg.init_cash - closed_net,
        drawdown_curve=metrics.drawdown_curve[minutes - 1 :: minutes]
        if metrics.drawdown_curve is not None
        else None,
        buy_and_hold_curve=metrics.buy_and_hold_curve[minutes - 1 :: minutes]
        if metrics.buy_and_hold_curve is not None
        else None,
    )
    parent_curve = equity.iloc[minutes - 1 :: minutes]
    return {
        "metrics": json_value(metrics),
        "trades": json_value(trades),
        "equity_curve": [
            {"timestamp": pd.Timestamp(str(ts)).isoformat(), "value": str(value)}
            for ts, value in parent_curve.items()
        ],
        "config_used": json_value(cfg),
        "fill_events": json_value(ledger.fills),
        "signals": signals,
        "counters": dict(ledger.counters),
        "ambiguous_execution_bars": ambiguous,
        "comparison_metrics": {
            "parent_close_max_drawdown": str(_max_drawdown(parent_curve.astype(float)))
        },
        "exit_policy": exit_policy,
        "risk_policy": json_value(POLICY) if exit_policy == "swing" else None,
        "position_episodes": [
            {
                **json_value(episode),
                "remaining_quantity": str(ledger.remaining_qty)
                if ledger.current is episode
                else "0",
            }
            for episode in ledger.episodes
        ],
        "assumptions": {
            "execution_timeframe": "1min",
            "metrics_equity_sampling": "1min_close",
            "stored_equity_sampling": "parent_close",
            "trade_count_basis": "position_episode",
            "source_exit_policy": "replace_close_stop_loss_take_profit"
            if exit_policy == "swing"
            else "honor_original_close_same_ledger",
            "same_direction_signal_policy": "preserve_existing_plan",
            "intraminute_path": "worse_of_O_H_L_C_and_O_L_H_C",
            "path_comparison_basis": "realized_plus_close_unrealized_before_fees_slippage",
            "path_uncertainty": "two_paths_are_scenarios_not_tick_reconstruction",
            "funding_order": "minute_open_before_queued_market_orders",
            "funding_existing_position": "quantity_in_ledger_immediately_before_minute_open",
            "simultaneous_funding_order": "model_assumption_not_exchange_event_evidence",
            "funding_price_basis": "minute_open_proxy_not_settlement_mark",
            "funding_status": "observed_settlements_only" if cfg.include_funding else "disabled",
        },
        "provenance": {
            "source_hash": hashlib.sha256(source.encode()).hexdigest(),
            "parameters_hash": digest(parameters),
            "engine_hash": engine_digest(),
            "risk_state_hash": hashlib.sha256(
                (
                    Path(__file__).resolve().parents[2] / "strategy/python_runtime/swing_risk.py"
                ).read_bytes()
            ).hexdigest(),
            "runner_image_id": getattr(transport, "image_id", None),
            "parent_data_hash": digest(
                {"times": [ts.isoformat() for ts in parent_timestamps], "bars": parents}
            ),
            "execution_data_hash": digest(
                {
                    "times": index.to_numpy(dtype="datetime64[ns]").astype(np.int64).tolist(),
                    "prices": prices,
                }
            ),
            "funding_hash": digest(rates),
            "warmup_bars": warmup_bars,
        },
    }

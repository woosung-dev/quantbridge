"""Tier-1 가상 strategy 래퍼 — indicator + alertcondition → 자동 매매 실행.

ADR-011 §2.1.4 차별화 핵심. `collect_alerts()`가 반환한 AlertHook의
`condition_ast`를 매 bar `_eval_expr`로 재평가하여 SignalKind → strategy.*
매핑으로 자동 entry/close 호출.

v1 정책:
- LONG_ENTRY  → strategy.entry("L", long) (기존 short 자동 reverse)
- SHORT_ENTRY → strategy.entry("S", short) (기존 long 자동 reverse)
- LONG_EXIT   → strategy.close("L")
- SHORT_EXIT  → strategy.close("S")
- INFORMATION / UNKNOWN → 무시 + warning
- discrepancy=True → warning 기록 후 condition_signal 우선 (collect_alerts가 이미 반영)

H2+ 이연: trail_points / qty_percent / pyramiding / stop/limit 쌍 복합 exit (ADR-011 §13).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

import pandas as pd

from src.strategy.pine_v2.alert_hook import AlertHook, SignalKind, collect_alerts
from src.strategy.pine_v2.event_loop import _validate_ohlcv
from src.strategy.pine_v2.interpreter import (
    BarContext,
    Interpreter,
    PineRuntimeError,
    pine_version_from_ast,
)
from src.strategy.pine_v2.parser_adapter import parse_to_ast
from src.strategy.pine_v2.rendering import RenderingRegistry
from src.strategy.pine_v2.runtime import PersistentStore
from src.strategy.pine_v2.signal_trace import SignalObservation
from src.strategy.pine_v2.strategy_state import MarketIntent, StrategyState

ActionKind = Literal["entry", "close"]


@dataclass(frozen=True)
class VirtualAction:
    """SignalKind → strategy 호출로 매핑된 action."""

    kind: ActionKind
    trade_id: str
    direction: Literal["long", "short"] | None  # close에는 None


_SIGNAL_TO_ACTION: dict[SignalKind, VirtualAction] = {
    SignalKind.LONG_ENTRY: VirtualAction(kind="entry", trade_id="L", direction="long"),
    SignalKind.SHORT_ENTRY: VirtualAction(kind="entry", trade_id="S", direction="short"),
    SignalKind.LONG_EXIT: VirtualAction(kind="close", trade_id="L", direction=None),
    SignalKind.SHORT_EXIT: VirtualAction(kind="close", trade_id="S", direction=None),
}


def signal_to_action(signal: SignalKind) -> VirtualAction | None:
    """SignalKind을 VirtualAction으로 변환. 매매 신호가 아니면 None."""
    return _SIGNAL_TO_ACTION.get(signal)


# --- VirtualRunResult / VirtualStrategyWrapper / run_virtual_strategy ------


@dataclass
class VirtualRunResult:
    """Tier-1 가상 strategy 실행 결과."""

    bars_processed: int
    strategy_state: StrategyState
    alerts: list[AlertHook]
    rendering: RenderingRegistry | None = None  # line/box/label/table handle 수집
    warnings: list[str] = field(default_factory=list)
    errors: list[tuple[int, str]] = field(default_factory=list)
    signal_trace: list[SignalObservation] = field(default_factory=list)
    degraded_calls_seen: list[str] = field(default_factory=list)


class VirtualStrategyWrapper:
    """Alert hook을 매 bar 재평가하여 strategy.* 호출로 연결.

    - interpreter.execute(tree) 직후 `process_bar(bar_idx)` 호출.
    - 각 AlertHook.condition_ast를 `_eval_expr`로 평가 → truthy 여부 판정.
    - bar_close는 기존 False→True edge 동작을 유지한다.
    - next_bar_open은 실제 호출의 모든 true 사건을 단일 포지션 큐로 전달한다.
    - discrepancy=True alert은 최초 발견 시 1회 warning 기록.
    - LONG/SHORT 반대 포지션이 존재하면 자동 reverse (기존 청산 → 신규 진입).
    """

    def __init__(
        self,
        alerts: list[AlertHook],
        interp: Interpreter,
        *,
        strict: bool = True,
    ) -> None:
        self.alerts = alerts
        self.interp = interp
        self.strict = strict
        self.warnings: list[str] = []
        # 각 alert index → 직전 bar 평가 결과 (edge trigger용). 첫 bar의 이전 상태는 False.
        self._prev: dict[int, bool] = {a.index: False for a in alerts}
        self._discrepancy_logged: set[int] = set()

    def process_bar(
        self, bar_idx: int, observations: list[SignalObservation] | None = None
    ) -> None:
        """현재 봉 관찰값 또는 기존 조건 재평가로 strategy action을 디스패치한다."""
        next_open_actions: list[VirtualAction] = []
        for hook in self.alerts:
            if observations is None and hook.condition_ast is None:
                # condition AST가 없는 alert는 재평가 불가 — 무시
                continue
            if observations is not None:
                # 실제 호출에서 평가한 값을 재사용해 상태형 ta.*를 두 번 호출하지 않는다.
                cur = any(
                    self.interp._truthy(observation.value)
                    for observation in observations
                    if observation.source_line == hook.source_line
                    and observation.source_column == hook.source_column
                    and observation.function == hook.kind
                )
            else:
                try:
                    raw = self.interp._eval_expr(hook.condition_ast)
                except PineRuntimeError as exc:
                    if self.strict:
                        raise
                    self.warnings.append(
                        f"bar {bar_idx}: alert#{hook.index} condition eval failed: {exc}"
                    )
                    continue
                cur = self.interp._truthy(raw)
            prev = self._prev[hook.index]
            self._prev[hook.index] = cur
            # 기존 즉시 체결은 edge 동작을 유지한다. 다음 봉 원장은 원본의 모든
            # true 사건을 읽고, 같은 방향 추가 진입은 아래 포지션 검사로 생략한다.
            if not cur or (prev and self.interp.strategy.fill_timing != "next_bar_open"):
                continue

            if hook.discrepancy and hook.index not in self._discrepancy_logged:
                self.warnings.append(
                    f"alert#{hook.index}: message='{hook.message}' vs "
                    f"condition='{hook.condition_expr}' discrepancy — "
                    f"using condition_signal={hook.signal.value}"
                )
                self._discrepancy_logged.add(hook.index)

            action = signal_to_action(hook.signal)
            if action is None:
                continue  # INFORMATION / UNKNOWN

            fill_price = self.interp.bar.current("close")
            state = self.interp.strategy
            if state.fill_timing == "next_bar_open":
                next_open_actions.append(action)
                continue
            if action.kind == "entry":
                # BL-188 v3 entry placement gate (Track A) — disallowed session 이면
                # silent skip → equity/state 영향 0. interpreter `_exec_strategy_call`
                # 의 entry hook 과 동일 정책.
                if state.sessions_allowed:
                    bar_ts = self.interp.bar.current_timestamp()
                    if bar_ts is not None:
                        from src.strategy.trading_sessions import is_allowed

                        if not is_allowed(list(state.sessions_allowed), bar_ts.to_pydatetime()):
                            continue

                # 반대 포지션 자동 reverse
                reverse_id = "S" if action.direction == "long" else "L"
                if reverse_id in state.open_trades:
                    state.close(reverse_id, bar=bar_idx, fill_price=fill_price)
                assert action.direction is not None
                # BL-185 spot-equivalent: configure_sizing 호출 시 default_qty_type 기반 계산.
                # 미호출 시 compute_qty()=1.0 (기존 호환).
                state.entry(
                    action.trade_id,
                    action.direction,
                    qty=state.compute_qty(fill_price=fill_price),
                    bar=bar_idx,
                    fill_price=fill_price,
                )
            else:  # close
                state.close(action.trade_id, bar=bar_idx, fill_price=fill_price)

        if len({action.direction for action in next_open_actions if action.kind == "entry"}) > 1:
            raise PineRuntimeError("동일 봉 매수·매도 신호가 충돌합니다")
        # 단일 포지션 신호 원장과 같이 명시 청산을 먼저 처리하고 같은 방향 추가
        # 진입은 생략한다. 실제 체결·반전·수량 계산은 다음 봉의 공통 큐가 담당한다.
        closing_ids = {action.trade_id for action in next_open_actions if action.kind == "close"}
        for action in sorted(
            dict.fromkeys(next_open_actions), key=lambda item: item.kind == "entry"
        ):
            state = self.interp.strategy
            if action.kind == "entry":
                if action.trade_id in state.open_trades and action.trade_id not in closing_ids:
                    continue
                if state.sessions_allowed:
                    from src.strategy.trading_sessions import is_allowed

                    bar_ts = self.interp.bar.current_timestamp()
                    if bar_ts is not None and not is_allowed(
                        list(state.sessions_allowed), bar_ts.to_pydatetime()
                    ):
                        continue
                assert action.direction is not None
            state.queue_market_intent(
                MarketIntent(
                    kind=action.kind,
                    trade_id=action.trade_id,
                    direction=action.direction or "long",
                    placed_bar=bar_idx,
                )
            )


def run_virtual_strategy(
    source: str,
    ohlcv: pd.DataFrame,
    *,
    strict: bool = True,
    initial_capital: float | None = None,
    default_qty_type: str | None = None,
    default_qty_value: float | None = None,
    leverage: float = 1.0,
    taker_cost_rate: float = 0.0,
    sessions_allowed: tuple[str, ...] = (),
    input_overrides: Mapping[str, Any] | None = None,
    pyramiding: int | None = None,
    fill_timing: str = "bar_close",
    capture_signals: bool = False,
    timeframe: str | None = None,
) -> VirtualRunResult:
    """indicator + alertcondition Pine 스크립트를 가상 strategy로 실행.

    - 매 bar interpreter.execute(tree) 실행 후 VirtualStrategyWrapper가 실제 alert
      관찰값 또는 기존 조건 재평가로 strategy.entry/close를 발행한다.
    - next_bar_open이면 시장가 인텐트를 다음 봉 시작에 체결한다. bar_close는
      기존 즉시 체결을 유지하며 마지막 봉의 next_bar_open 인텐트는 미체결로 남는다.

    BL-185 spot-equivalent: initial_capital 지정 시 configure_sizing 호출.
    process_bar 가 state.compute_qty(fill_price) 로 entry qty 계산.
    leverage 는 주문 수량이 아닌 격리 증거금 게이트와 청산가에만 적용한다.
    BL-460: taker_cost_rate 는 그 게이트가 보는 net 자본에만 반영한다(gross 불변).

    BL-188 v3: sessions_allowed → state.sessions_allowed 주입. 비어있으면 24h.
    비어있지 않으면 ohlcv.index 가 tz-aware DatetimeIndex 여야 함 (v2_adapter 보증).
    """
    _validate_ohlcv(ohlcv)
    tree = parse_to_ast(source)
    alerts = collect_alerts(source)

    timestamps: pd.DatetimeIndex | None = (
        ohlcv.index if isinstance(ohlcv.index, pd.DatetimeIndex) else None
    )

    store = PersistentStore()
    bar = BarContext(
        ohlcv.reset_index(drop=True),
        timestamps=timestamps,
        timeframe=timeframe,
        pine_version=pine_version_from_ast(tree),
    )
    # Sprint 51 BL-220 — input_overrides 주입 (Param Stability grid sweep cell 단위).
    observe_signals = capture_signals or fill_timing == "next_bar_open"
    interp = Interpreter(
        bar, store, input_overrides=input_overrides, capture_signals=observe_signals
    )
    if initial_capital is not None:
        interp.strategy.configure_sizing(
            initial_capital=initial_capital,
            default_qty_type=default_qty_type,
            default_qty_value=default_qty_value,
            leverage=leverage,
            taker_cost_rate=taker_cost_rate,
        )
    interp.strategy.sessions_allowed = tuple(sessions_allowed)
    interp.strategy.pyramiding = pyramiding  # BL-104 — cap. None 시 무효(회귀 0).
    interp.strategy.fill_timing = fill_timing
    wrapper = VirtualStrategyWrapper(alerts, interp, strict=strict)

    errors: list[tuple[int, str]] = []
    bars_processed = 0
    while bar.advance():
        store.begin_bar()
        interp.reset_transient()
        interp.begin_bar_snapshot()
        # BL-188 v3 — fill gate: bar_ts 전달 → check_pending_fills 가 disallowed
        # session 시 fill skip + carry-over.
        bar_ts = bar.current_timestamp()
        interp.strategy.process_market_intents(
            bar=bar.bar_index,
            open_=bar.current("open"),
            bar_ts=bar_ts.to_pydatetime() if bar_ts is not None else None,
        )
        interp.strategy.check_pending_fills(
            bar=bar.bar_index,
            open_=bar.current("open"),
            high=bar.current("high"),
            low=bar.current("low"),
            bar_ts=bar_ts.to_pydatetime() if bar_ts is not None else None,
        )
        interp.strategy.check_liquidations(
            bar=bar.bar_index,
            open_=bar.current("open"),
            high=bar.current("high"),
            low=bar.current("low"),
        )
        try:
            trace_start = len(interp.signal_trace)
            interp.execute(tree)
            wrapper.process_bar(
                bar.bar_index,
                observations=interp.signal_trace[trace_start:] if observe_signals else None,
            )
        except PineRuntimeError as exc:
            if strict:
                store.commit_bar()
                raise
            errors.append((bar.bar_index, str(exc)))
        if not capture_signals:
            # 내부 dispatch의 관찰값만 필요하면 봉마다 비워 전체 history를 보관하지 않는다.
            interp.signal_trace.clear()
        store.commit_bar()
        interp.append_var_series()
        bars_processed += 1

    return VirtualRunResult(
        bars_processed=bars_processed,
        strategy_state=interp.strategy,
        alerts=alerts,
        rendering=interp.rendering,
        warnings=wrapper.warnings,
        errors=errors,
        signal_trace=interp.signal_trace,
        degraded_calls_seen=interp.degraded_calls_seen if capture_signals else [],
    )

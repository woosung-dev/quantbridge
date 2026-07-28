"""Bar-by-bar 이벤트 루프 드라이버 (Week 2 Day 2).

Pine AST interpreter를 OHLCV DataFrame 위에서 반복 호출하여 시계열 실행.
ADR-011 §2.0.3 bar-by-bar 이벤트 루프 원칙 구현.

의미론:
- 각 bar 진입 시 `store.begin_bar()` → interpreter가 실행 → `store.commit_bar()`
- var/varip 상태는 bar 경계를 지나 유지됨 (PersistentStore 책임)
- transient(비영속) 변수는 매 bar 재초기화 (interpreter.reset_transient)
- realtime rollback은 현재 루프 범위 밖 (historical 백테스트 용)

공개 API:
- `run_historical(source, ohlcv) -> RunResult`
- `run_live(source, ohlcv, *, initial_capital=None, live_position_size_pct=None, leverage=1.0,
  sessions_allowed=(), pyramiding=None)
  -> LiveSignalResult` (Sprint 26. 사이징 인자는 BL-479 — 미지정 시 qty=1.0 fallback)
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from decimal import ROUND_DOWN, Decimal
from typing import Any, Literal

import pandas as pd

from src.strategy.pine_v2.interpreter import (
    BarContext,
    Interpreter,
    PineRuntimeError,
)
from src.strategy.pine_v2.parser_adapter import parse_to_ast
from src.strategy.pine_v2.runtime import PersistentStore
from src.strategy.pine_v2.sizing import resolve_default_qty


@dataclass
class RunResult:
    """이벤트 루프 실행 결과."""

    bars_processed: int
    final_state: dict[str, Any]  # PersistentStore snapshot (key → value)
    state_history: list[dict[str, Any]] = field(default_factory=list)  # 각 bar commit 후 state
    errors: list[tuple[int, str]] = field(default_factory=list)  # (bar_index, 메시지)
    # Sprint 8c: 외부 assertion 접근용. run_historical 종료 시 채워짐.
    strategy_state: Any | None = None  # StrategyState (trades / position_size 포함)
    var_series: dict[str, list[Any]] = field(default_factory=dict)  # user 변수 시계열

    def __len__(self) -> int:
        return self.bars_processed

    def to_dict(self) -> dict[str, Any]:
        return {
            "bars_processed": self.bars_processed,
            "final_state": self.final_state,
            "state_history_length": len(self.state_history),
            "errors": self.errors,
            "var_series_keys": sorted(self.var_series.keys()),
        }


def run_historical(
    source: str,
    ohlcv: pd.DataFrame,
    *,
    capture_history: bool = True,
    strict: bool = True,
    initial_capital: float | None = None,
    default_qty_type: str | None = None,
    default_qty_value: float | None = None,
    leverage: float = 1.0,
    sessions_allowed: tuple[str, ...] = (),
    input_overrides: Mapping[str, Any] | None = None,
    pyramiding: int | None = None,
    fill_timing: str = "bar_close",
) -> RunResult:
    """Pine 소스를 OHLCV bar-by-bar 실행.

    Args:
        source: Pine 소스 코드.
        ohlcv: columns must include open/high/low/close/volume.
        capture_history: 각 bar commit 후 state를 기록할지 (디버깅/테스트용).
        strict: True면 interpreter 오류를 즉시 raise, False면 errors에 기록 후 계속.
        initial_capital: BL-185 spot-equivalent. 지정 시 StrategyState.configure_sizing
            호출 → strategy.entry qty 미지정 시 default_qty_type/value 기반 계산.
            None 이면 기존 qty=1.0 fallback (호환).
        default_qty_type: "strategy.percent_of_equity" | "strategy.cash" | "strategy.fixed" | None.
        default_qty_value: percent / cash / fixed value. None 또는 default_qty_type=None 시 무시.
        leverage: 1.0 초과 시 격리 증거금 게이트와 강제청산을 적용한다.
        sessions_allowed: BL-188 v3 — entry placement + pending fill 양쪽에 적용되는
            session gate. 비어있으면 24h. 비어있지 않으면 ohlcv.index 가 tz-aware
            DatetimeIndex 여야 함 (v2_adapter 가 422 reject 책임).
    """
    _validate_ohlcv(ohlcv)
    tree = parse_to_ast(source)

    # BL-188 v3 — entry/fill gate 용 tz-aware timestamps. ohlcv.reset_index(drop=True)
    # 이전에 원본 index 를 보존하여 BarContext 에 주입.
    timestamps: pd.DatetimeIndex | None = (
        ohlcv.index if isinstance(ohlcv.index, pd.DatetimeIndex) else None
    )

    store = PersistentStore()
    bar = BarContext(ohlcv.reset_index(drop=True), timestamps=timestamps)
    # Sprint 51 BL-220 — input_overrides 주입 (Param Stability grid sweep cell 단위).
    interp = Interpreter(bar, store, input_overrides=input_overrides)
    if initial_capital is not None:
        interp.strategy.configure_sizing(
            initial_capital=initial_capital,
            default_qty_type=default_qty_type,
            default_qty_value=default_qty_value,
            leverage=leverage,
        )
    interp.strategy.sessions_allowed = tuple(sessions_allowed)
    interp.strategy.pyramiding = pyramiding  # BL-104 — cap. None 시 무효(회귀 0).
    # TV parity — 시장가 체결 타이밍 ("bar_close" 기본 = 기존 byte-identical).
    interp.strategy.fill_timing = fill_timing
    result = RunResult(bars_processed=0, final_state={})

    while bar.advance():
        store.begin_bar()
        interp.reset_transient()
        interp.begin_bar_snapshot()  # prev_close 갱신 (ta.atr 등에 사용)
        # pending stop 주문 체결 검사 — 이번 bar의 OHLC로 trigger 확인.
        # BL-188 v3 — fill gate (E3 Live parity): bar_ts 전달 → check_pending_fills 가
        # disallowed session 시 fill skip + carry-over.
        bar_ts = bar.current_timestamp()
        bar_ts_py = bar_ts.to_pydatetime() if bar_ts is not None else None
        # TV parity (next_bar_open) — 직전 bar 큐 인텐트를 이번 bar 시가로 체결.
        # pending stop/exit 검사보다 먼저 (entry 체결 후 같은 bar 브래킷 부착 순서 유지).
        interp.strategy.process_market_intents(
            bar=bar.bar_index,
            open_=bar.current("open"),
            bar_ts=bar_ts_py,
        )
        interp.strategy.check_pending_fills(
            bar=bar.bar_index,
            open_=bar.current("open"),
            high=bar.current("high"),
            low=bar.current("low"),
            bar_ts=bar_ts_py,
        )
        interp.strategy.check_liquidations(
            bar=bar.bar_index,
            open_=bar.current("open"),
            high=bar.current("high"),
            low=bar.current("low"),
        )
        # BL-104 — pending exit 브래킷 체결 검사 (entry fill 직후, execute 전).
        # pending_exits 비어있으면 즉시 no-op → strategy.exit 미사용 시 회귀 0.
        interp.strategy.check_exit_fills(
            bar=bar.bar_index,
            open_=bar.current("open"),
            high=bar.current("high"),
            low=bar.current("low"),
            bar_ts=bar_ts_py,
        )
        try:
            interp.execute(tree)
        except PineRuntimeError as e:
            msg = str(e)
            if strict:
                store.commit_bar()  # bar는 닫고 에러 전파
                raise
            result.errors.append((bar.bar_index, msg))
        store.commit_bar()
        interp.append_var_series()  # 이번 bar의 user 변수 값을 시리즈에 append
        # persistent("main::name") + transient(bare name) 병합하여 스냅샷
        combined = {**store.snapshot_dict(), **interp._transient}
        if capture_history:
            result.state_history.append(combined)
        result.bars_processed += 1

    # 마지막 bar의 병합 스냅샷
    result.final_state = {**store.snapshot_dict(), **interp._transient}
    # Sprint 8c: 테스트 접근용 — StrategyState + user 변수 시계열 복사.
    # deque → list 변환: RunResult.var_series 타입은 dict[str, list[Any]]
    result.strategy_state = interp.strategy
    result.var_series = {k: list(v) for k, v in interp._var_series.items()}
    return result


def _validate_ohlcv(df: pd.DataFrame) -> None:
    required = {"open", "high", "low", "close", "volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"OHLCV DataFrame missing columns: {sorted(missing)}")
    if len(df) == 0:
        raise ValueError("OHLCV DataFrame is empty")


# ── Sprint 26: Live Signal Auto-Trading (Option B — warmup replay) ────────


@dataclass
class LiveSignal:
    """Sprint 26 — `run_live` 가 마지막 bar 에서 추출한 entry/close signal.

    `tasks/live_signal.py:dispatch_live_signal_event_task` 가 OrderRequest 로 변환.
    sequence_no 는 codex G.0 P2 #5 — 같은 bar 안 다중 event 의 idempotency_key 보장.
    """

    action: Literal["entry", "close"]
    direction: Literal["long", "short"]
    trade_id: str
    qty: float
    sequence_no: int
    comment: str = ""
    # MP-1 — close signal 의 청산 realized PnL (매칭 closed_trade 기준). entry 는 None.
    # Order.realized_pnl 로 전파되어 kill-switch 손실 평가기가 실제로 작동하게 한다.
    realized_pnl: Decimal | None = None
    # Phase 3 — entry signal 의 exit 레벨 (pending_exits 레그에서 fold). close 는 None.
    # bracket placement: take_profit/stop_loss 는 entry 주문에 부착(거래소-네이티브 OCO),
    # trailing_stop(quote 거리) 은 포지션 open 후 별도 trailing 주문. exit 미사용 시 None.
    take_profit: Decimal | None = None
    stop_loss: Decimal | None = None
    trailing_stop: Decimal | None = None
    # catch-up 발행에서만 원래 이벤트가 난 bar 시각을 보존한다. 기본 라이브 호출은 None으로
    # 유지해 마지막 bar만 발행하던 기존 계약을 그대로 둔다.
    bar_time: datetime | None = None


@dataclass
class PendingOrderSnapshot:
    """거래소 조건부 진입 주문과 reconcile할 엔진의 desired 상태.

    ★`target_position` 이 사이징의 SSOT다. "이 주문이 체결되면 순 포지션이 얼마가 되어야
    하는가"(long +, short -)를 담으며, 주문 수량은 reconciler 가 **거래소 실포지션과의 차**
    로 계산한다. 엔진이 계산한 delta 를 그대로 내보내면 안 되는 이유는 세 가지다.

    - 같은 id 재발행 — `check_pending_fills` 는 체결 시 같은 id 의 open trade 를 먼저
      닫고 다시 연다(`strategy_state.py:788-796`). 순 변화가 0인데 delta 를 보내면
      거래소 포지션이 2배가 된다. 시드 전략 `s1_pbr` 이 정확히 이 형태다.
    - pending 이 2건 이상이면 delta 는 서로 모순된다. 각자 "지금 포지션" 을 가정하는데
      한쪽이 체결되면 그 가정이 깨진다.
    - 거래소 실포지션이 시뮬과 어긋났을 때 delta 로는 복구할 방법이 없다. 목표를 보내면
      reconciler 가 매 tick 스스로 수렴한다.

    `entry_qty` 는 엔진이 의도한 진입 수량으로 표시·진단용이다. 사이징에 쓰지 마라.
    """

    trade_id: str
    direction: Literal["long", "short"]
    target_position: Decimal
    entry_qty: Decimal
    stop_price: Decimal
    placed_bar: int
    comment: str = ""


@dataclass
class LiveSignalResult:
    """`run_live` 의 반환 — outbox INSERT + state upsert 에 필요한 정보 패키징."""

    last_bar_time: datetime
    signals: list[LiveSignal]
    strategy_state_report: dict[str, Any]
    total_closed_trades: int
    total_realized_pnl: Decimal
    # 마지막 bar 에서 엔진 게이트가 삼킨 진입만 표면화한다.
    entry_skips: list[dict[str, Any]] = field(default_factory=list)
    # 마지막 bar 에서 엔진이 판정한 강제청산 close만 표면화한다.
    liquidations: list[dict[str, Any]] = field(default_factory=list)
    # BL-362 — run_historical(strict=False) 가 삼킨 PineRuntimeError (bar_index, msg).
    # 호출자(live_signal task)가 coverage↔interpreter 발산을 fail-closed 처리하도록 표면화.
    errors: list[tuple[int, str]] = field(default_factory=list)
    pending_orders: list[PendingOrderSnapshot] = field(default_factory=list)


def _to_decimal(value: float | None) -> Decimal | None:
    """pine float exit 레벨 → Decimal 경계 변환. None/비정상(NaN·Inf·<=0) → None.

    OrderRequest 의 exit 필드는 Field(gt=0) — NaN/Inf/음수/0 은 ValidationError.
    dispatch 의 OrderRequest 조립은 try/except 밖이라 uncaught → 이벤트가 pending 으로
    남아 outbox 가 영구 재dispatch (poison pill). 백테스트에서 비정상 레그(예: loss>entry
    → 음수 stop)는 어차피 미체결(harmless)이라 None 으로 drop = no-bracket = sim 정합 + 안전.
    """
    if value is None or not math.isfinite(value) or value <= 0:
        return None
    return Decimal(str(value))


# 조건부 진입이 거치는 API 경계의 정밀도. `OrderRequest.quantity` 와 `trigger_price` 는
# 둘 다 Field(decimal_places=8) 이다. 시장가 경로는 `LiveSignalEvent.qty` 가
# Numeric(18,8) 이라 DB 왕복이 양자화해 주지만, 조건부 경로는 JSONB 문자열로만 나가서
# 그 양자화가 없다. percent_of_equity 사이징은 소수 20자리를 만들므로(실측
# 0.00029537036490054884) 여기서 자르지 않으면 전량 ValidationError 로 거부된다.
_AMOUNT_QUANTUM = Decimal("1E-8")


def _quantize_amount(value: Decimal) -> Decimal:
    """API 경계(소수 8자리)로 절삭한다. 0 방향 절삭이라 의도보다 커지지 않는다."""
    return value.quantize(_AMOUNT_QUANTUM, rounding=ROUND_DOWN)


def _pending_fills_blocked_by_session(strategy_state: Any, last_bar_time: datetime) -> bool:
    """마지막 bar 가 금지 세션이면 True.

    엔진은 금지 세션 bar 에서 `check_pending_fills` 를 통째로 건너뛰고 주문을
    carry-over 한다(`strategy_state.py:748-752`). 그 동안 거래소에 조건부 주문을
    남겨두면 엔진은 절대 체결하지 않는데 거래소는 체결해 발산한다.

    ★한계 — 판정 기준은 마지막 **종료된** bar 다. 세션 경계에서 최대 1 bar 어긋난다.
    """
    if not strategy_state.sessions_allowed:
        return False
    from src.strategy.trading_sessions import is_allowed

    return not is_allowed(list(strategy_state.sessions_allowed), last_bar_time)


def run_live(
    source: str,
    ohlcv: pd.DataFrame,
    *,
    initial_capital: float | None = None,
    live_position_size_pct: float | None = None,
    leverage: float = 1.0,
    sessions_allowed: tuple[str, ...] = (),
    pyramiding: int | None = None,
    fill_timing: str = "bar_close",
    emit_from_bar_time: datetime | None = None,
) -> LiveSignalResult:
    """Sprint 26 — Option B (warmup replay) 채택.

    매 evaluate 마다 충분한 warmup OHLCV (호출자가 limit_bars=300 등으로 fetch)
    위에서 `run_historical` 전체 재실행. var_series / StdlibDispatcher / StrategyState
    는 자연 재생되어 PersistentStore.hydrate 같은 별도 직렬화 path 불필요
    (codex G.0 P1 #1 — hydrate 부족 → Option B 선택).

    기본값에서는 마지막 bar 의 TradeEvent 만 LiveSignal 로 변환한다 (codex G.0 P1 #2 —
    same-bar entry+close 회귀 방어). `emit_from_bar_time`을 명시한 catch-up 호출만 그 시각
    뒤의 모든 bar 이벤트를 변환한다. action="fill" 은 broker 이벤트 (pending stop 체결)
    이므로 Pine signal 로 dispatch 안 함 — broker 가 자체 fill 알림 처리.

    Args:
        source: Pine source code.
        ohlcv: 최근 N bars OHLCV (warmup + last evaluate bar 포함). 'timestamp' 컬럼
            (or index) 가 마지막 bar time 추출에 사용.
        initial_capital: 세션 시작 시 스냅샷한 자본 기준선. None 이면 기존 qty=1.0 fallback.
        live_position_size_pct: `StrategySettings.position_size_pct`.
        leverage: 1.0 초과 시 격리 증거금 게이트와 청산가 모델을 적용한다.
        sessions_allowed: 비어있으면 OHLCV 프레임을 그대로 사용한다. 비어있지 않을 때
            tz-aware DatetimeIndex가 없으면 tz-aware `timestamp` 컬럼으로 인덱스를 세우되,
            해당 컬럼은 보존한다. 둘 다 불가하면 세션 필터가 조용히 무시되지 않도록 실패한다.
        pyramiding: 같은 방향 동시 진입 cap. None 이면 cap을 적용하지 않는다.
        fill_timing: 시장가 체결 시점. "next_bar_open"은 진입뿐 아니라 close/close_all
            청산도 다음 bar 시가로 지연하므로 손절 청산도 한 bar 늦어진다.
        emit_from_bar_time: 지정 시 이 시각보다 뒤의 bar 이벤트를 모두 발행한다. None이면
            기존처럼 마지막 bar 이벤트만 발행한다.

    Returns:
        LiveSignalResult — last_bar_time + signals + strategy_state_report + 누적 통계.

    Raises:
        ValueError: ohlcv 비어있음 / required 컬럼 누락 / 세션 필터에 필요한 tz-aware 시각 부재.
    """
    _validate_ohlcv(ohlcv)

    if sessions_allowed and (
        not isinstance(ohlcv.index, pd.DatetimeIndex) or ohlcv.index.tz is None
    ):
        if "timestamp" not in ohlcv.columns:
            raise ValueError(
                "sessions_allowed requires a timezone-aware DatetimeIndex or timestamp column"
            )
        timestamps = pd.DatetimeIndex(ohlcv["timestamp"])
        if timestamps.tz is None:
            raise ValueError(
                "sessions_allowed requires a timezone-aware DatetimeIndex or timestamp column"
            )
        ohlcv = ohlcv.set_index(timestamps, drop=False)

    # run_historical 전체 재실행 (warmup replay)
    qty_type, qty_value = resolve_default_qty(
        source,
        initial_capital=initial_capital,
        live_position_size_pct=live_position_size_pct,
    )
    result = run_historical(
        source,
        ohlcv,
        capture_history=False,
        strict=False,
        initial_capital=initial_capital,
        default_qty_type=qty_type,
        default_qty_value=qty_value,
        leverage=leverage,
        sessions_allowed=sessions_allowed,
        pyramiding=pyramiding,
        fill_timing=fill_timing,
    )
    strategy_state = result.strategy_state
    if strategy_state is None:
        raise RuntimeError("run_historical returned no strategy_state")

    # MP-1 — closed_trade 의 realized PnL 을 trade_id 로 인덱싱 (close signal 에 부착).
    # 같은 trade_id 가 재사용되면 마지막 청산 PnL 이 우선 (dict overwrite) — 마지막 bar
    # event 만 signal 로 나가므로 실무상 1:1.
    pnl_by_trade: dict[str, Decimal] = {
        t.id: Decimal(str(t.pnl)) for t in strategy_state.closed_trades if t.pnl is not None
    }

    # 마지막 bar 의 TradeEvent → LiveSignal 변환. 기본 경로는 기존 마지막-bar 필터를
    # 그대로 쓴다. catch-up만 각 event의 bar_index를 timestamp 컬럼 우선으로 매핑한다.
    last_bar_index = len(ohlcv) - 1
    last_bar_events = [e for e in strategy_state.events if e.bar_index == last_bar_index]
    emitted_events = last_bar_events
    if emit_from_bar_time is not None:
        emitted_events = [
            e
            for e in strategy_state.events
            if _extract_bar_time(ohlcv, e.bar_index) > emit_from_bar_time
        ]
    last_bar_entry_skips = [
        skip for skip in strategy_state.entry_skips if skip["bar_index"] == last_bar_index
    ]
    last_bar_liquidations = [
        trade.to_dict()
        for trade in strategy_state.closed_trades
        if trade.exit_bar == last_bar_index and trade.is_liquidation
    ]
    # entry / close 만 dispatch 대상 (fill 은 broker 측 pending stop 체결)
    signals: list[LiveSignal] = []
    for e in emitted_events:
        if e.action not in ("entry", "close"):
            continue
        # Phase 3 — entry signal 은 pending_exits 의 TP/SL/trail 레벨을 fold
        # (float pine 관례 → Decimal 경계 변환). close 는 exit 레벨 없음.
        if e.action == "entry":
            levels = strategy_state.exit_levels_for(e.trade_id)
            take_profit = _to_decimal(levels.take_profit)
            stop_loss = _to_decimal(levels.stop_loss)
            trailing_stop = _to_decimal(levels.trailing_stop)
        else:
            take_profit = stop_loss = trailing_stop = None
        signals.append(
            LiveSignal(
                action=e.action,
                direction=e.direction,
                trade_id=e.trade_id,
                qty=e.qty,
                sequence_no=e.sequence_no,
                comment=e.comment,
                # close signal 만 realized PnL carry (entry 는 None).
                realized_pnl=(pnl_by_trade.get(e.trade_id) if e.action == "close" else None),
                take_profit=take_profit,
                stop_loss=stop_loss,
                trailing_stop=trailing_stop,
                bar_time=(
                    _extract_bar_time(ohlcv, e.bar_index)
                    if emit_from_bar_time is not None
                    else None
                ),
            )
        )

    # last_bar_time 추출
    last_bar_time = _extract_last_bar_time(ohlcv)

    # 누적 통계
    closed = strategy_state.closed_trades
    total_pnl = sum(
        (Decimal(str(t.pnl)) for t in closed if t.pnl is not None),
        Decimal("0"),
    )
    # 조건부 진입의 desired set. 엔진 상태(`strategy_state`)는 읽기만 한다 —
    # 여기서 warnings 에 append 하면 "run_live 는 run_historical 의 단순 wrapper" 라는
    # mutation oracle 불변식(test_run_live_consistent_with_run_historical_final_state)이
    # 비정상 레그 입력에서 깨진다. 드롭 사유는 live 전용 키로만 표면화한다.
    pending_orders: list[PendingOrderSnapshot] = []
    pending_order_skips: list[dict[str, Any]] = []
    # 금지 세션 동안 엔진은 pending 체결을 아예 건너뛰고 주문을 carry-over 한다
    # (`strategy_state.py:748-752`). 그때 거래소에 주문을 남겨두면 엔진은 절대 체결하지
    # 않는데 거래소는 체결한다 -> 조용한 발산. desired 를 비워 reconciler 가 걷어내게 한다.
    if _pending_fills_blocked_by_session(strategy_state, last_bar_time):
        pending_order_skips.extend(
            {"trade_id": trade_id, "reason": "session_disallowed", "invalid_fields": []}
            for trade_id in sorted(strategy_state.pending_orders)
        )
    else:
        for trade_id, order in sorted(strategy_state.pending_orders.items()):
            entry_qty = _to_decimal(order.qty)
            stop_price = _to_decimal(order.stop_price)
            if entry_qty is None or stop_price is None:
                # OrderRequest 의 trigger_price/quantity 는 Field(gt=0) 이라 비정상 값이
                # 도달하면 ValidationError 로 outbox 가 영구 재시도하는 poison pill 이 된다.
                pending_order_skips.append(
                    {
                        "trade_id": trade_id,
                        "reason": "invalid_leg",
                        "invalid_fields": [
                            name
                            for name, value in (("qty", entry_qty), ("stop_price", stop_price))
                            if value is None
                        ],
                    }
                )
                continue
            # 체결 후 순 포지션 = (같은 방향 open 중 이 id 를 제외한 합) + 신규 수량.
            # `check_pending_fills` 가 반대 방향 전량 close -> 같은 id close -> 신규 open
            # 순으로 도는 것을 그대로 옮긴 것이다(`strategy_state.py:788-796`).
            # 합산은 Decimal-first — `position_size` 는 float 누적이라 실측 라이브 수량에서
            # 오염된다(0.02953691 + 0.02946167 -> 0.058998579999999995).
            same_side_kept = sum(
                (
                    Decimal(str(trade.qty))
                    for other_id, trade in strategy_state.open_trades.items()
                    if trade.direction == order.direction and other_id != trade_id
                ),
                Decimal("0"),
            )
            magnitude = same_side_kept + entry_qty
            target = magnitude if order.direction == "long" else -magnitude
            # ★양자화 후 재검증. 절삭은 1E-8 미만 양수를 0 으로 만들 수 있고, 그 0 이
            # 그대로 나가면 Field(gt=0) ValidationError = 막으려던 바로 그 poison pill 이다.
            # 드롭 검사(`_to_decimal`)는 절삭 이전 값을 봤으므로 여기서 한 번 더 본다.
            quantized_qty = _quantize_amount(entry_qty)
            quantized_stop = _quantize_amount(stop_price)
            quantized_target = _quantize_amount(target)
            if quantized_qty <= 0 or quantized_stop <= 0 or quantized_target == 0:
                pending_order_skips.append(
                    {
                        "trade_id": trade_id,
                        "reason": "below_api_precision",
                        "invalid_fields": [
                            name
                            for name, value in (
                                ("qty", quantized_qty),
                                ("stop_price", quantized_stop),
                                ("target_position", quantized_target),
                            )
                            if value == 0
                        ],
                    }
                )
                continue
            pending_orders.append(
                PendingOrderSnapshot(
                    trade_id=trade_id,
                    direction=order.direction,
                    target_position=quantized_target,
                    entry_qty=quantized_qty,
                    stop_price=quantized_stop,
                    placed_bar=order.placed_bar,
                    comment=order.comment,
                )
            )

    strategy_state_report = strategy_state.to_report().copy()
    strategy_state_report.pop("entry_skips", None)
    strategy_state_report["last_bar_entry_skips"] = last_bar_entry_skips
    strategy_state_report["last_bar_liquidations"] = last_bar_liquidations
    strategy_state_report["pending_orders"] = [
        {
            "trade_id": order.trade_id,
            "direction": order.direction,
            "target_position": str(order.target_position),
            "entry_qty": str(order.entry_qty),
            "stop_price": str(order.stop_price),
            "placed_bar": order.placed_bar,
        }
        for order in pending_orders
    ]
    strategy_state_report["pending_order_skips"] = pending_order_skips
    # `placed_bar` 는 창 상대 인덱스라 그 자체로는 "창 이탈 임박" 을 판정할 수 없다.
    # 소비자가 headroom 을 계산할 수 있도록 창 크기를 함께 내보낸다.
    strategy_state_report["window_bars"] = len(ohlcv)

    return LiveSignalResult(
        last_bar_time=last_bar_time,
        signals=signals,
        strategy_state_report=strategy_state_report,
        total_closed_trades=len(closed),
        total_realized_pnl=total_pnl,
        entry_skips=last_bar_entry_skips,
        liquidations=last_bar_liquidations,
        errors=result.errors,  # BL-362 — 삼켜진 발산 표면화
        pending_orders=pending_orders,
    )


def _extract_last_bar_time(ohlcv: pd.DataFrame) -> datetime:
    """OHLCV 마지막 bar 의 timestamp 추출 (UTC tz-aware).

    'timestamp' 컬럼 우선 → DatetimeIndex fallback. naive 인 경우 UTC localize.
    """
    return _extract_bar_time(ohlcv, len(ohlcv) - 1)


def _extract_bar_time(ohlcv: pd.DataFrame, bar_index: int) -> datetime:
    """OHLCV의 bar 인덱스를 UTC tz-aware 시각으로 변환한다."""
    if "timestamp" in ohlcv.columns:
        ts = pd.Timestamp(ohlcv.iloc[bar_index]["timestamp"])
    elif isinstance(ohlcv.index, pd.DatetimeIndex):
        ts = pd.Timestamp(ohlcv.index[bar_index])
    else:
        raise ValueError("OHLCV must have 'timestamp' column or DatetimeIndex")
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.to_pydatetime()

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
- `run_live(source, ohlcv) -> LiveSignalResult` (Sprint 26)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Literal

import pandas as pd

from src.strategy.pine_v2.interpreter import (
    BarContext,
    Interpreter,
    PineRuntimeError,
)
from src.strategy.pine_v2.parser_adapter import parse_to_ast
from src.strategy.pine_v2.runtime import PersistentStore


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
) -> RunResult:
    """Pine 소스를 OHLCV bar-by-bar 실행.

    Args:
        source: Pine 소스 코드.
        ohlcv: columns must include open/high/low/close/volume.
        capture_history: 각 bar commit 후 state를 기록할지 (디버깅/테스트용).
        strict: True면 interpreter 오류를 즉시 raise, False면 errors에 기록 후 계속.
    """
    _validate_ohlcv(ohlcv)
    tree = parse_to_ast(source)

    store = PersistentStore()
    bar = BarContext(ohlcv.reset_index(drop=True))
    interp = Interpreter(bar, store)
    result = RunResult(bars_processed=0, final_state={})

    while bar.advance():
        store.begin_bar()
        interp.reset_transient()
        interp.begin_bar_snapshot()  # prev_close 갱신 (ta.atr 등에 사용)
        # pending stop 주문 체결 검사 — 이번 bar의 OHLC로 trigger 확인
        interp.strategy.check_pending_fills(
            bar=bar.bar_index,
            open_=bar.current("open"),
            high=bar.current("high"),
            low=bar.current("low"),
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


@dataclass
class LiveSignalResult:
    """`run_live` 의 반환 — outbox INSERT + state upsert 에 필요한 정보 패키징."""

    last_bar_time: datetime
    signals: list[LiveSignal]
    strategy_state_report: dict[str, Any]
    total_closed_trades: int
    total_realized_pnl: Decimal


def run_live(source: str, ohlcv: pd.DataFrame) -> LiveSignalResult:
    """Sprint 26 — Option B (warmup replay) 채택.

    매 evaluate 마다 충분한 warmup OHLCV (호출자가 limit_bars=300 등으로 fetch)
    위에서 `run_historical` 전체 재실행. var_series / StdlibDispatcher / StrategyState
    는 자연 재생되어 PersistentStore.hydrate 같은 별도 직렬화 path 불필요
    (codex G.0 P1 #1 — hydrate 부족 → Option B 선택).

    마지막 bar 의 TradeEvent 만 LiveSignal 로 변환 (codex G.0 P1 #2 — same-bar
    entry+close 회귀 방어). action="fill" 은 broker 이벤트 (pending stop 체결) 이므로
    Pine signal 로 dispatch 안 함 — broker 가 자체 fill 알림 처리.

    Args:
        source: Pine source code.
        ohlcv: 최근 N bars OHLCV (warmup + last evaluate bar 포함). 'timestamp' 컬럼
            (or index) 가 마지막 bar time 추출에 사용.

    Returns:
        LiveSignalResult — last_bar_time + signals + strategy_state_report + 누적 통계.

    Raises:
        ValueError: ohlcv 비어있음 / required 컬럼 누락.
    """
    _validate_ohlcv(ohlcv)

    # run_historical 전체 재실행 (warmup replay)
    result = run_historical(
        source, ohlcv, capture_history=False, strict=False
    )
    strategy_state = result.strategy_state
    if strategy_state is None:
        raise RuntimeError("run_historical returned no strategy_state")

    # 마지막 bar 의 TradeEvent → LiveSignal 변환
    last_bar_index = len(ohlcv) - 1
    last_bar_events = [
        e for e in strategy_state.events if e.bar_index == last_bar_index
    ]
    # entry / close 만 dispatch 대상 (fill 은 broker 측 pending stop 체결)
    signals: list[LiveSignal] = [
        LiveSignal(
            action=e.action,
            direction=e.direction,
            trade_id=e.trade_id,
            qty=e.qty,
            sequence_no=e.sequence_no,
            comment=e.comment,
        )
        for e in last_bar_events
        if e.action in ("entry", "close")
    ]

    # last_bar_time 추출
    last_bar_time = _extract_last_bar_time(ohlcv)

    # 누적 통계
    closed = strategy_state.closed_trades
    total_pnl = sum(
        (Decimal(str(t.pnl)) for t in closed if t.pnl is not None),
        Decimal("0"),
    )

    return LiveSignalResult(
        last_bar_time=last_bar_time,
        signals=signals,
        strategy_state_report=strategy_state.to_report(),
        total_closed_trades=len(closed),
        total_realized_pnl=total_pnl,
    )


def _extract_last_bar_time(ohlcv: pd.DataFrame) -> datetime:
    """OHLCV 마지막 bar 의 timestamp 추출 (UTC tz-aware).

    'timestamp' 컬럼 우선 → DatetimeIndex fallback. naive 인 경우 UTC localize.
    """
    if "timestamp" in ohlcv.columns:
        ts = pd.Timestamp(ohlcv.iloc[-1]["timestamp"])
    elif isinstance(ohlcv.index, pd.DatetimeIndex):
        ts = pd.Timestamp(ohlcv.index[-1])
    else:
        raise ValueError("OHLCV must have 'timestamp' column or DatetimeIndex")
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    return ts.to_pydatetime()

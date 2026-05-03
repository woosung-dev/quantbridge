"""Sprint 26 — `run_live` (Option B warmup replay) tests.

codex G.0 P1 #1 (hydrate 부족 → Option B 채택) + P1 #2 (same-bar entry+close
final-state diff 감지 불가 → TradeEvent log) 회귀 방어.

run_live 는 thin wrapper around run_historical:
- 매 evaluate 마다 충분한 warmup OHLCV 위에서 전체 재실행
- 마지막 bar 의 TradeEvent (action=entry/close) 만 LiveSignal 로 변환
- action=fill (pending stop 체결) 은 broker 측 이벤트라 dispatch 안 함
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pandas as pd
import pytest

from src.strategy.pine_v2.event_loop import (
    LiveSignal,
    LiveSignalResult,
    run_historical,
    run_live,
)


def _ohlcv(closes: list[float], *, start: datetime | None = None) -> pd.DataFrame:
    """closes 리스트로부터 OHLCV DataFrame 생성. timestamp 컬럼 포함 (UTC tz-aware)."""
    if start is None:
        start = datetime(2026, 5, 1, 0, 0, tzinfo=UTC)
    opens = [closes[0], *closes[:-1]]
    return pd.DataFrame({
        "timestamp": [start + timedelta(hours=i) for i in range(len(closes))],
        "open": opens,
        "high": [c * 1.02 for c in closes],
        "low": [c * 0.98 for c in closes],
        "close": closes,
        "volume": [100.0] * len(closes),
    })


_BUY_ON_GREEN = """//@version=5
strategy("buy on green bar")
if (close > open)
    strategy.entry("L", strategy.long, qty=1.0)
"""


_BUY_AND_CLOSE = """//@version=5
strategy("buy and close")
if (close > open)
    strategy.entry("L", strategy.long, qty=1.0)
if (close < open)
    strategy.close("L")
"""


_NEVER_TRIGGER = """//@version=5
strategy("never enters")
"""


# ── Test cases ───────────────────────────────────────────────────────────


def test_empty_ohlcv_raises_value_error() -> None:
    """codex G.0 plan §4 B.2 case 1 — 빈 ohlcv → ValueError."""
    with pytest.raises(ValueError, match="empty"):
        run_live(_BUY_ON_GREEN, pd.DataFrame({"open": [], "high": [], "low": [], "close": [], "volume": []}))


def test_warmup_only_no_signals() -> None:
    """case 2 — entry trigger 미발생 strategy → signals=[] (빈 리스트)."""
    # 5 bars, 모두 close==open → never green
    ohlcv = pd.DataFrame({
        "timestamp": [datetime(2026, 5, 1, h, tzinfo=UTC) for h in range(5)],
        "open": [100.0] * 5,
        "high": [101.0] * 5,
        "low": [99.0] * 5,
        "close": [100.0] * 5,
        "volume": [100.0] * 5,
    })
    result = run_live(_NEVER_TRIGGER, ohlcv)
    assert result.signals == []
    assert result.total_closed_trades == 0


def test_entry_signal_at_last_bar() -> None:
    """case 3 — last bar 가 green → entry signal 1건."""
    # 5 bars, 마지막만 green (close > open)
    ohlcv = _ohlcv([100.0, 99.0, 98.0, 97.0, 99.0])  # 마지막 bar: open=97 → close=99 (green)
    result = run_live(_BUY_ON_GREEN, ohlcv)
    assert len(result.signals) == 1
    sig = result.signals[0]
    assert sig.action == "entry"
    assert sig.direction == "long"
    assert sig.trade_id == "L"
    assert sig.qty == 1.0
    assert sig.sequence_no == 0


def test_no_signals_when_entry_in_earlier_bar() -> None:
    """case 6 — 마지막 bar 가 아닌 곳에서 entry → signals=[] (last bar 의 event 만 dispatch)."""
    # 5 bars, 첫 bar 만 green (4 bars 가 모두 동일 close=open=100)
    ohlcv = pd.DataFrame({
        "timestamp": [datetime(2026, 5, 1, h, tzinfo=UTC) for h in range(5)],
        "open": [99.0, 100.0, 100.0, 100.0, 100.0],
        "high": [101.0] * 5,
        "low": [98.0] * 5,
        "close": [100.0, 100.0, 100.0, 100.0, 100.0],  # 첫 bar 만 close > open
        "volume": [100.0] * 5,
    })
    result = run_live(_BUY_AND_CLOSE, ohlcv)
    # 첫 bar 에 entry 발생했으나 last bar 의 event 가 아니라 dispatch 안 함
    assert result.signals == []


def test_same_bar_entry_then_close_codex_p1_2() -> None:
    """codex G.0 P1 #2 회귀 — same-bar entry+close 두 signal 모두 detect.

    final-state diff 방식은 close 후 open_trades 가 비어 있어 entry 를 못 감지.
    TradeEvent log 가 두 event 를 모두 보존 → run_live 가 둘 다 LiveSignal 로 변환.
    """
    # 6 bars, 마지막 1 bar 에서 (1) entry green + (2) close. 단순 예시:
    # 5 bars warmup (close==open=100) → 6 bar 째 entry (close=110>open=100) +
    # 같은 bar 에서 close. _BUY_AND_CLOSE 는 같은 bar 에서 (close>open) 가 entry,
    # (close<open) 이 close. 한 bar 에서 둘 다 trigger 시키려면 다른 strategy 필요.
    # 대신 entry+close 가 같은 bar 에서 발생하는 시나리오: pending stop 으로는 못 감지.
    #
    # 실용적 검증: TradeEvent.events 자체로 same-bar entry+close 가 보존됨을 확인.
    # 구체적 strategy 시나리오는 close_all 호출로:
    src = """//@version=5
strategy("same-bar entry+close")
if (close > open)
    strategy.entry("L", strategy.long, qty=1.0)
    strategy.close("L")
"""
    ohlcv = _ohlcv([100.0, 99.0, 98.0, 97.0, 99.0])  # 마지막 green
    result = run_live(src, ohlcv)
    # entry + close 같은 bar → 두 signal
    assert len(result.signals) == 2
    actions = [s.action for s in result.signals]
    assert "entry" in actions
    assert "close" in actions
    # sequence_no 0 + 1 (entry first, close second — events.append 순서)
    assert result.signals[0].sequence_no == 0
    assert result.signals[1].sequence_no == 1


def test_last_bar_time_utc_tz_aware() -> None:
    """case 7 — last_bar_time 은 항상 UTC tz-aware (codex P1 #6 closed-bar 무관)."""
    ohlcv = _ohlcv([100.0, 101.0, 102.0])
    result = run_live(_BUY_ON_GREEN, ohlcv)
    assert result.last_bar_time.tzinfo is not None
    # 정확히 마지막 timestamp 매칭
    assert result.last_bar_time == datetime(2026, 5, 1, 2, 0, tzinfo=UTC)


def test_total_realized_pnl_uses_decimal() -> None:
    """누적 PnL 은 Decimal 로 반환 (price precision 보장)."""
    src = """//@version=5
strategy("entry then close next bar")
if (close > open)
    strategy.entry("L", strategy.long, qty=1.0)
if (close < open)
    strategy.close("L")
"""
    # 4 bars: green → green → red → red. close at red, pnl 추적
    ohlcv = pd.DataFrame({
        "timestamp": [datetime(2026, 5, 1, h, tzinfo=UTC) for h in range(4)],
        "open": [100.0, 100.0, 110.0, 105.0],
        "high": [102.0, 112.0, 112.0, 105.0],
        "low": [99.0, 99.0, 100.0, 100.0],
        "close": [101.0, 110.0, 105.0, 100.0],  # green green red red
        "volume": [100.0] * 4,
    })
    result = run_live(src, ohlcv)
    assert isinstance(result.total_realized_pnl, Decimal)
    assert result.total_closed_trades >= 1


def test_strategy_state_report_present() -> None:
    """strategy_state_report dict 가 to_report() 결과 반영."""
    ohlcv = _ohlcv([100.0, 99.0, 98.0, 97.0, 99.0])
    result = run_live(_BUY_ON_GREEN, ohlcv)
    report = result.strategy_state_report
    assert "open_trades" in report
    assert "closed_trades" in report
    assert "warnings" in report


def test_run_live_consistent_with_run_historical_final_state() -> None:
    """mutation oracle parity — run_historical(full).strategy_state.to_report()
    가 run_live(full).strategy_state_report 와 동일.

    Option B (warmup replay) 핵심 검증 — run_live 가 단순 wrapper 라서 identical.
    """
    ohlcv = _ohlcv([100.0, 99.0, 98.0, 97.0, 99.0, 95.0])
    historical = run_historical(_BUY_ON_GREEN, ohlcv, capture_history=False, strict=False)
    live = run_live(_BUY_ON_GREEN, ohlcv)
    assert historical.strategy_state is not None
    assert live.strategy_state_report == historical.strategy_state.to_report()


def test_run_live_idempotent_same_input() -> None:
    """동일 ohlcv 두 번 run_live → 동일 sequence_no (TradeEvent 결정성)."""
    ohlcv = _ohlcv([100.0, 99.0, 98.0, 97.0, 99.0])
    r1 = run_live(_BUY_ON_GREEN, ohlcv)
    r2 = run_live(_BUY_ON_GREEN, ohlcv)
    assert [s.sequence_no for s in r1.signals] == [s.sequence_no for s in r2.signals]
    assert [s.trade_id for s in r1.signals] == [s.trade_id for s in r2.signals]


def test_live_signal_dataclass_fields() -> None:
    """LiveSignal 필드 sanity — frozen 아님, dict 변환 지원."""
    sig = LiveSignal(
        action="entry", direction="long", trade_id="L", qty=1.5, sequence_no=0
    )
    assert sig.action == "entry"
    assert sig.qty == 1.5


def test_live_signal_result_dataclass_fields() -> None:
    """LiveSignalResult 필드 sanity."""
    result = LiveSignalResult(
        last_bar_time=datetime(2026, 5, 1, tzinfo=UTC),
        signals=[],
        strategy_state_report={},
        total_closed_trades=0,
        total_realized_pnl=Decimal("0"),
    )
    assert result.signals == []
    assert result.total_realized_pnl == Decimal("0")

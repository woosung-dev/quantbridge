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
from src.strategy.pine_v2.strategy_state import StrategyState


def _ohlcv(closes: list[float], *, start: datetime | None = None) -> pd.DataFrame:
    """closes 리스트로부터 OHLCV DataFrame 생성. timestamp 컬럼 포함 (UTC tz-aware)."""
    if start is None:
        start = datetime(2026, 5, 1, 0, 0, tzinfo=UTC)
    opens = [closes[0], *closes[:-1]]
    return pd.DataFrame(
        {
            "timestamp": [start + timedelta(hours=i) for i in range(len(closes))],
            "open": opens,
            "high": [c * 1.02 for c in closes],
            "low": [c * 0.98 for c in closes],
            "close": closes,
            "volume": [100.0] * len(closes),
        }
    )


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


# BL-362 — coverage↔interpreter divergence fixture. ta.ewma 는 미구현 ta 함수라
# strict=False 실행 시 매 bar PineRuntimeError("...not supported...") 를 수집.
_TA_EWMA_DIVERGENCE = """//@version=5
strategy("ewma divergence")
x = ta.ewma(close, 10)
if (close > open)
    strategy.entry("L", strategy.long, qty=1.0)
"""


# ── Test cases ───────────────────────────────────────────────────────────


def test_empty_ohlcv_raises_value_error() -> None:
    """codex G.0 plan §4 B.2 case 1 — 빈 ohlcv → ValueError."""
    with pytest.raises(ValueError, match="empty"):
        run_live(
            _BUY_ON_GREEN,
            pd.DataFrame({"open": [], "high": [], "low": [], "close": [], "volume": []}),
        )


def test_warmup_only_no_signals() -> None:
    """case 2 — entry trigger 미발생 strategy → signals=[] (빈 리스트)."""
    # 5 bars, 모두 close==open → never green
    ohlcv = pd.DataFrame(
        {
            "timestamp": [datetime(2026, 5, 1, h, tzinfo=UTC) for h in range(5)],
            "open": [100.0] * 5,
            "high": [101.0] * 5,
            "low": [99.0] * 5,
            "close": [100.0] * 5,
            "volume": [100.0] * 5,
        }
    )
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
    ohlcv = pd.DataFrame(
        {
            "timestamp": [datetime(2026, 5, 1, h, tzinfo=UTC) for h in range(5)],
            "open": [99.0, 100.0, 100.0, 100.0, 100.0],
            "high": [101.0] * 5,
            "low": [98.0] * 5,
            "close": [100.0, 100.0, 100.0, 100.0, 100.0],  # 첫 bar 만 close > open
            "volume": [100.0] * 5,
        }
    )
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
    ohlcv = pd.DataFrame(
        {
            "timestamp": [datetime(2026, 5, 1, h, tzinfo=UTC) for h in range(4)],
            "open": [100.0, 100.0, 110.0, 105.0],
            "high": [102.0, 112.0, 112.0, 105.0],
            "low": [99.0, 99.0, 100.0, 100.0],
            "close": [101.0, 110.0, 105.0, 100.0],  # green green red red
            "volume": [100.0] * 4,
        }
    )
    result = run_live(src, ohlcv)
    assert isinstance(result.total_realized_pnl, Decimal)
    assert result.total_closed_trades >= 1


def test_close_signal_carries_realized_pnl_mp1() -> None:
    """MP-1: close LiveSignal 은 매칭 closed_trade 의 realized PnL 을 carry.

    이 값이 Order.realized_pnl 로 전파되어 kill-switch CumulativeLoss/DailyLoss
    평가기가 실제로 작동하게 된다 (이전엔 realized_pnl 미기록으로 SUM=0 → 영구 inert).
    """
    # bar1 green(open100→close150) entry long; bar4 big red(open152→close50) close → 손실
    ohlcv = _ohlcv([100.0, 150.0, 151.0, 152.0, 50.0])
    result = run_live(_BUY_AND_CLOSE, ohlcv)
    closes = [s for s in result.signals if s.action == "close"]
    assert len(closes) == 1, f"expected 1 close signal, got {[s.action for s in result.signals]}"
    assert closes[0].realized_pnl is not None, "close signal 이 realized_pnl 을 carry 안 함 (MP-1)"
    assert closes[0].realized_pnl < Decimal("0"), "losing close 의 realized_pnl 은 음수여야 함"


def test_entry_signal_has_no_realized_pnl_mp1() -> None:
    """entry signal 은 realized_pnl 없음 (None) — 청산 시점이 아니므로."""
    ohlcv = _ohlcv([100.0, 99.0, 98.0, 97.0, 99.0])  # last bar green → entry only
    result = run_live(_BUY_ON_GREEN, ohlcv)
    entries = [s for s in result.signals if s.action == "entry"]
    assert len(entries) == 1
    assert entries[0].realized_pnl is None


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
    assert live.strategy_state_report == {
        **{
            key: value
            for key, value in historical.strategy_state.to_report().items()
            if key != "entry_skips"
        },
        "last_bar_entry_skips": [],
        "last_bar_liquidations": [],
        # G1 — 조건부 진입 desired set 도 live 전용 키다. run_live 는 엔진 상태를
        # 읽기만 하므로 나머지 키는 여전히 run_historical 과 byte-identical 이어야 한다.
        "pending_orders": [],
        "pending_order_skips": [],
        "window_bars": len(ohlcv),
        # ADR-025 — 원장 권한 census 도 live 전용 키다. `ledger_conditional_fills` 를 안
        # 넘긴 호출(= 백테스트와 같은 경로)에서는 **반드시 비어 있어야 한다.** 여기에 값이
        # 생기면 라이브 전용 분기가 기본 경로로 샌 것이다.
        "ledger_fill_census": {},
    }


def test_run_live_idempotent_same_input() -> None:
    """동일 ohlcv 두 번 run_live → 동일 sequence_no (TradeEvent 결정성)."""
    ohlcv = _ohlcv([100.0, 99.0, 98.0, 97.0, 99.0])
    r1 = run_live(_BUY_ON_GREEN, ohlcv)
    r2 = run_live(_BUY_ON_GREEN, ohlcv)
    assert [s.sequence_no for s in r1.signals] == [s.sequence_no for s in r2.signals]
    assert [s.trade_id for s in r1.signals] == [s.trade_id for s in r2.signals]


def test_live_signal_dataclass_fields() -> None:
    """LiveSignal 필드 sanity — frozen 아님, dict 변환 지원."""
    sig = LiveSignal(action="entry", direction="long", trade_id="L", qty=1.5, sequence_no=0)
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
    assert result.entry_skips == []
    assert result.liquidations == []
    # BL-362 — errors 필드는 default 빈 리스트 (기존 생성자 호환).
    assert result.errors == []


def test_entry_skip_records_margin_preflight_with_positive_control() -> None:
    """증거금 사전 게이트는 충분할 때 통과하고 부족할 때만 구조화 skip을 남긴다.

    required_margin = qty x price / leverage다. 64 x 64 / 2 = 2048,
    margin_available_ok = 4096 x 0.95 = 3891.2 이므로 통과한다.
    128 x 64 / 2 = 4096은 버퍼를 넘겨 skip한다. 2048/4096이 서로 달라
    전부 차단하거나 버퍼를 빼먹은 오답이 통과할 수 없다.
    """
    sufficient = StrategyState()
    sufficient.configure_sizing(initial_capital=4096.0, leverage=2.0)
    assert sufficient.entry("ok", "long", qty=64.0, bar=1, fill_price=64.0) is not None
    assert sufficient.entry_skips == []

    insufficient = StrategyState()
    insufficient.configure_sizing(initial_capital=4096.0, leverage=2.0)
    assert insufficient.entry("blocked", "long", qty=128.0, bar=2, fill_price=64.0) is None
    assert insufficient.entry_skips == [
        {"bar_index": 2, "reason": "margin_insufficient", "trade_id": "blocked"}
    ]


def test_entry_skip_records_second_margin_gate_with_positive_control() -> None:
    """_open_trade의 방어 게이트도 같은 증거금 skip을 기록한다."""
    sufficient = StrategyState()
    sufficient.configure_sizing(initial_capital=4096.0, leverage=2.0)
    assert (
        sufficient._open_trade(
            trade_id="ok",
            direction="long",
            qty=64.0,
            bar=1,
            fill_price=64.0,
            comment="",
            event_action="entry",
        )
        is not None
    )
    assert sufficient.entry_skips == []

    insufficient = StrategyState()
    insufficient.configure_sizing(initial_capital=4096.0, leverage=2.0)
    assert (
        insufficient._open_trade(
            trade_id="blocked",
            direction="long",
            qty=128.0,
            bar=2,
            fill_price=64.0,
            comment="",
            event_action="entry",
        )
        is None
    )
    assert insufficient.entry_skips == [
        {"bar_index": 2, "reason": "margin_insufficient", "trade_id": "blocked"}
    ]


def test_entry_skip_records_pending_margin_gate_with_positive_control() -> None:
    """pending stop 체결 게이트도 부족분만 기록하고 주문을 취소한다."""
    sufficient = StrategyState()
    sufficient.configure_sizing(initial_capital=4096.0, leverage=2.0)
    sufficient.entry("ok", "long", qty=64.0, bar=0, fill_price=64.0, stop=64.0)
    assert len(sufficient.check_pending_fills(bar=1, open_=64.0, high=64.0, low=64.0)) == 1
    assert sufficient.entry_skips == []

    insufficient = StrategyState()
    insufficient.configure_sizing(initial_capital=4096.0, leverage=2.0)
    insufficient.entry("blocked", "long", qty=128.0, bar=0, fill_price=64.0, stop=64.0)
    assert insufficient.check_pending_fills(bar=2, open_=64.0, high=64.0, low=64.0) == []
    assert insufficient.entry_skips == [
        {"bar_index": 2, "reason": "margin_insufficient", "trade_id": "blocked"}
    ]


def test_entry_skip_records_non_finite_qty_with_finite_positive_control() -> None:
    """유한 수량은 기록하지 않고 infinity 수량만 non_finite_qty로 남긴다."""
    sufficient = StrategyState()
    assert sufficient.entry("ok", "long", qty=1.0, bar=1, fill_price=64.0) is not None
    assert sufficient.entry_skips == []

    non_finite = StrategyState()
    assert non_finite.entry("blocked", "long", qty=float("inf"), bar=2, fill_price=64.0) is None
    assert non_finite.entry_skips == [
        {"bar_index": 2, "reason": "non_finite_qty", "trade_id": "blocked"}
    ]


def test_entry_skip_records_pyramiding_cap_with_capacity_positive_control() -> None:
    """pyramiding 여유는 통과하고 cap 초과만 구조화 skip을 남긴다."""
    sufficient = StrategyState(pyramiding=2)
    assert sufficient.entry("A", "long", qty=1.0, bar=0, fill_price=64.0) is not None
    assert sufficient.entry("B", "long", qty=1.0, bar=1, fill_price=64.0) is not None
    assert sufficient.entry_skips == []

    capped = StrategyState(pyramiding=1)
    assert capped.entry("A", "long", qty=1.0, bar=0, fill_price=64.0) is not None
    assert capped.entry("B", "long", qty=1.0, bar=2, fill_price=64.0) is None
    assert capped.entry_skips == [{"bar_index": 2, "reason": "pyramiding_cap", "trade_id": "B"}]


def test_entry_skip_records_session_gate_with_allowed_positive_control() -> None:
    """strategy.entry 세션 게이트는 허용 bar를 통과시키고 차단 bar를 기록한다."""
    source = """//@version=5
strategy("session entry")
strategy.entry("L", strategy.long, qty=1)
"""
    allowed = _ohlcv([64.0], start=datetime(2026, 5, 1, 0, tzinfo=UTC)).set_index("timestamp")
    allowed_result = run_historical(source, allowed, sessions_allowed=("asia",))
    assert allowed_result.strategy_state is not None
    assert allowed_result.strategy_state.entry_skips == []

    blocked = _ohlcv([64.0], start=datetime(2026, 5, 1, 12, tzinfo=UTC)).set_index("timestamp")
    blocked_result = run_historical(source, blocked, sessions_allowed=("asia",))
    assert blocked_result.strategy_state is not None
    assert blocked_result.strategy_state.entry_skips == [
        {"bar_index": 0, "reason": "session_closed", "trade_id": "L"}
    ]


def test_when_false_does_not_record_a_phantom_session_closed_skip() -> None:
    """`when=false` 는 진입 의도 자체가 없으므로 세션 skip 으로 기록하면 안 된다.

    최종 리뷰 지적. 세션 게이트가 `when=` 판정보다 먼저 돌면, 애초에 나갈 생각이
    없던 진입이 "거래 시간대 밖에서 막혔다" 로 둔갑해 메트릭과 화면에 유령 1건이
    뜬다. 두 분기 모두 `return None` 이라 실행 결과는 같고 사유만 정확해진다.
    """
    blocked_bar = _ohlcv([64.0], start=datetime(2026, 5, 1, 12, tzinfo=UTC)).set_index("timestamp")

    # 양성 대조군 — when 이 없으면 세션 밖 진입은 여전히 기록된다.
    positive = run_historical(
        '//@version=5\nstrategy("s")\nstrategy.entry("L", strategy.long, qty=1)\n',
        blocked_bar,
        sessions_allowed=("asia",),
    )
    assert positive.strategy_state is not None
    assert [s["reason"] for s in positive.strategy_state.entry_skips] == ["session_closed"]

    # 본 케이스 — when=false 면 세션 밖이어도 기록이 없어야 한다.
    result = run_historical(
        '//@version=5\nstrategy("s")\nstrategy.entry("L", strategy.long, qty=1, when=false)\n',
        blocked_bar,
        sessions_allowed=("asia",),
    )
    assert result.strategy_state is not None
    assert result.strategy_state.entry_skips == []
    assert result.strategy_state.open_trades == {}


def test_run_live_forwards_leverage_to_margin_gate() -> None:
    """2x가 필요한 증거금을 켜고 1x 호환 경로는 기존 진입을 유지한다."""
    source = """//@version=5
strategy("leveraged entry")
strategy.entry("L", strategy.long, qty=128)
"""
    ohlcv = _ohlcv([64.0])

    blocked = run_live(source, ohlcv, initial_capital=4096.0, leverage=2.0)
    assert blocked.signals == []
    assert blocked.entry_skips == [
        {"bar_index": 0, "reason": "margin_insufficient", "trade_id": "L"}
    ]
    assert blocked.strategy_state_report["last_bar_entry_skips"] == blocked.entry_skips

    one_x = run_live(source, ohlcv, initial_capital=4096.0, leverage=1.0)
    assert len(one_x.signals) == 1
    assert one_x.entry_skips == []


def test_run_live_session_gate_repairs_timestamp_column_range_index() -> None:
    """RangeIndex 라이브 프레임도 timestamp 컬럼으로 세션 게이트를 실제 적용한다."""
    source = """//@version=5
strategy("session entry")
strategy.entry("L", strategy.long, qty=1)
"""
    allowed = _ohlcv([64.0], start=datetime(2026, 5, 1, 0, tzinfo=UTC))
    assert isinstance(allowed.index, pd.RangeIndex)
    allowed_result = run_live(source, allowed, sessions_allowed=("asia",))
    assert [signal.trade_id for signal in allowed_result.signals] == ["L"]
    assert allowed_result.entry_skips == []

    blocked = _ohlcv([64.0], start=datetime(2026, 5, 1, 12, tzinfo=UTC))
    assert isinstance(blocked.index, pd.RangeIndex)
    blocked_result = run_live(source, blocked, sessions_allowed=("asia",))
    assert blocked_result.signals == []
    assert blocked_result.entry_skips == [
        {"bar_index": 0, "reason": "session_closed", "trade_id": "L"}
    ]


def test_run_live_empty_sessions_leaves_frame_and_behavior_unchanged() -> None:
    """세션 미설정 라이브 프레임은 인덱스와 신호 결과가 기존 경로와 동일하다."""
    ohlcv = _ohlcv([64.0])
    original = ohlcv.copy(deep=True)

    result = run_live(_BUY_ON_GREEN, ohlcv, sessions_allowed=())
    baseline = run_live(_BUY_ON_GREEN, original)

    pd.testing.assert_frame_equal(ohlcv, original)
    assert result.last_bar_time == baseline.last_bar_time
    assert result.signals == baseline.signals
    assert result.total_closed_trades == baseline.total_closed_trades
    assert result.total_realized_pnl == baseline.total_realized_pnl
    assert result.entry_skips == baseline.entry_skips
    assert result.errors == baseline.errors
    assert {
        key: value
        for key, value in result.strategy_state_report.items()
        if key != "position_avg_price"
    } == {
        key: value
        for key, value in baseline.strategy_state_report.items()
        if key != "position_avg_price"
    }
    assert pd.isna(result.strategy_state_report["position_avg_price"])
    assert pd.isna(baseline.strategy_state_report["position_avg_price"])


def test_run_live_sessions_rejects_tz_naive_timestamp() -> None:
    """세션 필터에서 tz-naive timestamp는 조용히 24시간 진입으로 폴백하지 않는다."""
    ohlcv = _ohlcv([64.0])
    ohlcv["timestamp"] = ohlcv["timestamp"].dt.tz_localize(None)

    with pytest.raises(ValueError, match="timezone-aware DatetimeIndex or timestamp column"):
        run_live(_BUY_ON_GREEN, ohlcv, sessions_allowed=("asia",))


def test_run_live_sessions_rejects_missing_time_information() -> None:
    """세션 필터에서 시각 없는 프레임은 게이트 무시 대신 즉시 실패한다."""
    ohlcv = _ohlcv([64.0]).drop(columns=["timestamp"])

    with pytest.raises(ValueError, match="timezone-aware DatetimeIndex or timestamp column"):
        run_live(_BUY_ON_GREEN, ohlcv, sessions_allowed=("asia",))


def test_run_live_forwards_pyramiding_and_records_cap_skip() -> None:
    """cap 미만은 통과하고 초과한 마지막 bar 진입은 skip 사유를 보존한다."""
    source = """//@version=5
strategy("pyramiding")
if bar_index == 0
    strategy.entry("A", strategy.long, qty=1)
if bar_index == 1
    strategy.entry("B", strategy.long, qty=1)
"""
    ohlcv = _ohlcv([64.0, 64.0])

    allowed = run_live(source, ohlcv, pyramiding=2)
    assert [signal.trade_id for signal in allowed.signals] == ["B"]
    assert allowed.entry_skips == []

    blocked = run_live(source, ohlcv, pyramiding=1)
    assert blocked.signals == []
    assert blocked.entry_skips == [{"bar_index": 1, "reason": "pyramiding_cap", "trade_id": "B"}]
    assert blocked.strategy_state_report["last_bar_entry_skips"] == blocked.entry_skips


def test_run_live_returns_only_last_bar_entry_skips() -> None:
    """라이브 report는 마지막 bar skip만 남기고 백테스트 report는 전체를 보존한다."""
    source = """//@version=5
strategy("non-finite entries")
qty = strategy.equity
if close > open
    strategy.entry("L", strategy.long, qty=qty)
"""
    ohlcv = _ohlcv([64.0, 64.0, 128.0, 128.0, 256.0])
    result = run_live(source, ohlcv)
    historical = run_historical(source, ohlcv)

    all_skips = [
        {"bar_index": 2, "reason": "non_finite_qty", "trade_id": "L"},
        {"bar_index": 4, "reason": "non_finite_qty", "trade_id": "L"},
    ]
    assert "entry_skips" not in result.strategy_state_report
    assert result.entry_skips == [all_skips[-1]]
    assert result.strategy_state_report["last_bar_entry_skips"] == result.entry_skips
    assert historical.strategy_state is not None
    assert historical.strategy_state.to_report()["entry_skips"] == all_skips


def test_run_live_surfaces_last_bar_liquidation_only_when_leveraged() -> None:
    """100 진입 후 80 하락은 10x만 강제청산 close와 관측값을 만든다."""
    source = """//@version=5
strategy("liquidation")
if bar_index == 0
    strategy.entry("L", strategy.long, qty=1)
"""
    ohlcv = pd.DataFrame(
        {
            "timestamp": [datetime(2026, 5, 1, hour, tzinfo=UTC) for hour in range(2)],
            "open": [100.0, 80.0],
            "high": [100.0, 80.0],
            "low": [100.0, 80.0],
            "close": [100.0, 80.0],
            "volume": [100.0, 100.0],
        }
    )

    one_x = run_live(source, ohlcv, initial_capital=100000.0, leverage=1.0)
    assert one_x.signals == []
    assert one_x.liquidations == []
    assert one_x.strategy_state_report["last_bar_liquidations"] == []

    ten_x = run_live(source, ohlcv, initial_capital=100000.0, leverage=10.0)
    assert [
        (signal.action, signal.direction, signal.trade_id, signal.qty, signal.comment)
        for signal in ten_x.signals
    ] == [("close", "long", "L", 1.0, "liquidation")]
    assert ten_x.signals[0].realized_pnl == Decimal("-20.0")
    assert ten_x.liquidations == ten_x.strategy_state_report["last_bar_liquidations"]
    assert ten_x.liquidations == [
        {
            "id": "L",
            "direction": "long",
            "qty": 1.0,
            "entry_bar": 0,
            "entry_price": 100.0,
            "exit_bar": 1,
            "exit_price": 80.0,
            "pnl": -20.0,
            "comment": "liquidation",
            "liquidated": True,
        }
    ]
    assert ten_x.strategy_state_report["liquidation_count"] == 1


def test_entry_skip_deduplicates_only_an_identical_consecutive_attempt() -> None:
    """같은 시도는 하나로, bar 또는 trade가 다르면 각각 남긴다."""
    repeated = StrategyState()
    repeated._record_entry_skip(bar=1, reason="margin_insufficient", trade_id="L")
    repeated._record_entry_skip(bar=1, reason="margin_insufficient", trade_id="L")
    assert repeated.entry_skips == [
        {"bar_index": 1, "reason": "margin_insufficient", "trade_id": "L"}
    ]

    different_bar = StrategyState()
    different_bar._record_entry_skip(bar=1, reason="margin_insufficient", trade_id="L")
    different_bar._record_entry_skip(bar=2, reason="margin_insufficient", trade_id="L")
    assert len(different_bar.entry_skips) == 2

    different_trade = StrategyState()
    different_trade._record_entry_skip(bar=1, reason="margin_insufficient", trade_id="L")
    different_trade._record_entry_skip(bar=1, reason="margin_insufficient", trade_id="S")
    assert len(different_trade.entry_skips) == 2


def test_run_live_propagates_runtime_errors() -> None:
    """BL-362 — run_live 가 strict=False 로 삼켜진 errors 를 LiveSignalResult.errors 로 표면화.

    이전엔 run_historical 의 errors 가 run_live boundary 에서 소멸 → 라이브가 오신호를
    조용히 dispatch. 이제 표면화하여 호출자(live_signal task)가 fail-closed 가능.
    """
    result = run_live(_TA_EWMA_DIVERGENCE, _ohlcv([100.0, 101.0, 102.0]))
    assert result.errors  # non-empty — 발산 표면화
    assert "not supported" in result.errors[-1][1]


def test_run_live_clean_source_empty_errors() -> None:
    """regression — clean source 는 errors 빈 리스트 (정상 dispatch 경로 불변)."""
    result = run_live(_BUY_ON_GREEN, _ohlcv([100.0, 99.0, 98.0, 97.0, 99.0]))
    assert result.errors == []

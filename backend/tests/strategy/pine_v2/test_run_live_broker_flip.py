"""BL-560 — 반전 체결의 청산 leg 를 거래소에 다시 지시하지 않는다.

조건부 진입은 거래소에 **병합 주문 1건**으로 등재된다
(`trading/services/conditional_entry_planner.py:444` —
`abs(target_position - current_position)`). 숏 8 보유 + 롱 8 pending 이면
`buy 16` **한 장**이 청산과 진입을 동시에 한다.

트리거되면 거래소는 한 번에 플립한다. 엔진은 **다음 봉 평가**에서야
`check_pending_fills` 로 그 체결을 재도출하고, 그때 반대편을
`_flip_opposite_positions` 로 `action="close"` 기록한다. 그 close 를 다시 주문으로
내보내면 **이미 닫힌 포지션을 또 닫으라는 지시**가 되어
`110017 reduce-only ... same side` 로 거절된다.

실측(soak 3h20m · PbR · BTC/USDT 1m · bybit demo, 2026-07-30): **2.60 건/h ·
청산 시도의 46.2%(6/13) · 6/6 전건이 직전 체결과 같은 방향**.

★**엔진 원장은 맞다** — 숏은 닫혔고 롱이 열렸다. 틀린 것은 그 장부 기록을
거래소 지시로 **재발신**하는 것이다. 그래서 고치는 자리는 `close()` 가 아니라
`run_live` 의 dispatch 필터다.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pandas as pd

from src.strategy.pine_v2.event_loop import run_historical, run_live
from src.tasks.live_signal import _signal_to_order_side

# 숏 보유 + 반대 방향 pending stop. 거래소에는 `buy 16` 한 장으로 등재된다.
_SHORT_HELD_LONG_STOP = """//@version=5
strategy("short held, long stop")
if bar_index == 0
    strategy.entry("HeldShort", strategy.short, qty=8)
if bar_index == 1
    strategy.entry("PivRevLE", strategy.long, qty=8, stop=128)
"""

# 같은 반전을 **시장가**로 하는 전략. 이쪽은 거래소가 아직 숏을 들고 있는 상태에서
# 엔진이 close 를 보내므로 거절되지 않는다 — 계속 dispatch 되어야 한다.
_SHORT_HELD_LONG_MARKET = """//@version=5
strategy("short held, long market")
if bar_index == 0
    strategy.entry("HeldShort", strategy.short, qty=8)
if bar_index == 2
    strategy.entry("PivRevLE", strategy.long, qty=8)
"""


def _flip_frame() -> pd.DataFrame:
    """bar 2 에서 롱 stop 128 이 체결되는 3-bar 프레임.

    bar 2: open=120 · high=130 → `try_fill` 이 max(open, stop)=128 로 체결한다.
    """
    start = datetime(2026, 5, 1, tzinfo=UTC)
    return pd.DataFrame(
        {
            "timestamp": [start + timedelta(hours=index) for index in range(3)],
            "open": [100.0, 100.0, 120.0],
            "high": [100.0, 105.0, 130.0],
            "low": [100.0, 95.0, 118.0],
            "close": [100.0, 100.0, 125.0],
            "volume": [100.0] * 3,
        }
    )


def test_pending_fill_flip_close_is_not_dispatched() -> None:
    """★본 케이스 — 반전 체결로 닫힌 숏은 청산 주문을 만들지 않는다.

    거래소는 이 시점에 이미 롱이다. 여기서 close(short) 를 내보내면
    `_signal_to_order_side` 가 **buy** 를 만들어 `reduce_only=True` 로 나가고,
    거래소는 같은 방향이라 거절한다.
    """
    result = run_live(_SHORT_HELD_LONG_STOP, _flip_frame())

    assert result.signals == [], (
        "반전 체결의 청산 leg 가 주문으로 나갔다 — "
        f"{[(s.action, s.direction, s.trade_id) for s in result.signals]}"
    )


def test_broker_flip_close_side_would_have_matched_the_filled_leg() -> None:
    """6/6 패턴의 핵심 — 그 close 의 주문 방향이 **직전 체결과 같다**.

    dispatch 여부와 무관하게 원장에는 close(short) + fill(long) 두 이벤트가 남는다.
    close(short) → buy, fill(long) → buy. 같은 방향이라는 것이 실측 6/6 의 서명이며,
    이 단언이 깨지면 위 테스트가 막고 있는 대상이 바뀐 것이다.
    """
    historical = run_historical(_SHORT_HELD_LONG_STOP, _flip_frame(), capture_history=False)
    assert historical.strategy_state is not None
    last_bar_events = [e for e in historical.strategy_state.events if e.bar_index == 2]

    assert [(e.action, e.direction) for e in last_bar_events] == [
        ("close", "short"),
        ("fill", "long"),
    ]
    close_event, fill_event = last_bar_events
    # fill = 롱 진입 = buy. close(short) 도 buy → 같은 방향.
    assert _signal_to_order_side("close", close_event.direction) == _signal_to_order_side(
        "entry", fill_event.direction
    )


def test_broker_flip_still_records_the_close_in_the_ledger() -> None:
    """★원장은 한 자리도 바뀌지 않는다 — 숏은 닫혔고 롱이 열렸다.

    고치는 자리가 `close()` 였다면 여기가 깨진다. dispatch 필터만 건드렸다면 불변이다.
    """
    result = run_live(_SHORT_HELD_LONG_STOP, _flip_frame())
    report = result.strategy_state_report

    assert [(t["id"], t["direction"]) for t in report["open_trades"]] == [("PivRevLE", "long")]
    assert [(t["id"], t["direction"], t["exit_price"]) for t in report["closed_trades"]] == [
        ("HeldShort", "short", 128.0)
    ]
    # 숏 8 을 100 에 열어 128 에 닫았다 → (128 - 100) * 8 * -1 = -224.
    assert report["closed_trades"][0]["pnl"] == -224.0
    assert result.total_closed_trades == 1


def test_broker_flip_close_is_not_dispatched_in_gap_catchup_either() -> None:
    """평가 공백 catch-up 경로도 같다 — 필터는 한 자리다.

    공백이 있었다는 것은 거래소가 그 사이 이미 체결했다는 뜻이므로 이쪽이 오히려
    더 위험하다. 여기서 새어 나가면 공백 1회당 거절 1건이 쌓인다.
    """
    frame = _flip_frame()
    result = run_live(
        _SHORT_HELD_LONG_STOP, frame, emit_from_bar_time=frame.iloc[0]["timestamp"]
    )

    assert result.signals == [], (
        "catch-up 경로로 반전 청산 leg 가 새어 나갔다 — "
        f"{[(s.action, s.direction, s.trade_id) for s in result.signals]}"
    )


def test_market_reversal_close_survives_gap_catchup() -> None:
    """★회귀 방어 (catch-up) — 시장가 반전은 공백 복구에서도 두 장 그대로다."""
    frame = _flip_frame()
    result = run_live(
        _SHORT_HELD_LONG_MARKET, frame, emit_from_bar_time=frame.iloc[0]["timestamp"]
    )

    assert [(s.action, s.direction, s.trade_id) for s in result.signals] == [
        ("close", "short", "HeldShort"),
        ("entry", "long", "PivRevLE"),
    ]


def test_market_reversal_still_dispatches_both_close_and_entry() -> None:
    """★회귀 방어 — 시장가 반전은 close + entry 두 장이 계속 나가야 한다.

    이 경로는 엔진이 먼저 결정하고 거래소가 뒤따른다. close 를 보낼 때 거래소에는
    아직 숏이 있으므로 거절되지 않는다. 여기까지 같이 죽이면 **청산이 통째로 사라진다.**
    """
    result = run_live(_SHORT_HELD_LONG_MARKET, _flip_frame())

    assert [
        (s.action, s.direction, s.trade_id, s.sequence_no) for s in result.signals
    ] == [
        ("close", "short", "HeldShort", 0),
        ("entry", "long", "PivRevLE", 1),
    ]

"""`strategy.entry(limit=)` — 지정가 진입 (2026-08-15 surface-truth · U8).

**고치기 전에 무슨 일이 벌어졌나.** `limit=` 은 `interpreter._exec_strategy_call` 의
`unsupported` 목록에 있었고, Coverage 는 **함수 이름만** 보므로(`strategy.entry` 는 지원
목록에 있다) 화면은 그 전략을 **「지원됨」 초록 칩**으로 표시했다. 백테스트는 지정가를
**시장가로 치환**해 돌았고, 그 사실을 알리는 경고는 화면에 도달하지 않았다. 사용자는
자기가 쓰지 않은 전략의 결과를 자기 전략의 결과로 받았다.

★**이 파일은 `test_pivot_and_stop_order.py` 의 stop 케이스를 미러링한다** — 같은 하네스,
같은 bar 구성, 부등호만 반대다. limit 은 stop 과 **부등호가 정반대**이므로(「뚫으면」 ↔
「되돌아오면」) 그 대칭이 곧 명세다.

★**라이브는 fail-closed 다.** 지정가 진입은 거래소로 나가지 않는다 — 라이브 발주 경로가
`trigger_price`(stop) 하나만 표현하기 때문이다. 그 축은
`tests/strategy/pine_v2/test_limit_entry_live_fail_closed.py` 가 잰다.
"""

from __future__ import annotations

import pandas as pd

from src.strategy.pine_v2.interpreter import BarContext, Interpreter
from src.strategy.pine_v2.parser_adapter import parse_to_ast
from src.strategy.pine_v2.runtime import PersistentStore


def _ohlcv(
    highs: list[float],
    lows: list[float],
    closes: list[float],
    opens: list[float] | None = None,
) -> pd.DataFrame:
    n = len(highs)
    if opens is None:
        opens = [closes[0], *closes[:-1]]
    return pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": [100.0] * n,
        }
    )


def _run(source: str, ohlcv: pd.DataFrame) -> Interpreter:
    """`test_pivot_and_stop_order.py` 와 **같은** 수동 루프.

    `check_pending_fills` 를 execute 앞에 두는 순서가 그 파일의 계약이고, 그래야
    「같은 bar 즉시 체결 금지」가 재현된다.
    """
    bar = BarContext(ohlcv)
    store = PersistentStore()
    interp = Interpreter(bar, store)
    tree = parse_to_ast(source)
    while bar.advance():
        store.begin_bar()
        interp.reset_transient()
        interp.begin_bar_snapshot()
        interp.strategy.check_pending_fills(
            bar=bar.bar_index,
            open_=bar.current("open"),
            high=bar.current("high"),
            low=bar.current("low"),
        )
        interp.execute(tree)
        store.commit_bar()
        interp.append_var_series()
    return interp


def test_limit_long_fills_when_low_pulls_back_to_the_price() -> None:
    """BUY LIMIT — low 가 limit 까지 **내려와야** 체결. stop 과 부등호가 반대다."""
    source = """//@version=5
strategy("t")
if bar_index == 0
    strategy.entry("L", strategy.long, qty=1.0, limit=95.0)
"""
    # bar 0: 발주 (low=99 > 95 이고 같은 bar 는 어차피 체결 금지)
    # bar 1: low=94 ≤ 95 → fill at min(open=100, 95) = 95
    ohlcv = _ohlcv(
        highs=[101.0, 101.0, 110.0],
        lows=[99.0, 94.0, 100.0],
        closes=[100.0, 100.0, 105.0],
        opens=[100.0, 100.0, 100.0],
    )
    interp = _run(source, ohlcv)

    assert "L" in interp.strategy.open_trades, "지정가 진입이 체결되지 않았다"
    trade = interp.strategy.open_trades["L"]
    assert trade.entry_bar == 1
    assert trade.entry_price == 95.0


def test_limit_short_fills_when_high_pulls_up_to_the_price() -> None:
    """SELL LIMIT — high 가 limit 까지 **올라와야** 체결."""
    source = """//@version=5
strategy("t")
if bar_index == 0
    strategy.entry("S", strategy.short, qty=1.0, limit=105.0)
"""
    ohlcv = _ohlcv(
        highs=[101.0, 106.0, 104.0],
        lows=[99.0, 99.0, 98.0],
        closes=[100.0, 103.0, 100.0],
        opens=[100.0, 100.0, 100.0],
    )
    interp = _run(source, ohlcv)

    assert "S" in interp.strategy.open_trades
    trade = interp.strategy.open_trades["S"]
    assert trade.entry_bar == 1
    assert trade.entry_price == 105.0


def test_limit_long_gap_down_fills_at_the_better_open() -> None:
    """★갭 처리도 stop 과 반대다 — limit 은 **유리한** 쪽(더 싼 open)으로 체결된다.

    stop 은 갭에서 불리한 쪽(open)으로 체결된다(`test_stop_long_fills_...`). 같은
    `min/max` 를 쓰지만 방향이 반대이므로, 이 케이스가 부호를 뒤집는 실수를 잡는다.
    """
    source = """//@version=5
strategy("t")
if bar_index == 0
    strategy.entry("L", strategy.long, qty=1.0, limit=95.0)
"""
    # bar 1 이 90 으로 갭다운 — limit 95 보다 이미 아래다. 95 가 아니라 90 에 체결돼야 한다.
    ohlcv = _ohlcv(
        highs=[101.0, 92.0, 100.0],
        lows=[99.0, 88.0, 95.0],
        closes=[100.0, 91.0, 98.0],
        opens=[100.0, 90.0, 95.0],
    )
    interp = _run(source, ohlcv)

    trade = interp.strategy.open_trades["L"]
    assert trade.entry_price == 90.0, (
        f"갭다운에서 limit 은 더 싼 open 에 체결돼야 한다 (실제 {trade.entry_price})"
    )


def test_limit_never_fills_when_price_never_returns() -> None:
    """★음성 대조 — 가격이 안 오면 **체결되지 않고 pending 으로 남는다**.

    이게 없으면 「limit 을 시장가로 즉시 체결」하는 구현이 위 세 테스트를 전부 통과한다
    (bar 1 에서 어차피 체결되므로). 그 구현이 정확히 **고치기 전의 동작**이다.
    """
    source = """//@version=5
strategy("t")
if bar_index == 0
    strategy.entry("L", strategy.long, qty=1.0, limit=50.0)
"""
    ohlcv = _ohlcv(
        highs=[101.0, 110.0, 120.0],
        lows=[99.0, 100.0, 110.0],
        closes=[100.0, 105.0, 115.0],
        opens=[100.0, 100.0, 105.0],
    )
    interp = _run(source, ohlcv)

    assert not interp.strategy.open_trades, (
        f"가격이 limit 에 닿은 적이 없는데 진입했다: {interp.strategy.open_trades}"
    )
    assert "L" in interp.strategy.pending_orders, "미체결 지정가 주문이 pending 에 남아야 한다"
    assert interp.strategy.pending_orders["L"].limit_price == 50.0
    assert interp.strategy.pending_orders["L"].stop_price is None


def test_stop_and_limit_together_keeps_stop_and_says_so() -> None:
    """stop-limit 조합은 표현 불가 — stop 을 쓰고 **말한다**.

    조용히 한쪽을 고르면 사용자는 자기 주문이 무엇이 됐는지 알 수 없다. 이 회차의 주제가
    바로 그 침묵이다.
    """
    source = """//@version=5
strategy("t")
if bar_index == 0
    strategy.entry("L", strategy.long, qty=1.0, stop=105.0, limit=95.0)
"""
    ohlcv = _ohlcv(
        highs=[101.0, 110.0, 120.0],
        lows=[99.0, 94.0, 110.0],
        closes=[100.0, 108.0, 115.0],
        opens=[100.0, 100.0, 108.0],
    )
    interp = _run(source, ohlcv)

    # stop=105 가 이긴다 → bar 1 high=110 에서 105 체결 (limit 95 였다면 95 였을 것이다).
    trade = interp.strategy.open_trades["L"]
    assert trade.entry_price == 105.0
    assert any("stop-limit" in w for w in interp.strategy.warnings), (
        f"조합을 어떻게 처리했는지 말하지 않았다: {interp.strategy.warnings}"
    )


# ---------------------------------------------------------------------------
# ★`fill_timing="next_bar_open"` 축 — 위 케이스들이 **못 보는 분기**다.
#
# 엔진 기본값은 `bar_close`(`strategy_state.py:399`)라 위 수동 루프는
# `interpreter.py` 의 `next_bar_open` 시장가 인텐트 분기를 한 번도 지나지 않는다.
# 그런데 이 회차 수리의 핵심 한 줄이 정확히 그 분기의 `and limit is None` 이다.
#
# ★2026-08-15 실측 — 그 가드를 지우는 변이가 **전건 초록으로 빠져나갔다.** 계획서가
#   ★★로 표시한 줄에 커버리지가 0 이었다. 「변이를 심었으면 그 변이가 도달했는지 따로
#   확인해라」의 다음 단계가 이것이다 — **변이가 파일에는 도달했지만 어떤 테스트도 그
#   코드 경로를 실행하지 않았다.**
# ---------------------------------------------------------------------------


def test_limit_entry_is_not_converted_to_market_under_next_bar_open() -> None:
    """★TV parity 모드에서도 지정가는 시장가로 치환되지 않는다.

    `and limit is None` 가드가 빠지면 이 진입은 `MarketIntent` 큐로 가서 **다음 bar 시가에
    시장가 체결**된다 — 사용자가 「50 에 사겠다」고 썼는데 100 에 사지는 것이다.
    """
    from src.strategy.pine_v2.event_loop import run_historical

    source = """//@version=5
strategy("t")
if bar_index == 0
    strategy.entry("L", strategy.long, qty=1.0, limit=50.0)
"""
    # 가격이 50 근처로 내려오지 않는다 ⇒ 지정가라면 **영원히 미체결**이어야 한다.
    ohlcv = _ohlcv(
        highs=[101.0, 110.0, 120.0],
        lows=[99.0, 100.0, 110.0],
        closes=[100.0, 105.0, 115.0],
        opens=[100.0, 100.0, 105.0],
    )
    result = run_historical(source, ohlcv, fill_timing="next_bar_open")

    assert not result.strategy_state.open_trades, (
        "next_bar_open 모드에서 지정가 진입이 시장가로 치환됐다 "
        f"(`and limit is None` 가드 부재): {result.strategy_state.open_trades}"
    )
    assert "L" in result.strategy_state.pending_orders
    assert result.strategy_state.pending_orders["L"].limit_price == 50.0


def test_market_entry_still_uses_the_next_bar_open_intent_queue() -> None:
    """★음성 대조 — 시장가 진입은 그대로 인텐트 큐를 지나 다음 bar 시가에 체결된다.

    이게 없으면 「`next_bar_open` 분기를 통째로 끄기」로도 위 테스트가 통과한다(판별력 0).
    """
    from src.strategy.pine_v2.event_loop import run_historical

    source = """//@version=5
strategy("t")
if bar_index == 0
    strategy.entry("L", strategy.long, qty=1.0)
"""
    ohlcv = _ohlcv(
        highs=[101.0, 110.0, 120.0],
        lows=[99.0, 100.0, 110.0],
        closes=[100.0, 105.0, 115.0],
        opens=[100.0, 100.0, 105.0],
    )
    result = run_historical(source, ohlcv, fill_timing="next_bar_open")

    trade = result.strategy_state.open_trades["L"]
    assert trade.entry_bar == 1, "다음 bar 로 미뤄져야 한다"
    assert trade.entry_price == 100.0, "다음 bar **시가**에 체결돼야 한다"


# ---------------------------------------------------------------------------
# ★위치 인자 축 — 2026-08-15 적대 리뷰 P1.
#
# Pine v5 시그니처는 `strategy.entry(id, direction, qty, limit, stop, oca_name, ...)` 다.
# 위 케이스들은 전부 **named** (`limit=95`)를 쓰므로 `kwargs` 만 읽는 구현으로도 통과한다.
# 실측: `strategy.entry("L", strategy.long, 8, 10)` 이 `run_live` 에서 **시장가 signal**
# `entry/L/long/8` 을 냈고 pending·skip 은 둘 다 비어 있었다 — 이 회차가 닫으려던 구멍이
# 위치 인자 축에 그대로 남아 있었다.
# ---------------------------------------------------------------------------


def test_positional_limit_is_read_as_the_fourth_argument() -> None:
    """★`strategy.entry(id, dir, qty, limit)` — 네 번째 위치 인자가 limit 이다."""
    source = """//@version=5
strategy("t")
if bar_index == 0
    strategy.entry("L", strategy.long, 1.0, 95.0)
"""
    ohlcv = _ohlcv(
        highs=[101.0, 101.0, 110.0],
        lows=[99.0, 94.0, 100.0],
        closes=[100.0, 100.0, 105.0],
        opens=[100.0, 100.0, 100.0],
    )
    interp = _run(source, ohlcv)

    trade = interp.strategy.open_trades["L"]
    assert trade.entry_bar == 1
    assert trade.entry_price == 95.0, "위치 인자 limit 이 버려지고 시장가로 샜다"


def test_positional_stop_is_read_as_the_fifth_argument() -> None:
    """★`stop` 은 **5번째** 위치 인자다. 이 누락은 이 회차 이전부터 있었다."""
    source = """//@version=5
strategy("t")
if bar_index == 0
    strategy.entry("L", strategy.long, 1.0, na, 105.0)
"""
    ohlcv = _ohlcv(
        highs=[101.0, 110.0, 120.0],
        lows=[99.0, 100.0, 115.0],
        closes=[100.0, 110.0, 120.0],
        opens=[100.0, 100.0, 110.0],
    )
    interp = _run(source, ohlcv)

    trade = interp.strategy.open_trades["L"]
    assert trade.entry_bar == 1
    assert trade.entry_price == 105.0, "위치 인자 stop 이 버려지고 시장가로 샜다"
    assert interp.strategy.pending_orders == {}


def test_positional_limit_is_fail_closed_in_live() -> None:
    """★배선 — 위치 인자 경로도 라이브에서 **막힌다**.

    순수 엔진 테스트만으로는 부족하다. 실제 결함이 관측된 자리가 `run_live` 였다.
    """
    from datetime import UTC, datetime, timedelta

    from src.strategy.pine_v2.event_loop import run_live

    start = datetime(2026, 5, 1, tzinfo=UTC)
    live_ohlcv = _ohlcv(
        highs=[110.0, 110.0],
        lows=[90.0, 90.0],
        closes=[100.0, 100.0],
        opens=[100.0, 100.0],
    )
    live_ohlcv.insert(0, "timestamp", [start + timedelta(hours=i) for i in range(2)])
    source = """//@version=5
strategy("t")
if bar_index == 1
    strategy.entry("L", strategy.long, 8, 10)
"""
    result = run_live(source, live_ohlcv)

    assert result.signals == [], f"위치 인자 지정가가 시장가 signal 로 샜다: {result.signals}"
    assert result.pending_orders == []
    skips = result.strategy_state_report["pending_order_skips"]
    assert [s["reason"] for s in skips] == ["limit_entry_unsupported_live"], skips

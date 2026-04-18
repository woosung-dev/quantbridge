"""strategy.* 실행 핸들러 회귀 (Week 2 Day 4).

- strategy.entry (long/short) — 시장가, 현재 bar close 체결
- strategy.close — id로 청산
- strategy.close_all — 모두 청산
- strategy.position_size / position_avg_price — 현재 상태
- 미지원 kwarg(stop, limit, trail_points 등)는 warning에 기록
"""
from __future__ import annotations

import pandas as pd

from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.interpreter import BarContext, Interpreter
from src.strategy.pine_v2.parser_adapter import parse_to_ast
from src.strategy.pine_v2.runtime import PersistentStore
from src.strategy.pine_v2.strategy_state import StrategyState, Trade


def _ohlcv(closes: list[float]) -> pd.DataFrame:
    opens = [closes[0], *closes[:-1]]
    return pd.DataFrame({
        "open": opens,
        "high": [c * 1.01 for c in closes],
        "low": [c * 0.99 for c in closes],
        "close": closes,
        "volume": [100.0] * len(closes),
    })


# -------- 단위: StrategyState 직접 ------------------------------------


def test_strategy_state_entry_and_close_long() -> None:
    s = StrategyState()
    s.entry("L", "long", qty=1.0, bar=0, fill_price=100.0)
    assert s.position_size == 1.0
    assert s.position_avg_price == 100.0
    closed = s.close("L", bar=5, fill_price=120.0)
    assert closed is not None
    assert closed.pnl == 20.0  # (120 - 100) * 1 * (+1)
    assert s.position_size == 0.0


def test_strategy_state_short_pnl_sign() -> None:
    s = StrategyState()
    s.entry("S", "short", qty=2.0, bar=0, fill_price=100.0)
    assert s.position_size == -2.0
    closed = s.close("S", bar=3, fill_price=90.0)
    assert closed is not None
    assert closed.pnl == 20.0  # (90 - 100) * 2 * (-1)


def test_strategy_state_close_all() -> None:
    s = StrategyState()
    s.entry("A", "long", qty=1.0, bar=0, fill_price=10.0)
    s.entry("B", "long", qty=2.0, bar=1, fill_price=20.0)
    closed = s.close_all(bar=5, fill_price=30.0)
    assert len(closed) == 2
    assert s.position_size == 0.0
    # A pnl = (30-10)*1 = 20, B pnl = (30-20)*2 = 20
    total_pnl = sum((t.pnl or 0.0) for t in closed)
    assert total_pnl == 40.0


def test_strategy_state_duplicate_id_overrides() -> None:
    """같은 id로 중복 entry 시 기존 포지션 먼저 청산 후 새로 진입."""
    s = StrategyState()
    s.entry("X", "long", qty=1.0, bar=0, fill_price=100.0)
    s.entry("X", "long", qty=2.0, bar=3, fill_price=110.0)
    # 기존은 bar 3 fill 110.0으로 청산됨 → pnl = 10
    assert len(s.closed_trades) == 1
    assert s.closed_trades[0].pnl == 10.0
    # 새 포지션은 open
    assert s.position_size == 2.0
    assert s.position_avg_price == 110.0


def test_strategy_entry_unsupported_kwargs_warning() -> None:
    s = StrategyState()
    s.entry(
        "X", "long", qty=1.0, bar=0, fill_price=100.0,
        unsupported_kwargs=["stop", "trail_points"],
    )
    assert len(s.warnings) == 1
    assert "stop" in s.warnings[0]
    assert "trail_points" in s.warnings[0]


# -------- 통합: Pine 소스 실행 ----------------------------------------


def test_entry_long_via_pine_source_runs_without_error() -> None:
    """run_historical은 RunResult만 반환. 실행이 끝까지 진행되는지 확인."""
    source = """//@version=5
strategy("test")
if close > open
    strategy.entry("Long", strategy.long, qty=1.0)
"""
    closes = [10.0, 15.0, 20.0]
    r = run_historical(source, _ohlcv(closes))
    assert r.bars_processed == 3
    # strategy 상태 접근은 아래 Interpreter 직접 테스트에서 검증


def test_strategy_via_interpreter_direct() -> None:
    """interpreter 직접 사용으로 strategy 상태 검증."""
    source = """//@version=5
strategy("t")
if close > open
    strategy.entry("L", strategy.long, qty=1.0)
"""
    ohlcv = _ohlcv([10.0, 15.0, 12.0, 20.0])
    bar = BarContext(ohlcv)
    store = PersistentStore()
    interp = Interpreter(bar, store)
    tree = parse_to_ast(source)

    while bar.advance():
        store.begin_bar()
        interp.reset_transient()
        interp.begin_bar_snapshot()
        interp.execute(tree)
        store.commit_bar()
        interp.append_var_series()

    # bar 0: open=close=10 → skip
    # bar 1: open=10, close=15 → entry at 15
    # bar 2: open=15, close=12 → skip (close < open)
    # bar 3: open=12, close=20 → **override** (close existing at 20, re-enter at 20)

    # 최종 포지션: bar 3에서 신규 entry L open
    assert interp.strategy.position_size == 1.0
    # 한 번 close (bar 3 override) → closed_trades 1개
    assert len(interp.strategy.closed_trades) == 1
    closed = interp.strategy.closed_trades[0]
    assert closed.entry_bar == 1
    assert closed.entry_price == 15.0
    assert closed.exit_bar == 3
    assert closed.exit_price == 20.0
    assert closed.pnl == 5.0


def test_strategy_close_by_id() -> None:
    source = """//@version=5
strategy("t")
if bar_index == 1
    strategy.entry("X", strategy.long, qty=1.0)
if bar_index == 3
    strategy.close("X")
"""
    ohlcv = _ohlcv([10.0, 20.0, 30.0, 40.0, 50.0])
    bar = BarContext(ohlcv)
    store = PersistentStore()
    interp = Interpreter(bar, store)
    tree = parse_to_ast(source)
    while bar.advance():
        store.begin_bar()
        interp.reset_transient()
        interp.begin_bar_snapshot()
        interp.execute(tree)
        store.commit_bar()
        interp.append_var_series()

    assert len(interp.strategy.closed_trades) == 1
    closed = interp.strategy.closed_trades[0]
    assert closed.entry_bar == 1 and closed.entry_price == 20.0
    assert closed.exit_bar == 3 and closed.exit_price == 40.0
    assert closed.pnl == 20.0  # (40-20)*1
    assert interp.strategy.position_size == 0.0


def test_strategy_close_all() -> None:
    source = """//@version=5
strategy("t")
if bar_index == 1
    strategy.entry("A", strategy.long, qty=1.0)
if bar_index == 2
    strategy.entry("B", strategy.short, qty=1.0)
if bar_index == 4
    strategy.close_all()
"""
    ohlcv = _ohlcv([10.0, 20.0, 25.0, 30.0, 35.0])
    bar = BarContext(ohlcv)
    store = PersistentStore()
    interp = Interpreter(bar, store)
    tree = parse_to_ast(source)
    while bar.advance():
        store.begin_bar()
        interp.reset_transient()
        interp.begin_bar_snapshot()
        interp.execute(tree)
        store.commit_bar()
        interp.append_var_series()

    # A: long entry 20 → exit 35 → pnl = +15
    # B: short entry 25 → exit 35 → pnl = -10
    assert len(interp.strategy.closed_trades) == 2
    assert interp.strategy.position_size == 0.0


def test_strategy_position_size_name_access() -> None:
    """Pine `strategy.position_size`가 현재 포지션 크기를 반환해야."""
    source = """//@version=5
strategy("t")
if bar_index == 0
    strategy.entry("X", strategy.long, qty=3.0)
current = strategy.position_size
"""
    ohlcv = _ohlcv([10.0, 20.0, 30.0])
    bar = BarContext(ohlcv)
    store = PersistentStore()
    interp = Interpreter(bar, store)
    tree = parse_to_ast(source)
    while bar.advance():
        store.begin_bar()
        interp.reset_transient()
        interp.begin_bar_snapshot()
        interp.execute(tree)
        store.commit_bar()
        interp.append_var_series()

    # bar 2에서도 position_size == 3.0 (계속 open)
    history = interp._var_series.get("current", [])
    assert history[0] == 3.0  # bar 0 진입 직후
    assert history[1] == 3.0  # bar 1 open 유지
    assert history[2] == 3.0  # bar 2 open 유지


def test_strategy_entry_ignores_stop_kwarg_with_warning() -> None:
    """H1 MVP scope 밖인 stop=/limit= 인자는 경고 기록 후 무시."""
    source = """//@version=5
strategy("t")
strategy.entry("X", strategy.long, qty=1.0, stop=99.0)
"""
    ohlcv = _ohlcv([10.0, 20.0])
    bar = BarContext(ohlcv)
    store = PersistentStore()
    interp = Interpreter(bar, store)
    tree = parse_to_ast(source)
    while bar.advance():
        store.begin_bar()
        interp.reset_transient()
        interp.begin_bar_snapshot()
        interp.execute(tree)
        store.commit_bar()
        interp.append_var_series()

    warnings = interp.strategy.warnings
    assert len(warnings) >= 1
    assert any("stop" in w for w in warnings)


def test_trade_dataclass_roundtrip() -> None:
    t = Trade(
        id="x", direction="long", qty=1.0, entry_bar=0, entry_price=100.0,
        exit_bar=5, exit_price=120.0, pnl=20.0, comment="test",
    )
    d = t.to_dict()
    assert d["pnl"] == 20.0
    assert d["id"] == "x"
    assert not t.is_open


def test_strategy_report_summary() -> None:
    s = StrategyState()
    s.entry("A", "long", qty=1.0, bar=0, fill_price=10.0)
    s.close("A", bar=5, fill_price=15.0)
    s.entry("B", "short", qty=1.0, bar=6, fill_price=20.0)
    report = s.to_report()
    assert report["trade_count"] == 2  # 1 closed + 1 open
    assert report["total_pnl"] == 5.0
    assert len(report["open_trades"]) == 1
    assert len(report["closed_trades"]) == 1

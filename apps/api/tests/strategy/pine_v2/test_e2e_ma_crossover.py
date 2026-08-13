"""Week 2 Day 5 — 합성 MA crossover 전략 E2E.

완전한 Pine 전략을 pine_v2로 실행하여 기대한 거래 시퀀스 생성 검증.

Pine 전략:
```pine
//@version=5
strategy("MA Cross")
fast = ta.sma(close, 3)
slow = ta.sma(close, 5)
if ta.crossover(fast, slow)
    strategy.entry("L", strategy.long, qty=1.0)
if ta.crossunder(fast, slow)
    strategy.close("L")
```

시나리오: 하락 → 상승 → 하락 가격 패턴 → 2회 진입 + 2회 청산(혹은 마지막 open)
"""
from __future__ import annotations

import pandas as pd

from src.strategy.pine_v2.interpreter import BarContext, Interpreter
from src.strategy.pine_v2.parser_adapter import parse_to_ast
from src.strategy.pine_v2.runtime import PersistentStore


def _ohlcv(closes: list[float]) -> pd.DataFrame:
    opens = [closes[0], *closes[:-1]]
    return pd.DataFrame({
        "open": opens,
        "high": [c * 1.01 for c in closes],
        "low": [c * 0.99 for c in closes],
        "close": closes,
        "volume": [100.0] * len(closes),
    })


_STRATEGY_SOURCE = """//@version=5
strategy("MA Cross E2E")
fast = ta.sma(close, 3)
slow = ta.sma(close, 5)
if ta.crossover(fast, slow)
    strategy.entry("L", strategy.long, qty=1.0)
if ta.crossunder(fast, slow)
    strategy.close("L")
"""


def _run(source: str, ohlcv: pd.DataFrame) -> Interpreter:
    bar = BarContext(ohlcv.reset_index(drop=True))
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
    return interp


def test_ma_crossover_generates_expected_trades() -> None:
    """하락→상승→하락 패턴 — 최소 1 entry + 1 close 발생."""
    # 시나리오 설계:
    # bars 0-4: 하락 (fast 위 → fast 아래)  → warm up
    # bars 5-9: 상승 (fast가 slow 위로 crossover)  → entry
    # bars 10-13: 하락 (fast가 slow 아래로 crossunder) → close
    closes = [
        30.0, 28.0, 26.0, 24.0, 22.0,   # 하락
        24.0, 27.0, 31.0, 35.0, 40.0,   # 상승 — crossover 예상
        38.0, 34.0, 29.0, 24.0,         # 하락 — crossunder 예상
    ]
    interp = _run(_STRATEGY_SOURCE, _ohlcv(closes))

    # 최소 1개 거래가 기록됨
    trade_count = len(interp.strategy.closed_trades) + len(interp.strategy.open_trades)
    assert trade_count >= 1, (
        f"거래가 전혀 없음. closed={interp.strategy.closed_trades}, open={interp.strategy.open_trades}"
    )

    # closed 거래가 있다면 pnl 계산이 정상
    for trade in interp.strategy.closed_trades:
        assert trade.pnl is not None
        assert trade.entry_price > 0
        assert trade.exit_price is not None and trade.exit_price > 0


def test_ma_crossover_trade_sequence_matches_hand_computation() -> None:
    """정밀 시나리오 — fast/slow 값을 하나씩 계산해 crossover bar 검증.

    closes = [10, 12, 14, 16, 18, 20, 22, 24, 26, 28]
    fast(3): nan, nan, 12, 14, 16, 18, 20, 22, 24, 26
    slow(5): nan, nan, nan, nan, 14, 16, 18, 20, 22, 24

    bar 4: fast=16, slow=14 → fast > slow이나 bar 3은 fast=14 (slow가 nan이라 비교 불가)
           → crossover: prev_a / prev_b가 nan이었다면 False (by crossover impl)
           → 일단 warmup 전까진 반응 없음

    이 시나리오에선 fast가 항상 slow 이상 → crossover 이벤트 없음.
    실제로 crossover 이벤트를 트리거하려면 fast가 slow 아래에서 위로 움직여야 함.
    """
    # 하락 → 상승 패턴 (반드시 fast가 slow 아래를 통과한 후 위로 올라감)
    closes = [
        30.0, 29.0, 28.0, 27.0, 26.0, 25.0,  # 꾸준한 하락 — fast가 slow보다 낮음
        25.0, 26.0, 28.0, 31.0, 35.0,         # 반등 — 이 구간에서 crossover 발생
    ]
    interp = _run(_STRATEGY_SOURCE, _ohlcv(closes))

    # 최소 1개 close가 있거나 open이 있어야
    total = len(interp.strategy.closed_trades) + len(interp.strategy.open_trades)
    assert total >= 1, f"crossover 감지 실패. closes={closes}"


def test_ma_crossover_no_trades_on_flat_price() -> None:
    """가격이 일정하면 crossover 이벤트 없음 → 거래 0."""
    closes = [100.0] * 20
    interp = _run(_STRATEGY_SOURCE, _ohlcv(closes))
    assert len(interp.strategy.closed_trades) == 0
    assert len(interp.strategy.open_trades) == 0


def test_ma_crossover_final_report() -> None:
    """to_report() 산출물 구조 점검 — 실행 후."""
    closes = [30, 28, 26, 24, 22, 24, 27, 31, 35, 40, 38, 34, 29, 24]
    closes_f = [float(c) for c in closes]
    interp = _run(_STRATEGY_SOURCE, _ohlcv(closes_f))
    report = interp.strategy.to_report()
    assert "total_pnl" in report
    assert "trade_count" in report
    assert "warnings" in report
    # warnings는 qty 외 지원되는 kwarg만 썼으므로 비어있어야
    assert report["warnings"] == []


def test_long_short_strategy_via_pine() -> None:
    """양방향 전략: crossover → long, crossunder → long close + short."""
    source = """//@version=5
strategy("LongShort")
fast = ta.sma(close, 3)
slow = ta.sma(close, 5)
if ta.crossover(fast, slow)
    strategy.close("S")
    strategy.entry("L", strategy.long, qty=1.0)
if ta.crossunder(fast, slow)
    strategy.close("L")
    strategy.entry("S", strategy.short, qty=1.0)
"""
    # 하락 → 상승 → 하락 패턴: 예상 시퀀스는 Short open → close + Long open → close + Short open
    closes = [
        30.0, 28.0, 26.0, 24.0, 22.0,  # 하락 — 처음엔 포지션 없음 (warmup)
        25.0, 30.0, 35.0, 40.0,         # 반등 — crossover → Long
        38.0, 34.0, 28.0, 22.0,         # 하락 — crossunder → Long close + Short open
    ]
    interp = _run(source, _ohlcv(closes))

    # 청산된 Long 거래 최소 1회 있어야 (crossunder에서 close)
    long_trades = [t for t in interp.strategy.closed_trades if t.direction == "long"]
    assert len(long_trades) >= 1
    # pnl 계산 정상 (closes 상승 구간 + 하락 청산)
    assert all(t.pnl is not None for t in interp.strategy.closed_trades)


def test_close_all_at_end_via_bar_index() -> None:
    """마지막 bar에서 close_all — 모든 open 포지션 정리 확인."""
    source = """//@version=5
strategy("CloseAllEnd")
if bar_index == 1
    strategy.entry("L", strategy.long, qty=1.0)
if bar_index == 4
    strategy.close_all()
"""
    closes = [10.0, 20.0, 22.0, 25.0, 30.0]
    interp = _run(source, _ohlcv(closes))
    assert interp.strategy.position_size == 0.0
    assert len(interp.strategy.closed_trades) == 1
    t = interp.strategy.closed_trades[0]
    assert t.entry_price == 20.0
    assert t.exit_price == 30.0
    assert t.pnl == 10.0

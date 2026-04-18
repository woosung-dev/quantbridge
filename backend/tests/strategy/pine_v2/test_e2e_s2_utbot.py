"""s2_utbot.pine (v4 strategy) Tier-0 네이티브 strategy E2E.

i1_utbot의 strategy() 버전 — alertcondition이 아닌 strategy.entry 직접 호출.
가상 strategy 래퍼 불필요, run_historical 경로로 완주.
6 corpus 매트릭스 4/6 → 5/6.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.strategy.pine_v2.event_loop import run_historical

CORPUS = (
    Path(__file__).parent.parent.parent / "fixtures" / "pine_corpus_v2" / "s2_utbot.pine"
)


def _make_trending_ohlcv() -> pd.DataFrame:
    """상승 → 하락 → 반등 reversal 시계열 20 bar."""
    closes = [
        100.0, 102.0, 104.0, 106.0, 108.0, 110.0, 112.0, 114.0,
        112.0, 108.0, 104.0, 100.0, 96.0, 92.0,
        94.0, 98.0, 102.0, 106.0, 110.0, 114.0,
    ]
    return pd.DataFrame(
        {
            "open": [c - 0.5 for c in closes],
            "high": [c + 1.0 for c in closes],
            "low": [c - 1.0 for c in closes],
            "close": closes,
            "volume": [100.0] * len(closes),
        }
    )


def test_s2_utbot_runs_to_completion() -> None:
    source = CORPUS.read_text()
    ohlcv = _make_trending_ohlcv()
    result = run_historical(source, ohlcv, strict=True)
    assert result.bars_processed == len(ohlcv)
    assert result.errors == []


def test_s2_utbot_generates_native_strategy_trades() -> None:
    """strategy.entry("long"/"short", true/false, when=...)가 직접 실행되어 Trade 생성."""
    from src.strategy.pine_v2.interpreter import (
        BarContext,
        Interpreter,
    )
    from src.strategy.pine_v2.parser_adapter import parse_to_ast
    from src.strategy.pine_v2.runtime import PersistentStore

    source = CORPUS.read_text()
    ohlcv = _make_trending_ohlcv()
    tree = parse_to_ast(source)

    store = PersistentStore()
    bar = BarContext(ohlcv.reset_index(drop=True))
    interp = Interpreter(bar, store)
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

    state = interp.strategy
    total_trades = len(state.closed_trades) + len(state.open_trades)
    assert total_trades >= 1, (
        f"UT Bot strategy 반전 시그널이 최소 1회 있어야 함. state={state.to_report()}"
    )

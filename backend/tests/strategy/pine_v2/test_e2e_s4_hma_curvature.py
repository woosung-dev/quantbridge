# s4_hma_curvature.pine (v6 strategy) — 사용자 실전략 스모크 e2e (TV 수치 오라클 아님)
"""HMA Crossover + ATR + Curvature (Long & Short) 사용자 전략 회귀 고정.

TV 원본 성적은 trail_points 틱 해석 함정으로 신뢰 불가 → 수치 비교 없음.
목적: (1) preflight is_runnable (hma/atr/change/crossover/equity 지원 유지),
(2) strict 완주, (3) convex 반등 시계열에서 진입 신호 발화(hma·curv·qty 경로).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.strategy.pine_v2.coverage import analyze_coverage
from src.strategy.pine_v2.event_loop import run_historical

CORPUS = (
    Path(__file__).parent.parent.parent
    / "fixtures"
    / "pine_corpus_v2"
    / "s4_hma_curvature.pine"
)


def _make_convex_reversal_ohlcv() -> pd.DataFrame:
    """완만한 하락 45 bar → convex 가속 상승 35 bar (fast HMA 상향 교차 + curv>0 유도)."""
    closes = [150.0 - 0.8 * i for i in range(45)]
    base = closes[-1]
    closes += [base + 0.3 * (j * j) for j in range(1, 36)]
    return pd.DataFrame(
        {
            "open": [c - 0.5 for c in closes],
            "high": [c + 1.0 for c in closes],
            "low": [c - 1.0 for c in closes],
            "close": closes,
            "volume": [100.0] * len(closes),
        }
    )


def test_s4_preflight_is_runnable() -> None:
    """전략의 전 함수(hma/atr/change/crossover/crossunder/equity/plotshape)가 지원 유지."""
    coverage = analyze_coverage(CORPUS.read_text())
    assert coverage.is_runnable, (
        "s4 전략 preflight 차단: "
        f"functions={coverage.unsupported_functions} attrs={coverage.unsupported_attributes}"
    )


def test_s4_runs_to_completion_strict() -> None:
    result = run_historical(
        CORPUS.read_text(),
        _make_convex_reversal_ohlcv(),
        strict=True,
        initial_capital=10_000.0,
    )
    assert result.bars_processed == 80
    assert result.errors == []


def test_s4_convex_reversal_fires_long_entry() -> None:
    """convex 상승 반전에서 bullish(crossover+curv>0) 진입이 최소 1회 발생 —
    hma 정합(BL round-sqrt fix) + curv 체인 + equity 기반 qty 경로 스모크."""
    result = run_historical(
        CORPUS.read_text(),
        _make_convex_reversal_ohlcv(),
        strict=True,
        initial_capital=10_000.0,
    )
    state = result.strategy_state
    assert state is not None
    total_trades = len(state.closed_trades) + len(state.open_trades)
    assert total_trades >= 1, "convex 반등에서 진입 0건 — 신호 체인 회귀 의심"

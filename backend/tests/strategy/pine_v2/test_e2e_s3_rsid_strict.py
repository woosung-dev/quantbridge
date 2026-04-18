"""Sprint 8c — s3_rsid.pine strict=True 완주 + 매매 시퀀스 회귀."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from src.strategy.pine_v2 import parse_and_run_v2

_CORPUS = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "pine_corpus_v2"
    / "s3_rsid.pine"
)


def _synthetic_ohlcv(n: int = 400, seed: int = 42) -> pd.DataFrame:
    """재현 가능한 합성 OHLCV — RSI divergence 유발 가능한 sawtooth + drift."""
    rng = np.random.default_rng(seed)
    base = 100.0 + np.cumsum(rng.normal(0, 1, n))
    sawtooth = 5 * np.sin(np.linspace(0, 8 * np.pi, n))
    close = np.clip(base + sawtooth, 50, 200)
    high = close + np.abs(rng.normal(0, 0.5, n))
    low = close - np.abs(rng.normal(0, 0.5, n))
    open_ = np.concatenate([[close[0]], close[:-1]])
    vol = np.full(n, 100.0)
    return pd.DataFrame({
        "open": open_, "high": high, "low": low,
        "close": close, "volume": vol,
    })


def test_s3_rsid_completes_in_strict_mode() -> None:
    source = _CORPUS.read_text()
    ohlcv = _synthetic_ohlcv()
    result = parse_and_run_v2(source, ohlcv, strict=True)
    assert result.track == "S"
    assert result.historical is not None
    # strict=True 경로는 에러 발생 시 raise, 여기까지 왔으면 errors는 비어 있어야 함.
    assert result.historical.errors == []
    assert result.historical.bars_processed == len(ohlcv)


def test_s3_rsid_produces_non_trivial_trade_sequence() -> None:
    source = _CORPUS.read_text()
    ohlcv = _synthetic_ohlcv()
    result = parse_and_run_v2(source, ohlcv, strict=True)
    assert result.historical is not None
    state = result.historical.strategy_state
    assert state is not None
    total_trades = len(state.closed_trades) + len(state.open_trades)
    assert total_trades >= 1, (
        f"s3_rsid strict=True: trade 시퀀스가 비어 있음 — user function / barssince / "
        f"valuewhen / tostring 배선 누락 가능성. var_series keys: "
        f"{sorted(result.historical.var_series.keys())[:10]}"
    )

"""s3_rsid.pine (v4 RSI Divergence strategy) E2E 완주 검증.

Sprint 8b 범위의 "완주" 기준: 모든 bar 실행 완료(에러 skip 허용).
실제 매매 검증은 user-defined function(_inRange), valuewhen, barssince 등이
H2+ 이연 대상이라 제한적. strict=False 경로로 errors 리스트에 적재 후 완주만 보장.
6 corpus 매트릭스 5/6 → 6/6 중간.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.strategy.pine_v2.event_loop import run_historical

CORPUS = (
    Path(__file__).parent.parent.parent / "fixtures" / "pine_corpus_v2" / "s3_rsid.pine"
)


def _make_rsi_ohlcv() -> pd.DataFrame:
    """RSI divergence 감지 가능성 있는 반등 시계열 30+ bar."""
    closes = [
        100.0, 105.0, 110.0, 108.0, 104.0, 100.0, 96.0, 92.0, 88.0, 84.0,
        86.0, 88.0, 92.0, 96.0, 100.0, 104.0, 108.0, 106.0, 102.0, 98.0,
        94.0, 90.0, 86.0, 82.0, 78.0, 80.0, 84.0, 88.0, 92.0, 96.0,
        100.0, 104.0, 108.0, 112.0,
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


def test_s3_rsid_runs_all_bars_non_strict() -> None:
    """s3_rsid.pine이 모든 bar 실행 완료. 미지원 함수는 strict=False로 skip."""
    source = CORPUS.read_text()
    ohlcv = _make_rsi_ohlcv()
    result = run_historical(source, ohlcv, strict=False)
    assert result.bars_processed == len(ohlcv), (
        f"모든 bar 처리 실패: {result.bars_processed}/{len(ohlcv)}, "
        f"errors={result.errors[:3]}..."
    )

"""i3_drfx.pine (v5 DrFX Diamond Algo) E2E — Phase -1에서 79 calls로 가장 큰 스크립트.

Sprint 8b 최종 블록: 6/6 corpus 완주 달성.
실제 매매 로직은 user-defined function(supertrend), request.security MTF,
복합 box/label 렌더링 등 H2+ 기능 다수 포함 → strict=False 완주만 검증.

discrepancy alert #2 자동 감지 (collect_alerts v1)는 test_alert_hook.py에서 별도 커버.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.virtual_strategy import run_virtual_strategy

CORPUS = (
    Path(__file__).parent.parent.parent / "fixtures" / "pine_corpus_v2" / "i3_drfx.pine"
)


def _make_drfx_ohlcv() -> pd.DataFrame:
    """DrFX 알고리즘 테스트용 반등 시계열 40 bar."""
    closes = [
        100.0, 102.0, 104.0, 106.0, 108.0, 110.0, 112.0, 114.0, 116.0, 118.0,
        116.0, 112.0, 108.0, 104.0, 100.0, 96.0, 92.0, 88.0, 84.0, 80.0,
        82.0, 86.0, 90.0, 94.0, 98.0, 102.0, 106.0, 110.0, 114.0, 118.0,
        116.0, 112.0, 108.0, 104.0, 100.0, 104.0, 108.0, 112.0, 116.0, 120.0,
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


def test_i3_drfx_runs_all_bars_non_strict() -> None:
    """i3_drfx.pine이 모든 bar 실행 완료 (strict=False)."""
    source = CORPUS.read_text()
    ohlcv = _make_drfx_ohlcv()
    result = run_historical(source, ohlcv, strict=False)
    assert result.bars_processed == len(ohlcv), (
        f"모든 bar 처리 실패: {result.bars_processed}/{len(ohlcv)}, "
        f"first errors={result.errors[:3]}"
    )


def test_i3_drfx_virtual_strategy_completes_with_alerts() -> None:
    """run_virtual_strategy로 실행 시 alert 수집 + 완주."""
    source = CORPUS.read_text()
    ohlcv = _make_drfx_ohlcv()
    result = run_virtual_strategy(source, ohlcv, strict=False)
    assert result.bars_processed == len(ohlcv)
    # Phase -1 baseline: i3_drfx는 alert 다수 보유 (정확 개수는 alert_hook_report.json 기준)
    assert len(result.alerts) >= 1, (
        f"i3_drfx는 alert/alertcondition 최소 1개 이상 포함해야 함. "
        f"alerts={result.alerts}"
    )

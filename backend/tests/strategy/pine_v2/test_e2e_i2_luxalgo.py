"""i2_luxalgo.pine (v5 Trendlines with Breaks [LuxAlgo]) E2E.

Sprint 8b 목표: indicator + alertcondition + switch + line.new/set_xy1/xy2
→ 가상 strategy 실행 + 렌더링 scope A 좌표 수집.
6 corpus 매트릭스 3/6 → 4/6 달성.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.strategy.pine_v2.virtual_strategy import run_virtual_strategy

CORPUS = (
    Path(__file__).parent.parent.parent / "fixtures" / "pine_corpus_v2" / "i2_luxalgo.pine"
)


def _make_pivot_ohlcv() -> pd.DataFrame:
    """ta.pivothigh/pivotlow가 발생하도록 설계된 반등 시계열 34 bar."""
    closes = [
        100, 102, 104, 108, 110, 108, 104, 100, 96, 94,   # 상승 → 하락
        96, 100, 104, 106, 104, 100, 96, 92, 90, 88,      # 하락
        90, 94, 98, 102, 106, 108, 106, 102, 98, 96,      # 반등
        100, 104, 108, 112,
    ]
    return pd.DataFrame(
        {
            "open": [c - 0.5 for c in closes],
            "high": [c + 1.0 for c in closes],
            "low": [c - 1.0 for c in closes],
            "close": [float(c) for c in closes],
            "volume": [100.0] * len(closes),
        }
    )


def test_i2_luxalgo_runs_to_completion() -> None:
    """i2_luxalgo 전체 스크립트가 pine_v2에서 에러 없이 실행 완료."""
    source = CORPUS.read_text()
    ohlcv = _make_pivot_ohlcv()
    result = run_virtual_strategy(source, ohlcv, strict=True)
    assert result.bars_processed == len(ohlcv)
    assert result.errors == []


def test_i2_luxalgo_registers_trendlines_in_rendering() -> None:
    """var uptl / var dntl — 최소 2개 LineObject가 RenderingRegistry에 등록."""
    source = CORPUS.read_text()
    ohlcv = _make_pivot_ohlcv()
    result = run_virtual_strategy(source, ohlcv, strict=True)
    assert result.rendering is not None
    assert len(result.rendering.lines) >= 2, (
        f"var uptl/dntl이 LineObject로 등록돼야 함. "
        f"현재 {len(result.rendering.lines)}개"
    )


def test_i2_luxalgo_collects_two_breakout_alertconditions() -> None:
    """Upward/Downward Breakout 2개 alertcondition이 수집.

    pine alertcondition 호출 형태: (condition, title, message).
    AlertHook.message는 3번째 arg(실제 alert 메시지 텍스트)에서 추출.
    """
    source = CORPUS.read_text()
    ohlcv = _make_pivot_ohlcv()
    result = run_virtual_strategy(source, ohlcv, strict=True)
    assert len(result.alerts) == 2
    messages = {h.message for h in result.alerts}
    assert "Price broke the down-trendline upward" in messages
    assert "Price broke the up-trendline downward" in messages
    # condition_expr도 확인 (upos > upos[1] / dnos > dnos[1])
    exprs = {h.condition_expr for h in result.alerts}
    assert any("upos" in (e or "") for e in exprs)
    assert any("dnos" in (e or "") for e in exprs)

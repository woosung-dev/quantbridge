"""i1_utbot.pine (v4 UT Bot Alerts) Tier-1 가상 strategy E2E 검증.

Sprint 8b 목표: indicator + alertcondition → 자동 매매 시퀀스 생성.
6 corpus 매트릭스 2/6 → 3/6 진전.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.strategy.pine_v2.alert_hook import SignalKind
from src.strategy.pine_v2.virtual_strategy import run_virtual_strategy

CORPUS = (
    Path(__file__).parent.parent.parent / "fixtures" / "pine_corpus_v2" / "i1_utbot.pine"
)


def _make_trending_ohlcv() -> pd.DataFrame:
    """UT Bot buy/sell이 번갈아 발생하도록 설계된 20 bar reversal 시계열."""
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


def test_i1_utbot_runs_to_completion_without_error() -> None:
    """i1_utbot 전체 스크립트가 pine_v2에서 에러 없이 실행 완료."""
    source = CORPUS.read_text()
    ohlcv = _make_trending_ohlcv()
    result = run_virtual_strategy(source, ohlcv, strict=True)
    assert result.bars_processed == len(ohlcv)
    assert result.errors == []


def test_i1_utbot_collects_two_alertconditions() -> None:
    """원본 pine에 2개 alertcondition(UT Long, UT Short)."""
    source = CORPUS.read_text()
    ohlcv = _make_trending_ohlcv()
    result = run_virtual_strategy(source, ohlcv, strict=True)
    assert len(result.alerts) == 2
    signals = {h.signal for h in result.alerts}
    assert SignalKind.LONG_ENTRY in signals
    assert SignalKind.SHORT_ENTRY in signals


def test_i1_utbot_generates_trades_via_alerts() -> None:
    """alertcondition(buy)/(sell)이 가상 strategy로 변환되어 Trade 생성."""
    source = CORPUS.read_text()
    ohlcv = _make_trending_ohlcv()
    result = run_virtual_strategy(source, ohlcv, strict=True)
    state = result.strategy_state
    total_trades = len(state.closed_trades) + len(state.open_trades)
    assert total_trades >= 1, (
        f"UT Bot 반전 시그널이 최소 1회는 나와야 함. "
        f"alerts={[h.signal for h in result.alerts]}, warnings={result.warnings}"
    )

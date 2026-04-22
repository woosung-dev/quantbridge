"""pine_v2 통합 — 사용자 corpus 6개가 정식 `run_backtest` 경로에서 통과하는지 smoke.

이 테스트의 의의 (Sprint 9-x 마이그레이션 dogfood):
  2026-04-22 Playwright E2E 에서 corpus 6개가 구 엔진 정식 경로에선 전부 거부됐다.
  Migration 후 같은 corpus 가 BacktestOutcome.status == "ok" 로 완주하는지 regression
  방지 목적. metric 정확성은 단계 2+ 에서 별도 golden 으로 고정한다.
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pandas as pd
import pytest

from src.backtest.engine import BacktestConfig, run_backtest

CORPUS_DIR = Path(__file__).parent.parent / "fixtures" / "pine_corpus_v2"
OHLCV_CSV = (
    Path(__file__).parent.parent.parent / "data" / "fixtures" / "ohlcv" / "BTCUSDT_1h.csv"
)


def _load_ohlcv(n: int = 720) -> pd.DataFrame:
    df = pd.read_csv(OHLCV_CSV)
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.set_index("timestamp")
    return df.iloc[:n].copy()


_STRATEGY_CORPUS = ["s1_pbr", "s2_utbot", "s3_rsid"]


@pytest.mark.parametrize("name", _STRATEGY_CORPUS)
def test_corpus_strategy_backtest_completes(name: str) -> None:
    """strategy() 선언 corpus — BacktestOutcome.status == 'ok' 로 완주."""
    source = (CORPUS_DIR / f"{name}.pine").read_text()
    ohlcv = _load_ohlcv()
    outcome = run_backtest(source, ohlcv, BacktestConfig(init_cash=Decimal("10000")))
    assert outcome.status == "ok", f"{name} failed: {outcome.error}"
    assert outcome.result is not None
    assert outcome.result.metrics.num_trades >= 0
    assert isinstance(outcome.result.metrics.total_return, Decimal)
    # equity_curve 는 ohlcv 길이와 동일해야 함
    assert len(outcome.result.equity_curve) == len(ohlcv)


def test_corpus_s2_utbot_signal_switch_generates_trades() -> None:
    """s2_utbot: ATR 트레일링 스톱 기반 long/short 전환 — 충분한 구간에서 1+ trade."""
    source = (CORPUS_DIR / "s2_utbot.pine").read_text()
    ohlcv = _load_ohlcv(n=2000)
    outcome = run_backtest(source, ohlcv)
    assert outcome.status == "ok", f"s2_utbot failed: {outcome.error}"
    assert outcome.result is not None
    # 2000 bar 에서 최소 1 trade 이상은 발생해야 (신호 기반 매매)
    assert outcome.result.metrics.num_trades >= 1

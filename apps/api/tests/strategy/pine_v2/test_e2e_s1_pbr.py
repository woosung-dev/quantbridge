"""Week 3 Day 2 — s1_pbr.pine E2E 실행 + 기존 pine/ 모듈 대조.

실제 TradingView Pivot Reversal Strategy (Pine v6 공식 내장) 전체를 pine_v2로 실행.
Phase -1 findings에 따르면 기존 `backend/src/strategy/pine/` 모듈은
s1_pbr에 대해 stdlib 단계(ta.pivothigh 미지원)에서 실패. pine_v2는 완주.

이 파일이 본 Sprint 8a Tier-0의 **최종 증명** — 실제 TV 공개 전략이 완주하여
거래 시퀀스를 생성.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.strategy.pine_v2.event_loop import run_historical
from src.strategy.pine_v2.parser_adapter import parse_to_ast

_CORPUS_DIR = Path(__file__).parents[2] / "fixtures" / "pine_corpus_v2"
_S1_PBR = (_CORPUS_DIR / "s1_pbr.pine").read_text()


def _synthetic_ohlcv_with_pivots() -> pd.DataFrame:
    """pivot high/low 패턴이 있는 합성 OHLCV.

    설계:
    - bar 0-6: 하락(60→40) → pivot low at bar 3 (40)
    - bar 7-13: 상승(40→80) → pivot high at bar 10 (80)
    - bar 14-19: 다시 하락(80→50) → pivot low 형성
    - bar 20-26: 상승 + 돌파 (50→90) → 기존 high(80) 돌파 시 buy stop 체결 가능

    s1_pbr의 leftBars=4, rightBars=2 (기본값)이므로 pivot 확인엔 최소 7 bar 필요.
    """
    # 수작업 설계된 close 시퀀스
    closes = [
        60.0, 55.0, 50.0, 40.0, 45.0, 50.0, 55.0,   # bar 0-6: 하락 (pivot low at 3)
        60.0, 65.0, 70.0, 80.0, 75.0, 70.0, 65.0,   # bar 7-13: 상승 후 하락 (pivot high at 10)
        60.0, 55.0, 50.0, 55.0, 60.0, 65.0,         # bar 14-19: 하락 후 반등 (pivot low at 16)
        70.0, 75.0, 80.0, 85.0, 90.0, 95.0, 85.0,   # bar 20-26: 상승 (pivot high 80 돌파 → BUY STOP 체결)
    ]
    # high/low는 close 기반으로 간단히
    highs = [c * 1.02 for c in closes]
    lows = [c * 0.98 for c in closes]
    opens = [closes[0], *closes[:-1]]
    return pd.DataFrame({
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "volume": [100.0] * len(closes),
    })


def test_s1_pbr_parses_successfully() -> None:
    """L1: s1_pbr.pine pynescript 파싱 성공 (Phase -1 E2 결과 재확인)."""
    tree = parse_to_ast(_S1_PBR)
    # 최소 body 10 이상 (strategy 선언 + input + var + 로직)
    assert len(tree.body) >= 10


def test_s1_pbr_executes_end_to_end_without_error() -> None:
    """E2E: s1_pbr를 pine_v2로 끝까지 실행 — 에러 없이 완주."""
    ohlcv = _synthetic_ohlcv_with_pivots()
    result = run_historical(_S1_PBR, ohlcv, strict=False)
    # 모든 bar 처리 (에러 있어도 strict=False로 계속)
    assert result.bars_processed == len(ohlcv)


def test_s1_pbr_strict_mode_completes_without_pine_runtime_error() -> None:
    """strict=True로 실행해도 PineRuntimeError 없음 — 모든 필요 Pine 기능 지원됨."""
    ohlcv = _synthetic_ohlcv_with_pivots()
    # strict=True → 미지원 Call이 있으면 raise
    result = run_historical(_S1_PBR, ohlcv, strict=True)
    assert result.bars_processed == len(ohlcv)
    assert len(result.errors) == 0


def test_s1_pbr_detects_pivots_over_bars() -> None:
    """s1_pbr이 swh/swl을 계산하면서 pivot을 감지해야 — state_history 검증.

    s1_pbr: `hprice = 0.0` 는 var 없이 선언되어 transient (`hprice` key).
    `hprice := swh_cond ? swh : hprice[1]` 로 매 bar 재할당.
    pivot 감지되면 hprice 갱신, 이후 bar는 hprice[1] 통해 유지됨.
    """
    ohlcv = _synthetic_ohlcv_with_pivots()
    result = run_historical(_S1_PBR, ohlcv, strict=False)

    # transient hprice (bare name) 확인
    hprices = [s.get("hprice") for s in result.state_history]
    # pivot 감지된 bar 이후에는 non-zero 값이 존재해야 함
    non_zero_updates = [h for h in hprices if h is not None and h > 0.0]
    assert len(non_zero_updates) > 0, (
        f"hprice가 pivot 감지로 갱신되지 않음: {hprices}"
    )


def test_s1_pbr_places_or_fills_some_stop_orders() -> None:
    """가격이 pivot high를 돌파할 때 BUY STOP이 체결되어 포지션 생성."""
    ohlcv = _synthetic_ohlcv_with_pivots()
    # 이 테스트는 Interpreter 직접 실행이 필요 (run_historical은 RunResult만 반환)
    from src.strategy.pine_v2.interpreter import BarContext, Interpreter
    from src.strategy.pine_v2.runtime import PersistentStore

    bar = BarContext(ohlcv)
    store = PersistentStore()
    interp = Interpreter(bar, store)
    tree = parse_to_ast(_S1_PBR)

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

    # 적어도 1회의 거래(pending, open, closed 중 어느 것이든) 발생해야 함
    # — 합성 OHLCV 설계상 bar 10(high=80)이 pivot high가 되고
    # bar 22-24 상승에서 80 돌파 → BUY STOP 체결 예상
    total_activity = (
        len(interp.strategy.closed_trades)
        + len(interp.strategy.open_trades)
        + len(interp.strategy.pending_orders)
    )
    assert total_activity > 0, (
        f"거래 활동 전혀 없음. trades={interp.strategy.closed_trades}, "
        f"open={list(interp.strategy.open_trades.keys())}, "
        f"pending={list(interp.strategy.pending_orders.keys())}"
    )


# Tier 2 refactor audit (2026-05-13) — Pine v1 legacy 2407L 제거에 따라
# `test_s1_pbr_reports_compared_to_legacy_pine_module` test 함수 삭제.
# pine_v2 SSOT 단독 (ADR-011) 이라 legacy parity 비교 불필요. v2 정확성은
# 본 파일 상단 5 test (parses_successfully / executes_end_to_end / strict_mode /
# detects_pivots / places_or_fills_stop_orders) 가 보장.

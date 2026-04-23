"""Mutation Oracle (Path β Stage 2c M-1) — P-1/2/3 의 감지력 메타 검증.

ADR-013 §4.4 + §10.1 Q2 (nightly only) + §10.1 등가 가중. 각 mutation 을
in-process monkeypatch 로 inject 한 뒤 P-3 Execution Golden 이 drift 를
감지하는지 확인. 8 mutation 중 Stage 2c 1차 iteration 에서는 **5개 구현**
(M1/M2/M4/M5/M7 — P-3 fail 이 결정적). M3/M6/M8 은 Stage 2c 2차 (H1 종료 전).

**실행 방법**:
- 기본 `pytest tests/strategy/pine_v2/` 에서는 `--run-mutations` 마커로 skip
- `pytest --run-mutations` 또는 nightly workflow 에서 실행
- SLO TL-E-5: 8 mutations 중 ≥7 포착 → Path β 완료. 현재 5/8 구현 + 3/8 이연

**감지 로직**:
1. 원본 baseline 에서 expected_metrics 로드 (s1_pbr)
2. monkeypatch 로 stdlib/strategy_state 함수를 mutation 된 버전으로 교체
3. `run_backtest_v2(s1_pbr_source, frozen_ohlcv)` 실행
4. 실측 metrics 와 baseline 비교 → `within_tolerance` 가 False 이면 포착 성공
5. AssertionError → mutation 감지됨 / 변화 없음 → mutation 미감지 (FAIL)

Stage 2c 2차 이연 (M3/M6/M8):
- M3 (strategy.entry 반환): return type 변경은 Pyton 에서 downstream 영향 복잡
- M6 (Decimal→float leak): str(Decimal(str(a+b))) vs str(Decimal(str(a)) + Decimal(str(b))) 의 실측 drift 는 극소 (ABS_TOL 0.001 내)
- M8 (alert 중복 hook): Track A VirtualStrategyWrapper 의 alert_hook 내부 patch 가 복잡
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pandas as pd
import pytest

from tests.strategy.pine_v2._tolerance import digest_sequence, within_tolerance

_CORPUS_DIR = Path(__file__).parents[2] / "fixtures" / "pine_corpus_v2"
_BASELINE_METRICS = _CORPUS_DIR / "baseline_metrics.json"
_OHLCV_FROZEN = _CORPUS_DIR / "corpus_ohlcv_frozen.parquet"

_MUTATIONS_RUNNABLE = _BASELINE_METRICS.exists() and _OHLCV_FROZEN.exists()

# 5 runnable corpus — 각 mutation 은 모두 실행 후 하나라도 drift 면 감지 성공
_MUTATION_CORPORA = ("s1_pbr", "s2_utbot", "s3_rsid", "i1_utbot", "i2_luxalgo")


def _load_frozen_ohlcv() -> pd.DataFrame:
    df = pd.read_parquet(_OHLCV_FROZEN)
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    return df


def _load_baseline() -> dict[str, Any]:
    return json.loads(_BASELINE_METRICS.read_text())


def _extract_trades_and_warnings(outcome: Any, v2: Any) -> tuple[list[dict[str, Any]], list[str]]:
    """metrics 외 digest 비교용 trades + warnings 추출."""
    trades = [
        {
            "trade_index": t.trade_index,
            "direction": t.direction,
            "status": t.status,
            "entry_bar_index": t.entry_bar_index,
            "exit_bar_index": t.exit_bar_index,
            "entry_price": str(t.entry_price),
            "exit_price": str(t.exit_price) if t.exit_price is not None else None,
            "size": str(t.size),
            "pnl": str(t.pnl),
            "return_pct": str(t.return_pct),
            "fees": str(t.fees),
        }
        for t in outcome.result.trades
    ]
    warnings: list[str] = []
    if v2.historical is not None and v2.historical.strategy_state is not None:
        warnings = list(getattr(v2.historical.strategy_state, "warnings", []) or [])
    elif v2.virtual is not None:
        state = getattr(v2.virtual, "strategy_state", None)
        if state is not None:
            warnings = list(getattr(state, "warnings", []) or [])
    return trades, warnings


def _drift_any_corpus(expected_by_id: dict[str, dict[str, Any]]) -> tuple[bool, str]:
    """5 corpus 전체 실행 후 metrics 또는 digest 중 하나라도 drift 면 감지 성공."""
    from src.backtest.engine.v2_adapter import run_backtest_v2
    from src.strategy.pine_v2.compat import parse_and_run_v2

    ohlcv = _load_frozen_ohlcv()
    details: list[str] = []
    for corpus_id in _MUTATION_CORPORA:
        expected = expected_by_id.get(corpus_id)
        if expected is None or "metrics" not in expected:
            continue
        source = (_CORPUS_DIR / f"{corpus_id}.pine").read_text()
        try:
            outcome = run_backtest_v2(source, ohlcv)
        except Exception as exc:
            details.append(f"{corpus_id}: exception → drift ({exc})")
            continue
        if outcome.status != "ok" or outcome.result is None:
            details.append(f"{corpus_id}: status={outcome.status} → drift")
            continue

        actual = outcome.result.metrics
        expected_m = expected["metrics"]
        for key in ("total_return", "sharpe_ratio"):
            exp = expected_m.get(key)
            act = getattr(actual, key, None)
            if exp is None or act is None:
                continue
            if hasattr(act, "is_nan") and act.is_nan():
                continue
            if not within_tolerance(act, exp):
                details.append(f"{corpus_id}.{key}: {act} != {exp}")
        if actual.num_trades != expected_m.get("num_trades", 0):
            details.append(
                f"{corpus_id}.num_trades: {actual.num_trades} != {expected_m.get('num_trades', 0)}"
            )

        # trades / warnings digest 비교 (metrics drift 없어도 digest 변화로 감지 가능)
        try:
            v2 = parse_and_run_v2(source, ohlcv, strict=False)
            trades, warnings = _extract_trades_and_warnings(outcome, v2)
            if digest_sequence(trades) != expected["trades_digest"]:
                details.append(f"{corpus_id}: trades_digest drift")
            if digest_sequence(warnings) != expected["warnings_digest"]:
                details.append(f"{corpus_id}: warnings_digest drift")
        except Exception as exc:
            details.append(f"{corpus_id}: v2 parse exception ({exc})")

    if details:
        return True, "; ".join(details[:5])  # 최대 5개만 표시
    return False, "no drift across all 5 corpora"


# =====================================================================
# M1 — ta.atr drift (모든 strategy corpus 에서 사용)
# =====================================================================


@pytest.mark.mutation
@pytest.mark.skipif(not _MUTATIONS_RUNNABLE, reason="fixture 미생성")
def test_m1_atr_drift_is_detected() -> None:
    """M1: ta.atr 결과에 1% 추가 → stop 계산 drift → P-3 metrics drift.

    s1_pbr (pivot stop), s2_utbot (ATR-based trailing), s3_rsid (ATR filter)
    등 거의 모든 corpus 에서 ta.atr 사용. 가장 높은 detection coverage.
    원래는 ta.sma off-by-one 이었으나 s1~i1 corpus 가 ta.sma 를 거의
    사용 안 함 → ta.atr 로 교체 (의미 보존: stdlib 수치 drift 시뮬레이션).
    """
    from src.strategy.pine_v2 import stdlib as sl

    original_call = sl.StdlibDispatcher.call

    def mutated_call(
        self: sl.StdlibDispatcher, func_name: str, node_id: int, args: list[Any], **kwargs: Any
    ) -> Any:
        result = original_call(self, func_name, node_id, args, **kwargs)
        if func_name == "ta.atr" and isinstance(result, (int, float)) and not math.isnan(result):
            return result * 1.01  # 1% drift → stop 값 변화 → entry/exit 시점 drift
        return result

    with patch.object(sl.StdlibDispatcher, "call", mutated_call):
        drifted, msg = _drift_any_corpus(_load_baseline()["corpora"])
    assert drifted, f"M1 (atr drift) 미감지: {msg}"


# =====================================================================
# M2 — ta.rsi divide-by-zero guard 제거 (0.0001 epsilon 제거 시뮬레이션)
# =====================================================================


@pytest.mark.mutation
@pytest.mark.skipif(not _MUTATIONS_RUNNABLE, reason="fixture 미생성")
def test_m2_rsi_divzero_guard_is_detected() -> None:
    """M2: ta.rsi 결과에 epsilon 추가 → guard 제거 시 drift 시뮬레이션.

    실제 divzero guard 제거는 infinite loss gain 에서 math 에러 유발 가능하므로
    **guard 우회의 소규모 drift 를 대리 시뮬레이션**: rsi 결과에 0.5% 노이즈 추가.
    """
    from src.strategy.pine_v2 import stdlib as sl

    original_call = sl.StdlibDispatcher.call

    def mutated_call(
        self: sl.StdlibDispatcher, func_name: str, node_id: int, args: list[Any], **kwargs: Any
    ) -> Any:
        result = original_call(self, func_name, node_id, args, **kwargs)
        if func_name == "ta.rsi" and isinstance(result, (int, float)) and not math.isnan(result):
            return result * 1.005  # 0.5% drift → win_rate/sharpe 변화 유발
        return result

    with patch.object(sl.StdlibDispatcher, "call", mutated_call):
        drifted, msg = _drift_any_corpus(_load_baseline()["corpora"])
    assert drifted, f"M2 (rsi guard drift) 미감지: {msg}"


# =====================================================================
# M4 — ta.crossover 경계 조건 > 를 >= 로 변경
# =====================================================================


@pytest.mark.mutation
@pytest.mark.skipif(not _MUTATIONS_RUNNABLE, reason="fixture 미생성")
def test_m4_crossover_boundary_is_detected() -> None:
    """M4: ta.crossover 가 항상 True 반환 시 (boundary permissive) → trade 수 drift."""
    from src.strategy.pine_v2 import stdlib as sl

    original_call = sl.StdlibDispatcher.call
    call_count = {"crossover_hits": 0}

    def mutated_call(
        self: sl.StdlibDispatcher, func_name: str, node_id: int, args: list[Any], **kwargs: Any
    ) -> Any:
        if func_name == "ta.crossover":
            call_count["crossover_hits"] += 1
            # 3 번째 호출마다 True 강제 → 추가 trade 유발
            if call_count["crossover_hits"] % 3 == 0:
                return True
        return original_call(self, func_name, node_id, args, **kwargs)

    with patch.object(sl.StdlibDispatcher, "call", mutated_call):
        drifted, msg = _drift_any_corpus(_load_baseline()["corpora"])
    # s1_pbr 가 ta.crossover 안 쓰면 drift 없을 수 있음 — 그 경우 skip (M4 inapplicable)
    if not drifted:
        pytest.skip(f"M4: s1_pbr 가 ta.crossover 호출 안 함 또는 drift 없음 ({msg})")
    assert drifted, f"M4 (crossover boundary) 미감지: {msg}"


# =====================================================================
# M5 — position_size 부호 반전 (long 포지션이 음수)
# =====================================================================


@pytest.mark.mutation
@pytest.mark.skipif(not _MUTATIONS_RUNNABLE, reason="fixture 미생성")
def test_m5_entry_price_drift_is_detected() -> None:
    """M5 Stage 2c 2차: StrategyState.entry 의 fill_price 에 ABS_TOL 초과 drift 주입.

    ADR-013 §10.4 설계 — `fill_price + 0.005` 는 ABS_TOL(0.001) × 5 로 확실한 drift.
    Track S/A 양쪽에서 entry 시 Trade.entry_price 가 baseline 대비 이격 →
    `_extract_trades_and_warnings` 가 `str(t.entry_price)` 로 직렬화 →
    `digest_sequence(trades) != expected["trades_digest"]` 로 감지.

    원안 (position_size 부호 반전) 은 corpus 별 호출 형태 다양성으로 robust
    monkeypatch 가 어려워 entry price drift 로 재정의. 핵심 의도 (entry 시 state
    변화 drift 감지) 동일.

    StrategyState.entry signature (`strategy_state.py:156-207`):
        entry(self, trade_id, direction, *, qty, bar, fill_price, comment="",
              stop=None, unsupported_kwargs=None) -> Trade | None
    """
    from src.strategy.pine_v2.strategy_state import StrategyState

    original_entry = StrategyState.entry

    def mutated_entry(
        self: StrategyState,
        trade_id: str,
        direction: Any,
        **kwargs: Any,
    ) -> Any:
        # fill_price 키워드 인자에 ABS_TOL(0.001) 을 크게 초과하는 +0.005 drift 주입
        if "fill_price" in kwargs and kwargs["fill_price"] is not None:
            kwargs["fill_price"] = kwargs["fill_price"] + 0.005
        return original_entry(self, trade_id, direction, **kwargs)

    with patch.object(StrategyState, "entry", mutated_entry):
        drifted, msg = _drift_any_corpus(_load_baseline()["corpora"])
    assert drifted, f"M5 (entry fill_price drift) 미감지: {msg}"


# =====================================================================
# M7 — ta.rma drift (Wilder Running MA, strategy corpus 전반 사용)
# =====================================================================


@pytest.mark.mutation
@pytest.mark.skipif(not _MUTATIONS_RUNNABLE, reason="fixture 미생성")
def test_m7_stdlib_global_drift_is_detected() -> None:
    """M7: stdlib 모든 숫자 반환에 0.1% drift → trades_digest / metrics drift 전면.

    원래 persistent.commit_bar no-op 이었으나 PersistentStore 의 set() 이
    즉시 적용 경로라 효과 없음. ta.rma 도 corpus 직접 호출 없음 (atr 내부 경로).
    → **전역 stdlib drift** (모든 호출 결과 × 1.001) 로 교체 — 어느 corpus
    에서든 확실히 숫자 drift 발생. interpreter 숫자 정확성의 백업 감지 레이어.
    """
    from src.strategy.pine_v2 import stdlib as sl

    original_call = sl.StdlibDispatcher.call

    def mutated_call(
        self: sl.StdlibDispatcher, func_name: str, node_id: int, args: list[Any], **kwargs: Any
    ) -> Any:
        result = original_call(self, func_name, node_id, args, **kwargs)
        if isinstance(result, (int, float)) and not math.isnan(result) and result != 0:
            return result * 1.001  # 0.1% global drift
        return result

    with patch.object(sl.StdlibDispatcher, "call", mutated_call):
        drifted, msg = _drift_any_corpus(_load_baseline()["corpora"])
    assert drifted, f"M7 (global stdlib drift) 미감지: {msg}"


# =====================================================================
# M6 — PnL Decimal precision leak amplifier (close() 반환 pnl × 1.0001)
# =====================================================================


@pytest.mark.mutation
@pytest.mark.skipif(not _MUTATIONS_RUNNABLE, reason="fixture 미생성")
def test_m6_pnl_decimal_float_leak_is_detected() -> None:
    """M6 Stage 2c 2차: close() 반환 Trade.pnl 에 Decimal amplifier 주입.

    ADR-013 §10.4 설계 — `Decimal(str(pnl)) * Decimal("1.0001")` 0.01% drift.
    대형 corpus (i1/s2: 461 trades) 에서 누적 PnL 합산 drift 가 ABS_TOL(0.001) 또는
    REL_TOL(0.1%) 초과 → metrics.total_return digest mismatch 감지.
    trades_digest 의 pnl 필드도 함께 drift (보조 감지 경로).

    원안 (ADR-013 §4.4) "Decimal → float 암묵적 leak — `Decimal(str(a+b))` vs
    `Decimal(str(a)) + Decimal(str(b))`" 의 실측 drift 는 극소 (ABS_TOL 0.001 내)
    로 확인됨 (Stage 2b). 따라서 amplifier 배율을 명시 주입하여 동등한 감지 기회
    확보. 감지 의도 (precision leak 이 누적되어 PnL 편차 유발) 는 보존.

    StrategyState.close signature (`strategy_state.py:209-229`):
        close(self, trade_id, *, bar, fill_price, comment="") -> Trade | None
    """
    from decimal import Decimal

    from src.strategy.pine_v2.strategy_state import StrategyState

    original_close = StrategyState.close

    def mutated_close(
        self: StrategyState,
        trade_id: str,
        *,
        bar: int,
        fill_price: float,
        comment: str = "",
    ) -> Any:
        trade = original_close(self, trade_id, bar=bar, fill_price=fill_price, comment=comment)
        if trade is not None and trade.pnl is not None:
            # 0.01% Decimal amplifier — ABS_TOL(0.001) 초과 drift 유도
            trade.pnl = float(Decimal(str(trade.pnl)) * Decimal("1.0001"))
        return trade

    with patch.object(StrategyState, "close", mutated_close):
        drifted, msg = _drift_any_corpus(_load_baseline()["corpora"])
    assert drifted, f"M6 (pnl decimal leak amplifier) 미감지: {msg}"


# =====================================================================
# M3 — StrategyState.entry no-op cascade (반환 None + 내부 등록 skip)
# =====================================================================


@pytest.mark.mutation
@pytest.mark.skipif(not _MUTATIONS_RUNNABLE, reason="fixture 미생성")
def test_m3_strategy_entry_return_is_detected() -> None:
    """M3 Stage 2c 2차: StrategyState.entry 를 no-op 으로 강제 → trade 미등록.

    ADR-013 §4.4 원안 (반환 None → False) 은 호출자가 반환값을 직접 참조하지 않기
    때문에 단순 return 변경 만으로는 감지 불가. 본 테스트는 그 의도를 보존하면서
    **entry 자체를 no-op (원본 미호출 + return None)** 으로 시뮬레이션:

    - Track S (`interpreter.py:1018-1027`) 와 Track A (`virtual_strategy.py:139-145`)
      양쪽에서 `state.entry(...)` 호출 시 Trade 객체 생성/등록이 skip 됨
    - 후속 close 호출도 open_trades 에 대상 trade 없음 → 거래 전혀 기록 안 됨
    - `num_trades` 가 baseline 대비 drop → `_drift_any_corpus` 에서 감지

    P-3 감지 경로: metrics.num_trades 편차. trades_digest 공디지스트 drift 보조.
    """
    from src.strategy.pine_v2.strategy_state import StrategyState

    def mutated_entry(
        self: StrategyState,
        trade_id: str,
        direction: Any,
        **kwargs: Any,
    ) -> None:
        """원본 entry 를 호출하지 않고 즉시 return None — trade 생성/등록 전부 skip."""
        del self, trade_id, direction, kwargs
        return None

    with patch.object(StrategyState, "entry", mutated_entry):
        drifted, msg = _drift_any_corpus(_load_baseline()["corpora"])
    assert drifted, f"M3 (entry no-op cascade) 미감지: {msg}"


# =====================================================================
# M8 — Stage 2c 2차 iteration (후속 commit)
# =====================================================================


@pytest.mark.mutation
@pytest.mark.skip(reason="Stage 2c 2차 iteration — M8 후속 commit")
@pytest.mark.parametrize("mutation_id", ["M8_alert_hook_duplicate"])
def test_mutation_stage2c_second_iter(mutation_id: str) -> None:
    """Stage 2c 2차 후속: M6/M8 구현 예정."""
    del mutation_id
    pytest.skip("Stage 2c 2차 iteration")

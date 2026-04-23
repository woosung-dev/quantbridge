"""Trust Layer CI — 3-Layer Parity (P-1 / P-2 / P-3) + Mutation Oracle.

Path β Stage 2 실 구현 (2026-04-23). P-1 은 기존
`test_pynescript_baseline_parity.py` 로 위임, P-2 는 여기서 실 구현,
P-3 / Mutation / regen 은 fixture 생성 후 green (현재는 skipif).

**참조:**
- ADR-013: `docs/dev-log/013-trust-layer-ci-design.md`
- 아키텍처: `docs/04_architecture/trust-layer-architecture.md`
- 요구사항/SLO: `docs/01_requirements/trust-layer-requirements.md`

**구조 (ADR-013 §4):**

- **P-1** AST Shape Parity — `test_pynescript_baseline_parity.py` (types/nodes/edge_digest)
- **P-2** Coverage SSOT Sync — `coverage._TA_FUNCTIONS ∪ _UTILITY_FUNCTIONS == interpreter.STDLIB_NAMES`
- **P-3** Execution Golden — 6 corpus × `corpus_ohlcv_frozen.parquet` → metrics digest diff
- **Meta** Mutation Oracle — 8개 hand-crafted mutation, ≥ 7/8 포착 요구 (nightly)

**Stage 1 확정 결정 (Day 3 오픈 질문 답):**

| 질문 | 결정 | 근거 |
|---|---|---|
| Q1. Evaluator 병렬 vs 직렬 | **병렬** | Gate-0 에서 병렬 2중 blind 이미 성공적. 빠르고 편향 낮음 |
| Q2. Mutation oracle CI 포함 | **Nightly only** (`--run-mutations`) | CI 시간 예산 (≤3분) 초과 방지. 회귀는 main nightly 로 검증 |
| Q3. baseline_metrics.json 포맷 | **plain JSON** (no msgpack/pickle) | git diff 가능 → PR 리뷰 가치가 속도 절감보다 큼 |
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest

from src.strategy.pine_v2 import coverage as cov
from src.strategy.pine_v2.interpreter import STDLIB_NAMES
from tests.strategy.pine_v2._tolerance import (
    digest_sequence,
    normalize_decimal,
    within_tolerance,
)

# ---------------------------------------------------------------------
# Fixture paths (Stage 2 에서 실 값 채움)
# ---------------------------------------------------------------------
_CORPUS_DIR = Path(__file__).parents[2] / "fixtures" / "pine_corpus_v2"
_OHLCV_FROZEN = _CORPUS_DIR / "corpus_ohlcv_frozen.parquet"
_BASELINE_METRICS = _CORPUS_DIR / "baseline_metrics.json"

_BASELINE_PRESENT = _BASELINE_METRICS.exists() and _OHLCV_FROZEN.exists()

# i3_drfx 는 Sprint Y1 Coverage Analyzer 에서 is_runnable=false 로 reject
# → P-3 실행 대상 제외 (baseline 에 "note": "Skipped" 로만 기록)
RUNNABLE_CORPUS: tuple[str, ...] = (
    "s1_pbr",
    "s2_utbot",
    "s3_rsid",
    "i1_utbot",
    "i2_luxalgo",
)

# Mutation Oracle 8개 (ADR-013 §4.4). M3 는 Stage 2 실측 후 layer 재분류 (opus W2).
MUTATION_IDS: tuple[str, ...] = (
    "M1_sma_off_by_one",
    "M2_rsi_divzero_guard_removed",
    "M3_strategy_entry_return_none",
    "M4_crossover_boundary_geq",
    "M5_position_size_sign_flip",
    "M6_decimal_float_leak",
    "M7_persistent_rollback_missing",
    "M8_alert_hook_duplicate",
)


# =====================================================================
# P-1 AST Shape Parity — `test_pynescript_baseline_parity.py` 로 위임
# =====================================================================
# (Stage 2 에서 기존 파일에 edge_digest 검증 추가. 중복 방지로 본 파일엔 stub 없음.)


# =====================================================================
# P-2 Coverage SSOT Sync (리플렉션 기반 실 구현)
# =====================================================================


def test_p2_stdlib_names_equals_coverage_ta_plus_utility() -> None:
    """P-2: `interpreter.STDLIB_NAMES == coverage._TA_FUNCTIONS | coverage._UTILITY_FUNCTIONS`.

    양방향 strict equality. 이 하나로 다음 두 실패 시나리오 모두 감지:

    1. "stdlib 에 새 함수 추가 + coverage.py 갱신 누락"
       → STDLIB_NAMES 에는 있으나 coverage 에 없음 → 좌 ⊄ 우 → FAIL
       → 사용자가 parse_preview 경고 못 봄 (whack-a-mole 재발)

    2. "coverage.py 에는 있는데 stdlib 구현 삭제"
       → coverage 에는 있으나 STDLIB_NAMES 에 없음 → 우 ⊄ 좌 → FAIL
       → 런타임 NotImplementedError

    SSOT 동기화 규약 (ADR-016 §5): stdlib.py / interpreter.STDLIB_NAMES /
    coverage._TA_FUNCTIONS 3곳을 **동시 갱신** 의무.
    """
    coverage_side = cov._TA_FUNCTIONS | cov._UTILITY_FUNCTIONS
    extra_in_interpreter = STDLIB_NAMES - coverage_side
    extra_in_coverage = coverage_side - STDLIB_NAMES

    assert extra_in_interpreter == frozenset(), (
        f"interpreter.STDLIB_NAMES 에는 있으나 coverage.py 에 누락된 함수: "
        f"{sorted(extra_in_interpreter)}. "
        "coverage.py 의 _TA_FUNCTIONS / _UTILITY_FUNCTIONS 에 추가하세요. "
        "사용자가 parse_preview 에서 경고를 못 보는 whack-a-mole 재발 위험."
    )
    assert extra_in_coverage == frozenset(), (
        f"coverage.py 에는 있으나 interpreter.STDLIB_NAMES 에 누락된 함수: "
        f"{sorted(extra_in_coverage)}. "
        "interpreter.STDLIB_NAMES (모듈 top-level frozenset) 에 추가하세요. "
        "런타임 NotImplementedError 위험."
    )


def test_p2_coverage_strategy_functions_match_spec() -> None:
    """P-2: `coverage._STRATEGY_FUNCTIONS` 가 4개 핵심 호출 (entry/close/close_all/exit).

    interpreter 의 `_exec_strategy_call` 및 관련 핸들러가 이 4 함수를 처리.
    새로운 strategy.* 함수 추가 시 (예: strategy.cancel) 여기도 갱신 필요.
    """
    expected = frozenset(
        {
            "strategy.entry",
            "strategy.close",
            "strategy.close_all",
            "strategy.exit",
        }
    )
    assert expected == cov._STRATEGY_FUNCTIONS, (
        f"strategy.* 함수 드리프트: "
        f"코드 {sorted(cov._STRATEGY_FUNCTIONS)} vs 스펙 {sorted(expected)}"
    )


def test_p2_supported_functions_union_consistency() -> None:
    """P-2: `SUPPORTED_FUNCTIONS` 가 9개 하위 그룹 합집합과 일치.

    coverage.py 의 내부 그룹 frozenset 들을 `|` 한 결과가 SUPPORTED_FUNCTIONS.
    그룹 추가/삭제 시 합집합 재계산 누락 방지.
    """
    expected_union = (
        cov._TA_FUNCTIONS
        | cov._UTILITY_FUNCTIONS
        | cov._STRATEGY_FUNCTIONS
        | cov._DECLARATION_FUNCTIONS
        | cov._PLOT_FUNCTIONS
        | cov._INPUT_FUNCTIONS
        | cov._STRING_FUNCTIONS
        | cov._MATH_FUNCTIONS
        | cov._V4_ALIASES
    )
    assert expected_union == cov.SUPPORTED_FUNCTIONS, (
        "SUPPORTED_FUNCTIONS 가 9 하위 그룹 합집합과 불일치. "
        "coverage.py 의 그룹 정의와 최종 변수 선언 재확인 필요."
    )


def test_p2_supported_attributes_union_consistency() -> None:
    """P-2: `SUPPORTED_ATTRIBUTES` 가 3 그룹 합집합 (series + strategy_attrs + syminfo).

    Enum 상수 (color.*, shape.* 등) 는 is_supported_attribute 내 prefix 검사 경로
    로 처리. 본 테스트는 fixed attribute set 만 검증.
    """
    expected_union = cov._SERIES_ATTRS | cov._STRATEGY_ATTRS | cov._SYMINFO_ATTRS
    assert expected_union == cov.SUPPORTED_ATTRIBUTES, (
        "SUPPORTED_ATTRIBUTES 가 3 하위 그룹 합집합과 불일치."
    )


# =====================================================================
# P-3 Execution Golden (metrics digest diff) — fixture 생성 후 활성
# =====================================================================


def _load_frozen_ohlcv() -> pd.DataFrame:
    """고정 parquet → DataFrame (engine 계약)."""
    df = pd.read_parquet(_OHLCV_FROZEN)
    if "timestamp" in df.columns:
        df = df.set_index("timestamp")
    return df


def _extract_trades_and_runtime(
    source: str, ohlcv_df: pd.DataFrame
) -> tuple[list[dict[str, Any]], dict[str, Any], list[str]]:
    """corpus 실행 → (trades_as_dicts, var_series, warnings). regen 스크립트 동일 로직."""
    from src.backtest.engine.v2_adapter import run_backtest_v2
    from src.strategy.pine_v2.compat import parse_and_run_v2

    outcome = run_backtest_v2(source, ohlcv_df)
    if outcome.status != "ok" or outcome.result is None:
        raise RuntimeError(f"run_backtest_v2 failed: status={outcome.status} error={outcome.error}")

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

    # var_series + warnings 는 parse_and_run_v2 재호출 (ADR-013 §4.3)
    v2 = parse_and_run_v2(source, ohlcv_df, strict=False)
    var_series: dict[str, Any] = {}
    warnings: list[str] = []
    if v2.historical is not None:
        var_series = dict(v2.historical.var_series or {})
        if v2.historical.strategy_state is not None:
            warnings = list(getattr(v2.historical.strategy_state, "warnings", []) or [])
    elif v2.virtual is not None:
        var_series = dict(getattr(v2.virtual, "var_series", {}) or {})
        state = getattr(v2.virtual, "strategy_state", None)
        if state is not None:
            warnings = list(getattr(state, "warnings", []) or [])
        else:
            warnings = list(getattr(v2.virtual, "warnings", []) or [])

    return trades, var_series, warnings


_DECIMAL_METRIC_KEYS = (
    "total_return",
    "sharpe_ratio",
    "max_drawdown",
    "win_rate",
    "profit_factor",
    "sortino_ratio",
    "calmar_ratio",
    "avg_win",
    "avg_loss",
)
_INT_METRIC_KEYS = ("num_trades", "long_count", "short_count")


@pytest.mark.skipif(
    not _BASELINE_PRESENT,
    reason="Stage 2 fixtures 미생성 (baseline_metrics.json / corpus_ohlcv_frozen.parquet)",
)
@pytest.mark.parametrize("corpus_id", RUNNABLE_CORPUS)
def test_p3_execution_metrics_match_golden(corpus_id: str) -> None:
    """P-3: 6 corpus × corpus_ohlcv_frozen.parquet → metrics + digests baseline 일치.

    stdlib/interpreter/strategy_state 의 숫자 편차를 CI 에서 감지.
    허용 오차 = max(절대 0.001, 상대 0.1%) per ADR-013 §4.3.
    """
    from src.backtest.engine.v2_adapter import run_backtest_v2

    baseline = json.loads(_BASELINE_METRICS.read_text())
    expected = baseline["corpora"].get(corpus_id, {})
    assert "metrics" in expected, (
        f"{corpus_id}: baseline 에 metrics 누락 (skip/error 상태). "
        "scripts/regen_trust_layer_baseline.py --confirm 로 재생성."
    )

    source = (_CORPUS_DIR / f"{corpus_id}.pine").read_text()
    ohlcv_df = _load_frozen_ohlcv()

    outcome = run_backtest_v2(source, ohlcv_df)
    assert outcome.status == "ok" and outcome.result is not None, (
        f"{corpus_id}: run_backtest_v2 status={outcome.status} error={outcome.error}"
    )

    actual = outcome.result.metrics
    expected_m = expected["metrics"]

    # Decimal metric 비교
    for key in _DECIMAL_METRIC_KEYS:
        actual_val = getattr(actual, key)
        expected_val = expected_m.get(key)
        if expected_val is None:
            is_none_like = actual_val is None or (
                hasattr(actual_val, "is_nan") and actual_val.is_nan()
            )
            assert is_none_like, f"{corpus_id}.{key}: baseline=None 이지만 actual={actual_val}"
        else:
            assert actual_val is not None, (
                f"{corpus_id}.{key}: actual=None, baseline={expected_val}"
            )
            assert within_tolerance(actual_val, expected_val), (
                f"{corpus_id}.{key}: 드리프트\n"
                f"  actual={normalize_decimal(actual_val)} baseline={expected_val}\n"
                "의도된 변경이면 regen_trust_layer_baseline.py --confirm 실행."
            )

    # Integer metric 비교
    for key in _INT_METRIC_KEYS:
        actual_val = getattr(actual, key)
        expected_val = expected_m.get(key, 0)
        if actual_val is None:
            actual_val = 0
        assert actual_val == expected_val, (
            f"{corpus_id}.{key}: expected={expected_val} actual={actual_val}"
        )

    # Digest 비교 (길이 독립 fingerprint)
    trades, var_series, warnings = _extract_trades_and_runtime(source, ohlcv_df)
    actual_trades_digest = digest_sequence(trades)
    actual_var_series_digest = digest_sequence(var_series)
    actual_warnings_digest = digest_sequence(warnings)

    assert actual_trades_digest == expected["trades_digest"], (
        f"{corpus_id}: trades digest drift\n"
        f"  actual={actual_trades_digest}\n"
        f"  baseline={expected['trades_digest']}"
    )
    assert actual_var_series_digest == expected["var_series_digest"], (
        f"{corpus_id}: var_series digest drift\n"
        f"  actual={actual_var_series_digest}\n"
        f"  baseline={expected['var_series_digest']}"
    )
    assert actual_warnings_digest == expected["warnings_digest"], (
        f"{corpus_id}: warnings digest drift\n"
        f"  actual={actual_warnings_digest}\n"
        f"  baseline={expected['warnings_digest']}"
    )


@pytest.mark.skipif(
    not _BASELINE_PRESENT,
    reason="Stage 2 fixtures 미생성",
)
def test_p3_i3_drfx_is_skipped_in_baseline() -> None:
    """P-3 부록: i3_drfx 는 baseline 에 Skipped note 만 포함 (Y1 Coverage reject)."""
    baseline = json.loads(_BASELINE_METRICS.read_text())
    i3 = baseline["corpora"].get("i3_drfx", {})
    assert "note" in i3, "i3_drfx baseline 에 'note' 필드 필요"
    assert i3["note"].startswith("Skipped"), (
        f"i3_drfx.note 는 'Skipped' 로 시작해야 함, got: {i3['note']!r}"
    )
    assert "metrics" not in i3, "i3_drfx 는 metrics 없어야 함 (Y1 reject)"


# =====================================================================
# Mutation Oracle (메타 게이트, nightly only)
# =====================================================================


@pytest.mark.skip(reason="Mutation oracle 은 nightly workflow 또는 `pytest --run-mutations` 수동")
@pytest.mark.parametrize("mutation_id", MUTATION_IDS)
def test_mutation_is_detected_by_some_parity_layer(mutation_id: str) -> None:
    """Mutation Oracle: 각 mutation 이 P-1/2/3 중 **최소 1 layer** 에 의해 포착된다."""
    del mutation_id
    pytest.skip("Mutation oracle — nightly only (Stage 2 후속)")


# =====================================================================
# Baseline regen 스크립트 게이트 (TL-E-6)
# =====================================================================


_REGEN_SCRIPT = Path(__file__).parents[3] / "scripts" / "regen_trust_layer_baseline.py"


@pytest.mark.skipif(not _REGEN_SCRIPT.exists(), reason="regen_trust_layer_baseline.py 미생성")
def test_regen_script_without_confirm_fails() -> None:
    """`regen_trust_layer_baseline.py` 가 `--confirm` 없이 호출되면 exit code != 0.

    SLO TL-E-6 (requirements §3.1 Hard Block) — 오남용 방지 게이트.
    """
    import shutil
    import subprocess
    import sys

    # sys.executable 을 사용해 현재 venv python 으로 실행 (shell 우회, S603 안전)
    py = sys.executable or shutil.which("python") or "python"
    result = subprocess.run(
        [py, str(_REGEN_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=_REGEN_SCRIPT.parents[1],  # backend/
        timeout=30,
    )
    assert result.returncode != 0, (
        f"--confirm 없이 호출했는데 성공함: returncode={result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "--confirm" in result.stderr, f"에러 메시지에 '--confirm' 힌트 누락: {result.stderr}"

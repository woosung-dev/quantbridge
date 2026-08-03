"""Trust Layer CI — 3-Layer Parity (P-1 / P-2 / P-3) + Mutation Oracle.

Path β Stage 2 실 구현 (2026-04-23). P-1 은 기존
`test_pynescript_baseline_parity.py` 로 위임, P-2 는 여기서 실 구현,
P-3 / Mutation / regen 은 fixture 생성 후 green (현재는 skipif).

**참조:**
- ADR-020: `docs/decisions/020-trust-layer-ci-design.md`
- 아키텍처: `docs/reference/architecture/trust-layer-architecture.md`
- 당시 요구사항/SLO: `docs/archive/product/requirements/2026-04-23-trust-layer-requirements.md`

**구조 (ADR-020 §4):**

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
from tests.strategy.pine_v2._corpus import RUNNABLE_CORPUS as _RUNNABLE_CORPUS
from tests.strategy.pine_v2._corpus import SKIPPED_CORPUS as _SKIPPED_CORPUS
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

# ★목록은 `_corpus.py` 하나뿐이다 — regen 스크립트와 mutation oracle 도 같은 것을 읽는다
#   ([BL-588]). 예전엔 세 곳에 따로 적혀 있었고 그중 하나가 5벌에서 멈춰 있었다.
RUNNABLE_CORPUS = _RUNNABLE_CORPUS

# Mutation Oracle 8개 (ADR-020 §4.4). M3 는 Stage 2 실측 후 layer 재분류 (opus W2).
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
    """P-2: `SUPPORTED_FUNCTIONS` 가 하위 그룹 합집합과 일치.

    coverage.py 의 내부 그룹 frozenset 들을 `|` 한 결과가 SUPPORTED_FUNCTIONS.
    그룹 추가/삭제 시 합집합 재계산 누락 방지.

    Sprint 29 Slice A: _SECURITY_FUNCTIONS + _HEIKINASHI_FUNCTIONS 추가 (12그룹).
    G2 (2026-07-12 pine-batch QA): _ARRAY_FUNCTIONS 추가 (13그룹).
    """
    expected_union = (
        cov._TA_FUNCTIONS
        | cov._UTILITY_FUNCTIONS
        | cov._STRATEGY_FUNCTIONS
        | cov._DECLARATION_FUNCTIONS
        | cov._PLOT_FUNCTIONS
        | cov._RENDERING_METHODS
        | cov._INPUT_FUNCTIONS
        | cov._STRING_FUNCTIONS
        | cov._MATH_FUNCTIONS
        | cov._V4_ALIASES
        | cov._SECURITY_FUNCTIONS  # Sprint 29 Slice A
        | cov._HEIKINASHI_FUNCTIONS  # Sprint 29 Slice A (a)
        | cov._ARRAY_FUNCTIONS  # G2 (2026-07-12): array.* 최소 서브셋 (_names SSOT)
    )
    assert expected_union == cov.SUPPORTED_FUNCTIONS, (
        "SUPPORTED_FUNCTIONS 가 13 하위 그룹 합집합과 불일치. "
        "coverage.py 의 그룹 정의와 최종 변수 선언 재확인 필요."
    )


def test_p2_supported_attributes_union_consistency() -> None:
    """P-2: `SUPPORTED_ATTRIBUTES` 가 6 그룹 합집합.

    Series + strategy_attrs + syminfo + (Sprint 21) currency / strategy_extra / timeframe
    explicit constant sets. Enum 상수 (color.*, shape.* 등) 는 is_supported_attribute
    내 prefix 검사 경로로 처리.

    Sprint 21 (codex G.0 P1 #3): currency./strategy./timeframe. 의 prefix 추가는
    false-pass risk → explicit set 만 union. 본 test 는 SSOT 의무.
    """
    expected_union = (
        cov._SERIES_ATTRS | cov._STRATEGY_ATTRS | cov._SYMINFO_ATTRS
        | cov._CURRENCY_CONSTANTS | cov._STRATEGY_CONSTANTS_EXTRA | cov._TIMEFRAME_CONSTANTS
    )
    assert expected_union == cov.SUPPORTED_ATTRIBUTES, (
        "SUPPORTED_ATTRIBUTES 가 6 하위 그룹 합집합과 불일치 "
        "(Sprint 21 신규 constant sets 동기화 누락 가능)."
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

    # var_series + warnings 는 parse_and_run_v2 재호출 (ADR-020 §4.3)
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
# 문자열 metric — 오차 개념이 없으므로 exact 비교. `sharpe_ratio` 는 degenerate 실행에서
# 전부 0 이라 값 채널만으로는 컨벤션 뒤집힘(monthly ↔ daily ↔ unavailable ↔
# unavailable_nonpositive_equity)이 diff 0 이다. 착수 전 실측 — `sharpe_ratio` 가
# `unavailable_nonpositive_equity` 대신 `unavailable` 을 돌려주게 변조해도 이 파일은
# 16 passed 로 green 이었다(전용 단위 테스트 `test_metrics_nonpositive_equity.py` 는 red).
# 즉 구멍은 컨벤션 자체가 아니라 **엔드투엔드 코퍼스 회귀망의 채널 부재**였다.
_STR_METRIC_KEYS = ("sharpe_convention",)

# ★`regen_trust_layer_baseline.py` 의 `"schema_version": 2` 와 **쌍**이다. 한쪽만 올리면
#   아래 envelope 검사가 red 로 알려준다 — 그게 이 상수를 여기 두는 이유다.
_EXPECTED_SCHEMA_VERSION = 2


@pytest.mark.skipif(
    not _BASELINE_PRESENT,
    reason="Stage 2 fixtures 미생성 (baseline_metrics.json / corpus_ohlcv_frozen.parquet)",
)
@pytest.mark.parametrize("corpus_id", RUNNABLE_CORPUS)
def test_p3_execution_metrics_match_golden(corpus_id: str) -> None:
    """P-3: 6 corpus × corpus_ohlcv_frozen.parquet → metrics + digests baseline 일치.

    stdlib/interpreter/strategy_state 의 숫자 편차를 CI 에서 감지.
    허용 오차 = max(절대 0.001, 상대 0.1%) per ADR-020 §4.3.
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

    # 문자열 metric 비교 (exact)
    # ★`_INT_METRIC_KEYS` 루프처럼 `.get(key, <기본값>)` 을 쓰지 않는다 — 그러면 regen
    #   누락으로 baseline 에 키가 없을 때 "기본값 == 기본값" 으로 조용히 통과한다.
    #   키 부재는 통과가 아니라 실패다.
    for key in _STR_METRIC_KEYS:
        assert key in expected_m, (
            f"{corpus_id}.{key}: baseline 에 키 없음 (schema_version 2 미만). "
            "scripts/regen_trust_layer_baseline.py --confirm 로 재생성."
        )
        actual_val = getattr(actual, key)
        expected_val = expected_m[key]
        assert actual_val == expected_val, (
            f"{corpus_id}.{key}: 컨벤션 드리프트\n"
            f"  actual={actual_val!r} baseline={expected_val!r}\n"
            "의도된 변경이면 regen_trust_layer_baseline.py --confirm 실행."
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


# metric 범위 가정 (opus Gate-1 W-2 / Gate-2 M-2)
# _tolerance.py docstring 이 `[1e-4, 1e1]` 가정 → 실측 baseline 이 이 범위 안인지 검증.
# 범위 초과 시 ABS_TOL/REL_TOL 재정규화 의무 신호.
_METRIC_RANGE_MIN = 1e-4  # 절대값 이하는 precision 28 에서 안전
_METRIC_RANGE_MAX = 1e2  # 절대값 이 이상이면 REL_TOL 0.1% 가 과민반응
# 주의: max_drawdown 은 음수이나 절대값만 체크. total_return 도 손실이면 음수.


@pytest.mark.skipif(
    not _BASELINE_PRESENT,
    reason="Stage 2 fixtures 미생성",
)
@pytest.mark.parametrize("corpus_id", RUNNABLE_CORPUS)
def test_p3_baseline_metric_range_sanity(corpus_id: str) -> None:
    """P-3 sanity (opus Gate-2 M-2): baseline Decimal metric 절대값이 허용 범위.

    `_tolerance.py` docstring 이 metric 범위를 `[1e-4, 1e1]` 로 가정하지만
    실측 분포가 이 경계에 근접 (예: max_drawdown=-7.75 는 78% 경계). 범위를
    **[1e-4, 1e2]** 로 완화하되 그래도 초과 시 assert fail 하여 `_tolerance.py`
    ABS_TOL/REL_TOL 재정규화 PR 의무를 트리거.

    정수 metric (num_trades, long_count, short_count), None 값은 스킵.
    0 값은 범위 체크 통과 (within_tolerance 의 abs 경로로 처리).
    """
    from decimal import Decimal

    baseline = json.loads(_BASELINE_METRICS.read_text())
    corpus = baseline["corpora"].get(corpus_id, {})
    metrics = corpus.get("metrics")
    assert metrics is not None, (
        f"{corpus_id}: baseline metrics 누락 — regen 필요"
    )

    for key in _DECIMAL_METRIC_KEYS:
        value_str = metrics.get(key)
        if value_str is None:
            continue
        value = abs(Decimal(value_str))
        if value == 0:
            continue
        assert value >= Decimal(str(_METRIC_RANGE_MIN)), (
            f"{corpus_id}.{key}={value_str} 절대값 < {_METRIC_RANGE_MIN}. "
            "precision 28 에서 유효숫자 부족 가능 — _tolerance.py ABS_TOL 재검토."
        )
        assert value <= Decimal(str(_METRIC_RANGE_MAX)), (
            f"{corpus_id}.{key}={value_str} 절대값 > {_METRIC_RANGE_MAX}. "
            "REL_TOL 0.1% 가 과민반응 가능 — _tolerance.py REL_TOL 완화 또는 "
            "해당 metric 정규화 (예: total_return 을 백분율 대신 비율로) 재검토."
        )


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


# ---------------------------------------------------------------------
# 정답지 envelope — [BL-585] 값이 있는데 읽는 곳이 없었다
# ---------------------------------------------------------------------
#
# `ohlcv_sha256` / `schema_version` / `tool_versions.python` 은 regen 스크립트가 **쓰기만**
# 하고 레포 어디서도 읽지 않았다(실측 grep 0곳). 그래서 런타임이 3.12 -> 3.13 으로
# 드리프트하는 동안 아무도 몰랐고, CI 가 재현 못 하는 baseline 이 만들어졌다([BL-587]).
#
# ★★red 를 「회귀」로 읽지 마라. 아래 세 assert 는 **숫자가 틀렸다**고 말하는 게 아니라
#   **이 정답지가 다른 세계에서 만들어졌다**고 말한다. 그래서 조치는 "코드를 고쳐라" 가
#   아니라 "regen 하고 값이 그대로인지 확인해라" 다. 이 구분을 메시지에 박아두지 않으면
#   다음 사람이 baseline 의 숫자를 손으로 고친다(이 파일이 막으려는 바로 그 행위다).
_ENVELOPE_RED_MEANS = (
    "\n★이것은 회귀가 아니다 — 정답지가 **다른 환경에서** 만들어졌다는 뜻이다.\n"
    "  조치: `uv run python scripts/regen_trust_layer_baseline.py --confirm` 로 재생성한 뒤\n"
    "        `git diff` 로 **corpora 숫자가 그대로인지** 확인해라.\n"
    "  ★baseline 의 값을 손으로 고치지 마라. 그건 이 회귀망을 무력화하는 것이다."
)


@pytest.mark.skipif(not _BASELINE_PRESENT, reason="Stage 2 fixtures 미생성")
def test_envelope_ohlcv_sha256_matches_frozen_parquet() -> None:
    """정답지가 선언한 입력 해시가 실제 코퍼스 parquet 과 같은가.

    다르면 정답지와 입력이 짝이 아니다 — 숫자 비교 전체가 무의미해진다.
    """
    import hashlib

    hasher = hashlib.sha256()
    with _OHLCV_FROZEN.open("rb") as fp:
        for chunk in iter(lambda: fp.read(65536), b""):
            hasher.update(chunk)
    actual = hasher.hexdigest()

    declared = json.loads(_BASELINE_METRICS.read_text()).get("ohlcv_sha256")
    assert declared == actual, (
        f"입력 코퍼스가 정답지와 짝이 아니다.\n"
        f"  baseline_metrics.json: {declared}\n"
        f"  corpus_ohlcv_frozen.parquet 실측: {actual}{_ENVELOPE_RED_MEANS}"
    )


@pytest.mark.skipif(not _BASELINE_PRESENT, reason="Stage 2 fixtures 미생성")
def test_envelope_schema_version_is_current() -> None:
    """정답지 스키마 버전이 이 테스트가 아는 버전인가.

    ★`_STR_METRIC_KEYS` 대조(:347)가 "schema_version 2 미만" 을 이미 전제한다. 전제를
    선언만 하고 검사하지 않으면 낡은 정답지에서 그 대조가 조용히 안 돈다.
    """
    declared = json.loads(_BASELINE_METRICS.read_text()).get("schema_version")
    assert declared == _EXPECTED_SCHEMA_VERSION, (
        f"정답지 schema_version={declared!r}, 이 테스트가 아는 버전={_EXPECTED_SCHEMA_VERSION}."
        f"{_ENVELOPE_RED_MEANS}"
    )


@pytest.mark.skipif(not _BASELINE_PRESENT, reason="Stage 2 fixtures 미생성")
def test_envelope_python_minor_matches_runtime() -> None:
    """정답지를 만든 python minor 가 지금 도는 런타임과 같은가.

    ★[BL-587] 이 이 채널의 부재로 생겼다 — `requires-python = ">=3.12"` 만 있고 핀이 없어
    워크트리 bootstrap 의 `uv sync` 가 3.13 을 집었고, CI(3.12)가 재현 못 하는 baseline 이
    만들어졌다. 원인 차단은 `backend/.python-version`, 이 assert 는 **그 핀이 풀렸을 때의
    탐지기**다. 둘 다 필요하다.
    """
    import sys as _sys

    runtime = f"{_sys.version_info.major}.{_sys.version_info.minor}"
    declared = json.loads(_BASELINE_METRICS.read_text()).get("tool_versions", {}).get("python")
    assert declared == runtime, (
        f"정답지는 python {declared} 에서, 지금 스위트는 python {runtime} 에서 돈다.\n"
        f"  ★핀은 `backend/.python-version` 이다 — 풀렸는지 먼저 봐라.{_ENVELOPE_RED_MEANS}"
    )


@pytest.mark.skipif(not _BASELINE_PRESENT, reason="Stage 2 fixtures 미생성")
def test_envelope_corpus_set_is_exactly_the_canonical_list() -> None:
    """정답지에 실린 코퍼스 집합이 정본 목록과 **정확히** 같은가.

    ★[BL-588] — 이 불변식은 원래 `baseline_metrics.schema.json` 의
    `minProperties/maxProperties: 8` 에만 있었는데, **그 스키마는 어디서도 로드되지
    않았다**(레포 전체 `jsonschema` import 0건). 스키마를 지우면서 유일하게 중복이
    아니었던 이 검사를 평범한 assert 로 옮겨 왔고, 개수가 아니라 **키 집합**을 본다 —
    한 벌이 빠지고 다른 한 벌이 들어와도 개수는 8 그대로다.

    빠지면 그 코퍼스의 회귀는 **조용히** 감시 대상에서 사라진다.
    """
    declared = set(json.loads(_BASELINE_METRICS.read_text()).get("corpora", {}))
    canonical = set(RUNNABLE_CORPUS) | set(_SKIPPED_CORPUS)
    assert declared == canonical, (
        f"정답지 코퍼스 집합이 정본과 다르다.\n"
        f"  정답지에만: {sorted(declared - canonical)}\n"
        f"  정본에만:   {sorted(canonical - declared)}{_ENVELOPE_RED_MEANS}"
    )

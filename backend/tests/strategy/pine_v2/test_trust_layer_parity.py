"""Trust Layer CI — 3-Layer Parity (P-1 / P-2 / P-3) + Mutation Oracle 스켈레톤.

Path β Stage 1 산출물 (2026-04-23 작성). Stage 2 에서 실제 구현.

**참조:**
- ADR-013: `docs/dev-log/013-trust-layer-ci-design.md`
- 아키텍처: `docs/04_architecture/trust-layer-architecture.md`
- 요구사항/SLO: `docs/01_requirements/trust-layer-requirements.md`

**구조 (ADR-013 §4):**

- **P-1** AST Shape Parity — 부모-자식 edge digest (기존 `baseline.json` 확장)
- **P-2** Coverage SSOT Sync — `coverage.SUPPORTED_*` ⟺ `stdlib/interpreter` 리플렉션
- **P-3** Execution Golden — 6 corpus × `corpus_ohlcv_frozen.parquet` → metrics digest diff
- **Meta** Mutation Oracle — 8개 hand-crafted mutation, ≥ 7/8 포착 요구 (nightly)

본 파일은 **스켈레톤** — pytest.skip 으로 collection error 없이 실행 가능하되
실제 검증 로직은 Stage 2 에서 채운다. Gate-1 (codex + opus 2중 blind) 는
본 스켈레톤의 **계약 (함수 시그니처 + docstring + 마커)** 을 대상으로 평가.

**Stage 1 확정 결정 (Day 3 오픈 질문 답):**

| 질문 | 결정 | 근거 |
|---|---|---|
| Q1. Evaluator 병렬 vs 직렬 | **병렬** | Gate-0 에서 병렬 2중 blind 이미 성공적. 빠르고 편향 낮음 |
| Q2. Mutation oracle CI 포함 | **Nightly only** (`--run-mutations`) | CI 시간 예산 (≤3분) 초과 방지. 회귀는 main nightly 로 검증 |
| Q3. baseline_metrics.json 포맷 | **plain JSON** (no msgpack/pickle) | git diff 가능 → PR 리뷰 가치가 속도 절감보다 큼 |
"""
from __future__ import annotations

from pathlib import Path

import pytest

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

# Mutation Oracle 8개 (ADR-013 §4.4)
# M3 (strategy.entry 반환값) 의 최종 layer 분류는 Stage 2 실측 후 확정
# (opus Gate-0 W2 반영 — 현재는 "P-2 or P-3" 로 유보)
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
# P-1 AST Shape Parity (edge digest 확장)
# =====================================================================


@pytest.mark.parametrize("script_name", sorted(RUNNABLE_CORPUS + ("i3_drfx",)))
def test_p1_ast_edge_digest_matches_baseline(script_name: str) -> None:
    """P-1: pynescript AST 의 부모-자식 edge digest 가 baseline.json 과 일치한다.

    기존 `test_pynescript_baseline_parity.py` 는 노드 수 + 타입 히스토그램만 검증.
    Stage 2 에서 `parent_qualname → child_qualname` 쌍 정렬 튜플의 sha256 을
    `baseline.json[script_name]["edge_digest"]` 로 추가 비교.

    감지 대상:
    - pynescript 버전 업그레이드 시 AST 구조 변경
    - corpus .pine 파일 의도치 않은 수정

    Stage 2 구현 예정.
    """
    del script_name  # Stage 1 stub — Stage 2 에서 사용
    pytest.skip("Stage 2 구현 예정 (P-1 edge digest)")


# =====================================================================
# P-2 Coverage SSOT Sync (리플렉션 기반)
# =====================================================================


def test_p2_supported_functions_are_all_bound() -> None:
    """P-2 (→): `coverage.SUPPORTED_FUNCTIONS` 의 모든 원소가 실제 구현과 매핑.

    Stage 2 — 실측된 실체 (codex Gate-1 W-C1 반영, TA_CALLABLES 는 존재하지 않음):

    - **SSOT**: `interpreter._STDLIB_NAMES` (set, interpreter.py:684~) — 실제 dispatch 대상
    - **Dispatch**: `stdlib.StdlibDispatcher.call()` (stdlib.py:538) 의 if-elif 체인
    - **NOP 핸들러**: `interpreter._handle_plot_nop / _handle_alert / _handle_input` 등
    - **리플렉션 방식**: `_STDLIB_NAMES` 를 SSOT 로 사용하거나, `StdlibDispatcher.call`
      소스를 AST 파싱하여 dispatch 케이스 추출 (Stage 2 에서 둘 중 택1 결정)

    양방향 assertion 중 정방향:
        `cov.SUPPORTED_FUNCTIONS ⊆ {_STDLIB_NAMES ∪ NOP 허용 목록}`

    잡는 것: "coverage.py 에는 있는데 stdlib 구현 삭제" → 런타임 NotImplementedError
    """
    pytest.skip("Stage 2 구현 예정 (P-2 forward direction)")


def test_p2_all_bindings_are_in_supported() -> None:
    """P-2 (←): 실제 구현된 stdlib 함수는 모두 `SUPPORTED_FUNCTIONS` 에 등재.

    Stage 2: `{_STDLIB_NAMES ∪ NOP} ⊆ cov.SUPPORTED_FUNCTIONS` (codex W-C1 반영).

    잡는 것: "stdlib 에 새 함수 추가 + coverage.py 갱신 누락"
    → 사용자가 parse_preview 에서 경고 못 봄 (whack-a-mole 재발)
    """
    pytest.skip("Stage 2 구현 예정 (P-2 reverse direction)")


def test_p2_supported_attributes_bidirectional() -> None:
    """P-2: `SUPPORTED_ATTRIBUTES` 도 양방향 동기화.

    `interpreter._eval_attribute` 분기와 매치. 시계열 / strategy state / syminfo /
    barstate 카테고리 모두 동일 규칙.

    Stage 2 구현 예정.
    """
    pytest.skip("Stage 2 구현 예정 (P-2 attributes)")


# =====================================================================
# P-3 Execution Golden (metrics digest diff)
# =====================================================================


@pytest.mark.skipif(
    not _BASELINE_PRESENT,
    reason="Stage 2 fixtures 미생성 (baseline_metrics.json / corpus_ohlcv_frozen.parquet)",
)
@pytest.mark.parametrize("corpus_id", RUNNABLE_CORPUS)
def test_p3_execution_metrics_match_golden(corpus_id: str) -> None:
    """P-3: 6 corpus × `corpus_ohlcv_frozen.parquet` → metrics digest 가 baseline 과 일치.

    Stage 2 실행 단계:
    1. `run_backtest_v2(corpus_source, ohlcv_frozen)` → `BacktestOutcome`
    2. outcome.metrics 를 baseline_metrics.json[corpus_id].metrics 와 비교
       - 허용 오차: `_tolerance.within_tolerance(...)` (max 절대 1e-3 / 상대 1e-3)
    3. `var_series` / `trades` / `warnings` 는 sha256 digest 로 비교 (길이 독립)
    4. 실패 시 artifact 로 전체 dump 업로드 (GitHub Actions upload-artifact)

    Decimal-first 엄수: 모든 중간 값 `Decimal(str(x))` 로 변환. float 금지.

    Stage 2 구현 예정.
    """
    del corpus_id  # Stage 1 stub
    pytest.skip("Stage 2 구현 예정 (P-3 execution golden)")


@pytest.mark.skipif(
    not _BASELINE_PRESENT,
    reason="Stage 2 fixtures 미생성",
)
def test_p3_i3_drfx_is_skipped_in_baseline() -> None:
    """P-3 부록: i3_drfx 는 baseline 에 `{"note": "Skipped — is_runnable=false"}` 기록만.

    Sprint Y1 Coverage Analyzer 에서 ta.supertrend / tostring / request.security 등
    미지원 → 422 reject. Trust Layer P-3 대상에서도 자연스럽게 제외.

    baseline 스키마 정합성 확인용.

    Stage 2 구현 예정.
    """
    pytest.skip("Stage 2 구현 예정 (P-3 skip semantics)")


# =====================================================================
# Mutation Oracle (메타 게이트, nightly only)
# =====================================================================


@pytest.mark.skip(reason="Mutation oracle 은 nightly workflow 또는 `pytest --run-mutations` 수동")
@pytest.mark.parametrize("mutation_id", MUTATION_IDS)
def test_mutation_is_detected_by_some_parity_layer(mutation_id: str) -> None:
    """Mutation Oracle: 각 mutation 이 P-1/2/3 중 **최소 1 layer** 에 의해 포착된다.

    Stage 2 실행 단계 (nightly):
    1. 해당 mutation 을 pine_v2 구현에 inject (subprocess 에서 isolated venv)
    2. P-1/2/3 테스트 실행
    3. 하나라도 fail 하면 "포착 성공"
    4. 8 개 중 ≥ 7 개 성공 필요 (SLO TL-E-5)

    Layer 별 포착 예상:
    - M1 (sma off-by-one) → P-3 (total_return drift)
    - M2 (rsi divzero) → P-3 (corpus 실행 실패 또는 NaN leak)
    - M3 (strategy.entry return) → P-2 or P-3 (Stage 2 실측 후 재분류; opus Gate-0 W2)
    - M4 (crossover >=) → P-3 (trade 발생 시점 shift)
    - M5 (position_size 부호) → P-3 (trades_digest 변화)
    - M6 (Decimal → float leak) → P-3 (상대 오차 >0.001% 확대)
    - M7 (persistent rollback 누락) → P-3 (var_series_digest 변화)
    - M8 (alert 중복 hook) → P-3 (trade 수 2배 + trades_digest 변화)

    Stage 2 구현 예정.
    """
    del mutation_id  # Stage 1 stub
    pytest.skip("Mutation oracle — nightly only")


# =====================================================================
# Baseline regen 스크립트 게이트 (TL-E-6)
# =====================================================================


def test_regen_script_without_confirm_fails() -> None:
    """`regen_trust_layer_baseline.py` 가 `--confirm` 없이 호출되면 exit code ≠ 0.

    SLO TL-E-6 (requirements §3.1 Hard Block). 오남용 방지 게이트.

    Stage 2 구현 예정 (subprocess 로 스크립트 실행 후 returncode 검증).
    """
    pytest.skip("Stage 2 구현 예정 (regen --confirm 게이트)")

"""Monte Carlo 결정성 + 정확 snapshot.

Sprint H2 Phase A iter-1 (FIX-5):
- 기존 동일-seed 동치성 테스트는 "계산이 바뀌어도 deterministic 한" 회귀를
  놓친다 (양쪽 run 이 똑같이 잘못돼도 통과).
- 고정 curve + seed → 정확 값 snapshot 으로 재현성 + 계산 invariant 동시 보장.
- 다른 seed 간 *정확* 값 발산까지 검증해 probabilistic flake 없는 "다른 seed →
  다른 결과" 를 재현.
"""

from __future__ import annotations

from decimal import Decimal

from src.stress_test.engine import run_monte_carlo

# --------------------------------------------------------------------------
# Snapshot 입력 — 20-bar 혼합 curve. up + down 을 섞어 max_drawdown 도 non-zero.
# 값 변경 시 전체 snapshot 을 재수집해야 함 (테스트 failure → 의도적 변경 / regression
# 구분 가능).
# --------------------------------------------------------------------------
_CURVE_A_VALUES: tuple[int, ...] = (
    10000, 10050, 9980, 10100, 10200, 10150, 10080, 10250, 10300, 10200,
    10350, 10280, 10400, 10350, 10500, 10450, 10550, 10500, 10600, 10550,
)
CURVE_A: list[Decimal] = [Decimal(str(v)) for v in _CURVE_A_VALUES]

EXPECTED_SEED_42 = {
    "samples": 200,
    "ci_lower_95": "9919.5485869",
    "ci_upper_95": "11205.36909448",
    "median_final_equity": "10525.9063118",
    "max_drawdown_mean": "0.02330391",
    "max_drawdown_p95": "0.04397063",
    "pct_5_first": "10000.0",
    "pct_5_last": "9919.5485869",
    "pct_50_last": "10525.9063118",
    "pct_95_first": "10000.0",
    "pct_95_last": "11205.36909448",
}

EXPECTED_SEED_43 = {
    "samples": 200,
    "ci_lower_95": "9906.84141521",
    "ci_upper_95": "11276.2159478",
    "median_final_equity": "10555.10879121",
    "max_drawdown_mean": "0.02298073",
    "max_drawdown_p95": "0.04371849",
    "pct_5_first": "10000.0",
    "pct_5_last": "9906.84141521",
    "pct_50_last": "10555.10879121",
    "pct_95_first": "10000.0",
    "pct_95_last": "11276.2159478",
}


def _assert_snapshot(curve: list[Decimal], seed: int, expected: dict[str, object]) -> None:
    r = run_monte_carlo(curve, n_samples=200, seed=seed)
    assert r.samples == expected["samples"]
    assert r.ci_lower_95 == Decimal(str(expected["ci_lower_95"]))
    assert r.ci_upper_95 == Decimal(str(expected["ci_upper_95"]))
    assert r.median_final_equity == Decimal(str(expected["median_final_equity"]))
    assert r.max_drawdown_mean == Decimal(str(expected["max_drawdown_mean"]))
    assert r.max_drawdown_p95 == Decimal(str(expected["max_drawdown_p95"]))
    assert r.equity_percentiles["5"][0] == Decimal(str(expected["pct_5_first"]))
    assert r.equity_percentiles["5"][-1] == Decimal(str(expected["pct_5_last"]))
    assert r.equity_percentiles["50"][-1] == Decimal(str(expected["pct_50_last"]))
    assert r.equity_percentiles["95"][0] == Decimal(str(expected["pct_95_first"]))
    assert r.equity_percentiles["95"][-1] == Decimal(str(expected["pct_95_last"]))


def test_same_seed_produces_same_result() -> None:
    """Pure determinism invariant — snapshot 없이도 유지되어야 하는 최소 계약."""
    r1 = run_monte_carlo(CURVE_A, n_samples=100, seed=42)
    r2 = run_monte_carlo(CURVE_A, n_samples=100, seed=42)
    assert r1.samples == r2.samples == 100
    assert r1.ci_lower_95 == r2.ci_lower_95
    assert r1.ci_upper_95 == r2.ci_upper_95
    assert r1.median_final_equity == r2.median_final_equity
    assert r1.max_drawdown_mean == r2.max_drawdown_mean
    assert r1.max_drawdown_p95 == r2.max_drawdown_p95
    assert r1.equity_percentiles == r2.equity_percentiles


def test_snapshot_curve_a_seed_42() -> None:
    """FIX-5: 고정 입력/seed 에 대한 정확 값 snapshot.

    값 변경 시 의도적 변경인지 regression 인지 판별 필요.
    계산이 바뀌어도 deterministic 한 경우까지 잡기 위한 회귀 테스트.
    """
    _assert_snapshot(CURVE_A, seed=42, expected=EXPECTED_SEED_42)


def test_snapshot_curve_a_seed_43() -> None:
    """다른 seed → 다른 정확 값 (probabilistic "다르다" 가 아닌 결정적 snapshot 비교).

    seed=42 와 다른 값이 나오는 것이 단순한 "적어도 하나 다르다" 체크보다 강한
    invariant — seed 가 실제 분기에 영향을 주고, 그 분기가 우리가 기록한 경로와
    동일함을 모두 보장.
    """
    _assert_snapshot(CURVE_A, seed=43, expected=EXPECTED_SEED_43)


def test_snapshot_42_vs_43_diverges() -> None:
    """두 snapshot 이 실제로 다르다는 sanity — snapshot update 실수 방지."""
    assert EXPECTED_SEED_42["ci_lower_95"] != EXPECTED_SEED_43["ci_lower_95"]
    assert EXPECTED_SEED_42["median_final_equity"] != EXPECTED_SEED_43["median_final_equity"]
    assert EXPECTED_SEED_42["ci_upper_95"] != EXPECTED_SEED_43["ci_upper_95"]

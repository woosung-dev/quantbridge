# Sprint 58 BL-241/242 — 신규 Pine built-in 함수 단위 테스트.
"""ta.wma / ta.cross / ta.mom / fixnan / ta.hma / ta.bb / ta.obv + strategy.equity."""

from __future__ import annotations

import math

import pytest

from src.strategy.pine_v2.stdlib import (
    IndicatorState,
    fn_fixnan,
    ta_bb,
    ta_cross,
    ta_hma,
    ta_mom,
    ta_obv,
    ta_wma,
)

nan = float("nan")


# ── ta.wma ──────────────────────────────────────────────────────────────────


def test_ta_wma_warmup_returns_nan() -> None:
    st = IndicatorState()
    assert math.isnan(ta_wma(st, 1, 1.0, 3))
    assert math.isnan(ta_wma(st, 1, 2.0, 3))


def test_ta_wma_length3_correct() -> None:
    """WMA([1,2,3], 3) = (1*1 + 2*2 + 3*3)/(1+2+3) = 14/6 ≈ 2.3333."""
    st = IndicatorState()
    ta_wma(st, 1, 1.0, 3)
    ta_wma(st, 1, 2.0, 3)
    result = ta_wma(st, 1, 3.0, 3)
    assert abs(result - 14 / 6) < 1e-9


def test_ta_wma_nan_input_returns_nan() -> None:
    st = IndicatorState()
    assert math.isnan(ta_wma(st, 2, nan, 3))


def test_ta_wma_length1_returns_source() -> None:
    st = IndicatorState()
    assert ta_wma(st, 3, 7.0, 1) == pytest.approx(7.0)


# ── ta.cross ────────────────────────────────────────────────────────────────


def test_ta_cross_crossover_detected() -> None:
    st = IndicatorState()
    ta_cross(st, 10, 1.0, 2.0)  # prev: a < b
    assert ta_cross(st, 10, 3.0, 2.0) is True  # a crosses above b


def test_ta_cross_crossunder_detected() -> None:
    st = IndicatorState()
    ta_cross(st, 11, 3.0, 2.0)  # prev: a > b
    assert ta_cross(st, 11, 1.0, 2.0) is True  # a crosses below b


def test_ta_cross_no_cross() -> None:
    st = IndicatorState()
    ta_cross(st, 12, 1.0, 2.0)
    assert ta_cross(st, 12, 1.5, 2.0) is False  # both bars a < b


def test_ta_cross_first_bar_no_cross() -> None:
    st = IndicatorState()
    assert ta_cross(st, 13, 5.0, 3.0) is False  # no prev → no cross


# ── ta.mom ──────────────────────────────────────────────────────────────────


def test_ta_mom_warmup_returns_nan() -> None:
    st = IndicatorState()
    assert math.isnan(ta_mom(st, 20, 10.0, 2))
    assert math.isnan(ta_mom(st, 20, 12.0, 2))


def test_ta_mom_length2_correct() -> None:
    """mom([10, 12, 15], length=2) = 15 - 10 = 5."""
    st = IndicatorState()
    ta_mom(st, 21, 10.0, 2)
    ta_mom(st, 21, 12.0, 2)
    assert ta_mom(st, 21, 15.0, 2) == pytest.approx(5.0)


def test_ta_mom_default_length1() -> None:
    """length=1: mom = current - previous."""
    st = IndicatorState()
    ta_mom(st, 22, 10.0, 1)
    assert ta_mom(st, 22, 13.0, 1) == pytest.approx(3.0)


# ── fn_fixnan ────────────────────────────────────────────────────────────────


def test_fn_fixnan_non_nan_passthrough() -> None:
    st = IndicatorState()
    assert fn_fixnan(st, 30, 5.0) == pytest.approx(5.0)


def test_fn_fixnan_nan_returns_last_valid() -> None:
    st = IndicatorState()
    fn_fixnan(st, 31, 5.0)
    assert fn_fixnan(st, 31, nan) == pytest.approx(5.0)


def test_fn_fixnan_initial_nan_stays_nan() -> None:
    st = IndicatorState()
    assert math.isnan(fn_fixnan(st, 32, nan))


def test_fn_fixnan_updates_on_valid() -> None:
    st = IndicatorState()
    fn_fixnan(st, 33, 5.0)
    fn_fixnan(st, 33, nan)
    fn_fixnan(st, 33, 8.0)  # update valid
    assert fn_fixnan(st, 33, nan) == pytest.approx(8.0)


# ── ta.hma ───────────────────────────────────────────────────────────────────


def test_ta_hma_warmup_returns_nan() -> None:
    st = IndicatorState()
    assert math.isnan(ta_hma(st, 40, 1.0, 4))


def test_ta_hma_length1_no_nan() -> None:
    """length=1 → 충분한 데이터 후 nan 아님."""
    st = IndicatorState()
    result = ta_hma(st, 41, 5.0, 1)
    assert not math.isnan(result)


def test_ta_hma_deterministic() -> None:
    """동일 입력 → 동일 결과 (결정성)."""
    def run(vals: list[float]) -> float:
        st = IndicatorState()
        r = nan
        for v in vals:
            r = ta_hma(st, 50, v, 4)
        return r

    data = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    assert run(data) == pytest.approx(run(data))


# ── ta.bb ────────────────────────────────────────────────────────────────────


def test_ta_bb_warmup_returns_nan_list() -> None:
    st = IndicatorState()
    upper, basis, lower = ta_bb(st, 60, 10.0, 3)
    assert all(math.isnan(v) for v in [upper, basis, lower])


def test_ta_bb_length3_structure() -> None:
    """bb 결과는 [upper, basis, lower], upper > basis > lower (stdev>0)."""
    st = IndicatorState()
    ta_bb(st, 61, 10.0, 3)
    ta_bb(st, 61, 12.0, 3)
    upper, basis, lower = ta_bb(st, 61, 11.0, 3)
    assert not math.isnan(upper)
    assert upper > basis > lower


def test_ta_bb_flat_series_zero_stdev() -> None:
    """같은 값 반복 → stdev=0 → upper=basis=lower."""
    st = IndicatorState()
    for _ in range(3):
        upper, basis, lower = ta_bb(st, 62, 5.0, 3)
    assert upper == pytest.approx(5.0)
    assert basis == pytest.approx(5.0)
    assert lower == pytest.approx(5.0)


def test_ta_bb_basis_equals_sma() -> None:
    """basis = SMA(source, length)."""
    from src.strategy.pine_v2.stdlib import ta_sma
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    st_bb = IndicatorState()
    st_sma = IndicatorState()
    for v in values:
        _, basis, _ = ta_bb(st_bb, 63, v, 3, 2.0)
        sma = ta_sma(st_sma, 63, v, 3)
    assert (math.isnan(basis) and math.isnan(sma)) or basis == pytest.approx(sma)


# ── ta.obv ───────────────────────────────────────────────────────────────────


def test_ta_obv_initial_zero() -> None:
    st = IndicatorState()
    result = ta_obv(st, 70, 100.0, 1000.0, nan)
    assert result == pytest.approx(0.0)


def test_ta_obv_up_bar_adds_volume() -> None:
    st = IndicatorState()
    ta_obv(st, 71, 100.0, 1000.0, nan)
    result = ta_obv(st, 71, 101.0, 500.0, 100.0)  # close > prev_close
    assert result == pytest.approx(500.0)


def test_ta_obv_down_bar_subtracts_volume() -> None:
    st = IndicatorState()
    ta_obv(st, 72, 100.0, 1000.0, nan)
    ta_obv(st, 72, 101.0, 500.0, 100.0)   # +500
    result = ta_obv(st, 72, 99.0, 300.0, 101.0)   # close < prev_close → -300
    assert result == pytest.approx(200.0)


def test_ta_obv_unchanged_bar_no_change() -> None:
    st = IndicatorState()
    ta_obv(st, 73, 100.0, 1000.0, nan)
    ta_obv(st, 73, 101.0, 500.0, 100.0)   # +500
    result = ta_obv(st, 73, 101.0, 300.0, 101.0)  # close == prev_close → no change
    assert result == pytest.approx(500.0)

"""수치 v2는 상수·정확 분수·작은 양의 분모로 검증하며 생성 코드를 읽지 않는다."""

from __future__ import annotations

import importlib.util
import math
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

import pytest

_PATH = Path(__file__).resolve().parents[5] / "tools/research/strategy_oracle.py"
_SPEC = importlib.util.spec_from_file_location("independent_numeric_oracle", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
oracle = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = oracle
_SPEC.loader.exec_module(oracle)


def bars(values: list[str]) -> list[dict[str, str]]:
    start = datetime(2026, 2, 1, tzinfo=UTC)
    return [
        {
            "timestamp": (start + timedelta(hours=index)).isoformat(),
            **dict.fromkeys(("open", "high", "low", "close"), value),
            "volume": "10",
        }
        for index, value in enumerate(values)
    ]


def data_for(values: list[str]):
    data = oracle._Math()
    data.extend(bars(values))
    return data


def fraction_cmp(a: Fraction, b: Fraction) -> int:
    tolerance = Fraction("1e-12") * max(1, abs(a), abs(b))
    return 0 if abs(a - b) <= tolerance else 1 if a > b else -1


@pytest.mark.parametrize("sign", [-1, 1])
def test_signal_band_has_inclusive_boundary_and_symmetric_strictness(sign: int) -> None:
    boundary = sign * 1e-12
    inside = math.nextafter(boundary, 0)
    outside = math.nextafter(boundary, sign * math.inf)
    assert oracle._comparison(inside, 0) == oracle._comparison(boundary, 0) == 0
    assert oracle._comparison(outside, 0) == sign
    assert oracle._comparison(0, outside) == -sign
    assert oracle._cross([0, outside], [0, 0], up=sign > 0)
    assert not oracle._cross([0, boundary], [0, 0], up=sign > 0)


@pytest.mark.parametrize("invalid", [math.nan, math.inf, -math.inf])
def test_nonfinite_is_never_a_signal_comparison(invalid: float) -> None:
    for operator in (oracle._gt, oracle._lt, oracle._ge, oracle._le):
        assert not operator(invalid, 0)
        assert not operator(0, invalid)
    assert not oracle._cross([invalid, 2], [0, 1])


@pytest.mark.parametrize("value", ["0.007", "184.18570528881713", "100000000.000001"])
def test_constant_kernels_preserve_the_exact_parsed_input(value: str) -> None:
    data = data_for([value] * 900)
    parsed = float(value)
    for length in (3, 8, 14, 20, 25, 50, 200):
        assert data.sma(length)[-1] == parsed
        assert data.ema(length)[-1] == parsed
        assert data.smooth(f"rma-{length}", data.fields["close"], length, wilder=True)[-1] == parsed
        assert data.rolling(f"std-{length}", data.fields["close"], length, "std")[-1] == 0
    assert data.fields["hlc3"][-1] == parsed
    assert data.cci()[-1] == 0
    assert data.rsi(14)[-1] == 100
    assert all(series[-1] == 0 for series in data.dmi())
    assert all(math.isnan(series[-1]) for series in data.stochastic(rsi=True))
    assert all(math.isnan(series[-1]) for series in data.stochastic())
    assert data.vwap()[-1] == data.anchored_vwap()[-1] == parsed
    assert all(series[-1] == 0 for series in data.macd(12, 26, 9))
    slope, lower, upper = data.regression()
    assert slope[-1] == 0
    assert lower[-1] == upper[-1] == parsed
    assert data.htf_regime()[-1] == 0


def test_small_positive_structural_denominators_remain_valid() -> None:
    history = bars(["1e-15"] * 40)
    for bar in history:
        bar.update(high="2e-15", low="0", volume="1e-30")
    data = oracle._Math()
    data.extend(history)
    assert data.stochastic()[0][-1] == 50
    assert data.vwap()[-1] == float("1e-15")
    assert all(series[-1] == 0 for series in data.dmi())
    gains = data.smooth("tiny-gain", [1e-20] * 30, 14, wilder=True)
    losses = data.smooth("tiny-loss", [1e-20] * 30, 14, wilder=True)
    assert gains[-1] == losses[-1] == 1e-20
    assert 100 - 100 / (1 + gains[-1] / losses[-1]) == 50


def test_large_offset_small_variance_matches_exact_binary_input_fraction() -> None:
    values = [1e8 - 1e-6, 1e8 + 1e-6] * 10
    fractions = [Fraction.from_float(value) for value in values]
    center = sum(fractions) / len(fractions)
    variance = sum((value - center) ** 2 for value in fractions) / len(fractions)
    assert oracle._population_std(values) == pytest.approx(math.sqrt(float(variance)), rel=1e-15)
    assert oracle._population_std(values) > 0
    assert oracle._mean(values) == float(center)


def test_dmi_adx_known_large_price_trend_and_tiny_rsi_changes() -> None:
    history = bars([str(100000000 + index) for index in range(40)])
    for bar in history:
        close = Decimal(bar["close"])
        bar.update(high=str(close + Decimal("0.25")), low=str(close - Decimal("0.25")))
    data = oracle._Math()
    data.extend(history)
    plus, minus, adx = data.dmi()
    # 첫 TR=.5, 이후 TR=1.25, +DM은 첫0/이후1이다. 초기14봉을 직접 합산한다.
    assert data.atr(14)[13] == float(Fraction(67, 56))
    assert plus[13] == pytest.approx(float(Fraction(5200, 67)), rel=1e-14)
    assert minus[-1] == 0
    assert adx[-1] == 100
    small = data_for(["1e-15", "2e-15", "1e-15"])
    assert small.rsi(2)[-1] == 50


@pytest.mark.parametrize("base", ["0.007", "184.18570528881713", "100000000.000001"])
def test_sma_cross_and_invalidation_match_exact_decimal_fraction_contract(base: str) -> None:
    value, step = Decimal(base), Decimal("0.001")
    values = [value - step] * 9 + [value] * 12 + [value + step] * 3 + [value] * 8 + [value - step]
    history = bars([str(value) for value in values])
    states = {direction: {} for direction in ("flat", "long", "short")}
    previous = None
    for size in range(1, len(history) + 1):
        exact = [Fraction(bar["close"]) for bar in history[:size]]
        current = fraction_cmp(sum(exact[-3:]) / 3, sum(exact[-8:]) / 8) if size >= 8 else None
        long = current is not None and previous is not None and previous <= 0 and current > 0
        short = current is not None and previous is not None and previous >= 0 and current < 0
        for direction, state in states.items():
            expected = (
                ("short" if short else "close" if current == -1 else "hold")
                if direction == "long"
                else ("long" if long else "close" if current == 1 else "hold")
                if direction == "short"
                else "long"
                if long
                else "short"
                if short
                else "hold"
            )
            assert (
                oracle.expected_action("D01", history[:size], {"direction": direction}, state)
                == expected
            )
        previous = current


def test_strict_rsi_pivot_excludes_band_ties_but_keeps_integer_confirmation() -> None:
    for delta, expected_pivot in ((1e-11, False), (1e-8, True)):
        data = data_for(["100"] * 12)
        data.cache["rsi14"] = [50, 45, 40, 30, 30 + delta, 40, 45] + [50] * 5
        data.divergence()
        pivot = data.cache["divergence_low_pivot"][6]
        assert (pivot == 3) if expected_pivot else math.isnan(pivot)


def test_raw_price_extreme_ties_keep_exact_latest_policy() -> None:
    history = bars(["90"] * 26)
    history[-2]["high"] = "100"
    history[-1]["high"] = "99.99999999999"
    data = oracle._Math()
    data.extend(history)
    assert oracle._comparison(100, float(history[-1]["high"])) == 0
    assert data.aroon()[0][-1] == 96
    assert data.rolling("raw-max", data.fields["high"], 26, "max")[-1] == 100


@pytest.mark.parametrize("ident", [f"{index:02}" for index in range(1, 31)])
@pytest.mark.parametrize("value", ["0.007", "184.18570528881713", "100000000.000001"])
def test_all_30_constant_signals_have_no_roundoff_entry_or_false_invalidation(
    ident: str, value: str
) -> None:
    data = data_for([value] * 260)
    conditions = oracle._conditions(ident, data)
    # 수학적으로 상수여도 정의상 청산하는 전략은 명시한다: RSI100, ADX0, 구름 안, 기울기0.
    expected_long = "close" if ident in {"05", "06", "07", "27"} else "hold"
    expected_short = "close" if ident in {"06", "07", "11", "27"} else "hold"
    assert oracle._decision(*conditions, "flat") == "hold"
    assert oracle._decision(*conditions, "long") == expected_long
    assert oracle._decision(*conditions, "short") == expected_short

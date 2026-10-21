"""자연어 판정기는 생성 compiler·앱 지표·공통 리스크 함수를 정답으로 사용하지 않는다."""

from __future__ import annotations

import importlib.util
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

_PATH = Path(__file__).resolve().parents[5] / "tools/research/strategy_oracle.py"
_SPEC = importlib.util.spec_from_file_location("independent_strategy_oracle", _PATH)
assert _SPEC is not None and _SPEC.loader is not None
oracle = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = oracle
_SPEC.loader.exec_module(oracle)


def history(closes: list[float]) -> list[dict[str, Any]]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        {
            "timestamp": (start + timedelta(hours=index)).isoformat(),
            "open": str(value),
            "high": str(value + 1),
            "low": str(value - 1),
            "close": str(value),
            "volume": "10",
        }
        for index, value in enumerate(closes)
    ]


def mirror(bars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            **bar,
            "open": str(200 - float(bar["open"])),
            "close": str(200 - float(bar["close"])),
            "high": str(200 - float(bar["low"])),
            "low": str(200 - float(bar["high"])),
        }
        for bar in bars
    ]


def action(ident: str, bars: list[dict[str, Any]], direction: str = "flat") -> str:
    return oracle.expected_action(ident, bars, {"direction": direction}, {})


@pytest.mark.parametrize("ident", ["D01", "D02", "D03", "D04", "D05"])
def test_development_entry_has_positive_negative_and_symmetric_cases(ident: str) -> None:
    bars = history([100 - i for i in range(21)] + [120])
    assert action(ident, bars) == "long"
    assert action(ident, mirror(bars)) == "short"
    assert action(ident, history([100] * 30)) == "hold"
    assert action(ident, bars, "short") == "long"


def test_heikin_ashi_first_two_color_confirmation_and_invalidation() -> None:
    bars = history([100] * 15 + [105, 110])
    bars[-2].update(open="100", low="100", high="105")
    bars[-1].update(open="105", low="105", high="110")
    assert action("D06", bars) == "long"
    assert action("D06", mirror(bars)) == "short"
    assert action("D06", bars, "short") == "long"
    assert action("D06", history([100, 100, 90]), "long") == "close"
    assert action("D06", bars + history([115])[-1:]) == "hold"


@pytest.mark.parametrize("ident", ["D01", "D02", "D03", "D04", "D05", "D06"])
def test_streaming_and_fresh_prefix_match_without_future_data(ident: str) -> None:
    bars = history([100 - i / 2 for i in range(25)] + [115, 120, 110, 105, 125])
    state: dict[str, Any] = {}
    observed = []
    for index in range(1, len(bars) + 1):
        observed.append(oracle.expected_action(ident, bars[:index], {"direction": "flat"}, state))
    expected = [action(ident, bars[:index]) for index in range(1, len(bars) + 1)]
    assert observed == expected
    future = bars + history([999, 1, 800])
    assert action(ident, future[: len(bars)]) == observed[-1]


def test_rsi_flat_seed_and_population_standard_deviation() -> None:
    data = oracle._Math()
    data.extend(history([100] * 8))
    rsi = data.rsi(7)
    assert all(__import__("math").isnan(value) for value in rsi[:7])
    assert rsi[7] == 100
    assert data.rolling("population", [1, 2, 3], 3, "std")[-1] == pytest.approx((2 / 3) ** 0.5)
    ema = data.smooth("ema_known", [2, 4, 6, 10], 3)
    assert ema[2:] == pytest.approx([4, 7])
    rma = data.smooth("rma_known", [2, 4, 6, 10], 3, wilder=True)
    assert rma[2:] == pytest.approx([4, 6])


def test_crossing_equality_is_not_a_cross_and_zero_volume_vwap_holds() -> None:
    assert not oracle._cross([1, 2], [2, 2])
    assert oracle._cross([2, 3], [2, 2])
    bars = history([100 - i for i in range(21)] + [120])
    for bar in bars:
        bar["volume"] = "0"
    assert action("D05", bars, "long") == "hold"


@pytest.mark.parametrize(
    ("direction", "expected"),
    [
        (
            "long",
            {"risk": "11", "stop": "89", "partial": "116.5", "activation": "122", "distance": "22"},
        ),
        (
            "short",
            {"risk": "11", "stop": "111", "partial": "83.5", "activation": "78", "distance": "22"},
        ),
    ],
)
def test_risk_closed_form_matches_hand_calculation(
    direction: str, expected: dict[str, str]
) -> None:
    result = oracle.expected_risk_plan(
        Decimal(100), [{"low": "90", "high": "110"}, {"low": "91", "high": "109"}], direction
    )
    assert result == {key: Decimal(value) for key, value in expected.items()}


def test_unsupported_oracle_is_explicitly_unavailable() -> None:
    with pytest.raises(oracle.OracleUnavailable):
        action("unknown", history([100]))


def wave_bars(count: int = 720) -> list[dict[str, Any]]:
    import math

    bars: list[dict[str, Any]] = []
    start = datetime(2026, 1, 1, tzinfo=UTC)
    for index in range(count):
        trend = (
            100 + index * 0.07
            if index < 240
            else 116.8 - (index - 240) * 0.13
            if index < 480
            else 85.6 + (index - 480) * 0.1
        )
        close = trend + 6 * math.sin(index / 11) + 2 * math.sin(index / 3)
        open_ = float(bars[-1]["close"]) if bars else close
        bars.append(
            {
                "timestamp": (start + timedelta(hours=index)).isoformat(),
                "open": str(open_),
                "high": str(max(open_, close) + 0.3 + (index % 7) / 10),
                "low": str(min(open_, close) - 0.3 - (index % 5) / 10),
                "close": str(close),
                "volume": str(10 + index % 19),
            }
        )
    return bars


_SIMPLE = (
    "01",
    "02",
    "03",
    "04",
    "08",
    "10",
    "11",
    "12",
    "13",
    "14",
    "15",
    "17",
    "18",
    "19",
    "20",
    "21",
    "23",
    "24",
    "25",
    "26",
    "28",
    "29",
)


@pytest.mark.parametrize("ident", _SIMPLE)
def test_evaluation_rules_have_both_direction_opportunities_and_neutral_case(ident: str) -> None:
    bars = wave_bars()
    found: set[str] = set()
    for tape in (bars, mirror(bars)):
        state: dict[str, Any] = {}
        for size in range(1, len(tape) + 1):
            found.add(oracle.expected_action(ident, tape[:size], {"direction": "flat"}, state))
    assert {"long", "short"} <= found
    assert action(ident, history([100] * 300)) == "hold"


@pytest.mark.parametrize("ident", _SIMPLE)
def test_evaluation_streaming_prefix_and_price_scaling(ident: str) -> None:
    bars = wave_bars()[:260]
    scaled = [
        {**bar, **{key: str(float(bar[key]) * 2) for key in ("open", "high", "low", "close")}}
        for bar in bars
    ]
    left_state: dict[str, Any] = {}
    right_state: dict[str, Any] = {}
    for size in range(1, len(bars) + 1):
        original = oracle.expected_action(ident, bars[:size], {"direction": "flat"}, left_state)
        assert original == oracle.expected_action(
            ident, scaled[:size], {"direction": "flat"}, right_state
        )
        if size in (10, 100, 200, 260):
            assert original == action(ident, bars[:size])
    assert action(ident, (bars + history([999, 1, 500]))[: len(bars)]) == original


def test_independent_indicator_known_values() -> None:
    data = oracle._Math()
    data.extend(history([10, 12, 11, 11]))
    assert data.obv() == [0, 10, 0, 0]
    atr = oracle._Math()
    atr.extend(history([10, 12, 14, 16]))
    assert atr.atr(3)[2:] == pytest.approx([8 / 3, 25 / 9])
    cci = oracle._Math()
    cci.extend(history(list(range(1, 21))))
    assert cci.cci()[-1] == pytest.approx(9.5 / (0.015 * 5))
    aroon = oracle._Math()
    aroon.extend(history(list(range(10, 36))))
    assert aroon.aroon()[0][-1] == 100
    assert aroon.aroon()[1][-1] == 0
    flow = oracle._Math()
    flow.extend(history(list(range(10, 60))))
    assert flow.cmf()[-1] == 0
    assert flow.mfi()[-1] == 100
    assert flow.tsi()[0][-1] == pytest.approx(100)


def test_oracle_never_imports_app_indicators_compiler_or_reference_specs() -> None:
    import ast

    tree = ast.parse(_PATH.read_text())
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom):
            modules.append(node.module or "")
    assert not any(
        name.startswith(("src.", "tools.")) or "compiler" in name or "catalogue" in name
        for name in modules
    )


@pytest.mark.parametrize("ident", ["05", "06", "07", "27", "30"])
def test_complex_equations_have_positive_negative_and_no_future_access(ident: str) -> None:
    bars = wave_bars(1440 if ident == "30" else 720)
    found: set[str] = set()
    for tape in (bars, mirror(bars)):
        state: dict[str, Any] = {}
        for size in range(1, len(tape) + 1):
            observed = oracle.expected_action(ident, tape[:size], {"direction": "flat"}, state)
            found.add(observed)
            if size in (200, len(tape)):
                assert observed == action(ident, tape[:size])
    assert {"long", "short"} <= found
    assert action(ident, history([100] * 900)) == "hold"
    assert action(ident, (bars + history([9999, 1]))[: len(bars)]) == action(ident, bars)


def test_supertrend_band_ratchet_and_adx_known_trend() -> None:
    trend = oracle._Math()
    trend.extend(history([100] * 10 + [110, 90]))
    assert trend.supertrend()[-3:] == [-1, 1, -1]
    dmi = oracle._Math()
    dmi.extend(history(list(range(100, 140))))
    plus, minus, adx = dmi.dmi()
    assert plus[-1] > 0
    assert minus[-1] == 0
    assert adx[-1] == pytest.approx(100)


def test_ichimoku_uses_displayed_cloud_from_26_bars_ago() -> None:
    data = oracle._Math()
    data.extend(history(list(range(100, 180))))
    tenkan, kijun, upper, lower = data.ichimoku()
    assert tenkan[-1] == 175
    assert kijun[-1] == 166.5
    assert upper[-1] == 144.75
    assert lower[-1] == 127.5
    assert __import__("math").isnan(upper[76])


def test_regression_known_line_and_htf_only_complete_buckets() -> None:
    data = oracle._Math()
    data.extend(history(list(range(100, 150))))
    slopes, lower, upper = data.regression()
    assert slopes[-1] == 1
    assert lower[-1] == upper[-1] == 149
    htf = oracle._Math()
    bars = history(list(range(100, 902)))
    bars[800]["close"] = "1"
    bars[801]["close"] = "1"
    htf.extend(bars)
    regimes = htf.htf_regime()
    assert regimes[798] == 0
    assert regimes[799:] == [1, 1, 1]
    assert len(htf.cache["htf_closes"]) == 200


@pytest.mark.parametrize("ident", ["09", "16", "22"])
def test_ambiguous_rules_are_unavailable_instead_of_false_hold(ident: str) -> None:
    assert oracle.unsupported_reason(ident)
    with pytest.raises(oracle.OracleUnavailable):
        action(ident, history([100] * 300))

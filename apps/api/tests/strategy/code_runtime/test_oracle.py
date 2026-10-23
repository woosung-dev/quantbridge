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


def test_all_30_evaluation_rules_have_independent_definitions() -> None:
    assert {f"{index:02}" for index in range(1, 31)} <= set(oracle.supported_ids())
    assert all(oracle.unsupported_reason(f"{index:02}") is None for index in range(1, 31))


def test_squeeze_known_bandwidth_requires_120_prior_valid_values_and_next_bar() -> None:
    import math

    bars = history([100] * 140 + [110])
    data = oracle._Math()
    data.extend(bars)
    longs, shorts = data.squeeze()
    assert all(math.isnan(value) for value in data.cache["squeeze_event"][:139])
    assert data.cache["squeeze_event"][139] == 139
    assert longs[139] == shorts[139] == 0
    assert data.sma(20)[140] == 100.5
    assert data.cache["squeeze_std20"][140] == pytest.approx(4.75**0.5)
    assert data.cache["squeeze_width"][140] == pytest.approx(4 * 4.75**0.5 / 100.5)
    assert action("09", bars) == "long"
    assert action("09", mirror(bars)) == "short"
    assert action("09", history([100] * 139 + [110])) == "hold"


def test_squeeze_consumes_signal_regardless_of_position_and_resets_on_new_event() -> None:
    bars = history([100] * 140 + [110, 100, 90] + [100] * 20 + [110])
    state: dict[str, Any] = {}
    # 동방향 진입은 경제적으로 hold지만 squeeze는 이 시점에 이미 소비한다.
    assert oracle.expected_action("09", bars[:141], {"direction": "long"}, state) == "hold"
    assert oracle.expected_action("09", bars[:141], {"direction": "flat"}, state) == "long"
    assert oracle.expected_action("09", bars[:143], {"direction": "flat"}, state) == "hold"
    data = state["_independent_oracle"][1]
    assert data.cache["squeeze_consumed"][140] == 1
    assert data.cache["squeeze_short"][142] == 0
    assert oracle.expected_action("09", bars, {"direction": "flat"}, state) == "long"
    assert data.cache["squeeze_event"][-2] == len(bars) - 2


def test_squeeze_event_priority_and_five_bar_expiry() -> None:
    prefix = [99, 101] * 70
    inside = [101.5, 98.5, 101.5, 98.5, 101.5]
    assert action("09", history(prefix + inside[:4] + [110])) == "long"
    assert action("09", history(prefix + inside + [110])) == "hold"
    # 과거 고변동 구간이 창을 벗어나면서 같은 봉의 BW 신저점과 상단 교차가 겹친다.
    bars = history([80, 120] * 70 + [100] * 19 + [101])
    data = oracle._Math()
    data.extend(bars)
    longs, _ = data.squeeze()
    assert data.cache["squeeze_event"][-1] == len(bars) - 1
    assert longs[-1] == 0
    assert action("09", bars) == action("09", mirror(bars)) == "hold"


def divergence_bars() -> list[dict[str, Any]]:
    return history([100, 101] * 10 + [50] + list(range(51, 61)) + [59, 58, 45, 46, 47, 48, 50])


def append_bars(bars: list[dict[str, Any]], closes: list[float]) -> list[dict[str, Any]]:
    extra = history(closes)
    start = datetime.fromisoformat(str(bars[-1]["timestamp"]).replace("Z", "+00:00"))
    for index, bar in enumerate(extra, 1):
        bar["timestamp"] = (start + timedelta(hours=index)).isoformat()
    return bars + extra


def test_divergence_exact_pivots_rsi_known_value_and_single_confirmation_bar() -> None:
    from fractions import Fraction

    bars = divergence_bars()
    data = oracle._Math()
    data.extend(bars)
    longs, shorts, levels, _ = data.divergence()
    # 14개 변화는 상승/하락 각각 7개다. 이후 여섯 변화의 Wilder 가중합을 손계산한다.
    decay = Fraction(13, 14)
    gain = Fraction(1, 2) * decay**6 + (decay**5 + decay**3 + decay) / 14
    loss = Fraction(1, 2) * decay**6 + (decay**4 + decay**2 + 51) / 14
    assert data.rsi(14)[14] == 50
    assert data.rsi(14)[20] == pytest.approx(float(100 * gain / (gain + loss)))
    assert data.rsi(14)[33] == pytest.approx(18.861148730896815)
    assert data.cache["divergence_low_pivot"][23] == 20
    assert data.cache["divergence_low_pivot"][36] == 33
    assert longs[36] == shorts[36] == 0
    assert data.cache["divergence_pending_long"][36] == 44
    assert levels[37] == 44
    assert action("16", bars) == "long"
    assert action("16", mirror(bars)) == "short"
    assert action("16", bars[:-1]) == "hold"
    late = [dict(bar) for bar in bars]
    late[-1].update(open="48", high="49", low="47", close="48")
    late = append_bars(late, [100])
    assert action("16", late) == "hold"


def test_divergence_invalidation_uses_latest_signal_pivot_and_strict_equality() -> None:
    bars = divergence_bars()
    equal = append_bars(bars, [44])
    below = append_bars(bars, [43])
    assert action("16", equal, "long") == "hold"
    assert action("16", below, "long") == "close"
    assert action("16", mirror(below), "short") == "close"
    assert action("16", history([100] * 100 + [1]), "long") == "hold"


def test_divergence_strict_rsi_ties_and_latest_separate_equal_pivot() -> None:
    data = oracle._Math()
    data.extend(history([100] * 25))
    # 중심과 이웃이 동률인 plateau는 pivot이 아니다.
    data.cache["rsi14"] = [50, 45, 40, 30, 30, 40, 45] + [50] * 18
    data.divergence()
    assert all(__import__("math").isnan(value) for value in data.cache["divergence_low_pivot"])
    data = oracle._Math()
    data.extend(history([100] * 25))
    # 떨어진 두 pivot의 RSI가 같아도 최신 확정 pivot으로 기준을 갱신한다.
    data.cache["rsi14"] = [50, 45, 40, 30, 40, 45, 50, 45, 40, 30, 40, 45, 50] + [50] * 12
    longs, _, _, _ = data.divergence()
    assert data.cache["divergence_low_pivot"][12] == 9
    assert not any(longs)


@pytest.mark.parametrize(("gap", "expected"), [(60, 1), (61, 0)])
def test_divergence_pivot_gap_inclusive_boundary(gap: int, expected: int) -> None:
    second = 3 + gap
    bars = history([100] * (second + 5))
    bars[3]["low"] = "90"
    bars[second]["low"] = "80"
    bars[-1].update(close="102", high="103")
    data = oracle._Math()
    data.extend(bars)
    values = [50.0] * len(bars)
    values[3], values[second] = 20, 30
    data.cache["rsi14"] = values
    longs, _, levels, _ = data.divergence()
    assert longs[-1] == expected
    if expected:
        assert levels[-1] == 80


def test_divergence_invalidation_changes_on_signal_not_pivot_confirmation() -> None:
    bars = history([100] * 28)
    for index, price in [(3, 90), (13, 80), (23, 70)]:
        bars[index]["low"] = str(price)
    for index in (17, 27):
        bars[index].update(close="102", high="103")
    data = oracle._Math()
    data.extend(bars)
    values = [50.0] * len(bars)
    values[3], values[13], values[23] = 20, 30, 40
    data.cache["rsi14"] = values
    longs, _, levels, _ = data.divergence()
    assert longs[17] == longs[27] == 1
    assert levels[17] == levels[26] == 80
    assert levels[27] == 70


def test_anchored_vwap_exact_hlc3_volume_before_at_and_after_anchor() -> None:
    import math

    bars = history([999, 12, 16])
    bars[0].update(timestamp="2025-12-31T23:00:00Z", volume="999000")
    bars[1].update(timestamp="2026-01-01T00:00:00Z", high="16", low="8", volume="2")
    bars[2].update(timestamp="2026-01-02T00:00:00Z", high="25", low="13", volume="1")
    data = oracle._Math()
    data.extend(bars)
    values = data.anchored_vwap()
    assert math.isnan(values[0])
    assert values[1:] == [12, 14]


def anchored_breakout_bars() -> list[dict[str, Any]]:
    bars = history([100] * (288 + 21) + [110])
    start = datetime(2025, 12, 20, tzinfo=UTC)
    for index, bar in enumerate(bars):
        bar["timestamp"] = (start + timedelta(hours=index)).isoformat()
    return bars


def test_anchored_vwap_both_direction_breakouts_and_invalidation() -> None:
    bars = anchored_breakout_bars()
    assert bars[288]["timestamp"] == "2026-01-01T00:00:00+00:00"
    assert action("22", bars) == "long"
    assert action("22", mirror(bars)) == "short"
    assert action("22", bars[:289]) == "hold"
    invalidated = append_bars(bars, [99.5])
    assert action("22", invalidated, "long") == "close"
    assert action("22", mirror(invalidated), "short") == "close"


@pytest.mark.parametrize("ident", ["09", "16", "22"])
def test_new_oracles_handle_zero_denominators_and_stream_without_future_data(ident: str) -> None:
    bars = (
        history([100] * 140 + [110, 100, 90] + [100] * 20 + [110])
        if ident == "09"
        else divergence_bars()
        if ident == "16"
        else anchored_breakout_bars()
    )
    state: dict[str, Any] = {}
    for size in range(1, len(bars) + 1):
        observed = oracle.expected_action(ident, bars[:size], {"direction": "flat"}, state)
        if size in (10, len(bars) // 2, len(bars)):
            assert observed == action(ident, bars[:size])
    future = append_bars(bars, [9999, 1, 8000])
    assert action(ident, future[: len(bars)]) == observed
    zero = history([0 if ident == "09" else 100] * 300)
    if ident == "22":
        for bar in zero:
            bar["volume"] = "0"
    assert action(ident, zero) == "hold"

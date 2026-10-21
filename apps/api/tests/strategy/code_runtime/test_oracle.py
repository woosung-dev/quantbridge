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

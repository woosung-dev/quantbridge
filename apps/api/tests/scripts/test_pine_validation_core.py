"""전체 사건 대조·선물 체결·독립 수치 계산의 작은 손계산 오라클. DB·네트워크 없음."""

from __future__ import annotations

import ast
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.pine_validation.compare import compare_events
from scripts.pine_validation.futures import compare_futures, simulate_futures
from scripts.pine_validation.models import SignalEvent, coerce_events
from scripts.pine_validation.oracles import (
    atr,
    compute_oracle,
    crossover,
    crossunder,
    ema,
    events_from_conditions,
    rma,
    rsi,
    sma,
    source_values,
    supertrend,
    utbot,
)

BASE = datetime(2026, 10, 1, tzinfo=UTC)


def at(index: int) -> datetime:
    return BASE + timedelta(hours=index)


def event(index: int, direction: str = "long") -> SignalEvent:
    return SignalEvent(at(index), direction)  # type: ignore[arg-type]


def candles(values: list[float]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "open": values,
            "high": [price + 1 for price in values],
            "low": [price - 1 for price in values],
            "close": values,
            "volume": [1.0] * len(values),
        },
        index=pd.date_range(BASE, periods=len(values), freq="h"),
    )


def test_json_event_roundtrip_preserves_confirmation_and_display_time() -> None:
    events = coerce_events(
        json.dumps(
            {
                "events": [
                    {
                        "bar_time": "2026-10-01T09:00:00+09:00",
                        "direction": "short",
                        "confirmed_at": "2026-10-01T01:00:00Z",
                        "display_time": "2026-09-30T23:00:00Z",
                        "source_line": 12,
                    }
                ]
            }
        )
    )
    assert events == [SignalEvent(at(0), "short", at(1), at(-1), 12)]
    assert coerce_events([events[0].to_dict()]) == events
    with pytest.raises(ValueError, match="시간대"):
        coerce_events([{"bar_time": "2026-10-01T00:00:00", "direction": "long"}])
    with pytest.raises(ValueError, match="확정 시각"):
        SignalEvent(at(1), "long", confirmed_at=at(0))


def test_matching_latest_event_does_not_hide_earlier_missing_signal() -> None:
    result = compare_events([event(0), event(3, "short")], [event(3, "short")])
    assert result.status == "mismatch"
    assert result.missing == [event(0)]
    assert result.left_count == 2 and result.right_count == 1


def test_empty_comparison_is_not_a_pass_and_duplicate_counts_are_preserved() -> None:
    assert compare_events([], []).status == "no_signal"
    result = compare_events([event(0), event(0)], [event(0)])
    assert result.status == "mismatch" and len(result.missing) == 1
    assert compare_events([event(0)], [event(0)]).status == "exact_match"


def test_opposite_and_one_bar_lag_remain_mismatches() -> None:
    result = compare_events(
        [event(0), event(2, "short")],
        [event(0, "short"), event(3, "short")],
        bar_times=[at(i) for i in range(5)],
    )
    assert result.status == "mismatch"
    assert len(result.opposite) == 1
    assert result.bar_lags[0]["lag_bars"] == 1
    assert result.bar_lags[0]["lag_seconds"] == 3600
    assert len(result.missing) == len(result.extra) == 2


def test_comparison_window_is_explicit_and_half_open() -> None:
    result = compare_events(
        [event(0), event(1), event(2)], [event(1)], window_start=at(1), window_end=at(2)
    )
    assert result.status == "exact_match" and result.left_count == 1
    with pytest.raises(ValueError, match="종료"):
        compare_events([], [], window_start=at(1), window_end=at(1))


def test_confirmation_and_display_differences_cannot_pass_same_event_bar() -> None:
    reference = SignalEvent(at(0), "long", at(1), at(-2), 10)
    candidate = SignalEvent(at(0), "long", at(2), at(0), 99)
    result = compare_events([reference], [candidate])
    assert result.status == "mismatch"
    assert result.missing == result.extra == []
    assert {row["field"] for row in result.metadata_differences} == {"confirmed_at", "display_time"}
    assert {row["reason"] for row in result.metadata_differences} == {"metadata_mismatch"}
    missing = compare_events([reference], [event(0)])
    assert missing.status == "mismatch"
    assert {row["reason"] for row in missing.metadata_differences} == {"metadata_missing"}


def test_metadata_pairing_ignores_source_line_and_duplicate_order() -> None:
    first = SignalEvent(at(0), "long", at(1), at(-1), 10)
    second = SignalEvent(at(0), "long", at(1), at(-2), 11)
    assert compare_events([first, second], [second, first]).status == "exact_match"
    assert (
        compare_events([first], [SignalEvent(at(0), "long", at(1), at(-1), 99)]).status
        == "exact_match"
    )


def test_futures_next_open_no_add_reverse_and_explicit_exit_hand_oracle() -> None:
    result = simulate_futures(
        candles([10, 11, 12, 13, 14, 15]),
        [event(0), event(1), event(2, "short"), event(3, "short_exit"), event(5)],
    )
    assert [
        (trade.direction, trade.entry_time, trade.exit_time, trade.pnl) for trade in result.trades
    ] == [
        ("long", at(1), at(3), Decimal("2")),
        ("short", at(3), at(4), Decimal("-1")),
    ]
    assert result.realized_pnl == Decimal("1")
    assert result.open_position is None
    assert result.pending_events == [event(5)]


def test_futures_does_not_close_at_end_or_treat_wrong_side_exit_as_reversal() -> None:
    result = simulate_futures(candles([10, 11, 12, 13]), [event(0, "short"), event(1, "long_exit")])
    assert result.trades == []
    assert result.open_position is not None
    assert result.open_position.direction == "short"
    assert result.open_position.entry_price == Decimal("11")
    assert result.open_position.exit_time is None
    other = simulate_futures(candles([10, 11, 12, 13]), [event(0, "long")])
    assert compare_futures(result, other)["status"] == "mismatch"
    assert compare_futures(result, result)["status"] == "exact_match"


def test_futures_conflicting_signals_and_missing_bars_are_errors() -> None:
    data = candles([10, 11, 12])
    with pytest.raises(ValueError, match="충돌"):
        simulate_futures(data, [event(0), event(0, "short")])
    with pytest.raises(ValueError, match="신호 봉"):
        simulate_futures(data, [event(8)])
    assert (
        compare_futures(simulate_futures(data, []), simulate_futures(data, []))["status"]
        == "no_signal"
    )


def test_pending_order_comparison_ignores_source_metadata_only() -> None:
    data = candles([10, 11, 12])
    pine = simulate_futures(data, [SignalEvent(at(2), "long", at(3), at(2), 42)])
    python = simulate_futures(data, [event(2)])
    assert compare_futures(pine, python)["status"] == "no_fills"
    other = simulate_futures(data, [event(2, "short")])
    assert compare_futures(pine, other)["status"] == "mismatch"


def test_pending_intents_ignore_source_metadata_but_are_not_fills() -> None:
    data = candles([10, 11])
    left = simulate_futures(data, [SignalEvent(at(1), "long", at(2), at(1), 3)])
    right = simulate_futures(data, [event(1)])
    assert compare_futures(left, right)["status"] == "no_fills"
    assert left.open_position is None and left.trades == []
    with pytest.raises(ValueError, match="확정되기 전"):
        simulate_futures(data, [SignalEvent(at(0), "long", at(2))])


def test_pine_smoothing_seeds_and_na_are_independent_hand_oracles() -> None:
    values = [np.nan, 1, 2, np.nan, 3, 6]
    np.testing.assert_allclose(
        sma(values, 3), [np.nan, np.nan, np.nan, np.nan, 2, 11 / 3], equal_nan=True
    )
    np.testing.assert_allclose(
        rma(values, 3), [np.nan, np.nan, np.nan, np.nan, 2, 10 / 3], equal_nan=True
    )
    np.testing.assert_allclose(ema(values[:5], 3), [np.nan, 1, 1.5, 1.5, 2.25], equal_nan=True)
    np.testing.assert_allclose(
        rsi([1, 2, 3, 2, 1], 2), [np.nan, np.nan, 100, 50, 25], equal_nan=True
    )
    np.testing.assert_allclose(atr(candles([10, 12, 15]), 2), [np.nan, 2.5, 3.25], equal_nan=True)


def test_crossing_requires_valid_previous_values_and_does_not_repeat_levels() -> None:
    assert crossover([np.nan, 1, 2, 3, 1], 1.5).tolist() == [False, False, True, False, False]
    assert crossunder([np.nan, 1, 2, 3, 1], 1.5).tolist() == [False, False, False, False, True]
    assert crossover([np.nan, 2], 1).tolist() == [False, False]
    with pytest.raises(ValueError, match="양의 정수"):
        rma([1, 2], 0)
    assert events_from_conditions(candles([1, 2]), [np.nan, True], [False, False]) == [event(1)]


def test_supertrend_and_utbot_reversals_hand_oracle() -> None:
    data = candles([10, 13, 7, 15])
    line, direction = supertrend(data, factor=1, atr_period=1)
    np.testing.assert_allclose(line, [12, 9, 14, 6])
    assert direction.tolist() == [1, -1, 1, -1]
    stop, buy, sell = utbot(data, key_value=1, atr_period=1)
    np.testing.assert_allclose(stop, [8, 9, 14, 6])
    assert buy.tolist() == [False, False, False, True]
    assert sell.tolist() == [False, False, True, False]


def test_registry_emits_original_condition_bars_without_filling_orders() -> None:
    result = compute_oracle("ema_cross", candles([2, 1, 3, 1]), {"fast": 1, "slow": 2})
    assert [(row.bar_time, row.direction) for row in result] == [
        (at(1), "short"),
        (at(2), "long"),
        (at(3), "short"),
    ]
    assert all(
        row.confirmed_at == row.bar_time + timedelta(hours=1) and row.display_time == row.bar_time
        for row in result
    )
    offset = compute_oracle(
        "ema_cross", candles([2, 1, 3, 1]), {"fast": 1, "slow": 2, "marker_offsets": {"long": -2}}
    )
    assert offset[1].display_time == at(0)
    with pytest.raises(ValueError, match="oracle이 없습니다"):
        compute_oracle("unreviewed", candles([1, 2]))
    data = candles([1, 2])
    data.loc[at(1), "high"] = np.nan
    assert np.isnan(source_values(data, "hl2")[1])


def test_oracles_do_not_import_pine_execution_or_app_settings() -> None:
    source = Path(__file__).parents[2] / "scripts" / "pine_validation" / "oracles.py"
    tree = ast.parse(source.read_text())
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
        elif isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
    assert imported
    assert not any(name.startswith("src.") for name in imported)

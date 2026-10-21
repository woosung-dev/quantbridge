"""성과 측정의 시간 경계·비용·후보 선택 시점을 실제 엔진으로 확인한다."""

from decimal import Decimal

import pandas as pd
import pytest

from scripts.pine_validation.evaluation import evaluate_performance, validate_evaluation

SOURCE = """//@version=5
indicator("Evaluation")
plotshape(bar_index % 2 == 0)
plotshape(bar_index % 2 == 1)
"""
BINDINGS = [
    {"function": "plotshape", "line": 3, "direction": "long"},
    {"function": "plotshape", "line": 4, "direction": "short"},
]
WINDOW = {"start": "2020-01-03T00:00:00Z", "end": "2020-01-15T00:00:00Z"}
PLAN = {
    "registered_at": "2020-02-01T00:00:00Z",
    "validation_start": "2020-01-07T00:00:00Z",
    "holdout_start": "2020-01-11T00:00:00Z",
    "init_cash": "10000",
    "position_size_pct": "20",
    "fees": "0.00055",
    "slippage": "0.00014",
    "cost_basis": "fixture cost assumption",
}


def frame():
    return pd.DataFrame(
        {"open": 100, "high": 110, "low": 90, "close": 100, "volume": 1},
        index=pd.date_range("2020-01-01", periods=14, freq="D", tz="UTC"),
    )


def test_each_split_has_fresh_positions_prior_history_only_and_explicit_costs():
    result = evaluate_performance(SOURCE, BINDINGS, frame(), {}, "1d", WINDOW, PLAN)
    assert result["status"] == "completed"
    assert result["holdout_status"] == "retrospective_not_untouched"
    assert result["funding_status"] == "not_provided"
    assert result["assumptions"]["position_size_pct"] == "20"
    assert len(result["runs"]) == 8
    for run in result["runs"]:
        assert run["status"] == "ok"
        assert run["execution_end"] == run["window"]["end"]
        assert run["history_start"] == "2020-01-01T00:00:00+00:00"
        assert run["trades"]
        assert all(trade["entry_time"] > run["window"]["start"] for trade in run["trades"])
        assert all(trade["entry_time"] < run["window"]["end"] for trade in run["trades"])
        assert Decimal(run["metrics"]["net_pnl"]) < 0
        assert Decimal(run["metrics"]["total_fees"]) > 0
        assert Decimal(run["metrics"]["total_slippage"]) > 0
        assert run["metrics"]["total_funding"] is None
    base, stress = result["runs"][:2]
    assert Decimal(stress["metrics"]["net_pnl"]) < Decimal(base["metrics"]["net_pnl"])


def test_future_prices_cannot_change_training_measurement():
    original = frame()
    changed = original.copy()
    changed.loc[changed.index >= PLAN["validation_start"], ["open", "high", "low", "close"]] *= 4
    first = evaluate_performance(SOURCE, BINDINGS, original, {}, "1d", WINDOW, PLAN)
    second = evaluate_performance(SOURCE, BINDINGS, changed, {}, "1d", WINDOW, PLAN)
    assert first["runs"][:2] == second["runs"][:2]


def test_observed_funding_is_applied_but_not_called_complete():
    funding = pd.Series([Decimal("0.01")], index=pd.DatetimeIndex(["2020-01-04T12:00:00Z"]))
    result = evaluate_performance(
        SOURCE, BINDINGS, frame(), {}, "1d", WINDOW, PLAN, funding_rates=funding
    )
    assert result["funding_status"] == "observed_settlements_only"
    assert Decimal(result["runs"][0]["metrics"]["total_funding"]) != 0
    assert result["runs"][0]["metrics"]["funding_data_incomplete"] is None


@pytest.mark.parametrize(
    "key,value",
    [
        ("fees", "NaN"),
        ("fees", "-1"),
        ("slippage", "Infinity"),
        ("init_cash", "0"),
        ("position_size_pct", "101"),
        ("holdout_start", "2020-01-06T00:00:00Z"),
        ("validation_start", "2020-01-07T12:00:00Z"),
    ],
)
def test_invalid_or_non_daily_aligned_plan_is_rejected(key, value):
    with pytest.raises(ValueError):
        validate_evaluation({**PLAN, key: value}, WINDOW)


def test_funding_file_requires_matching_hash_and_unique_finite_observations(tmp_path):
    import hashlib

    from scripts.pine_validation.evaluation import load_funding

    path = tmp_path / "funding.csv"
    provenance = {
        "file": "funding.csv",
        "symbol": "BYBIT:BTCUSDT.P",
        "source": "fixture",
        "observed_at": "2020-02-01T00:00:00Z",
    }
    path.write_text("time,rate\n2020-01-01T00:00:00Z,0.001\n")
    provenance["sha256"] = "0" * 64
    with pytest.raises(ValueError, match="hash"):
        load_funding(provenance, tmp_path)
    provenance["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
    rates, verified = load_funding(provenance, tmp_path)
    assert list(rates) == [Decimal("0.001")]
    assert verified == provenance
    for body in (
        "time,rate\n",
        "time,rate\n2020-01-01T00:00:00Z,NaN\n",
        "time,rate\n2020-01-01T00:00:00Z,0.1\n2020-01-01T00:00:00Z,0.1\n",
    ):
        path.write_text(body)
        provenance["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        with pytest.raises(ValueError):
            load_funding(provenance, tmp_path)

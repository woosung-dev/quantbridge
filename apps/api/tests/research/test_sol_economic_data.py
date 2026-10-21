"""경제 시세의 출처·기간·정밀 집계·재사용 표시 및 독립 집계 계약."""

from __future__ import annotations

import json
import sys
from copy import deepcopy
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.research.data import ASSETS, TIMEFRAMES, digest, json_write
from tools.research.sol_economic_data import (
    create_snapshot,
    economic_verdict,
    load_economic_cell,
    load_snapshot,
    signal_trace_digest,
    stress_scenarios,
    summarize_strategy_results,
)


@pytest.fixture
def sources(tmp_path: Path) -> tuple[Path, Path]:
    parent_dir, execution_dir = tmp_path / "parent", tmp_path / "execution"
    parent_dir.mkdir()
    execution_dir.mkdir()
    start = pd.Timestamp("2026-01-01", tz="UTC")
    end = start + pd.Timedelta(days=2)
    child_start = start + pd.Timedelta(days=1)
    index = pd.date_range(start, end, freq="1min", inclusive="left")
    minute = pd.DataFrame(
        {"open": "100", "high": "101", "low": "99", "close": "100", "volume": 1}, index=index
    )
    manifest = {
        "schema_version": 1,
        "exchange": "bybit",
        "category": "linear",
        "start": str(start),
        "end_exclusive": str(end),
        "warmup_bars": 0,
        "files": [],
        "funding": {},
    }
    children = []
    for symbol in ASSETS:
        for timeframe, (_, frequency) in TIMEFRAMES.items():
            parent = (
                minute.astype(float)
                .resample(frequency)
                .agg(
                    {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
                )
            )
            if timeframe == "4h":
                parent["volume"] += 0.01
            path = parent_dir / f"{symbol}-{timeframe}.csv"
            parent.to_csv(path, index_label="timestamp")
            manifest["files"].append(
                {
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "path": path.name,
                    "sha256": digest(path),
                    "start": str(start),
                    "end_exclusive": str(end),
                    "bars": len(parent),
                }
            )
        rates = pd.DataFrame(
            {"timestamp": pd.date_range(start, end, freq="8h", inclusive="left"), "rate": "0.0001"}
        )
        path = parent_dir / f"{symbol}-funding.csv"
        rates.to_csv(path, index=False)
        manifest["funding"][symbol] = {
            "path": path.name,
            "sha256": digest(path),
            "interval_minutes": 480,
            "count": len(rates),
        }
        child = minute.loc[minute.index >= child_start]
        path = execution_dir / f"{symbol}-1m.csv"
        child.to_csv(path, index_label="timestamp")
        children.append(
            {"symbol": symbol, "path": path.name, "sha256": digest(path), "bars": len(child)}
        )
    parent_path = parent_dir / "dataset.json"
    json_write(parent_path, manifest)
    execution_path = execution_dir / "execution-dataset.json"
    json_write(
        execution_path,
        {
            "exchange": "bybit",
            "category": "linear",
            "resolution": "1min",
            "start": str(child_start),
            "end_exclusive": str(end),
            "parent_dataset_sha256": digest(parent_path),
            "files": children,
        },
    )
    return parent_path, execution_path


def test_snapshot_is_reproducible_and_does_not_change_originals(
    sources: tuple[Path, Path], tmp_path: Path
) -> None:
    before = [digest(p) for p in sources]
    first = create_snapshot(*sources, tmp_path / "snapshot1")
    second = create_snapshot(*sources, tmp_path / "snapshot2")
    assert first == second
    assert [digest(p) for p in sources] == before
    assert first["holdout_status"] == "retrospective_not_untouched"
    assert first["promotable"] is False
    assert len(first["files"]) == 10
    assert all(item["ohlc_decimal_exact"] for item in first["aggregation_audit"])
    assert any(
        item["maximum_absolute_volume_difference"] != "0" for item in first["aggregation_audit"]
    )
    assert all(
        item["coverage"]["historical_schedule_independently_verified"] is False
        for item in first["files"]
        if item["role"] == "funding"
    )


def test_snapshot_never_overwrites_existing_destination(
    sources: tuple[Path, Path], tmp_path: Path
) -> None:
    target = tmp_path / "exists"
    target.mkdir()
    with pytest.raises(ValueError, match="덮어"):
        create_snapshot(*sources, target)


def test_source_hash_failure_happens_before_destination_creation(
    sources: tuple[Path, Path], tmp_path: Path
) -> None:
    path = sources[0].parent / "BTCUSDT-1h.csv"
    path.write_text(path.read_text() + "bad\n")
    with pytest.raises(ValueError, match="hash"):
        create_snapshot(*sources, tmp_path / "snapshot")
    assert not (tmp_path / "snapshot").exists()


def test_valid_hash_cannot_hide_missing_execution_candle(
    sources: tuple[Path, Path], tmp_path: Path
) -> None:
    manifest = json.loads(sources[1].read_text())
    path = sources[1].parent / manifest["files"][0]["path"]
    data = pd.read_csv(path).iloc[1:]
    data.to_csv(path, index=False)
    manifest["files"][0]["sha256"] = digest(path)
    manifest["files"][0]["bars"] = len(data)
    json_write(sources[1], manifest)
    with pytest.raises(ValueError, match="누락"):
        create_snapshot(*sources, tmp_path / "snapshot")


def test_valid_hash_cannot_hide_parent_execution_price_disagreement(
    sources: tuple[Path, Path], tmp_path: Path
) -> None:
    manifest = json.loads(sources[1].read_text())
    path = sources[1].parent / manifest["files"][0]["path"]
    data = pd.read_csv(path)
    data.loc[0, "high"] = 102
    data.to_csv(path, index=False)
    manifest["files"][0]["sha256"] = digest(path)
    json_write(sources[1], manifest)
    with pytest.raises(ValueError, match="OHLC"):
        create_snapshot(*sources, tmp_path / "snapshot")


def test_verified_snapshot_load_and_exact_cell_bounds(
    sources: tuple[Path, Path], tmp_path: Path
) -> None:
    target = tmp_path / "snapshot"
    manifest = create_snapshot(*sources, target)
    assert load_snapshot(target / "snapshot.json") == manifest
    frame, funding, minute = load_economic_cell(
        target / "snapshot.json",
        "BTCUSDT",
        "4h",
        "2026-01-02T00:00Z",
        "2026-01-03T00:00Z",
        execution=True,
        warmup_bars=2,
    )
    assert len(frame) == 8
    assert len(funding) == 3
    assert minute is not None and len(minute) == 1440
    with pytest.raises(ValueError, match="완전히"):
        load_economic_cell(
            target / "snapshot.json",
            "BTCUSDT",
            "1h",
            "2026-01-01T00:00Z",
            "2026-01-03T00:00Z",
            execution=True,
            warmup_bars=0,
        )
    (target / "parent/BTCUSDT-1h.csv").write_text("tampered")
    with pytest.raises(ValueError, match="SHA256"):
        load_snapshot(target / "snapshot.json")


def test_economic_scenarios_do_not_change_funding_sign_or_method_score() -> None:
    assert [s["id"] for s in stress_scenarios()] == [
        "baseline",
        "fees_x2",
        "slippage_x2",
        "funding_x2",
    ]
    metrics = {
        "total_return": ".2",
        "max_drawdown": "-.1",
        "profit_factor": "1.5",
        "funding_data_incomplete": False,
    }
    result = economic_verdict(metrics, 30)
    assert result["passed"]
    assert result["method_quality_score"] is None
    assert result["promotable"] is False
    assert not economic_verdict(metrics, 29)["passed"]
    assert not economic_verdict({**metrics, "funding_data_incomplete": None}, 30)["passed"]
    with pytest.raises(ValueError, match="유한"):
        economic_verdict({**metrics, "total_return": "NaN"}, 30)


def test_signal_dedup_keeps_hold_timing_and_ignores_cost_or_fill_noise() -> None:
    trace = [
        {
            "type": "intent",
            "bar_index": 0,
            "timestamp": "2026-01-01T00:00Z",
            "action": "hold",
            "position": "flat",
        },
        {"type": "intent", "bar_index": 1, "timestamp": "2026-01-01T01:00Z", "action": "long"},
    ]
    same = [{"type": "fill", "price": "101"}, *deepcopy(trace)]
    same[1]["position"] = "long"
    assert signal_trace_digest(trace) == signal_trace_digest(same)
    moved = deepcopy(trace)
    moved[1]["action"] = "hold"
    assert signal_trace_digest(trace) != signal_trace_digest(moved)
    with pytest.raises(ValueError, match="중복"):
        signal_trace_digest(trace + trace)
    with pytest.raises(ValueError, match="빈"):
        signal_trace_digest([])


def test_strategy_summary_deduplicates_identical_signals_and_separates_cost_scenarios() -> None:
    record = {
        "strategy_id": "01",
        "cell_id": "BTC-1h",
        "scenario": "baseline",
        "signal_sha256": "abc",
        "metrics": {"total_return": ".2", "max_drawdown": "-.1", "profit_factor": "1.5"},
        "closed_trades": 30,
    }
    stress = {**deepcopy(record), "scenario": "fees_x2"}
    stress["metrics"]["total_return"] = "-.1"
    summary = summarize_strategy_results([record, deepcopy(record), stress])[0]
    assert summary["scenarios"]["baseline"]["unique_signal_cells"] == 1
    assert summary["scenarios"]["baseline"]["median_net_return"] == "0.2"
    assert summary["scenarios"]["fees_x2"]["minimum_net_return"] == "-0.1"
    assert summary["all_stress_scenarios_present"] is False
    conflicting = deepcopy(record)
    conflicting["metrics"]["total_return"] = ".8"
    with pytest.raises(ValueError, match="다릅니다"):
        summarize_strategy_results([record, conflicting])

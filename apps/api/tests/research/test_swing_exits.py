"""새 청산 비교의 소스·기간·데이터·재개·거래 집계 계약. DB 미사용."""

import ast
import hashlib
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.research import swing_exits, swing_signals
from tools.research.catalogue import candidates, source_for
from tools.research.cli import cells
from tools.research.data import digest, json_write


def minute_frame():
    return pd.DataFrame(
        {
            "open": ["100"] * 4,
            "high": ["101"] * 4,
            "low": ["99"] * 4,
            "close": ["100"] * 4,
            "volume": ["10"] * 4,
        },
        index=pd.date_range("2026-01-01", periods=4, freq="1min", tz="UTC"),
    )


def test_all_hypotheses_preserve_entry_expressions_and_remove_position_dependent_exit():
    entry_sources = []
    for candidate in candidates():
        original = source_for(candidate)
        transformed, metadata = swing_signals.entry_source(candidate)
        before, after = ast.parse(original), ast.parse(transformed)
        original_on_bar, new_on_bar = before.body[-1], after.body[-1]
        assert ast.dump(ast.Module(body=original_on_bar.body[:10], type_ignores=[])) == ast.dump(
            ast.Module(body=new_on_bar.body[:10], type_ignores=[])
        )
        assert [ast.dump(node) for node in original_on_bar.body[-3:]] == [
            ast.dump(node) for node in new_on_bar.body[-3:]
        ]
        assert [ast.dump(node) for node in before.body[:-1]] == [
            ast.dump(node) for node in after.body[:-1]
        ]
        assert not any(
            isinstance(node, ast.Name) and node.id in {"position", "side", "risk_exit"}
            for node in ast.walk(new_on_bar)
        )
        assert metadata["original_source_sha256"] != metadata["entry_source_sha256"]
        assert metadata["original_source_sha256"] == hashlib.sha256(original.encode()).hexdigest()
        entry_sources.append(transformed)
    assert len(set(entry_sources)) == 100


def test_template_anchor_drift_blocks_transformation(monkeypatch):
    monkeypatch.setattr(
        swing_signals,
        "source_for",
        lambda _: "def on_bar(ctx, state):\n    return {'action':'long'}\n",
    )
    with pytest.raises(ValueError, match="앵커"):
        swing_signals.entry_source({})


@pytest.mark.parametrize(
    "mutation", ["missing_first", "missing_middle", "duplicate", "out_of_order"]
)
def test_one_minute_requires_every_requested_candle(mutation):
    frame = minute_frame()
    if mutation == "missing_first":
        frame = frame.iloc[1:]
    elif mutation == "missing_middle":
        frame = frame.drop(frame.index[2])
    elif mutation == "duplicate":
        frame = pd.concat([frame, frame.iloc[[-1]]])
    else:
        frame = frame.iloc[::-1]
    with pytest.raises(ValueError, match="기간 불일치"):
        swing_exits.validate_execution(
            frame, pd.Timestamp("2026-01-01", tz="UTC"), pd.Timestamp("2026-01-01T00:04Z")
        )


@pytest.mark.parametrize(
    "column,value", [("open", "nan"), ("volume", "-1"), ("high", "98"), ("close", "inf")]
)
def test_one_minute_rejects_nonfinite_and_impossible_prices(column, value):
    frame = minute_frame()
    frame.loc[frame.index[0], column] = value
    with pytest.raises(ValueError):
        swing_exits.validate_execution(
            frame, pd.Timestamp("2026-01-01", tz="UTC"), pd.Timestamp("2026-01-01T00:04Z")
        )


def test_freeze_download_resumes_exact_public_requests_without_another_network_call(
    tmp_path, monkeypatch
):
    start = pd.Timestamp("2026-01-01", tz="UTC")
    end = start + pd.Timedelta(minutes=4)
    calls = []

    def public_api(endpoint, **request):
        assert (
            endpoint == "kline" and request["interval"] == "1" and request["category"] == "linear"
        )
        calls.append(request)
        last = min(3, (request["end"] - int(start.timestamp() * 1000)) // 60_000)
        indices = range(last, max(-1, last - 2), -1)
        return {
            "symbol": "BTCUSDT",
            "list": [
                [
                    str(int((start + pd.Timedelta(minutes=index)).timestamp() * 1000)),
                    "100",
                    "101",
                    "99",
                    "100",
                    "10",
                    "1000",
                ]
                for index in indices
            ],
        }

    monkeypatch.setattr(swing_exits, "public_api", public_api)
    first = swing_exits.fetch_execution(tmp_path, "BTCUSDT", start, end)
    second = swing_exits.fetch_execution(tmp_path, "BTCUSDT", start, end)
    assert first.equals(second) and len(calls) == 2
    page = next((tmp_path / "pages" / "BTCUSDT").glob("*.json"))
    saved = json.loads(page.read_text())
    saved["rows"][0][1] = "200"
    json_write(page, saved)
    with pytest.raises(ValueError, match="hash"):
        swing_exits.fetch_execution(tmp_path, "BTCUSDT", start, end)


def test_new_comparison_never_automatically_reopens_original_final_period():
    parent = {"holdout_start": "2026-04-21T00:00:00Z", "end_exclusive": "2026-10-21T00:00:00Z"}
    start, end = swing_exits.development_window(parent)
    assert start == pd.Timestamp("2025-10-21T00:00:00Z")
    assert end == pd.Timestamp(parent["holdout_start"])
    assert all(pd.Timestamp(cell["end_exclusive"]) == end for cell in cells(parent))
    assert swing_exits.SWING_POLICY["promotable"] is False


def test_parent_ohlc_must_match_one_minute_aggregation_and_volume_difference_is_explicit(
    tmp_path, monkeypatch
):
    root, baseline = tmp_path / "new", tmp_path / "old"
    root.mkdir()
    baseline.mkdir()
    json_write(root / "execution-dataset.json", {})
    json_write(baseline / "dataset.json", {})
    minute = minute_frame().map(swing_exits.Decimal)
    parent = minute.resample("2min").agg(
        {"open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum"}
    )
    parent.loc[parent.index[0], "volume"] += 1
    monkeypatch.setattr(swing_exits, "TIMEFRAMES", {"2m": ("2", "2min")})
    monkeypatch.setattr(
        swing_exits,
        "load_dataset",
        lambda _: {"files": [{"symbol": "BTCUSDT", "timeframe": "2m", "path": "parent.csv"}]},
    )
    monkeypatch.setattr(
        swing_exits,
        "cached_candles",
        lambda path: parent if path.endswith("parent.csv") else minute,
    )
    manifest = {
        "start": "2026-01-01T00:00Z",
        "end_exclusive": "2026-01-01T00:04Z",
        "files": [{"symbol": "BTCUSDT", "path": "minute.csv"}],
    }
    audit = swing_exits.verify_parent_aggregation(root, baseline, manifest)
    assert audit["cells"][0]["ohlc_exact_match"] is True
    assert audit["cells"][0]["maximum_absolute_volume_difference"] == "1"
    parent.loc[parent.index[0], "high"] += 1
    with pytest.raises(ValueError, match="OHLC"):
        swing_exits.verify_parent_aggregation(root, baseline, manifest)


def test_baseline_reference_verifies_source_summary_and_original_result_bytes(tmp_path):
    path = tmp_path / "result.json"
    json_write(
        path,
        {
            "job_hash": "job",
            "metrics": {"total_return": "0.1"},
            "trades": [{"status": "closed"}, {"status": "open"}],
        },
    )
    record = {
        "job_hash": "job",
        "source_sha256": "source",
        "result_path": path.name,
        "result_sha256": digest(path),
        "metrics": {"total_return": "0.1"},
        "engine": {"old": True},
        "acceptance": {"passed": False},
    }
    reference = swing_exits.baseline_reference(
        tmp_path, record, {"original_source_sha256": "source"}
    )
    assert reference["kind"] == "referenced_existing_result_not_rerun"
    assert reference["closed_position_episodes"] == 1
    with pytest.raises(ValueError, match="소스"):
        swing_exits.baseline_reference(tmp_path, record, {"original_source_sha256": "other"})
    path.write_text(path.read_text() + " ")
    with pytest.raises(ValueError, match="hash"):
        swing_exits.baseline_reference(tmp_path, record, {"original_source_sha256": "source"})


def test_result_resume_and_partial_fill_count_do_not_inflate_closed_positions(
    tmp_path, monkeypatch
):
    from src.backtest.engine import swing_risk_adapter

    root, baseline = tmp_path / "new", tmp_path / "baseline"
    root.mkdir()
    baseline.mkdir()
    json_write(root / "execution-dataset.json", {})
    json_write(baseline / "dataset.json", {})
    calls = []

    def runner(*args, **kwargs):
        calls.append(kwargs["exit_policy"])
        baseline_mode = kwargs["exit_policy"] == "source"
        return {
            "metrics": {
                "total_return": "0.1" if baseline_mode else "0.2",
                "profit_factor": "2",
                "max_drawdown": "-0.2" if baseline_mode else "-0.1",
                "funding_data_incomplete": None,
            },
            "trades": [{"status": "closed"}],
            "fill_events": [{"reason": "partial"}, {"reason": "trailing"}],
            "comparison_metrics": {
                "parent_close_max_drawdown": "-0.20" if baseline_mode else "-0.09"
            },
        }

    monkeypatch.setattr(swing_risk_adapter, "run_swing_risk_backtest", runner)
    monkeypatch.setattr(swing_exits, "cell_inputs", lambda *args: (None, None, None))
    reference = {
        "job_hash": "old",
        "result_sha256": "hash",
        "metrics": {"total_return": "0.1", "max_drawdown": "-0.2"},
    }
    candidate = candidates()[0]
    cell = {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "months": 3,
        "start": "2026-01-21T00:00Z",
        "end_exclusive": "2026-04-21T00:00Z",
    }
    first = swing_exits.run_cell(
        root, baseline, {}, {}, candidate, cell, {"image_id": "frozen-image"}, reference
    )
    assert first["status"] == "completed" and first["closed_position_episodes"] == 1
    assert first["acceptance"]["checks"]["at_least_30_closed_trades"] is False
    assert first["comparison"]["delta_parent_close_absolute_max_drawdown"] == "-0.11"
    assert (
        swing_exits.run_cell(
            root, baseline, {}, {}, candidate, cell, {"image_id": "frozen-image"}, reference
        )["job_hash"]
        == first["job_hash"]
    )
    assert calls == ["source", "swing"]
    assert (
        first["comparison"]["baseline"]["kind"]
        == "executed_original_source_exits_on_same_1m_ledger"
    )
    assert first["comparison"]["delta_total_return"] == "0.1"
    result_path = root / first["result_path"]
    result_path.write_text(result_path.read_text() + " ")
    with pytest.raises(ValueError, match="변조"):
        swing_exits.run_cell(
            root, baseline, {}, {}, candidate, cell, {"image_id": "frozen-image"}, reference
        )


def test_report_counts_only_current_frozen_experiment_and_rejects_changed_result(tmp_path):
    json_write(
        tmp_path / "experiment.json",
        {"engine": {"version": "new"}, "execution_dataset_sha256": "data"},
    )
    result_path = tmp_path / "result.json"
    json_write(result_path, {"result": {"trades": []}})
    record = {
        "job_hash": "new",
        "engine": {"version": "new"},
        "execution_dataset_sha256": "data",
        "status": "completed",
        "candidate_id": "hyp",
        "cell": {"timeframe": "1h"},
        "metrics": {"total_return": "0.1"},
        "acceptance": {"passed": True},
        "comparison": {"baseline": {"acceptance": {"passed": False}}, "delta_total_return": "0.05"},
        "result_path": result_path.name,
        "result_sha256": digest(result_path),
    }
    swing_exits.append_journal(tmp_path / "swing-journal.jsonl", record)
    swing_exits.append_journal(
        tmp_path / "swing-journal.jsonl",
        {**record, "job_hash": "old", "engine": {"version": "old"}},
    )
    report = swing_exits.write_report(tmp_path)
    assert report["completed"] == 1 and report["promotable"] is False
    assert report["by_timeframe"]["1h"]["new_passing_cells"] == 1
    result_path.write_text("changed")
    with pytest.raises(ValueError, match="변조"):
        swing_exits.write_report(tmp_path)


def test_pilot_cannot_resume_after_policy_or_engine_change(tmp_path, monkeypatch):
    root, baseline = tmp_path / "new", tmp_path / "baseline"
    root.mkdir()
    baseline.mkdir()
    for path in [
        root / "execution-dataset.json",
        baseline / "dataset.json",
        baseline / "batch.json",
    ]:
        json_write(path, {})
    json_write(root / "experiment.json", {"engine": "previous"})
    monkeypatch.setattr(swing_exits, "load_dataset", lambda _: {})
    monkeypatch.setattr(swing_exits, "load_execution_dataset", lambda *args: {})
    monkeypatch.setattr(swing_exits, "baseline_records", lambda _: ({"engine": "old"}, {}))
    monkeypatch.setattr(swing_exits, "engine_identity", lambda: {"new": "engine"})
    with pytest.raises(ValueError, match="동결 실험"):
        swing_exits.run_batch(root, baseline, pilot=True)


def test_serial_batch_requires_actual_pilot_records_beyond_summary_count(tmp_path):
    json_write(tmp_path / "swing-pilot.json", {"completed": 120, "experiment_sha256": "claim"})
    parent = {"holdout_start": "2026-04-21T00:00:00Z", "end_exclusive": "2026-10-21T00:00:00Z"}
    with pytest.raises(ValueError, match="실제 master"):
        swing_exits.validate_pilot_evidence(tmp_path, {}, parent)

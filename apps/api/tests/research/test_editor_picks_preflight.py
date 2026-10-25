"""Pine 정적 거절과 독립 모델 실행을 섞지 않고 실패 분모를 보존한다."""

import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
from tools.research.editor_picks import execution, report
from tools.research.editor_picks.common import identity, sha, write


@pytest.fixture
def rejected_source(tmp_path, monkeypatch):
    original = b"//@version=5\nindicator('source')\nplot(close)\n"
    path = tmp_path / "sources/one.pine"
    path.parent.mkdir()
    path.write_bytes(original)
    row = {"id": "one", "status": "unsupported", "source_sha256": sha(original)}
    write(tmp_path / "screening/one.json", row)
    item = {
        "id": "one",
        "source_file": "sources/one.pine",
        "source_sha256": sha(original),
        "pine_preflight": {
            "status": "unsupported",
            "source_sha256": sha(original),
            "evidence_file": "screening/one.json",
            "evidence_sha256": sha((tmp_path / "screening/one.json").read_bytes()),
        },
    }
    write(tmp_path / "cohort.json", {"target": 1, "items": [item]})
    write(tmp_path / "data/dataset.json", {"end": "2026-10-24T00:00:00+00:00"})
    monkeypatch.setattr(execution, "implementation", lambda: {})
    original_artifact = execution.artifact

    def artifact(root, candidate, arm):
        if arm == "pine":
            return original_artifact(root, candidate, arm)
        if arm == "terra":
            return "trusted synthetic test source", "python", "f" * 64
        raise ValueError("completed_generation_missing")

    monkeypatch.setattr(execution, "artifact", artifact)
    return item


def test_rejected_pine_does_not_block_independent_terra_plan(tmp_path, rejected_source):
    frozen = execution.plan(tmp_path)
    assert frozen["artifacts"]["one"]["pine"] == {
        "preflight_failure": rejected_source["pine_preflight"]
    }
    assert frozen["artifacts"]["one"]["terra"]["language"] == "python"
    assert len(frozen["jobs"]) == frozen["expected_cells"] == 108
    with pytest.raises(ValueError, match="pine_static_preflight_failed"):
        execution.artifact(tmp_path, rejected_source, "pine")


def test_preflight_receipt_never_reads_market_data_or_requests_runtime(
    tmp_path, rejected_source, monkeypatch
):
    frozen = execution.plan(tmp_path)

    def forbidden(*args, **kwargs):
        pytest.fail("사전검사에서 거절한 원문은 실행하면 안 됩니다")

    monkeypatch.setattr(execution, "data", forbidden)
    monkeypatch.setattr("src.strategy.code_runtime.session.create_code_transport", forbidden)
    job = next(job for job in frozen["jobs"] if job["arm"] == "pine")
    evidence = execution.execute_job(tmp_path, frozen, job, {"pine": "p", "python": "y"})
    assert evidence["status"] == "failed"
    assert evidence["failure_stage"] == "static_preflight"
    assert evidence["source_present"] is True
    assert evidence["runtime_attempted"] is False
    assert execution.execute_job(tmp_path, frozen, job, {"pine": "p", "python": "y"}) == evidence
    write(
        tmp_path / "scope-audit.json",
        {
            "observed_at": "2026-10-24T07:13:14+00:00",
            "indicator_screening_counts": {"static_eligible": 11},
        },
    )
    write(tmp_path / "generation-policy.json", {"active_generation_arms": ["terra"]})
    summary = report.build(tmp_path, tmp_path / "full-plan.json")
    assert summary["status_counts"] == {"failed": 1, "not_run": 107}
    assert summary["runtime_evidence"]["pine"] == {
        "requested_cells": 0,
        "requested_originals": 0,
        "originals_with_completed_cells": 0,
        "originals_with_all_cells_completed": 0,
        "static_preflight_rejected_cells": 1,
        "legacy_unknown_request_cells": 0,
    }
    assert summary["source_acquisition"]["indicator_screening_counts"] == {"static_eligible": 11}
    assert summary["source_acquisition"]["observed_at"] == "2026-10-24T07:13:14+00:00"
    assert (
        summary["source_acquisition"]["screening_counts_scope"]
        == "historical_acquisition_snapshot_not_current_cohort_or_execution"
    )
    assert summary["generation_policy"]["active_generation_arms"] == ["terra"]
    assert summary["complete"] is False


@pytest.mark.parametrize("which", ["source", "screening"])
def test_frozen_preflight_rejects_tampered_original_or_screening(tmp_path, rejected_source, which):
    frozen = execution.plan(tmp_path)
    path = tmp_path / ("sources/one.pine" if which == "source" else "screening/one.json")
    path.write_text("changed")
    job = next(job for job in frozen["jobs"] if job["arm"] == "pine")
    with pytest.raises(ValueError, match="SHA256"):
        execution.execute_job(tmp_path, frozen, job, {"pine": "p", "python": "y"})


@pytest.mark.parametrize("status", ["static_eligible", "excluded", "screen_pending"])
def test_unfinished_or_eligible_rows_cannot_be_called_static_rejections(
    tmp_path, rejected_source, status
):
    rejected_source["pine_preflight"]["status"] = status
    with pytest.raises(ValueError, match="Pine 사전검사"):
        execution.pine_preflight_failure(tmp_path, rejected_source)


@pytest.mark.parametrize(
    "row",
    [
        {"id": "other", "status": "unsupported"},
        {"id": "one", "status": "unsupported"},
    ],
)
def test_rejection_proof_cannot_reference_another_or_unbound_original(
    tmp_path, rejected_source, row
):
    write(tmp_path / "screening/one.json", row)
    rejected_source["pine_preflight"]["evidence_sha256"] = sha(
        (tmp_path / "screening/one.json").read_bytes()
    )
    with pytest.raises(ValueError, match="실제 증거"):
        execution.pine_preflight_failure(tmp_path, rejected_source)


def test_market_input_failure_is_not_counted_as_runtime_attempt(
    tmp_path, rejected_source, monkeypatch
):
    frozen = execution.plan(tmp_path)

    def invalid_data(*args):
        raise ValueError("trusted fixture input unavailable")

    monkeypatch.setattr(execution, "data", invalid_data)
    job = next(job for job in frozen["jobs"] if job["arm"] == "terra")
    evidence = execution.execute_job(tmp_path, frozen, job, {"pine": "p", "python": "y"})
    assert evidence["status"] == "failed"
    assert evidence["failure_stage"] == "input_preparation"
    assert evidence["runtime_attempted"] is False


def test_one_completed_cell_cannot_be_reported_as_all_36_completed(
    tmp_path, rejected_source, monkeypatch
):
    frozen = execution.plan(tmp_path)
    jobs = [job for job in frozen["jobs"] if job["arm"] == "terra"]
    evidence = {identity(jobs[0]): {"status": "completed", "runtime_attempted": True}}
    monkeypatch.setattr(report, "receipts", lambda *args: evidence)
    partial = report.build(tmp_path, tmp_path / "full-plan.json")["runtime_evidence"]["terra"]
    assert partial["originals_with_completed_cells"] == 1
    assert partial["originals_with_all_cells_completed"] == 0
    evidence.update(
        {identity(job): {"status": "completed", "runtime_attempted": True} for job in jobs}
    )
    complete = report.build(tmp_path, tmp_path / "full-plan.json")["runtime_evidence"]["terra"]
    assert complete["originals_with_all_cells_completed"] == 1


@pytest.mark.parametrize(
    "timeframe,months,available",
    [
        ("1h", 6, True),
        ("4h", 12, True),
        ("1h", 24, False),
        ("4h", 24, False),
        ("1d", 6, False),
    ],
)
def test_actual_window_history_controls_warmup_without_shortening_it(
    tmp_path, rejected_source, monkeypatch, timeframe, months, available
):
    rejected_source["warmup_bars"] = 3000
    write(tmp_path / "cohort.json", {"target": 1, "items": [rejected_source]})
    frozen = execution.plan(tmp_path)
    end = pd.Timestamp(frozen["dataset"]["end"])
    baseline_start = end - pd.DateOffset(months=24)
    delta = pd.Timedelta(timeframe)
    parent = pd.DataFrame(
        {"open": "100", "high": "101", "low": "99", "close": "100", "volume": "1"},
        index=pd.date_range(baseline_start - 1000 * delta, end, freq=timeframe, inclusive="left"),
    )
    empty_index = pd.DatetimeIndex([], tz="UTC")
    monkeypatch.setattr(
        execution,
        "data",
        lambda *args: {
            timeframe: parent,
            "1min": parent.iloc[:0],
            "funding": pd.Series(index=empty_index, dtype=object),
        },
    )
    observed = []

    def trusted_spy(source, language, frame, *args, **kwargs):
        observed.append(frame)
        raise RuntimeError("reached_trusted_backtest_spy")

    monkeypatch.setattr("src.strategy.code_runtime.backtest.run_code_backtest", trusted_spy)
    job = next(
        job
        for job in frozen["jobs"]
        if job["arm"] == "terra" and job["timeframe"] == timeframe and job["months"] == months
    )
    evidence = execution.execute_job(tmp_path, frozen, job, {"pine": "p", "python": "y"})
    assert bool(observed) is available
    assert evidence["runtime_attempted"] is False
    if available:
        start = end - pd.DateOffset(months=months)
        assert sum(observed[0].index < start) == 3000
        assert "reached_trusted_backtest_spy" in evidence["error"]
    else:
        assert "실제 준비봉" in evidence["error"]

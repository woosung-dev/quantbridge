"""완료 episode 통계·동결 코드·native 수출 근거의 회귀 검증."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from tools.research.editor_picks import execution, verification  # noqa: E402
from tools.research.editor_picks.common import identity, receipt, sha, write  # noqa: E402


def test_episode_metrics_group_partial_fills_and_use_initial_risk():
    payload = {
        "equity_curve": [{}] * 10,
        "trades": [
            {
                "trade_index": 0,
                "status": "closed",
                "pnl": "15",
                "entry_bar_index": 1,
                "exit_bar_index": 4,
                "exit_phase": "bar_open",
            },
            {
                "trade_index": 1,
                "status": "closed",
                "pnl": "-5",
                "entry_bar_index": 4,
                "exit_bar_index": 6,
                "exit_phase": "intrabar_unknown",
            },
            {
                "trade_index": 2,
                "status": "open",
                "pnl": "999",
                "entry_bar_index": 8,
                "exit_bar_index": None,
                "exit_phase": "intrabar_unknown",
            },
        ],
    }
    trace = [
        {
            "type": "fill",
            "kind": "entry",
            "generation": generation,
            "plan": {"risk": "2.5", "initial_qty": "4"},
        }
        for generation in (1, 2, 3)
    ]
    trace += [{"type": "fill", "kind": "partial_take_profit", "generation": 1}]
    assert execution.episode_metrics(payload, trace) == {
        "avg_closed_episode_r": "0.5",
        "closed_episode_win_rate_pct": "50",
        "exposure_minute_pct": "80",
        "closed_episodes": 2,
    }
    with pytest.raises(ValueError, match="초기 위험 근거"):
        execution.episode_metrics(payload, [])


def test_empty_episode_statistics_are_undefined_without_trades():
    assert execution.episode_metrics({"trades": [], "equity_curve": [{}]}, []) == {
        "avg_closed_episode_r": None,
        "closed_episode_win_rate_pct": None,
        "exposure_minute_pct": "0",
        "closed_episodes": 0,
    }


def test_frozen_artifact_mutation_is_rejected_before_execution(tmp_path, monkeypatch):
    cohort = {"items": [{"id": "one"}]}
    write(tmp_path / "cohort.json", cohort)
    frozen = {
        "cohort_file": "cohort.json",
        "cohort_sha256": sha((tmp_path / "cohort.json").read_bytes()),
        "implementation": {},
        "artifacts": {"one": {"pine": {"language": "pine", "source_sha256": "frozen"}}},
    }
    monkeypatch.setattr(execution, "implementation", lambda: {})
    monkeypatch.setattr(execution, "artifact", lambda *_: ("changed", "pine", "changed"))
    with pytest.raises(ValueError, match="동결한 생성물"):
        execution.execute_job(tmp_path, frozen, {"id": "one", "arm": "pine"}, {})
    assert not (tmp_path / "results").exists()


def test_completed_receipt_requires_raw_execution_files(tmp_path):
    job = {"id": "one", "arm": "pine"}
    frozen = {"jobs": [job], "artifacts": {"one": {"pine": {"source_sha256": "code"}}}}
    request = {"plan": identity(frozen), "job": job, "source_sha256": "code"}
    folder = tmp_path / "results" / identity(request)
    write(folder / "request.json", request)
    receipt(folder, request, "completed", job=job, action_sha256="fake", ledger_sha256="fake")
    with pytest.raises(ValueError, match="필수 원시 근거"):
        verification.receipts(tmp_path, frozen)


def test_receipt_job_hash_cannot_be_reused_for_another_request(tmp_path):
    job = {"id": "one", "arm": "pine"}
    frozen = {"jobs": [job]}
    request = {"plan": identity(frozen), "job": job}
    folder = tmp_path / "results" / identity(request)
    write(folder / "request.json", request)
    receipt(folder, {**request, "changed": True}, "failed", job=job)
    with pytest.raises(ValueError, match="다른 요청"):
        verification.receipts(tmp_path, frozen)


def test_native_export_requires_all_timeframes_and_unchanged_capture(tmp_path):
    with pytest.raises(ValueError, match="세 시간봉"):
        verification.native_export_gate(tmp_path, "one", {"native_windows": {}}, "pine", "code")
    windows = {}
    for tf in ("1h", "4h", "1d"):
        path = tmp_path / "native" / "one" / f"{tf}.json"
        write(path, {"raw": tf})
        windows[tf] = {
            "status": "checked_partial_window",
            "capture_sha256": sha(path.read_bytes()),
            "checks": {"pine": {"passed": True, "source_sha256": "code"}},
        }
    proof = {"native_windows": windows}
    verification.native_export_gate(tmp_path, "one", proof, "pine", "code")
    write(tmp_path / "native/one/1h.json", {"raw": "changed"})
    with pytest.raises(ValueError, match="SHA256"):
        verification.native_export_gate(tmp_path, "one", proof, "pine", "code")


def test_economic_exact_requires_matching_execution_images():
    job = {"id": "one", "arm": "terra"}
    pine_job = {**job, "arm": "pine"}
    images = {"pine": "sha256:pine", "python": "sha256:python"}
    row = {
        "status": "completed",
        "action_sha256": "actions",
        "ledger_sha256": "ledger",
        "execution_images": images,
    }
    completed = {identity(job): dict(row), identity(pine_job): dict(row)}
    assert verification.exact_cells(completed, [job], "terra", images) == 1
    completed[identity(job)]["execution_images"] = {**images, "python": "changed"}
    assert verification.exact_cells(completed, [job], "terra", images) == 0

"""완료 episode 통계·동결 코드·native 수출 근거의 회귀 검증."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from tools.research.editor_picks import execution, verification  # noqa: E402
from tools.research.editor_picks.common import (  # noqa: E402
    NATIVE_POLICY,
    identity,
    receipt,
    sha,
    write,
)


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
        verification.native_export_gate(
            tmp_path, "one", {"native_windows": {}}, "pine", "code", 1000
        )
    windows = {}
    for tf in ("1h", "4h", "1d"):
        path = tmp_path / "native" / "one" / f"{tf}.json"
        write(
            path,
            {"raw": tf, "collection_policy": dict(NATIVE_POLICY), "quota_popup_observed": False},
        )
        windows[tf] = {
            "status": "checked_partial_window",
            "capture_sha256": sha(path.read_bytes()),
            "warmup_bars": 1000,
            "checked_bars": 500,
            "bars": 1500,
            "metadata": {"total_received_bars": 1501, "full_study_prefix_covered": True},
            "checks": {"pine": {"passed": True, "source_sha256": "code", "prefix_bars": 1333}},
        }
    proof = {"native_windows": windows, "native_policy": dict(NATIVE_POLICY)}
    verification.native_export_gate(tmp_path, "one", proof, "pine", "code", 1000)
    write(tmp_path / "native/one/1h.json", {"raw": "changed"})
    with pytest.raises(ValueError, match="SHA256"):
        verification.native_export_gate(tmp_path, "one", proof, "pine", "code", 1000)


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


def native_proof(root):
    windows = {}
    for tf in ("1h", "4h", "1d"):
        path = root / f"native/one/{tf}.json"
        write(path, {"collection_policy": dict(NATIVE_POLICY), "quota_popup_observed": False})
        windows[tf] = {
            "status": "checked_partial_window",
            "capture_sha256": sha(path.read_bytes()),
            "warmup_bars": 1000,
            "checked_bars": 500,
            "bars": 1500,
            "metadata": {"total_received_bars": 5000, "full_study_prefix_covered": True},
            "checks": {"pine": {"passed": True, "source_sha256": "code", "prefix_bars": 1333}},
        }
    return {"native_policy": dict(NATIVE_POLICY), "native_windows": windows}


def test_basic_native_policy_includes_warmup_and_allows_bounded_ui(tmp_path):
    assert NATIVE_POLICY == {
        "account": "basic",
        "max_total_bars": 5000,
        "warmup_included": True,
        "history_request_mode": "bounded_ui",
    }
    proof = native_proof(tmp_path)
    verification.native_export_gate(tmp_path, "one", proof, "pine", "code", 1000)


@pytest.mark.parametrize("received", [5001, 1499, True, 5000.0, None])
def test_native_export_rejects_unproven_total_received_bar_bound(tmp_path, received):
    proof = native_proof(tmp_path)
    proof["native_windows"]["1h"]["metadata"]["total_received_bars"] = received
    with pytest.raises(ValueError, match="native 검증"):
        verification.native_export_gate(tmp_path, "one", proof, "pine", "code", 1000)


@pytest.mark.parametrize(
    "change",
    ["missing", "over_cap", "missing_warmup", "wrong_mode", "untyped_warmup", "untyped_cap"],
)
def test_native_export_rejects_missing_or_changed_account_policy(tmp_path, change):
    proof = native_proof(tmp_path)
    if change == "missing":
        del proof["native_policy"]
    elif change == "over_cap":
        proof["native_policy"]["max_total_bars"] = 5001
    elif change == "missing_warmup":
        proof["native_policy"]["warmup_included"] = False
    elif change == "wrong_mode":
        proof["native_policy"]["history_request_mode"] = "unbounded"
    elif change == "untyped_warmup":
        proof["native_policy"]["warmup_included"] = 1
    else:
        proof["native_policy"]["max_total_bars"] = 5000.0
    with pytest.raises(ValueError, match="한도"):
        verification.native_export_gate(tmp_path, "one", proof, "pine", "code", 1000)

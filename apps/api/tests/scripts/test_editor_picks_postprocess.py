"""후처리의 원시 불변·Sharpe 표시 의미·core 검증과 안전 위임을 확인한다."""

import copy
import importlib.util
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from tools.research.editor_picks import __main__ as core  # noqa: E402
from tools.research.editor_picks import remote, report, verification  # noqa: E402
from tools.research.editor_picks.common import identity, read, sha, write  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "editor_picks_postprocess", ROOT / "tools/scripts/editor-picks-postprocess.py"
)
postprocess = importlib.util.module_from_spec(spec)
spec.loader.exec_module(postprocess)
CORE_RECEIPTS = getattr(
    verification.receipts, "editor_picks_receipts_original", verification.receipts
)


@pytest.fixture(autouse=True)
def restore_reader(monkeypatch):
    monkeypatch.setattr(verification, "read", read)
    monkeypatch.setattr(verification, "identity", identity)
    monkeypatch.setattr(verification, "receipts", CORE_RECEIPTS)
    monkeypatch.setattr(report, "receipts", CORE_RECEIPTS)
    monkeypatch.setattr(report, "METRICS", report.METRICS)


@pytest.mark.parametrize(
    "convention,expected",
    (
        ("unavailable", None),
        ("unavailable_nonpositive_equity", None),
        ("tv_monthly_rfr2", "0"),
        ("tv_daily_rfr2", "0"),
        (None, "0"),
    ),
)
def test_projection_preserves_raw_bytes_and_all_other_verdict_fields(
    tmp_path, convention, expected
):
    original = {
        "metrics": {
            "sharpe_ratio": "0",
            "sharpe_convention": convention,
            "profit_factor": "1.1",
            "drawdown_curve": [[1, "-0.1"]],
            "buy_and_hold_curve": [[1, "1.2"]],
            "custom_curve": [1],
        },
        "status": "completed",
        "economic_verdict": {"passed": False},
        "action_sha256": "actions",
        "ledger_sha256": "ledger",
        "funding_status": "observed_settlements_only",
        "files": {"request.json": "hash"},
    }
    path = tmp_path / "receipt.json"
    write(path, original)
    before = path.read_bytes()
    assert postprocess.install() is read
    installed = verification.read
    assert postprocess.install() is read
    assert verification.read is installed
    projected = verification.read(path)
    expected_value = copy.deepcopy(original)
    for key in postprocess.CURVES:
        expected_value["metrics"].pop(key)
    expected_value["metrics"]["sharpe_ratio"] = expected
    assert projected == expected_value
    assert path.read_bytes() == before
    assert read(path) == original
    assert report.METRICS.count("sharpe_convention") == 1
    assert installed.postprocessing["calculation_rerun"] is False
    other = tmp_path / "other.json"
    write(other, original)
    assert verification.read(other) == original


def test_core_receipt_file_hash_validation_is_not_bypassed(tmp_path):
    job = {"id": "one", "arm": "pine"}
    frozen = {"jobs": [job]}
    request = {"plan": identity(frozen), "job": job, "images": {"pine": "image"}}
    folder = tmp_path / "results/cell"
    write(folder / "request.json", request)
    write(
        folder / "receipt.json",
        {
            "job_hash": identity(request),
            "job": job,
            "status": "failed",
            "files": {"request.json": sha((folder / "request.json").read_bytes())},
        },
    )
    postprocess.install()
    assert verification.receipts(tmp_path, frozen)[identity(job)]["status"] == "failed"
    with (folder / "request.json").open("a") as stream:
        stream.write(" ")
    with pytest.raises(ValueError, match="SHA256"):
        verification.receipts(tmp_path, frozen)
    assert verification.identity is identity


def test_two_real_receipts_hash_the_plan_only_twice_and_share_report_binding(tmp_path, monkeypatch):
    jobs = [{"id": str(index), "arm": "pine"} for index in range(2)]
    frozen = {"jobs": jobs}
    for job in jobs:
        request = {"plan": identity(frozen), "job": job, "images": {"pine": "image"}}
        folder = tmp_path / "results" / job["id"]
        write(folder / "request.json", request)
        write(
            folder / "receipt.json",
            {
                "job_hash": identity(request),
                "job": job,
                "status": "failed",
                "files": {"request.json": sha((folder / "request.json").read_bytes())},
            },
        )
    calls = []

    def counted_identity(value):
        calls.append(value)
        return identity(value)

    monkeypatch.setattr(verification, "identity", counted_identity)
    postprocess.install()
    installed = verification.receipts
    postprocess.install()
    assert verification.receipts is installed and report.receipts is installed
    result = report.receipts(tmp_path, frozen)
    assert set(result) == {identity(job) for job in jobs}
    assert sum(value is frozen for value in calls) == 2
    assert verification.identity is counted_identity
    calls.clear()
    assert verification.receipts(tmp_path, frozen) == result
    assert sum(value is frozen for value in calls) == 2


def test_equal_but_distinct_objects_still_use_original_identity(tmp_path, monkeypatch):
    frozen = {"jobs": []}
    other = copy.deepcopy(frozen)
    calls = []

    def counted_identity(value):
        calls.append(value)
        return identity(value)

    def original_receipts(root, plan):
        assert verification.identity(other) == identity(other)
        return {}

    monkeypatch.setattr(verification, "identity", counted_identity)
    monkeypatch.setattr(verification, "receipts", original_receipts)
    postprocess.install()
    verification.receipts(tmp_path, frozen)
    assert sum(value is other for value in calls) == 1
    assert sum(value is frozen for value in calls) == 2
    assert verification.identity is counted_identity


def test_receipts_reject_plan_mutation_and_restore_identity(tmp_path, monkeypatch):
    frozen = {"jobs": []}

    def mutate(root, plan):
        assert verification.identity(plan) == identity(frozen)
        plan["jobs"].append({"id": "changed", "arm": "pine"})
        return {}

    monkeypatch.setattr(verification, "receipts", mutate)
    postprocess.install()
    with pytest.raises(ValueError, match="동결 계획이 변경"):
        verification.receipts(tmp_path, frozen)
    assert verification.identity is identity


def test_receipts_restore_identity_after_original_error(tmp_path, monkeypatch):
    def fail(root, frozen):
        assert verification.identity(frozen) == identity(frozen)
        raise RuntimeError("original receipt failure")

    monkeypatch.setattr(verification, "receipts", fail)
    postprocess.install()
    with pytest.raises(RuntimeError, match="original receipt failure"):
        report.receipts(tmp_path, {"jobs": []})
    assert verification.identity is identity


@pytest.mark.parametrize("command", ("report", "export"))
def test_cli_delegates_original_postprocessing_arguments_only(tmp_path, monkeypatch, command):
    arguments = ["--run-dir", str(tmp_path), command, "--plan", "full-plan.json"]
    before = sys.argv
    captured = []
    monkeypatch.setattr(core, "main", lambda: captured.append(sys.argv[1:]) or 7)
    assert postprocess.main(arguments) == 7
    assert captured == [arguments]
    assert sys.argv is before


def test_remote_finalize_delegation_preserves_provenance_arguments(monkeypatch):
    arguments = [
        "remote",
        "finalize",
        "--run-dir",
        "runs/research",
        "--head",
        "head",
        "--run-id",
        "123",
        "--attempt",
        "1",
        "--input-sha",
        "digest",
        "--shards",
        "20",
    ]
    captured = []
    monkeypatch.setattr(remote, "main", lambda: captured.append(sys.argv[1:]) or 0)
    assert postprocess.main(arguments) == 0
    assert captured == [arguments[1:]]


@pytest.mark.parametrize(
    "arguments",
    (
        ["--run-dir", "runs/research", "execute"],
        ["--run-dir", "runs/research", "generate"],
        ["remote", "worker"],
        ["remote", "pack"],
    ),
)
def test_cli_rejects_calculation_generation_or_other_remote_actions(arguments, monkeypatch):
    def forbidden():
        raise AssertionError("후처리 밖의 core 호출")

    monkeypatch.setattr(core, "main", forbidden)
    monkeypatch.setattr(remote, "main", forbidden)
    with pytest.raises(SystemExit):
        postprocess.main(arguments)

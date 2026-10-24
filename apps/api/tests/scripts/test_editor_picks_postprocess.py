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


@pytest.fixture(autouse=True)
def restore_reader(monkeypatch):
    monkeypatch.setattr(verification, "read", read)
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

"""full 원격 native 배정·실제 종료·원시 proof의 인증 수거를 확인한다."""

import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.research.editor_picks import remote, report, verification
from tools.research.editor_picks.common import identity, read, sha, write


def prepare(root, count=4):
    write(root / "cohort.json", {"items": [{"id": str(index)} for index in range(count)]})
    frozen = {
        "phase": "full",
        "jobs": [],
        "cohort_file": "cohort.json",
        "cohort_sha256": sha((root / "cohort.json").read_bytes()),
    }
    write(root / "full-plan.json", frozen)
    return frozen


@pytest.mark.parametrize("economic_code,native_code,expected", ((0, 7, 7), (3, 0, 3), (0, 0, 0)))
def test_worker_assigns_native_sources_and_preserves_real_failure_codes(
    tmp_path, monkeypatch, economic_code, native_code, expected
):
    frozen = prepare(tmp_path)
    monkeypatch.setenv("GH_TOKEN", "private")
    monkeypatch.setenv("EDITOR_PICKS_RESEARCH_KEY", "private")
    calls = []

    def run(command, **kwargs):
        assert "GH_TOKEN" not in kwargs["env"]
        assert "EDITOR_PICKS_RESEARCH_KEY" not in kwargs["env"]
        calls.append(command)
        return SimpleNamespace(
            returncode=native_code
            if "verify" in command and command[-1] == "1"
            else 0
            if "verify" in command
            else economic_code
        )

    monkeypatch.setattr(remote.subprocess, "run", run)
    assert remote.worker(tmp_path, tmp_path / "full-plan.json", 1, 2) == expected
    assert [command[-1] for command in calls[1:]] == ["1", "3"]
    terminal = read(tmp_path / "terminal-1.json")
    assert terminal["actual_returncode"] == expected
    assert terminal["economic_returncode"] == economic_code
    assert terminal["native_returncodes"] == {"1": native_code, "3": 0}
    assert terminal["plan_sha256"] == identity(frozen)


def native_bundle(root, archive, *, wrong_plan=False):
    frozen = prepare(root, count=1)
    provenance = {
        "plan": "full-plan.json",
        "plan_sha256": identity(frozen),
        "head": "a" * 40,
        "run_id": "1",
        "attempt": "1",
        "input_sha256": "b" * 64,
        "shard": 0,
        "shards": 1,
    }
    write(
        root / "verification/0.json",
        {
            "id": "0",
            "plan_sha256": "wrong" if wrong_plan else identity(frozen),
            "native_windows": {},
        },
    )
    write(
        root / "terminal-0.json",
        {
            "actual_returncode": 0,
            "economic_returncode": 0,
            "native_returncodes": {"0": 0},
            "plan_sha256": identity(frozen),
        },
    )
    write(
        root / "worker-full-0.json",
        {
            "status": "finished",
            "plan_sha256": identity(frozen),
            "shard": 0,
            "shards": 1,
            "jobs_consumed": 0,
        },
    )
    remote.pack_result(root, archive, 0, provenance)
    return frozen, provenance


def test_native_raw_proof_is_authenticated_and_reconciliation_keeps_it_immutable(
    tmp_path, monkeypatch
):
    source = tmp_path / "source"
    archive = tmp_path / "result.tar.gz"
    frozen, provenance = native_bundle(source, archive)
    with tarfile.open(archive) as bundle:
        assert "native-checks/0.json" in bundle.getnames()
        assert not any(name.startswith("verification/") for name in bundle.getnames())
    destination = tmp_path / "received"
    remote.collect_result(archive, destination, provenance)
    write(destination / "full-plan.json", frozen)
    write(destination / "cohort.json", read(source / "cohort.json"))
    original = (destination / "native-checks/0.json").read_bytes()
    calls = []

    def reconcile(root, plan):
        calls.append((root, plan))
        write(root / "verification/0.json", {"derived": True})

    monkeypatch.setattr(verification, "reconcile", reconcile, raising=False)
    monkeypatch.setattr(report, "build", lambda *_: {"complete": True})
    expected = {key: value for key, value in provenance.items() if key != "shard"}
    assert remote.finalize(destination, destination / "full-plan.json", expected)["complete"]
    assert calls == [(destination, destination / "full-plan.json")]
    assert (destination / "native-checks/0.json").read_bytes() == original
    remote.collect_result(archive, destination, provenance)


def test_native_wrong_plan_is_rejected_before_any_merge(tmp_path):
    archive = tmp_path / "result.tar.gz"
    _, provenance = native_bundle(tmp_path / "source", archive, wrong_plan=True)
    destination = tmp_path / "received"
    with pytest.raises(ValueError, match="plan SHA"):
        remote.collect_result(archive, destination, provenance)
    assert not destination.exists()

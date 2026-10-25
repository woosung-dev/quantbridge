"""동결 선택이 원격 실행·인증 수거까지 유지되며 기본 형식은 보존되는지 검사한다."""

import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.research.editor_picks import __main__ as cli
from tools.research.editor_picks import execution, remote, report, verification
from tools.research.editor_picks.common import identity, read, write


def _plan_inputs(root):
    root.mkdir()
    write(root / "cohort.json", {"target": 1, "items": []})
    write(root / "data/dataset.json", {})


def test_plan_one_preserves_shape_two_is_hashed_and_verification_accepts_it(tmp_path, monkeypatch):
    serial, parallel = tmp_path / "serial", tmp_path / "parallel"
    _plan_inputs(serial)
    _plan_inputs(parallel)
    monkeypatch.setattr(execution, "implementation", lambda: {})
    monkeypatch.setattr(execution, "now", lambda: "fixed-time")
    first = execution.plan(serial)
    original_bytes = (serial / "full-plan.json").read_bytes()
    assert execution.plan(serial, workers=1) == first
    assert (serial / "full-plan.json").read_bytes() == original_bytes
    assert "execution_workers" not in first
    second = execution.plan(parallel, workers=2)
    assert second["execution_workers"] == 2
    assert {k: v for k, v in second.items() if k != "execution_workers"} == first
    assert identity(first) != identity(second)
    monkeypatch.setattr(verification, "implementation", lambda: {})
    assert verification.frozen_inputs(parallel, second) == read(parallel / "cohort.json")
    with pytest.raises(ValueError, match="동결"):
        execution.plan(serial, workers=2)


@pytest.mark.parametrize("workers", [0, 3, True, 2.0])
def test_plan_rejects_invalid_budget_before_reading_inputs(workers, tmp_path):
    with pytest.raises(ValueError, match="1개 또는 2개"):
        execution.plan(tmp_path / "missing", workers=workers)


@pytest.mark.parametrize("workers", [1, 2])
def test_remote_worker_uses_frozen_budget_only_for_economic_cli(workers, tmp_path, monkeypatch):
    write(tmp_path / "cohort.json", {"items": [{"id": "source"}]})
    from tools.research.editor_picks.common import sha

    frozen = {"phase": "full", "cohort_file": "cohort.json", "cohort_sha256": sha((tmp_path / "cohort.json").read_bytes())}
    if workers == 2:
        frozen["execution_workers"] = 2
    write(tmp_path / "full-plan.json", frozen)
    commands = []

    def run(command, **kwargs):
        commands.append(command)
        assert set(kwargs["env"]) <= {"PATH", "HOME", "LANG", "TRADING_ENCRYPTION_KEYS", "PINE_AST_CACHE_DIR"}
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(remote.subprocess, "run", run)
    assert remote.worker(tmp_path, tmp_path / "full-plan.json", 0, 1) == 0
    assert len(commands) == 2
    assert ("--workers" in commands[0]) == (workers == 2)
    if workers == 2:
        assert commands[0][-2:] == ["--workers", "2"]
    assert "verify" in commands[1] and "--workers" not in commands[1]
    terminal = read(tmp_path / "terminal-0.json")
    assert terminal.get("execution_workers", 1) == workers
    assert ("execution_workers" in terminal) == (workers == 2)
    assert terminal["economic_returncode"] == 0 and terminal["native_returncodes"] == {"source": 0}


@pytest.mark.parametrize("workers", [0, 3, True, 2.0])
def test_remote_rejects_malformed_frozen_budget_without_launch(workers, tmp_path):
    write(tmp_path / "plan.json", {"execution_workers": workers})
    with patch.object(remote.subprocess, "run") as run:
        with pytest.raises(ValueError, match="동결 실행"):
            remote.worker(tmp_path, tmp_path / "plan.json", 0, 1)
        run.assert_not_called()
    assert not list(tmp_path.glob("worker-*"))


def _bundle(
    root, destination, *, declared=2, allocation=None, terminal=None, cells=4, legacy_evidence=False
):
    root.mkdir()
    frozen = {"phase": "pilot", "jobs": [{"id": str(index)} for index in range(cells)]}
    if declared == 2:
        frozen["execution_workers"] = 2
    write(root / "pilot-plan.json", frozen)
    provenance = {"plan": "pilot-plan.json", "plan_sha256": identity(frozen), "head": "a" * 40, "run_id": "1", "attempt": "1", "input_sha256": "b" * 64, "shard": 0, "shards": 1}
    allocated = {"status": "finished", "plan_sha256": identity(frozen), "shard": 0, "shards": 1, "jobs_consumed": cells}
    ended = {"actual_returncode": 0, "plan_sha256": identity(frozen)}
    if declared == 2 and not legacy_evidence:
        allocated.update(workers=2, worker_processes=min(2, cells), process_start_method="spawn")
        ended["execution_workers"] = 2
    allocated.update(allocation or {})
    ended.update(terminal or {})
    write(root / "worker-pilot-0.json", allocated)
    write(root / "terminal-0.json", ended)
    archive = root / "result.tar.gz"
    remote.pack_result(root, archive, 0, provenance)
    destination.mkdir()
    write(destination / "pilot-plan.json", frozen)
    remote.collect_result(archive, destination, provenance)
    return provenance


@pytest.mark.parametrize("declared,cells", [(1, 4), (2, 4), (2, 1), (2, 0)])
def test_authenticated_parallel_or_legacy_completion_evidence(declared, cells, tmp_path, monkeypatch):
    target = tmp_path / "target"
    expected = _bundle(tmp_path / "source", target, declared=declared, cells=cells)
    monkeypatch.setattr(report, "build", lambda *args: {"complete": True})
    assert remote.finalize(target, target / "pilot-plan.json", expected)["complete"] is True


@pytest.mark.parametrize(
    "allocation,terminal",
    [
        ({"workers": 1}, {}),
        ({"workers": 2.0}, {}),
        ({"worker_processes": 1}, {}),
        ({"worker_processes": 3}, {}),
        ({"worker_processes": 2.0}, {}),
        ({"process_start_method": "fork"}, {}),
        ({}, {"execution_workers": 1}),
        ({}, {"execution_workers": 2.0}),
    ],
)
def test_authenticated_wrong_parallel_evidence_cannot_finalize(allocation, terminal, tmp_path, monkeypatch):
    target = tmp_path / "target"
    expected = _bundle(tmp_path / "source", target, allocation=allocation, terminal=terminal)
    monkeypatch.setattr(report, "build", lambda *args: {"complete": True})
    result = remote.finalize(target, target / "pilot-plan.json", expected)
    assert result["complete"] is False
    assert len(result["failures"]) == 1 and "2프로세스" in result["failures"][0]["error"]


def test_declared_parallel_plan_cannot_finalize_serial_allocation(tmp_path, monkeypatch):
    target = tmp_path / "target"
    expected = _bundle(tmp_path / "source", target, legacy_evidence=True)
    monkeypatch.setattr(report, "build", lambda *args: {"complete": True})
    result = remote.finalize(target, target / "pilot-plan.json", expected)
    assert result["complete"] is False and "2프로세스" in result["failures"][0]["error"]


@pytest.mark.parametrize("arguments,workers", [([], 1), (["--workers", "1"], 1), (["--workers", "2"], 2)])
def test_plan_cli_passes_explicit_or_default_budget(arguments, workers, tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "run_dir", lambda _: tmp_path)
    monkeypatch.setattr("sys.argv", ["research", "--run-dir", "fixture", "plan", *arguments])
    with patch.object(execution, "plan", return_value={"expected_cells": 108, "phase": "full"}) as plan:
        assert cli.main() == 0
        plan.assert_called_once_with(tmp_path, False, workers=workers)

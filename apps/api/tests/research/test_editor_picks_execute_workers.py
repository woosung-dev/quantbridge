"""신뢰 합성 셀로 독립 spawn·배정·종료를 검사한다. 전략과 Docker는 실행하지 않는다."""

import json
import multiprocessing
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from tools.research.editor_picks import __main__ as cli
from tools.research.editor_picks import execution
from tools.research.editor_picks.common import cached, identity, immutable, lock, receipt, write

_IMAGES = {"pine": "sha256:synthetic-pine", "python": "sha256:synthetic-python"}
_EXECUTE_JOBS = execution._execute_jobs


def _trusted_job(root, frozen, job, images):
    request = {"plan": identity(frozen), "job": job, "images": images}
    folder = root / "results" / identity(request)
    with lock(folder / ".lock"):
        previous = cached(folder, request)
        if previous is not None and previous["status"] != "interrupted":
            return previous
        immutable(folder / "request.json", request)
        if job.get("contract_error"):
            raise ValueError("synthetic_contract_error")
        write(root / "observed" / f"{job['index']}.json", {"pid": os.getpid()})
        (folder / "payload.json").write_text(json.dumps({"fixture_index": job["index"]}))
        return receipt(folder, request, job.get("status", "completed"), job=job)


def _trusted_spawn_batch(root, frozen, jobs, images):
    # spawn에서 재수입되는 신뢰 fixture만 교체한다. 실제 child 제어 흐름은 그대로 검사한다.
    with (
        patch.object(execution, "require_runtime", return_value=images),
        patch.object(execution, "execute_job", side_effect=_trusted_job),
    ):
        return _EXECUTE_JOBS(root, frozen, jobs, images)


def _plan(root, jobs):
    root.mkdir()
    path = root / "plan.json"
    write(path, {"phase": "pilot", "jobs": jobs})
    return path


def _proofs(root):
    return {
        value["job"]["index"]: (value["status"], value["files"])
        for path in (root / "results").glob("*/receipt.json")
        if (value := json.loads(path.read_bytes()))
    }


def test_two_spawn_lanes_preserve_assignment_failed_receipts_and_payloads(tmp_path, monkeypatch):
    jobs = [{"index": index, **({"status": "failed"} if index == 7 else {})} for index in range(14)]
    serial, parallel = tmp_path / "serial", tmp_path / "parallel"
    serial_plan, parallel_plan = _plan(serial, jobs), _plan(parallel, jobs)
    monkeypatch.setattr(execution, "require_runtime", lambda: _IMAGES)
    monkeypatch.setattr(execution, "execute_job", _trusted_job)
    expected = execution.execute(serial, serial_plan, 1, 3)
    assert "workers" not in expected
    monkeypatch.setattr(execution, "_execute_jobs", _trusted_spawn_batch)
    actual = execution.execute(parallel, parallel_plan, 1, 3, workers=2)
    assert actual["jobs_consumed"] == expected["jobs_consumed"] == 5
    assert actual["workers"] == actual["worker_processes"] == 2
    assert actual["process_start_method"] == "spawn"
    assert _proofs(serial) == _proofs(parallel)
    assert set(_proofs(parallel)) == {1, 4, 7, 10, 13}
    assert _proofs(parallel)[7][0] == "failed"
    pids = {json.loads(p.read_bytes())["pid"] for p in (parallel / "observed").glob("*.json")}
    assert len(pids) == 2 and os.getpid() not in pids
    assert pids.isdisjoint(child.pid for child in multiprocessing.active_children())
    assert len(list(parallel.glob("worker-*.json"))) == 1
    assert not list(parallel.glob("terminal-*")) and not (parallel / "verification").exists()


def test_child_contract_error_joins_other_lane_without_success_allocation(tmp_path, monkeypatch):
    root = tmp_path / "error"
    plan = _plan(root, [{"index": 0, "contract_error": True}, {"index": 1}, {"index": 2}, {"index": 3}])
    monkeypatch.setattr(execution, "require_runtime", lambda: _IMAGES)
    monkeypatch.setattr(execution, "_execute_jobs", _trusted_spawn_batch)
    with pytest.raises(ValueError, match="synthetic_contract_error"):
        execution.execute(root, plan, workers=2)
    assert set(_proofs(root)) == {1, 3}
    assert not list(root.glob("worker-*.json"))
    pids = {json.loads(p.read_bytes())["pid"] for p in (root / "observed").glob("*.json")}
    assert pids.isdisjoint(child.pid for child in multiprocessing.active_children())


def test_child_image_mismatch_prevents_cell_execution(monkeypatch, tmp_path):
    monkeypatch.setattr(execution, "require_runtime", lambda: {**_IMAGES, "pine": "changed"})
    with patch.object(execution, "execute_job") as job:
        with pytest.raises(ValueError, match="이미지"):
            _EXECUTE_JOBS(tmp_path, {}, [{"index": 0}], _IMAGES)
        job.assert_not_called()


@pytest.mark.parametrize("workers", [0, 3, -1, True, 1.0])
def test_worker_budget_rejects_other_values_before_runtime(workers, tmp_path):
    with patch.object(execution, "require_runtime") as runtime:
        with pytest.raises(ValueError, match="1개 또는 2개"):
            execution.execute(tmp_path, tmp_path / "missing.json", workers=workers)
        runtime.assert_not_called()


def test_duplicate_assignment_rejected_before_spawning(tmp_path, monkeypatch):
    root = tmp_path / "duplicate"
    plan = _plan(root, [{"index": 0}, {"index": 0}])
    monkeypatch.setattr(execution, "require_runtime", lambda: _IMAGES)
    with patch.object(execution, "ProcessPoolExecutor") as pool:
        with pytest.raises(ValueError, match="중복"):
            execution.execute(root, plan, workers=2)
        pool.assert_not_called()
    assert not list(root.glob("worker-*.json"))


def test_same_request_still_uses_existing_nonblocking_lock(tmp_path):
    frozen, job = {}, {"index": 0}
    request = {"plan": identity(frozen), "job": job, "images": _IMAGES}
    with (
        lock(tmp_path / "results" / identity(request) / ".lock"),
        pytest.raises(BlockingIOError),
    ):
        _trusted_job(tmp_path, frozen, job, _IMAGES)


def test_empty_shard_starts_no_child(tmp_path, monkeypatch):
    root = tmp_path / "empty"
    plan = _plan(root, [{"index": 0}])
    monkeypatch.setattr(execution, "require_runtime", lambda: _IMAGES)
    with patch.object(execution, "ProcessPoolExecutor") as pool:
        result = execution.execute(root, plan, 1, 2, workers=2)
        pool.assert_not_called()
    assert result["jobs_consumed"] == result["worker_processes"] == 0


@pytest.mark.parametrize("arguments,workers", [([], 1), (["--workers", "1"], 1), (["--workers", "2"], 2)])
def test_cli_worker_selection_and_default(arguments, workers, tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "run_dir", lambda _: tmp_path)
    monkeypatch.setattr("sys.argv", ["research", "--run-dir", "fixture", "execute", "--plan", "plan.json", *arguments])
    with patch.object(execution, "execute", return_value={"status": "finished"}) as run:
        assert cli.main() == 0
        run.assert_called_once_with(tmp_path, Path("plan.json"), 0, 1, workers=workers)


@pytest.mark.parametrize("workers", ["0", "3"])
def test_cli_rejects_worker_budget_before_creating_run_directory(workers, monkeypatch):
    monkeypatch.setattr("sys.argv", ["research", "--run-dir", "fixture", "execute", "--plan", "plan.json", "--workers", workers])
    with patch.object(cli, "run_dir") as directory:
        with pytest.raises(SystemExit) as error:
            cli.main()
        assert error.value.code == 2
        directory.assert_not_called()

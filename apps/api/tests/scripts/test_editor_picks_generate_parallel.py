"""실제 provider 호출 없이 원문별 배치 동시성과 재사용·중단 계약을 검사한다."""

import argparse
import importlib.util
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))
from tools.research.editor_picks.common import read, sha, write  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "generate_parallel", ROOT / "tools/scripts/editor-picks-generate-parallel.py"
)
parallel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parallel)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    items = [{"id": str(index), "source_sha256": sha(str(index).encode())} for index in range(6)]
    write(tmp_path / "cohort.json", {"items": items})
    args = argparse.Namespace(
        run_dir=tmp_path, arm="terra", workers=3, limit=6, timeout=17, pilot=False
    )

    def missing(*unused):
        raise ValueError("completed_generation_missing")

    monkeypatch.setattr(parallel, "artifact", missing)
    # 누락된 monkeypatch가 실제 provider를 호출할 수 없게 기본값도 가짜로 고정한다.
    monkeypatch.setattr(parallel, "generate", lambda *args, **kwargs: {"status": "completed"})
    return args, items


@pytest.mark.parametrize("workers", [2, 3, 6])
def test_independent_sources_run_concurrently_with_ordered_audit(setup, monkeypatch, workers):
    args, items = setup
    args.workers = workers
    barrier = threading.Barrier(workers)
    lock = threading.Lock()
    active = peak = 0

    def generate(root, item, arm, *, timeout):
        nonlocal active, peak
        assert root == args.run_dir and arm == "terra" and timeout == 17
        with lock:
            active += 1
            peak = max(peak, active)
        barrier.wait(timeout=5)
        with lock:
            active -= 1
        return {"status": "completed"}

    monkeypatch.setattr(parallel, "generate", generate)
    result = parallel.dispatch(args)
    assert peak == workers and active == 0
    assert [row["id"] for row in result["rows"]] == [item["id"] for item in items]
    assert result["counts"] == {"completed": 6}
    summary_path = args.run_dir / result["summary_file"]
    assert read(summary_path)["consumed"] == 6
    request = read(summary_path.parent / "request.json")
    assert request["sources"] == items
    assert request["dispatcher_sha256"] == sha(Path(parallel.__file__).read_bytes())
    assert request["workers"] == workers and request["requested_model"] == "gpt-5.6-terra"
    assert result["files"]["summary.json"] == sha(summary_path.read_bytes())


def test_completed_artifacts_are_checked_and_not_regenerated(setup, monkeypatch):
    args, _ = setup
    checked, generated = [], []

    def artifact(root, item, arm):
        checked.append(item["id"])
        if item["id"] != "0":
            raise ValueError("missing")
        return "unchanged original", "python", "digest"

    def generate(root, item, arm, *, timeout):
        generated.append(item["id"])
        return {"status": "completed"}

    monkeypatch.setattr(parallel, "artifact", artifact)
    monkeypatch.setattr(parallel, "generate", generate)
    result = parallel.dispatch(args)
    assert set(checked) == set(map(str, range(6)))
    assert set(generated) == set(map(str, range(1, 6)))
    assert result["rows"][0]["artifact_reused"] is True


@pytest.mark.parametrize("status", ["timeout", "interrupted", "blocked"])
def test_two_incomplete_results_finish_current_batch_and_stop(setup, monkeypatch, status):
    args, _ = setup
    generated = []

    def generate(root, item, arm, *, timeout):
        generated.append(item["id"])
        return {"status": status if item["id"] in {"0", "1"} else "completed"}

    monkeypatch.setattr(parallel, "generate", generate)
    result = parallel.dispatch(args)
    assert set(generated) == {"0", "1", "2"}
    assert result["status"] == "blocked" and result["consumed"] == 3
    assert result["stopped_after_batch"] is True
    assert [row["id"] for row in result["rows"]] == ["0", "1", "2"]


def test_limit_and_pilot_select_only_requested_originals(setup, monkeypatch):
    args, items = setup
    args.pilot, args.limit = True, 1
    write(args.run_dir / "pilot-cohort.json", {"items": list(reversed(items))})
    result = parallel.dispatch(args)
    assert [row["id"] for row in result["rows"]] == ["5"]
    assert result["selected"] == result["consumed"] == 1


def test_duplicate_id_rejected_before_any_generation(setup):
    args, items = setup
    write(args.run_dir / "cohort.json", {"items": [items[0], items[0]]})
    with pytest.raises(ValueError, match="ID"):
        parallel.dispatch(args)
    assert not (args.run_dir / "generation-dispatch").exists()


@pytest.mark.parametrize(
    "field,value", [("workers", 0), ("workers", 7), ("limit", 0), ("timeout", 0), ("arm", "other")]
)
def test_invalid_limits_rejected_before_reading_cohort(setup, field, value):
    args, _ = setup
    setattr(args, field, value)
    with pytest.raises(ValueError, match="확인"):
        parallel.dispatch(args)
    assert not (args.run_dir / "generation-dispatch").exists()


def test_incomplete_streak_crosses_batch_boundary(setup, monkeypatch):
    args, _ = setup
    args.workers = 2
    generated = []

    def generate(root, item, arm, *, timeout):
        generated.append(item["id"])
        return {"status": "timeout" if item["id"] in {"1", "2"} else "completed"}

    monkeypatch.setattr(parallel, "generate", generate)
    result = parallel.dispatch(args)
    assert set(generated) == {"0", "1", "2", "3"}
    assert result["stopped_after_batch"] is True and result["consumed"] == 4


def test_completed_result_resets_incomplete_streak(setup, monkeypatch):
    args, _ = setup
    args.workers = 2
    monkeypatch.setattr(
        parallel,
        "generate",
        lambda root, item, arm, **kwargs: {
            "status": "timeout" if int(item["id"]) % 2 == 0 else "completed"
        },
    )
    result = parallel.dispatch(args)
    assert result["consumed"] == 6 and result["status"] == "completed"
    assert result["stopped_after_batch"] is False

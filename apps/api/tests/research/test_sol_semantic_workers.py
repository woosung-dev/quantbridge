"""격리 엔진을 실행하지 않고 의미 채점의 동시성·증거·분모 계약을 검증한다."""

import fcntl
import hashlib
import json
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from tools.research import sol_semantic_eval as semantic  # noqa: E402
from tools.research import sol_strategy_lab as subject  # noqa: E402


def make_trial(root, case_id, repetition=0, status="public_pass"):
    case = {"id": case_id, "prompt": "unit fixture"}
    folder = root / "trials/A/pine" / case_id / str(repetition)
    folder.mkdir(parents=True)
    result = {
        "case_id": case_id,
        "arm": "A",
        "language": "pine",
        "repetition": repetition,
        "status": status,
        "input_identity": f"fixture-{case_id}-{repetition}",
        "source_hash": hashlib.sha256(case_id.encode()).hexdigest(),
        "generation_output_tokens": 0,
        "generation_seconds": 0,
    }
    subject.json_write(folder / "trial.json", result)
    (folder / "source.txt").write_text(case_id)
    return (case, "A", "pine", repetition), folder


def passing(source):
    return {
        "status": "passed",
        "source_hash": hashlib.sha256(source.encode()).hexdigest(),
        "contract_points": 40,
        "ledger_points": 25,
        "reproducibility_points": 15,
    }


@pytest.mark.parametrize("workers", [1, 2])
def test_worker_bound_and_selected_order(tmp_path, monkeypatch, capsys, workers):
    jobs = [make_trial(tmp_path, f"case-{index}")[0] for index in range(4)]
    lock = threading.Lock()
    first_started, second_finished = threading.Event(), threading.Event()
    active, maximum, completed = 0, 0, []

    def evaluate(source, _language, _case_id):
        nonlocal active, maximum
        with lock:
            active += 1
            maximum = max(maximum, active)
        if workers == 2:
            if source == "case-0":
                first_started.set()
                assert second_finished.wait(3), "두 번째 worker가 시작되지 않았습니다"
            elif source == "case-1":
                assert first_started.wait(3)
        with lock:
            completed.append(source)
            active -= 1
        if source == "case-1":
            second_finished.set()
        return passing(source)

    monkeypatch.setattr(semantic, "evaluate", evaluate)
    ordered = []

    def summary(rows):
        ordered.extend(row["case_id"] for row in rows)
        return {"order": ordered}

    monkeypatch.setattr(semantic, "paired_summary", summary)
    subject.evaluate_semantics(tmp_path, jobs, workers)
    expected = [job[0]["id"] for job in jobs]
    printed = [json.loads(line)["case_id"] for line in capsys.readouterr().out.splitlines()]
    assert ordered == printed == expected
    assert maximum == workers
    if workers == 2:
        assert completed.index("case-1") < completed.index("case-0")
    assert json.loads((tmp_path / "semantic-summary.json").read_text()) == {"order": expected}


def test_cache_resume_preserves_evidence_and_does_not_evaluate(tmp_path, monkeypatch):
    jobs, evidence = [], {}
    for index in range(2):
        job, folder = make_trial(tmp_path, f"cached-{index}")
        jobs.append(job)
        result = json.loads((folder / "trial.json").read_text())
        subject.json_write(
            folder / "semantic.json",
            {**passing(f"cached-{index}"), "input_identity": result["input_identity"]},
        )
        for name in ("trial.json", "source.txt", "semantic.json"):
            evidence[folder / name] = (folder / name).read_bytes()

    def forbidden(*_args):
        pytest.fail("유효한 캐시를 다시 평가했습니다")

    monkeypatch.setattr(semantic, "evaluate", forbidden)
    subject.evaluate_semantics(tmp_path, jobs, 2)
    assert all(path.read_bytes() == payload for path, payload in evidence.items())


def test_cache_identity_mismatch_is_not_scored_as_failure(tmp_path, monkeypatch):
    job, folder = make_trial(tmp_path, "mismatch")
    subject.json_write(
        folder / "semantic.json", {**passing("mismatch"), "input_identity": "altered"}
    )
    with pytest.raises(ValueError, match="캐시"):
        subject.evaluate_semantics(tmp_path, [job], 2)
    assert not (tmp_path / "semantic-summary.json").exists()


def test_evaluation_and_generation_failures_stay_in_full_denominator(tmp_path, monkeypatch):
    jobs = [
        make_trial(tmp_path, "D01", index, "failed" if index == 2 else "public_pass")[0]
        for index in range(3)
    ]
    calls = []
    for index, source in enumerate(("raises", "passes")):
        folder = tmp_path / "trials/A/pine/D01" / str(index)
        (folder / "source.txt").write_text(source)
        result = json.loads((folder / "trial.json").read_text())
        result["source_hash"] = hashlib.sha256(source.encode()).hexdigest()
        subject.json_write(folder / "trial.json", result)

    def evaluate(source, *_args):
        # 동일 case의 두 호출 중 하나만 실패해도 두 결과와 생성 실패를 모두 센다.
        calls.append(source)
        if source == "raises":
            raise RuntimeError("fixture evaluation failure")
        return passing(source)

    monkeypatch.setattr(semantic, "evaluate", evaluate)
    subject.evaluate_semantics(tmp_path, jobs, 2)
    results = [
        json.loads((tmp_path / "trials/A/pine/D01" / str(i) / "semantic.json").read_text())
        for i in range(3)
    ]
    assert sorted(result["status"] for result in results) == [
        "failed",
        "generation_or_public_failure",
        "passed",
    ]
    summary = json.loads((tmp_path / "semantic-summary.json").read_text())
    # 통과100 + 의미검사실패20(기존 통합·생성예산 점수) + 생성실패0을 세 번으로 나눈다.
    assert summary["cell_means"]["A/pine"] == 40
    assert len(calls) == 2


def test_parallel_real_evaluator_keeps_five_fresh_transports_per_artifact(tmp_path, monkeypatch):
    """컨테이너만 결정론 더블로 대체해 기존 평가·broker·재현성 경로를 함께 검사한다."""
    jobs = [make_trial(tmp_path, "D01", index)[0] for index in range(2)]
    real_run = semantic.run_code_backtest
    transports, guard = [], threading.Lock()

    class Transport(semantic.OracleTransport):
        closed = False

        def close(self):
            self.closed = True

    def fresh():
        transport = Transport("D01")
        with guard:
            transports.append(transport)
        return transport

    def run(source, language, data, config, **kwargs):
        kwargs["transport_factory"] = kwargs.get("transport_factory") or fresh
        return real_run(source, language, data, config, **kwargs)

    monkeypatch.setattr(semantic, "run_code_backtest", run)
    monkeypatch.setattr(semantic, "probe_transport", lambda *_args: fresh())
    subject.evaluate_semantics(tmp_path, jobs, 2)
    assert len(transports) == 10
    assert len({id(transport.state) for transport in transports}) == 10
    assert all(transport.closed for transport in transports)
    results = [
        json.loads((tmp_path / "trials/A/pine/D01" / str(index) / "semantic.json").read_text())
        for index in range(2)
    ]
    assert all(result["status"] == "passed" for result in results)
    assert results[0]["result_hash"] == results[1]["result_hash"]
    assert results[0]["trace_hash"] == results[1]["trace_hash"]


@pytest.fixture
def cli(tmp_path, monkeypatch):
    monkeypatch.setattr(subject, "ROOT", tmp_path)
    monkeypatch.setattr(subject, "frozen_environment", lambda: {"frozen": "fixture"})
    run_dir = tmp_path / "runs" / "fixture"

    def run(*arguments):
        monkeypatch.setattr(
            sys, "argv", ["sol_strategy_lab", "--run-dir", str(run_dir), "--limit", "0", *arguments]
        )
        subject.main()
        return json.loads((run_dir / "manifest.json").read_text())

    return run, run_dir


@pytest.mark.parametrize(
    "stage, option, expected",
    [("pilot", [], 1), ("evaluation", [], 2), ("evaluation", ["--semantic-workers", "1"], 1)],
)
def test_semantic_workers_are_frozen_in_manifest(cli, stage, option, expected):
    run, _root = cli
    assert run("--stage", stage, *option)["semantic_workers"] == expected


@pytest.mark.parametrize("workers", ["0", "3", "-1"])
def test_semantic_worker_options_are_bounded(cli, workers):
    run, _root = cli
    with pytest.raises(SystemExit):
        run("--semantic-workers", workers)


def test_pilot_cannot_enable_two_workers(cli):
    run, _root = cli
    with pytest.raises(SystemExit):
        run("--stage", "pilot", "--semantic-workers", "2")


def test_changed_worker_count_rejects_manifest_reuse(cli):
    run, _root = cli
    run("--stage", "evaluation", "--semantic-workers", "1")
    with pytest.raises(SystemExit):
        run("--stage", "evaluation", "--semantic-workers", "2")


def test_run_lock_still_prevents_duplicate_runner(cli):
    run, root = cli
    root.mkdir(parents=True)
    with (root / ".runner.lock").open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(SystemExit):
            run("--stage", "evaluation")


def test_public_generation_phase_finishes_before_semantic_workers(cli, monkeypatch):
    run, _root = cli
    completed = set()
    guard = threading.Lock()

    def trial(_root, case, arm, language, repetition):
        with guard:
            completed.add((case["id"], arm, language, repetition))
        return {
            "case_id": case["id"],
            "arm": arm,
            "language": language,
            "repetition": repetition,
            "status": "public_pass",
        }

    observed = []

    def semantics(_root, selected, workers):
        assert completed == {
            (case["id"], arm, language, repetition) for case, arm, language, repetition in selected
        }
        assert len(completed) == 4
        assert workers == 1
        observed.append(True)

    monkeypatch.setattr(subject, "trial", trial)
    monkeypatch.setattr(subject, "evaluate_semantics", semantics)
    run("--semantics", "--limit", "4")
    assert observed == [True]

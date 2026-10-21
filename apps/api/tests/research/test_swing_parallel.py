"""병렬 연구의 파일 공유·단일 writer 병합·중단 재개의 경계. DB 미사용."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from tools.research import swing_parallel as parallel
from tools.research.catalogue import candidates, pilot_candidates
from tools.research.cli import append_journal, cells, hash_json, read_journal
from tools.research.data import digest, json_write
from tools.research.swing_signals import entry_source


def evidence(root):
    candidate = candidates()[0]
    _, metadata = entry_source(candidate)
    cell = {"symbol": "BTCUSDT", "timeframe": "1h", "months": 3}
    frozen = {
        "engine": {"image": "fixed"},
        "parent_dataset_sha256": "parents",
        "execution_dataset_sha256": "minutes",
    }
    job = {"candidate_id": candidate["id"], "cell": cell, **metadata, **frozen}
    record = {
        **job,
        "job_hash": hash_json(job),
        "status": "completed",
        "metrics": {"total_return": "0.1"},
        "comparison": {"baseline": {"metrics": {"total_return": "0.05"}}},
    }
    path = root / "result.json"
    json_write(path, record)
    record.update(result_path=path.name, result_sha256=digest(path))
    expected = {parallel.job_key(candidate["id"], cell): candidate}
    return record, frozen, expected


def test_hardlinks_share_only_frozen_inputs_and_keep_worker_results_separate(tmp_path):
    master, shard = tmp_path / "master", tmp_path / "master" / "shards" / "0"
    master.mkdir()
    for name in ["BTCUSDT-1m.csv", "ETHUSDT-1m.csv"]:
        (master / name).write_text("frozen data")
    json_write(
        master / "execution-dataset.json",
        {"files": [{"path": "BTCUSDT-1m.csv"}, {"path": "ETHUSDT-1m.csv"}]},
    )
    json_write(master / "experiment.json", {"frozen": True})
    parallel.link_data(master, shard)
    assert (master / "BTCUSDT-1m.csv").stat().st_ino == (shard / "BTCUSDT-1m.csv").stat().st_ino
    (shard / "swing-journal.jsonl").write_text("worker journal")
    assert not (master / "swing-journal.jsonl").exists()
    (shard / "experiment.json").unlink()
    json_write(shard / "experiment.json", {"different": True})
    with pytest.raises(ValueError, match="동결 파일"):
        parallel.link_data(master, shard)


def test_parent_merges_completed_results_with_normalized_path_and_resumes_without_duplicates(
    tmp_path,
):
    master, shard = tmp_path / "master", tmp_path / "master" / "shards" / "0"
    shard.mkdir(parents=True)
    record, frozen, expected = evidence(shard)
    append_journal(shard / "swing-journal.jsonl", record)
    parallel.merge_shards(master, [shard], frozen, expected)
    merged = read_journal(master / "swing-journal.jsonl")[record["job_hash"]]
    assert merged["result_path"] == "shards/0/result.json"
    parallel.validate_record(master, merged, frozen, expected)
    before = (master / "swing-journal.jsonl").read_bytes()
    parallel.merge_shards(master, [shard], frozen, expected)
    assert (master / "swing-journal.jsonl").read_bytes() == before


@pytest.mark.parametrize("mutation", ["job_hash", "source_hash", "result_bytes", "summary"])
def test_merge_rejects_changed_job_source_or_result(tmp_path, mutation):
    master, shard = tmp_path / "master", tmp_path / "master" / "shards" / "0"
    shard.mkdir(parents=True)
    record, frozen, expected = evidence(shard)
    if mutation == "job_hash":
        record["job_hash"] = "changed"
    elif mutation == "source_hash":
        record["entry_source_sha256"] = "changed"
    elif mutation == "result_bytes":
        (shard / record["result_path"]).write_text("changed")
    else:
        record["metrics"] = {"total_return": "999"}
    append_journal(shard / "swing-journal.jsonl", record)
    with pytest.raises(ValueError):
        parallel.merge_shards(master, [shard], frozen, expected)
    assert not (master / "swing-journal.jsonl").exists()


def test_interrupted_worker_does_not_promote_running_record_to_master(tmp_path):
    master, shard = tmp_path / "master", tmp_path / "master" / "shards" / "0"
    shard.mkdir(parents=True)
    record, frozen, expected = evidence(shard)
    append_journal(shard / "swing-journal.jsonl", {**record, "status": "running"})
    with (shard / "swing-journal.jsonl").open("ab") as stream:
        stream.write(b'{"unfinished"')
    parallel.merge_shards(master, [shard], frozen, expected)
    assert not (master / "swing-journal.jsonl").exists()


def test_parallel_worker_bound_rejects_oversubscription_before_runtime_access(tmp_path):
    with pytest.raises(ValueError, match="1~4"):
        parallel.run_parallel(tmp_path, tmp_path, "probe", workers=5)


def test_batch_gate_rejects_claimed_pilot_without_actual_completed_evidence(tmp_path):
    json_write(tmp_path / "swing-pilot.json", {"completed": 120, "experiment_sha256": "claimed"})
    parent = {"holdout_start": "2026-04-21T00:00:00Z", "end_exclusive": "2026-10-21T00:00:00Z"}
    with pytest.raises(ValueError, match="실제 master"):
        parallel.validate_pilot_gate(tmp_path, {}, parent)


def test_batch_gate_verifies_all_120_distinct_pilot_results_and_their_bytes(tmp_path):
    parent = {"holdout_start": "2026-04-21T00:00:00Z", "end_exclusive": "2026-10-21T00:00:00Z"}
    frozen = {
        "engine": {"image": "fixed"},
        "parent_dataset_sha256": "parents",
        "execution_dataset_sha256": "minutes",
    }
    paths = []
    for candidate in pilot_candidates():
        _, metadata = entry_source(candidate)
        for cell in cells(parent):
            job = {"candidate_id": candidate["id"], "cell": cell, **metadata, **frozen}
            record = {
                **job,
                "job_hash": hash_json(job),
                "status": "completed",
                "metrics": {},
                "comparison": {"baseline": {}},
            }
            path = tmp_path / (record["job_hash"] + ".json")
            json_write(path, record)
            record.update(result_path=path.name, result_sha256=digest(path))
            append_journal(tmp_path / "swing-journal.jsonl", record)
            paths.append(path)
    parallel.validate_pilot_gate(tmp_path, frozen, parent)
    assert len(paths) == 120
    paths[-1].write_text("changed")
    with pytest.raises(ValueError, match="변조"):
        parallel.validate_pilot_gate(tmp_path, frozen, parent)

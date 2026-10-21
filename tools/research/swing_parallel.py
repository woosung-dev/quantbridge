"""동결 swing 연구를 제한된 프로세스로 실행한다. 부모 프로세스만 원장에 병합한다."""

from __future__ import annotations

import argparse
import json
import multiprocessing
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "apps" / "api"))

from tools.research import swing_exits as study  # noqa: E402
from tools.research.catalogue import candidates, pilot_candidates  # noqa: E402
from tools.research.cli import (  # noqa: E402
    append_journal,
    cells,
    exclusive,
    hash_json,
    output_dir,
    read_journal,
)
from tools.research.data import digest, json_write  # noqa: E402
from tools.research.swing_signals import entry_source  # noqa: E402

TERMINAL = {"completed", "error", "timeout", "blocked"}


def job_key(candidate_id: str, cell: dict) -> str:
    return hash_json({"candidate_id": candidate_id, "cell": cell})


def link_data(master: Path, shard: Path) -> None:
    """동일 파일의 읽기 전용 소비 경로만 추가한다. 결과 파일은 공유하지 않는다."""
    shard.mkdir(parents=True, exist_ok=True)
    manifest = json.loads((master / "execution-dataset.json").read_text())
    for name in [
        "execution-dataset.json",
        "experiment.json",
        *[item["path"] for item in manifest["files"]],
    ]:
        source, destination = master / name, shard / name
        if destination.exists():
            if digest(destination) != digest(source):
                raise ValueError("기존 shard 데이터가 master의 동결 파일과 다릅니다")
        else:
            os.link(source, destination)


def validate_record(root: Path, record: dict, frozen: dict, expected: dict[str, dict]) -> None:
    key = job_key(record["candidate_id"], record["cell"])
    candidate = expected[key]
    if record["status"] == "completed":
        study.validate_completed_record(root, record, frozen, candidate)
        return
    _, metadata = entry_source(candidate)
    # 동결 CLI의 완료 comparison은 설명 문자열을 결과 dict로 교체하므로 원래 job 설명을 복원한다.
    original_job = {
        name: value for name, value in record.items() if name not in study.RECORD_FIELDS
    }
    original_job.update(metadata)
    if (
        record["engine"] != frozen["engine"]
        or record["execution_dataset_sha256"] != frozen["execution_dataset_sha256"]
        or record["parent_dataset_sha256"] != frozen["parent_dataset_sha256"]
        or any(
            record.get(name) != value for name, value in metadata.items() if name != "comparison"
        )
        or record["job_hash"] != hash_json(original_job)
    ):
        raise ValueError("shard 결과의 소스·정책·데이터·job hash가 동결 실험과 다릅니다")


def merge_shards(
    master: Path, shard_roots: list[Path], frozen: dict, expected: dict[str, dict]
) -> None:
    existing = read_journal(master / "swing-journal.jsonl")
    for shard in shard_roots:
        for record in read_journal(shard / "swing-journal.jsonl").values():
            if record["status"] not in TERMINAL:
                continue
            validate_record(shard, record, frozen, expected)
            old = existing.get(record["job_hash"])
            if old and old["status"] == "completed":
                validate_record(master, old, frozen, expected)
                continue
            merged = dict(record)
            if record["status"] == "completed":
                merged["result_path"] = str((shard / record["result_path"]).relative_to(master))
            append_journal(master / "swing-journal.jsonl", merged)
            existing[record["job_hash"]] = merged


def run_shard(payload: dict) -> int:
    root, baseline = Path(payload["root"]), Path(payload["baseline"])
    frozen = payload["frozen"]
    with exclusive(root):
        parent = study.load_dataset(baseline)
        execution = study.load_execution_dataset(root, baseline)
        _, prior = study.baseline_records(baseline)
        completed = 0
        for job in payload["jobs"]:
            candidate, cell = job["candidate"], job["cell"]
            _, metadata = entry_source(candidate)
            reference = study.baseline_reference(
                baseline,
                prior[(candidate["id"], cell["symbol"], cell["timeframe"], cell["months"])],
                metadata,
            )
            record = study.run_cell(
                root, baseline, parent, execution, candidate, cell, frozen["engine"], reference
            )
            completed += record["status"] == "completed"
        return completed


def validate_pilot_gate(master: Path, frozen: dict, parent: dict) -> None:
    study.validate_pilot_evidence(master, frozen, parent)


def run_parallel(
    master: Path, baseline: Path, phase: str, workers: int, offset: int = 0, limit: int = 16
) -> dict:
    if not 1 <= workers <= 4:
        raise ValueError("병렬 프로세스는 1~4개만 허용합니다")
    started = time.perf_counter()
    with exclusive(master):
        parent = study.load_dataset(baseline)
        study.load_execution_dataset(master, baseline)
        baseline_batch, _ = study.baseline_records(baseline)
        identity = study.engine_identity()
        frozen = {
            "parent_dataset_sha256": digest(baseline / "dataset.json"),
            "execution_dataset_sha256": digest(master / "execution-dataset.json"),
            "baseline_batch_sha256": digest(baseline / "batch.json"),
            "baseline_engine": baseline_batch["engine"],
            "engine": identity,
            "risk_policy": study.SWING_POLICY,
            "sources_sha256": hash_json([entry_source(item)[1] for item in candidates()]),
        }
        frozen_path = master / "experiment.json"
        if frozen_path.exists():
            if json.loads(frozen_path.read_text()) != frozen:
                raise ValueError("병렬 실행의 코드·데이터·정책이 동결 실험과 다릅니다")
        else:
            json_write(frozen_path, frozen)
        if phase == "batch":
            pilot = json.loads((master / "swing-pilot.json").read_text())
            if pilot.get("completed") != 120 or pilot.get("experiment_sha256") != digest(
                frozen_path
            ):
                raise ValueError("동일 실험의 120셀 pilot 완료 후 확대합니다")
            validate_pilot_gate(master, frozen, parent)
        cohort = candidates() if phase == "batch" else pilot_candidates()
        jobs = [
            {"candidate": candidate, "cell": cell} for candidate in cohort for cell in cells(parent)
        ]
        if phase == "probe":
            if offset < 0 or not 1 <= limit <= 20:
                raise ValueError("probe는 1~20개 셀과 음수가 아닌 offset만 허용합니다")
            jobs = jobs[offset : offset + limit]
        name = f"{phase}-w{workers}" + (f"-o{offset}-n{limit}" if phase == "probe" else "")
        plan = {
            "orchestrator_sha256": digest(Path(__file__)),
            "workers": workers,
            "phase": phase,
            "experiment_sha256": digest(frozen_path),
            "jobs": [{"candidate_id": job["candidate"]["id"], "cell": job["cell"]} for job in jobs],
            "allocation": "job_index_mod_worker_count",
            "data_sharing": "read_only_consumers_of_hardlinks",
            "master_writer": "parent_only",
        }
        plan_path = master / f"parallel-{name}-plan.json"
        if plan_path.exists():
            if json.loads(plan_path.read_text()) != plan:
                raise ValueError("병렬 계획이 변경되었습니다. 새 phase 이름이 필요합니다")
        else:
            json_write(plan_path, plan)
        expected = {job_key(job["candidate"]["id"], job["cell"]): job["candidate"] for job in jobs}
        shard_roots = [master / "shards" / name / str(index) for index in range(workers)]
        for shard in shard_roots:
            link_data(master, shard)
        merge_shards(master, shard_roots, frozen, expected)
        existing = read_journal(master / "swing-journal.jsonl")
        already = {}
        for row in existing.values():
            key = job_key(row["candidate_id"], row["cell"])
            if key in expected and row["status"] in TERMINAL:
                validate_record(master, row, frozen, expected)
                already[key] = row
        payloads = []
        for index, shard in enumerate(shard_roots):
            selected = [
                job
                for position, job in enumerate(jobs)
                if position % workers == index
                and job_key(job["candidate"]["id"], job["cell"]) not in already
            ]
            if selected:
                payloads.append(
                    {
                        "root": str(shard),
                        "baseline": str(baseline),
                        "frozen": frozen,
                        "jobs": selected,
                    }
                )
        errors = []
        try:
            with ProcessPoolExecutor(
                max_workers=workers, mp_context=multiprocessing.get_context("spawn")
            ) as pool:
                futures = [pool.submit(run_shard, payload) for payload in payloads]
                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as exc:
                        errors.append(f"{type(exc).__name__}: {exc}")
                    merge_shards(master, shard_roots, frozen, expected)
        finally:
            merge_shards(master, shard_roots, frozen, expected)
        records = [
            row
            for row in read_journal(master / "swing-journal.jsonl").values()
            if job_key(row["candidate_id"], row["cell"]) in expected
        ]
        completed = sum(row["status"] == "completed" for row in records)
        summary = {
            "status": "completed" if completed == len(jobs) else "incomplete",
            "completed": completed,
            "planned_cells": len(jobs),
            "completed_backtests": completed * 2,
            "newly_completed_cells": completed
            - sum(row["status"] == "completed" for row in already.values()),
            "workers": workers,
            "wall_seconds": time.perf_counter() - started,
            "worker_errors": errors,
            "experiment_sha256": digest(frozen_path),
            "parallel_plan_sha256": digest(plan_path),
            "promotable": False,
        }
        json_write(master / f"parallel-{name}-summary.json", summary)
        if phase in {"pilot", "batch"}:
            json_write(master / f"swing-{phase}.json", summary)
        study.write_report(master)
        return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--baseline-dir", default="runs/indicator-research-data")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int, default=16)
    parser.add_argument("phase", choices=["probe", "pilot", "batch"])
    args = parser.parse_args()
    try:
        master, baseline = output_dir(args.run_dir), Path(args.baseline_dir).resolve()
        if (
            not baseline.is_relative_to(ROOT / "runs")
            or master == baseline
            or master.is_relative_to(baseline)
            or baseline.is_relative_to(master)
        ):
            raise ValueError("baseline과 새 연구는 runs/의 별도 디렉터리여야 합니다")
        summary = run_parallel(master, baseline, args.phase, args.workers, args.offset, args.limit)
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0 if summary["status"] == "completed" else 1
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

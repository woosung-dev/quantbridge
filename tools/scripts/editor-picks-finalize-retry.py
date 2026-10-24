"""고정 20분할의 인프라 실패 15번만 attempt 2로 대체해 증거를 집계한다.

원본 attempt와 암호 봉투는 바꾸지 않는다. 기록된 provenance별 검증 후 기존
reconcile/report만 호출하며 금융·전략 계산을 다시 실행하지 않는다.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "apps/api")]

from tools.research.editor_picks import report, verification  # noqa: E402
from tools.research.editor_picks.common import checked_file, identity, read, write  # noqa: E402
from tools.research.editor_picks.remote import remote_namespace  # noqa: E402


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def mixed_namespace(selection_sha256: str) -> Path:
    return Path("remote") / ("mixed-" + selection_sha256)


def validate(root: Path, selection_path: Path) -> dict:
    """집계·앱 저장자가 재사용하는 읽기 전용 증거 검증. 판정을 새로 정의하지 않는다."""
    root = Path(root).resolve()
    selection_path = Path(selection_path)
    if not selection_path.is_file():
        selection_path = root / selection_path
    selection_path = selection_path.resolve()
    if not selection_path.is_relative_to(root):
        raise ValueError("선택 manifest는 연구 root 안에 있어야 합니다")
    selection = read(selection_path)
    base, selected, failed = selection["base"], selection["selected"], selection["failed_source"]
    if (
        selection["schema_version"] != 1
        or set(base) != {"head", "run_id", "input_sha256", "plan", "plan_sha256", "shards"}
        or base["shards"] != 20
    ):
        raise ValueError("고정 20분할 공통 provenance가 다릅니다")
    expected_selection = {shard: "2" if shard == 15 else "1" for shard in range(20)}
    if (
        len(selected) != 20
        or any(type(item["shard"]) is not int for item in selected)
        or len({item["shard"] for item in selected}) != 20
        or {item["shard"]: item["attempt"] for item in selected} != expected_selection
    ):
        raise ValueError("15만 attempt 2인 20개 유일한 선택이 필요합니다")
    if failed["shard"] != 15 or failed["attempt"] != "1":
        raise ValueError("원래 실패한 15번 attempt 1 증거가 필요합니다")
    frozen = read(root / base["plan"])
    if frozen["phase"] != "full" or identity(frozen) != base["plan_sha256"]:
        raise ValueError("선택한 금융 계획이 다릅니다")
    cohort = verification.frozen_inputs(root, frozen)
    runtime_manifest = read(root / "runtime/manifest.json")
    source_proof = read(root / "runtime/source-proof.json")
    images = {
        language: runtime_manifest["image_ids"][f"quantbridge-{language}-runner:local"]
        for language in ("pine", "python")
    }
    jobs = {identity(job): index for index, job in enumerate(frozen["jobs"])}
    if len(jobs) != len(frozen["jobs"]):
        raise ValueError("금융 계획의 셀이 중복됐습니다")

    def source(shard, attempt, failed_origin=False):
        provenance = {**base, "attempt": attempt, "shard": shard}
        prefix = remote_namespace(provenance) / str(shard)
        envelope_file = prefix / "envelope.json"
        envelope = read(root / envelope_file)
        if any(envelope.get(key) != value for key, value in provenance.items()):
            raise ValueError("선택한 봉투의 실제 provenance가 다릅니다")
        for name, expected in envelope["files"].items():
            if not (
                name.startswith("results/")
                or name.startswith("native-checks/")
                or name.startswith(f"{prefix}/")
            ):
                raise ValueError("선택 봉투 경로가 범위를 벗어납니다")
            checked_file(root, name, expected)

        def listed(name):
            relative = str(prefix / name)
            if relative not in envelope["files"]:
                raise ValueError("terminal·allocation·runtime 근거가 봉투에 등재되지 않았습니다")
            return read(checked_file(root, relative, envelope["files"][relative]))

        state_file = Path(f"private/stream-collection-{base['run_id']}-{attempt}.json")
        state = read(root / state_file)
        if state["provenance"] != {**base, "attempt": attempt}:
            raise ValueError("인증 수거 state의 provenance가 다릅니다")
        collected = state["collected"][str(shard)]
        asset_name = f"result-{base['run_id']}-{attempt}-{shard}.enc"
        envelope_hash = digest(root / envelope_file)
        if collected["asset_name"] != asset_name or (
            not failed_origin and collected.get("envelope_sha256") != envelope_hash
        ):
            raise ValueError("암호문 수거와 봉투 SHA의 결박이 다릅니다")
        runtime = listed("runtime-installed.json")
        if (
            runtime["images"] != runtime_manifest["image_ids"]
            or runtime["runtime"] != runtime_manifest["files"]
            or runtime["source_proof"] != source_proof
        ):
            raise ValueError("선택한 runtime·image·계산 소스가 다릅니다")
        terminal = listed(f"terminal-{shard}.json")
        if (
            terminal["shard"] != shard
            or terminal["shards"] != 20
            or terminal["plan_sha256"] != base["plan_sha256"]
        ):
            raise ValueError("terminal의 실제 배정이 다릅니다")
        record = {
            "shard": shard,
            "attempt": attempt,
            "provenance": provenance,
            "envelope_file": str(envelope_file),
            "envelope_sha256": envelope_hash,
            "asset_name": asset_name,
            "asset_digest": "sha256:" + collected["cipher_sha256"],
            "collection_state_file": str(state_file),
            "collection_state_sha256": digest(root / state_file),
        }
        return envelope, terminal, listed, record

    origin_envelope, origin_terminal, origin_listed, origin = source(15, "1", True)
    blocked = origin_listed("runtime-blocked-15.json")
    if (
        origin_terminal["actual_returncode"] == 0
        or origin_terminal["economic_returncode"] == 0
        or origin_terminal["native_returncodes"] != {}
        or blocked["status"] != "blocked"
        or blocked["plan_sha256"] != base["plan_sha256"]
        or "timed out after 15 seconds" not in blocked["error"]
        or "docker" not in blocked["error"]
        or any(name.startswith(("results/", "native-checks/")) for name in origin_envelope["files"])
    ):
        raise ValueError("원래 15번은 경제 셀 실행 전 Docker 조회 실패여야 합니다")
    expected_failed = {
        "asset_name": origin["asset_name"],
        "asset_digest": origin["asset_digest"],
        "envelope_sha256": origin["envelope_sha256"],
        "terminal_sha256": origin_envelope["files"][
            str(Path(origin["envelope_file"]).parent / "terminal-15.json")
        ],
        "runtime_blocked_sha256": origin_envelope["files"][
            str(Path(origin["envelope_file"]).parent / "runtime-blocked-15.json")
        ],
    }
    if any(failed[key] != value for key, value in expected_failed.items()):
        raise ValueError("성과 조회 전에 고정한 실패 원본 SHA가 다릅니다")
    covered, selected_sources = set(), []
    for shard, attempt in expected_selection.items():
        envelope, terminal, listed, record = source(shard, attempt)
        assigned_ids = {item["id"] for item in cohort["items"][shard::20]}
        if (
            terminal["actual_returncode"] != 0
            or terminal.get("economic_returncode") != 0
            or terminal.get("native_returncodes") != dict.fromkeys(assigned_ids, 0)
        ):
            raise ValueError("선택한 실행·native 검증이 실패했습니다")
        allocation = listed(f"worker-full-{shard}.json")
        assigned_jobs = {key for key, index in jobs.items() if index % 20 == shard}
        if allocation != {
            **allocation,
            "status": "finished",
            "plan_sha256": base["plan_sha256"],
            "shard": shard,
            "shards": 20,
            "jobs_consumed": len(assigned_jobs),
        }:
            raise ValueError("선택한 셀 배정 소비 근거가 다릅니다")
        observed = set()
        for name in envelope["files"]:
            if not (name.startswith("results/") and name.endswith("/receipt.json")):
                continue
            folder = Path(name).parent
            request_name = str(folder / "request.json")
            if request_name not in envelope["files"]:
                raise ValueError("receipt의 원시 요청이 봉투에 없습니다")
            request = read(root / request_name)
            value = verification.read(root / name)
            if any(
                envelope["files"].get(str(folder / filename)) != expected
                for filename, expected in value["files"].items()
            ):
                raise ValueError("receipt의 원시 파일이 선택 봉투와 결박되지 않았습니다")
            key = identity(request["job"])
            if (
                request["plan"] != base["plan_sha256"]
                or request["images"] != images
                or folder.name != identity(request)
                or key not in assigned_jobs
                or key in observed
                or key in covered
            ):
                raise ValueError("셀 소유권·중복·계획·실행 image가 다릅니다")
            observed.add(key)
        if observed != assigned_jobs:
            raise ValueError("배정한 정확한 셀 집합에 누락이 있습니다")
        for identifier in assigned_ids:
            name = f"native-checks/{identifier}.json"
            if name not in envelope["files"]:
                raise ValueError("배정한 원시 native proof가 봉투에 없습니다")
            proof = read(root / name)
            item = next(item for item in cohort["items"] if item["id"] == identifier)
            if (
                proof["id"] != identifier
                or proof["plan_sha256"] != base["plan_sha256"]
                or proof["source_sha256"] != item["source_sha256"]
                or proof["images"] != images
            ):
                raise ValueError("원시 native proof의 코드·계획·image가 다릅니다")
        covered |= observed
        selected_sources.append({**record, "jobs_consumed": len(observed)})
    completed = verification.receipts(root, frozen)
    if covered != set(jobs) or set(completed) != set(jobs):
        raise ValueError("전체 계획의 셀이 중복되거나 누락됐습니다")
    verification.frozen_inputs(root, frozen)
    return {
        "provenance": base,
        "selection_file": str(selection_path.relative_to(root)),
        "selection_sha256": identity(selection),
        "selection_file_sha256": digest(selection_path),
        "selected_shards": selected_sources,
        "failed_source": {**failed, "economic_cells": 0},
        "expected_cells": len(jobs),
    }


def finalize(root: Path, selection_path: Path) -> dict:
    root = Path(root).resolve()
    certificate = validate(root, selection_path)
    final_path = root / mixed_namespace(certificate["selection_sha256"]) / "finalization.json"
    report_path = root / "report/full/report.json"
    if final_path.exists():
        previous = read(final_path)
        if (
            any(previous.get(key) != value for key, value in certificate.items())
            or previous.get("complete") is not True
            or previous.get("report_sha256") != digest(report_path)
        ):
            raise ValueError("기존 혼합 종결의 인증 근거 또는 보고서가 바뀌었습니다")
        return previous
    plan = root / certificate["provenance"]["plan"]
    verification.reconcile(root, plan)
    summary = report.build(root, plan)
    result = {
        **certificate,
        "complete": summary["complete"],
        "failures": [],
        "report_summary": summary,
        "report_file": str(report_path.relative_to(root)),
        "report_sha256": digest(report_path),
    }
    verification.frozen_inputs(root, read(plan))
    write(final_path, result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location(
        "retry_postprocess", ROOT / "tools/scripts/editor-picks-postprocess.py"
    )
    postprocess = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(postprocess)
    postprocess.install()
    result = finalize(args.run_dir.resolve(), args.selection)
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result["complete"] else 1)


if __name__ == "__main__":
    main()

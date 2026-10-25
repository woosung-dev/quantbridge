"""공식 ARM에서 고정 네 셀의 순차/2프로세스 실행을 비교한다. 자동 채택·모델 호출 없음."""

from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import json
import math
import os
import platform
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import time
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[2]
ALLOWED_ENV = {"PATH", "HOME", "LANG", "TRADING_ENCRYPTION_KEYS", "PINE_AST_CACHE_DIR"}


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def identity(value):
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()
    ).hexdigest()


def registration(path):
    value = read(path)
    require(
        value["workflow_budget_seconds"] == 2100
        and value["probe_budget_seconds"] == 1800
        and value["existing_transport_timeout_seconds"] == 900,
        "등록 예산이 다릅니다",
    )
    require(
        identity(value["order"])
        == identity(
            [{"label": "serial", "workers": 1}, {"label": "parallel", "workers": 2}]
        )
        and value["job_repetitions_per_mode"] == 1,
        "등록 실행 순서가 다릅니다",
    )
    require(
        len(value["selected"]) == 2 and len({x["id"] for x in value["selected"]}) == 2,
        "원문 선택이 다릅니다",
    )
    expected = [
        {
            "id": item["id"],
            "arm": arm,
            "timeframe": "1h",
            "months": 24,
            "scenario": "baseline",
        }
        for item in value["selected"]
        for arm in ("pine", "terra")
    ]
    require(identity(value["jobs"]) == identity(expected), "고정 네 셀과 다릅니다")
    require(
        identity(value["success"])
        == identity(
            {
                "all_eight_statuses_completed": True,
                "action_ledger_metrics_and_raw_result_hashes_exact": True,
                "speedup_min": 1.2,
                "minimum_mem_available_bytes": 2 * 1024**3,
                "oom_kill_delta": 0,
                "missing_measurements_fail": True,
                "automatic_adoption": False,
            }
        ),
        "성공 기준이 다릅니다",
    )
    return value


def snapshot(proc=Path("/proc")):
    """host와 dockerd/격리 guest 메모리를 포함한 VM 지표이며 RSS로 부르지 않는다."""
    mem = {
        line.split(":")[0]: int(line.split()[1]) * 1024
        for line in (proc / "meminfo").read_text().splitlines()
        if line.startswith(("MemTotal:", "MemAvailable:"))
    }
    cpu = [int(v) for v in (proc / "stat").read_text().splitlines()[0].split()[1:9]]
    vm = dict(line.split() for line in (proc / "vmstat").read_text().splitlines())
    require(
        set(mem) == {"MemTotal", "MemAvailable"} and len(cpu) == 8 and "oom_kill" in vm,
        "VM 전체 관측이 부족합니다",
    )
    return {
        "mem_total": mem["MemTotal"],
        "mem_available": mem["MemAvailable"],
        "cpu_total": sum(cpu),
        "cpu_idle": cpu[3] + cpu[4],
        "oom_kill": int(vm["oom_kill"]),
    }


def observation(samples, elapsed):
    require(len(samples) >= 2 and elapsed > 0, "측정 표본이 부족합니다")
    first, last = samples[0], samples[-1]
    ticks = last["cpu_total"] - first["cpu_total"]
    idle = last["cpu_idle"] - first["cpu_idle"]
    require(
        ticks > 0 and 0 <= idle <= ticks and last["oom_kill"] >= first["oom_kill"],
        "CPU/OOM counter가 다릅니다",
    )
    return {
        "wall_seconds": elapsed,
        "vm_cpu_percent": (ticks - idle) * 100 / ticks,
        "vm_min_mem_available_bytes": min(s["mem_available"] for s in samples),
        "vm_peak_used_memory_bytes": max(
            s["mem_total"] - s["mem_available"] for s in samples
        ),
        "vm_oom_kill_delta": last["oom_kill"] - first["oom_kill"],
        "sample_count": len(samples),
        "rss_bytes": None,
        "memory_scope": "VM MemTotal-MemAvailable; host+containers+cache; RSS아님",
    }


def runner(reg, args, clean):
    require(
        platform.system() == "Linux"
        and platform.machine() in {"arm64", "aarch64"}
        and str(ROOT).startswith("/home/runner/work/")
        and os.cpu_count() == 4,
        "공식 4CPU ARM 연구 runner만 허용합니다",
    )
    require(
        snapshot()["mem_total"] >= reg["runner"]["memory_min_bytes"],
        "16GB급 VM 메모리 근거가 없습니다",
    )
    actual = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    require(
        actual == args.head == reg["binding_before_dispatch"]["control_head"],
        "검토된 control HEAD가 아닙니다",
    )
    require(
        str(args.run_id).isdecimal() and str(args.attempt) == "1",
        "실제 실행 출처가 없습니다",
    )
    if clean:
        require(
            set(os.environ) <= ALLOWED_ENV
            and os.environ.get("PINE_AST_CACHE_DIR") == ""
            and len(
                base64.b64decode(
                    os.environ.get("TRADING_ENCRYPTION_KEYS", ""),
                    altchars=b"-_",
                    validate=True,
                )
            )
            == 32,
            "AB 부모와 spawn 자식은 무자격 환경이어야 합니다",
        )


def core_equal(reg):
    for name, expected in reg["financial_core_files"].items():
        path = (ROOT / name).resolve()
        require(
            path.is_relative_to(ROOT) and digest(path) == expected,
            "동결 금융 core가 바뀌었습니다",
        )
    path = ROOT / "tools/research/editor_picks/execution.py"
    source = path.read_text()
    lines = source.splitlines(keepends=True)
    functions = {
        node.name: hashlib.sha256(
            "".join(
                lines[
                    min([node.lineno] + [d.lineno for d in node.decorator_list])
                    - 1 : node.end_lineno
                ]
            ).encode()
        ).hexdigest()
        for node in ast.parse(source).body
        if isinstance(node, ast.FunctionDef) and node.name in reg["financial_functions"]
    }
    require(functions == reg["financial_functions"], "금융 함수 본문이 바뀌었습니다")


def selection(parent, reg):
    frozen = read(parent / "full-plan.json")
    require(
        identity(frozen) == reg["parent_plan_sha256"], "인증 parent 계획이 다릅니다"
    )
    cohort = read(parent / frozen["cohort_file"])
    require(
        digest(parent / frozen["cohort_file"]) == reg["cohort_sha256"]
        and digest(parent / "data/dataset.json") == reg["dataset_sha256"]
        and digest(parent / "runtime/manifest.json") == reg["runtime_manifest_sha256"],
        "parent 입력 SHA가 다릅니다",
    )
    chosen = [
        item
        for item in cohort["items"]
        if all(
            "source_sha256" in frozen["artifacts"][item["id"]][arm]
            for arm in ("pine", "terra")
        )
    ][:2]
    expected = [
        {
            "id": i["id"],
            "source_sha256": i["source_sha256"],
            "artifacts": {
                a: frozen["artifacts"][i["id"]][a] for a in ("pine", "terra")
            },
        }
        for i in chosen
    ]
    require(
        expected == reg["selected"], "사전 선택 후 더 쉬운 원문으로 바꾸지 않습니다"
    )
    return chosen


def containers():
    listing = subprocess.check_output(
        ["docker", "ps", "-a", "--no-trunc", "--format", "{{.ID}} {{.Names}}"],
        text=True,
        timeout=10,
    )
    rows = [line.split() for line in listing.splitlines()]
    require(all(len(row) == 2 for row in rows), "container 목록이 잘못됐습니다")
    ids = {row[0] for row in rows}
    own_ids = [
        identifier
        for identifier, name in rows
        if re.fullmatch(r"qb-python-[a-f0-9]{32}", name)
    ]
    if not own_ids:
        return ids, {}
    template = '{"id":{{json .Id}},"name":{{json .Name}},"image":{{json .Image}},"created":{{json .Created}}}'
    inspected = subprocess.check_output(
        ["docker", "inspect", "--format", template, *own_ids], text=True, timeout=10
    )
    own = {
        value["id"]: value
        for line in inspected.splitlines()
        if (value := json.loads(line))
    }
    require(set(own) == set(own_ids), "container 소유 메타데이터가 부족합니다")
    return ids, own


def remaining_containers(state):
    _, own = containers()
    for identifier, value in own.items():
        created = datetime.fromisoformat(value["created"]).timestamp()
        require(
            identifier not in state["baseline_container_ids"]
            and value["image"] in state["allowed_image_ids"]
            and re.fullmatch(r"/qb-python-[a-f0-9]{32}", value["name"])
            and state["started_at_epoch"] <= created <= time.time(),
            "확인되지 않은 container는 제거하지 않습니다",
        )
    return own


def stopped_writers(folder, proc=Path("/proc")):
    state = read(folder / "process-state.json")
    require(
        type(state["pgid"]) is int and state["pgid"] > 1,
        "process group 근거가 없습니다",
    )
    for stat in proc.glob("[0-9]*/stat"):
        try:
            fields = stat.read_text().rsplit(")", 1)[1].split()
        except FileNotFoundError:
            continue
        require(
            not (int(fields[2]) == state["pgid"] and fields[0] != "Z"),
            "probe writer가 남아 있습니다",
        )
    require(not remaining_containers(state), "probe container가 남아 있습니다")


def monitored(command, folder, deadline, image_ids):
    require(time.monotonic() < deadline, "준비시간을 포함한 예산이 끝났습니다")
    baseline, own = containers()
    require(not own, "기존 sandbox가 있는 VM에서는 시작하지 않습니다")
    samples = [snapshot()]
    started = time.monotonic()
    with (folder / "worker-0.log").open("w") as output:
        require(time.monotonic() < deadline, "준비시간을 포함한 예산이 끝났습니다")
        state = {
            "baseline_container_ids": sorted(baseline),
            "allowed_image_ids": sorted(image_ids),
            "started_at_epoch": time.time(),
        }
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        state["pgid"] = process.pid
        (folder / "process-state.json").write_text(json.dumps(state))
        try:
            while process.poll() is None:
                require(time.monotonic() < deadline, "고정 총 실행 예산을 초과했습니다")
                time.sleep(1)
                samples.append(snapshot())
        finally:
            # 부모가 먼저 종료돼도 남은 spawn writer를 같은 process group에서 제거한다.
            for sig in (signal.SIGTERM, signal.SIGKILL):
                try:
                    os.killpg(process.pid, sig)
                except ProcessLookupError:
                    pass
                if sig == signal.SIGTERM:
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        pass
            process.wait(timeout=5)
            for identifier in remaining_containers(state):
                subprocess.run(
                    ["docker", "rm", "--force", identifier],
                    check=True,
                    capture_output=True,
                    timeout=10,
                )
            stopped_writers(folder)
    samples.append(snapshot())
    return process.returncode, observation(samples, time.monotonic() - started)


def compare(left, right, measurements, reg):
    all_completed = all(
        row["status"] == "completed" for rows in (left, right) for row in rows
    )
    hashes_equal = len(left) == len(right) == 4 and all(
        a["job"] == b["job"]
        and all(
            a.get(key) is not None and a[key] == b.get(key)
            for key in (
                "action_sha256",
                "ledger_sha256",
                "metrics_sha256",
                "result_sha256",
            )
        )
        for a, b in zip(left, right, strict=True)
    )
    require(len(measurements) == 2, "두 실행 관측이 필요합니다")
    for measured in measurements:
        require(
            all(
                type(measured.get(key)) in (int, float) and math.isfinite(measured[key])
                for key in (
                    "wall_seconds",
                    "vm_cpu_percent",
                    "vm_min_mem_available_bytes",
                    "vm_oom_kill_delta",
                    "sample_count",
                )
            )
            and measured["wall_seconds"] > 0
            and 0 <= measured["vm_cpu_percent"] <= 100
            and measured["sample_count"] >= 2,
            "VM 측정 누락·비유한값은 통과시키지 않습니다",
        )
    speedup = measurements[0]["wall_seconds"] / measurements[1]["wall_seconds"]
    memory_ok = all(
        m["vm_min_mem_available_bytes"] >= reg["success"]["minimum_mem_available_bytes"]
        and m["vm_oom_kill_delta"] == 0
        for m in measurements
    )
    return {
        "all_completed": all_completed,
        "hashes_equal": hashes_equal,
        "speedup": speedup,
        "memory_ok": memory_ok,
        "performance_criterion_passed": speedup >= reg["success"]["speedup_min"],
        "adoption_eligible": all_completed
        and hashes_equal
        and memory_ok
        and speedup >= reg["success"]["speedup_min"],
        "automatic_adoption": False,
    }


def run(args):
    reg = registration(args.registration)
    runner(reg, args, clean=True)
    core_equal(reg)
    parent, output = args.parent.resolve(), args.run_dir.resolve()
    require(
        parent.is_relative_to(ROOT / "runs")
        and output.is_relative_to(ROOT / "runs")
        and not output.exists()
        and digest(args.parent_cipher) == reg["parent_input_sha256"],
        "새 AB 결과 root와 인증 암호문만 허용합니다",
    )
    chosen = selection(parent, reg)
    sys.path[:0] = [str(ROOT), str(ROOT / "apps/api")]
    from tools.research.editor_picks import execution, verification
    from tools.research.editor_picks.common import checked_file, write

    images = execution.require_runtime()
    require(
        {f"quantbridge-{kind}-runner:local": value for kind, value in images.items()}
        == reg["image_ids"],
        "동결 실행 이미지가 다릅니다",
    )
    output.mkdir(parents=True)
    template = output / "template"
    template.mkdir()
    for item in chosen:
        checked_file(parent, item["source_file"], item["source_sha256"])
        for path in [parent / item["source_file"], parent / item["adapted_file"]]:
            target = template / path.relative_to(parent)
            target.parent.mkdir(parents=True, exist_ok=True)
            os.link(path, target)
        for arm in ("terra", "gemini"):
            source = parent / "generation" / item["id"] / arm
            if source.exists():
                shutil.copytree(
                    source,
                    template / "generation" / item["id"] / arm,
                    copy_function=os.link,
                )
    shutil.copytree(parent / "data", template / "data", copy_function=os.link)
    write(template / "cohort.json", {"target": 2, "items": chosen})
    probe = execution.plan(template)
    require(
        all(
            probe["artifacts"][item["id"]][arm] == reg_item["artifacts"][arm]
            for item, reg_item in zip(chosen, reg["selected"], strict=True)
            for arm in ("pine", "terra")
        ),
        "부모와 probe의 선택 코드가 다릅니다",
    )
    probe.update(jobs=reg["jobs"], expected_cells=4, phase="process_ab")
    write(output / "registration.json", reg)
    write(output / "probe-plan.json", probe)
    for mode in reg["order"]:
        target = output / mode["label"]
        shutil.copytree(template, target, copy_function=os.link)
        write(target / "probe-plan.json", probe)
        verification.frozen_inputs(target, probe)
    deadline = read(args.budget_file)["execution_deadline_monotonic"]
    remaining = deadline - time.monotonic()
    require(
        0 < remaining <= reg["probe_budget_seconds"],
        "준비시간을 포함한 사전 예산이 끝났습니다",
    )
    measurements, summaries = [], []
    for mode in reg["order"]:
        folder = output / mode["label"]
        command = [
            sys.executable,
            "-m",
            "tools.research.editor_picks",
            "--run-dir",
            str(folder),
            "execute",
            "--plan",
            str(folder / "probe-plan.json"),
            "--workers",
            str(mode["workers"]),
        ]
        code, measured = monitored(command, folder, deadline, reg["image_ids"].values())
        write(folder / "measurement.json", measured)
        require(code == 0, "실행 process가 실패했습니다")
        allocation = read(folder / "worker-process_ab-0.json")
        require(
            allocation["status"] == "finished"
            and allocation["jobs_consumed"] == 4
            and allocation["plan_sha256"] == identity(probe),
            "실제 배정 소비가 다릅니다",
        )
        if mode["workers"] == 2:
            require(
                allocation.get("workers") == 2
                and allocation.get("worker_processes") == 2
                and allocation.get("process_start_method") == "spawn",
                "두 독립 spawn process 근거가 없습니다",
            )
        rows = verification.receipts(folder, probe)
        require(len(rows) == 4, "네 셀 영수증이 필요합니다")
        evidence = []
        for job in reg["jobs"]:
            row = rows[identity(job)]
            evidence.append(
                {
                    "job": job,
                    "status": row["status"],
                    "action_sha256": row.get("action_sha256"),
                    "ledger_sha256": row.get("ledger_sha256"),
                    "metrics_sha256": identity(row["metrics"])
                    if "metrics" in row
                    else None,
                    "result_sha256": row["files"].get("result.json.gz"),
                }
            )
        summaries.append(evidence)
        measurements.append(measured)
    result = {
        "registration_sha256": digest(args.registration),
        "probe_plan_sha256": identity(probe),
        "measurements": measurements,
        "comparison": compare(*summaries, measurements, reg),
        "inference_scope": "고정 serial→parallel 순서의 단일표본; cache순서영향포함,일반적속도보장아님",
    }
    write(output / "summary.json", result)
    print(json.dumps(result, ensure_ascii=False))
    return 0 if result["comparison"]["adoption_eligible"] else 2


def finish(args):
    reg = registration(args.registration)
    runner(reg, args, clean=False)
    sys.path[:0] = [str(ROOT), str(ROOT / "apps/api")]
    from tools.research.editor_picks.common import write
    from tools.research.editor_picks.crypto import transform
    from tools.research.editor_picks.remote import pack_result

    key = base64.b64decode(os.environ[args.key_env], altchars=b"-_", validate=True)
    require(len(key) == 32, "증거 암호화 키 길이가 다릅니다")
    root = args.run_dir.resolve()
    require(root.is_relative_to(ROOT / "runs"), "AB 결과 root 밖입니다")
    with tempfile.TemporaryDirectory() as temporary:
        stage = Path(temporary)
        for mode in reg["order"]:
            folder = root / mode["label"]
            if not (folder / "probe-plan.json").exists():
                continue
            stopped_writers(folder)
            provenance = {
                "head": args.head,
                "run_id": args.run_id,
                "attempt": args.attempt,
                "input_sha256": reg["parent_input_sha256"],
                "plan": "probe-plan.json",
                "plan_sha256": identity(read(folder / "probe-plan.json")),
                "shards": 1,
                "shard": 0,
            }
            pack_result(folder, stage / (mode["label"] + ".tar.gz"), 0, provenance)
            for name in ("measurement.json", "process-state.json"):
                if (folder / name).exists():
                    (stage / (mode["label"] + "-" + name)).write_bytes(
                        (folder / name).read_bytes()
                    )
        for source, name in [
            (args.registration, "registration.json"),
            (root / "summary.json", "summary.json"),
        ]:
            if source.exists():
                (stage / name).write_bytes(source.read_bytes())
        archive = stage / "evidence.tar.gz"
        with tarfile.open(archive, "w:gz") as packed:
            for path in sorted(stage.iterdir()):
                if path != archive:
                    packed.add(path, arcname=path.name, recursive=False)
        require(any(stage.glob("serial.tar.gz")), "실제 probe 증거가 없습니다")
        transform(
            "encrypt",
            archive,
            args.cipher,
            key,
            f"editor-picks-process-ab/{identity(reg)}/{args.run_id}/{args.attempt}",
        )
        write(
            args.cipher.with_suffix(".proof.json"),
            {
                "sha256": digest(args.cipher),
                "bytes": args.cipher.stat().st_size,
                "registration_sha256": digest(args.registration),
                "strategy_or_metrics_public_output": False,
            },
        )
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "run", "finish"))
    parser.add_argument("--registration", required=True, type=Path)
    parser.add_argument("--parent", type=Path)
    parser.add_argument("--parent-cipher", type=Path)
    parser.add_argument("--budget-file", type=Path)
    parser.add_argument("--run-dir", type=Path)
    parser.add_argument("--head")
    parser.add_argument("--run-id")
    parser.add_argument("--attempt")
    parser.add_argument("--cipher", type=Path)
    parser.add_argument("--key-env")
    args = parser.parse_args()
    try:
        if args.action == "validate":
            reg = registration(args.registration)
            require(
                isinstance(reg["binding_before_dispatch"]["control_head"], str)
                and re.fullmatch(
                    r"[a-f0-9]{40}", reg["binding_before_dispatch"]["control_head"]
                ),
                "실행 전 HEAD 결박이 필요합니다",
            )
            print(
                json.dumps(
                    {"registration_sha256": digest(args.registration), "bound": True}
                )
            )
            return 0
        return run(args) if args.action == "run" else finish(args)
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "not_adopted",
                    "error_type": type(error).__name__,
                    "automatic_adoption": False,
                }
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

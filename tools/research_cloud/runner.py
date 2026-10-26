"""원 run_group과 실제 컨테이너 증거만 사용하는 세 범위 ARM pilot."""
import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time

SECRET = "PERIOD_STUDY_ARM64_PILOT_20261027_KEY"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def guard_environment(bundle):
    assert os.environ.get("DOCKER_HOST") == "unix:///var/run/docker.sock"
    assert not any(os.environ.get(k) for k in ("GH_TOKEN", "GITHUB_TOKEN", SECRET, "SOL_RESEARCH_EPOCH7_KEY"))
    assert not any(p.name.startswith(".env") for p in bundle.rglob("*"))


def gzip_os_19_sha(path):
    """원파일은 읽기만 하며 gzip OS byte9 하나만 0x13으로 바꾼 SHA를 구한다."""
    with path.open("rb") as stream:
        header = stream.read(10)
        if len(header) != 10 or header[:3] != b"\x1f\x8b\x08":
            return None
        value = hashlib.sha256(header[:9] + b"\x13")
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
        return value.hexdigest()


def compare_rows(rows, case, run):
    assert len(rows) == 2 and [r["policy"] for r in rows] == ["A", "B"]
    assert set(case["expected"]) == {"A", "B"}
    comparisons = []
    for row in rows:
        assert all(row[k] == case[k] for k in ("publication_id", "code_path", "timeframe", "period"))
        assert row["status"] == "completed" and type(row["metrics"]["total_trades"]) is int and row["metrics"]["total_trades"] > 0
        actual = (run / row["result_file"]).resolve()
        assert actual.is_relative_to(run.resolve()) and actual.is_file() and sha(actual) == row["result_sha256"]
        oracle = case["expected"][row["policy"]]
        exact = row["request_hash"] == oracle["request_hash"] and row["result_sha256"] == oracle["result_sha256"]
        normalized = gzip_os_19_sha(actual) if not exact else None
        header_only = (row["request_hash"] == oracle["request_hash"] and row["result_sha256"] != oracle["result_sha256"]
                       and normalized == oracle["result_sha256"])
        comparisons.append({"policy": row["policy"], "request_hash": row["request_hash"], "result_sha256": row["result_sha256"], "exact": exact,
                            "transport_header_only": header_only, "gzip_os_19_sha256": normalized})
    assert len(comparisons) == 2
    return comparisons


def verify_observation(events, expected_image, expected_count, containers_before, containers_after):
    assert not containers_before and not containers_after
    created = [e for e in events if e["action"] == "create"]
    destroyed = [e["container_id"] for e in events if e["action"] == "destroy"]
    assert len(created) == expected_count and len(destroyed) == expected_count
    assert len({e["container_id"] for e in created}) == expected_count
    assert set(destroyed) == {e["container_id"] for e in created}
    assert len({e["inspect"]["name"] for e in created}) == expected_count
    for event in created:
        actual = event["inspect"]
        assert actual["runtime"] == "runsc" and actual["network"] == "none" and actual["readonly"] is True
        assert actual["image_id"] == expected_image and actual["nano_cpus"] == 1000000000
        assert actual["memory"] == actual["memory_swap"] == 1073741824
    return True


class ContainerObserver:
    def __init__(self):
        self.events = []
        self.errors = []
        self.process = None
        self.thread = None

    def start(self):
        self.process = subprocess.Popen(["docker", "events", "--since", str(time.time() - 1), "--filter", "type=container", "--filter", "event=create", "--filter", "event=destroy", "--format", "{{json .}}"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
        self.thread = threading.Thread(target=self.observe, daemon=True)
        self.thread.start()
        time.sleep(0.2)
        assert self.process.poll() is None

    def observe(self):
        try:
            for line in self.process.stdout:
                value = json.loads(line)
                event = {"action": value["Action"], "container_id": value.get("id", value["Actor"]["ID"])}
                if event["action"] == "create":
                    response = subprocess.run(["docker", "inspect", event["container_id"]], check=True, capture_output=True, text=True, timeout=5)
                    actual = json.loads(response.stdout)[0]
                    config = actual["HostConfig"]
                    event["inspect"] = {"name": actual["Name"], "image_id": actual["Image"], "runtime": config["Runtime"], "network": config["NetworkMode"], "readonly": config["ReadonlyRootfs"], "nano_cpus": config["NanoCpus"], "memory": config["Memory"], "memory_swap": config["MemorySwap"]}
                self.events.append(event)
        except Exception as error:
            self.errors.append(type(error).__name__)

    def close(self, expected_count):
        if self.process is None:
            return
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and len([e for e in self.events if e["action"] == "destroy"]) < expected_count and not self.errors:
            time.sleep(0.05)
        self.process.terminate()
        self.process.wait(timeout=5)
        self.thread.join(timeout=5)
        if self.thread.is_alive():
            self.errors.append("observer_thread_not_joined")
        self.process.stdout.close()


def containers():
    return subprocess.run(["docker", "ps", "-aq"], check=True, capture_output=True, text=True).stdout.strip().splitlines()


def main():
    if not __debug__:
        raise SystemExit("optimized_python_not_allowed")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle", type=Path)
    parser.add_argument("--case", type=int, choices=(0, 1, 2), required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    bundle = args.bundle.resolve()
    guard_environment(bundle)
    # 애플리케이션 설정 import가 요구하는 일회용 키다. DB·거래소·기존 키에 연결하지 않는다.
    os.environ["TRADING_ENCRYPTION_KEYS"] = base64.urlsafe_b64encode(os.urandom(32)).decode()
    manifest = json.loads((bundle / "pilot.json").read_bytes())
    assert manifest["kind"] == "period_study_arm64_three_case_pilot_v1"
    for relative, expected in manifest["files"].items():
        path = (bundle / relative).resolve()
        assert path.is_relative_to(bundle) and path.is_file() and sha(path) == expected
    sys.path[:0] = [str(bundle / "code"), str(bundle / "code/apps/api")]
    from tools.research.period_study import controller
    from tools.research.period_study.state import read, identity
    assert controller.implementation() == manifest["implementation"]
    assert controller.runtime() == manifest["image_ids"]
    assert sys.version.split()[0] == manifest["python_version"]
    expected = [("TA1v6Y21", "pine", "shared_events"), ("Wh9xxUzY", "python", "shared_events"), ("Gkib6KgL", "python", "position_feedback")]
    assert len(manifest["cases"]) == 3
    assert [(c["publication_id"], c["code_path"], c["signal_mode"]) for c in manifest["cases"]] == expected
    assert all(c["timeframe"] == "1h" and c["period"] == "P1" and c["policies"] == ["A", "B"] for c in manifest["cases"])
    case = manifest["cases"][args.case]
    run = bundle / "input-run"
    assert not (run / "cells").exists()
    item = next(v for v in read(run / "catalogue.json")["items"] if v["id"] == case["publication_id"])
    assert read(run / f"reviews/{case['publication_id']}.json")["signal_mode"] == case["signal_mode"]
    output = bundle / "result-output"
    output.mkdir(exist_ok=False)
    receipt = {"case": args.case, "source_execution": False, "status": "preflight_passed", "image_ids": controller.runtime(), "implementation_identity": identity(controller.implementation())}
    if args.execute:
        count = 1 if case["signal_mode"] == "shared_events" else 2
        observer = ContainerObserver()
        receipt.update(financial_dispatch_attempted=False, comparisons=[], containers_before=containers())
        started = time.monotonic()
        try:
            assert not receipt["containers_before"]
            observer.start()
            receipt["financial_dispatch_attempted"] = True
            rows = controller.run_group(run, run, item, case["code_path"], "1h", "P1", policies=("A", "B"))
            receipt["comparisons"] = compare_rows(rows, case, run)
            receipt["status"] = "compared"
        except Exception as error:
            receipt.update(status="failed", error_type=type(error).__name__)
            if type(error).__name__ == "ValidationError":
                receipt["validation_fields"] = [
                    {"loc": list(item["loc"]), "type": item["type"]}
                    for item in error.errors(include_input=False, include_context=False, include_url=False)
                ]
        finally:
            observer.close(count)
            receipt.update(duration_seconds=time.monotonic() - started, container_events=observer.events, observer_errors=observer.errors, containers_after=containers())
            try:
                receipt["isolation_evidence_verified"] = not observer.errors and verify_observation(observer.events, manifest["image_ids"][case["code_path"]], count, receipt["containers_before"], receipt["containers_after"])
            except (AssertionError, KeyError):
                receipt["isolation_evidence_verified"] = False
            receipt["source_execution"] = receipt["isolation_evidence_verified"] and len(receipt["comparisons"]) == 2
            if (run / "cells").exists():
                shutil.copytree(run / "cells", output / "cells")
    (output / "receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, sort_keys=True) + "\n")
    if args.execute and (not receipt["source_execution"] or len(receipt["comparisons"]) != 2 or not all(c["exact"] or c["transport_header_only"] for c in receipt["comparisons"])):
        raise SystemExit(2)


if __name__ == "__main__":
    main()

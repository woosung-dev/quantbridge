"""무료 ARM1대의 원 CSV parser만 검사한다. Docker/선정/경제 실행 경로는 없다."""

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import urllib.request

SHARED_SHA = "b1bff43186779d21772cbf6af4a8724313a9126ef80bfd5c5401f8b0b4eb6c2b"
SHARED = Path(__file__).with_name("sol_arm_bootstrap.py")
if hashlib.sha256(SHARED.read_bytes()).hexdigest() != SHARED_SHA:
    raise ValueError("reviewed_bootstrap_changed")
spec = importlib.util.spec_from_file_location("data_preflight_shared", SHARED)
arm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(arm)
PREFIX = "https://github.com/woosung-dev/quantbridge/releases/download/sol-research-epoch7-20261023/"
BASE_SHA = "d5c85d3fd8bb1c9788d00f43692dea1244ba0066575b0acdab7131394a910f39"
PROBE_SHA = "bd1c748009d21c5d62a6c8ea8cb9d29c1eaabe06bb9a6b9d414c62c58e66eb87"
SNAPSHOT_SHA = "37c603f7bd3c0dbcc384ca3678eaf27e44d4750dc57562024e37cca31f3fd6f1"


def names(snapshot):
    if len(snapshot.get("files", [])) != 10 or set(snapshot.get("sources", {})) != {"parent", "execution"}:
        raise ValueError("original_thirteen_data_files_required")
    result = {"data/snapshot.json", "data/parent-manifest.json", "data/execution-manifest.json"}
    for item in snapshot["files"]:
        name = Path(item["snapshot_path"])
        if name.is_absolute() or ".." in name.parts or str(name) != item["snapshot_path"]:
            raise ValueError("data_path_escape")
        result.add("data/" + str(name))
    if len(result) != 13:
        raise ValueError("distinct_thirteen_data_files_required")
    return result


def build(args):
    if arm.sha(args.snapshot) != SNAPSHOT_SHA or arm.sha(args.probe) != PROBE_SHA:
        raise ValueError("original_snapshot_and_reviewed_probe_required")
    snapshot = arm.load(args.snapshot)
    allowed = names(snapshot)
    for item in snapshot["files"]:
        if arm.sha(args.snapshot.parent / item["snapshot_path"]) != item["sha256"]:
            raise ValueError("original_csv_bytes_changed")
    for name, item in snapshot["sources"].items():
        if arm.sha(args.snapshot.parent / (name + "-manifest.json")) != item["sha256"]:
            raise ValueError("original_source_manifest_changed")
    args.directory.mkdir(mode=0o700)
    archive = args.directory / "data-preflight.tar.gz"
    with archive.open("xb") as stream, tarfile.open(fileobj=stream, mode="w:gz", compresslevel=1) as bundle:
        for name in sorted(allowed):
            source = args.snapshot if name == "data/snapshot.json" else args.snapshot.parent / name.removeprefix("data/")
            bundle.add(source, arcname=name, recursive=False)
        bundle.add(args.probe, arcname="probe.py", recursive=False)
    arm.write(args.directory / "build.json", {"status": "DATA_PREFLIGHT_PAYLOAD_ONLY", "files": 14,
        "snapshot_sha256": SNAPSHOT_SHA, "probe_sha256": PROBE_SHA, "tar_sha256": arm.sha(archive),
        "tar_bytes": archive.stat().st_size, "native_calls": 0, "quality_or_selection_read": False})


def identity(event, environment):
    request = event.get("pull_request", {})
    if (environment.get("GITHUB_REPOSITORY") != arm.REPOSITORY or environment.get("GITHUB_ACTOR") != "woosung-dev"
            or environment.get("GITHUB_RUN_ATTEMPT") != "1" or environment.get("GITHUB_EVENT_NAME") != "pull_request"
            or environment.get("RUNNER_ENVIRONMENT") != "github-hosted" or event.get("repository", {}).get("private") is not False
            or event.get("action") != "labeled" or event.get("label", {}).get("name") != "sol-economic-data-preflight"
            or event.get("number") != 925 or request.get("number") != 925
            or request.get("user", {}).get("login") != "woosung-dev"
            or request.get("head", {}).get("repo", {}).get("full_name") != arm.REPOSITORY
            or request.get("head", {}).get("ref") != "stage/sol-research-arm-runners"
            or request.get("base", {}).get("ref") != "stage/sol-strategy-lab"):
        raise ValueError("public_owner_pr925_attempt1_preflight_label_required")


def configured(args):
    import re
    if not args.data_url.startswith(PREFIX) or not re.fullmatch(r"[a-f0-9]{64}", args.data_sha256) or args.data_sha256 == "0" * 64:
        raise ValueError("reviewed_data_cipher_pin_required")


def prepare(args):
    configured(args)
    args.directory.mkdir(mode=0o700)
    for name, url, checksum, context in (("base", PREFIX + "input.enc", BASE_SHA, "input-v7"),
            ("data", args.data_url, args.data_sha256, "economic-data-preflight-input-v8")):
        cipher, archive = args.directory / (name + ".enc"), args.directory / (name + ".tar")
        arm.download(url, checksum, cipher)
        arm.crypto(args, "decrypt", cipher, archive, context)
    base = args.directory / "bundle"
    base.mkdir(mode=0o700)
    arm.safe_extract(args.directory / "base.tar", base)
    with tarfile.open(args.directory / "data.tar", "r:gz") as bundle:
        members = bundle.getmembers()
        if (len(members) != 14 or len({m.name for m in members}) != 14
                or any(not m.isfile() for m in members) or sum(m.size for m in members) > 8 * 1024**3):
            raise ValueError("closed_data_probe_archive_required")
        by_name = {m.name: m for m in members}
        if "data/snapshot.json" not in by_name or by_name["data/snapshot.json"].size > 16 * 1024**2:
            raise ValueError("snapshot_metadata_required")
        raw = bundle.extractfile(by_name["data/snapshot.json"]).read()
        if hashlib.sha256(raw).hexdigest() != SNAPSHOT_SHA or set(by_name) != names(json.loads(raw)) | {"probe.py"}:
            raise ValueError("fixed_snapshot_archive_allowlist")
        if hashlib.sha256(bundle.extractfile(by_name["probe.py"]).read()).hexdigest() != PROBE_SHA:
            raise ValueError("reviewed_probe_hash")
    destination = args.directory / "data-probe"
    destination.mkdir(mode=0o700)
    arm.safe_extract(args.directory / "data.tar", destination)
    arm.write(args.directory / "prepared.json", {"status": "DATA_PREFLIGHT_AUTHENTICATED", "run_id": args.run_id,
        "base_sha256": BASE_SHA, "data_sha256": args.data_sha256, "probe_sha256": PROBE_SHA})


def probe(args):
    base, payload = args.directory / "bundle", args.directory / "data-probe"
    if arm.sha(payload / "probe.py") != PROBE_SHA:
        raise ValueError("reviewed_probe_changed")
    empty = args.directory / "empty"
    empty.mkdir(mode=0o700)
    environment = {"PATH": os.environ["PATH"], "PYTHONDONTWRITEBYTECODE": "1", "TZ": "UTC", "LANG": "C.UTF-8",
        "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
    command = [str(args.directory / "venv/bin/python"), "-B", str(payload / "probe.py"),
        "--source-root", str(base / "source"), "--pending", str(base / "inputs/pending.json"),
        "--snapshot", str(payload / "data/snapshot.json"), "--output", str(args.directory / "data-hashes.json")]
    with (args.directory / "private-probe.log").open("xb") as log:
        result = subprocess.run(command, cwd=empty, env=environment, stdout=log, stderr=log, timeout=1800, check=False)
    arm.write(args.directory / "probe-exit.json", {"returncode": result.returncode, "actual_wait_observed": True})
    if result.returncode:
        raise RuntimeError("data_probe_failed_no_economic_results")


def pack(args):
    if not args.directory.is_dir():
        return
    archive = args.directory / "private-result.tar.gz"
    with archive.open("xb") as stream, tarfile.open(fileobj=stream, mode="w:gz") as bundle:
        for name in ("data-hashes.json", "probe-exit.json", "prepared.json", "private-probe.log", "private-dependencies.log", "failure.json"):
            path = args.directory / name
            if path.is_file():
                bundle.add(path, arcname=name, recursive=False)
    arm.crypto(args, "encrypt", archive, args.directory / "result.enc", "economic-data-preflight-result-v8-" + args.run_id)
    if (args.directory / "result.enc").stat().st_size > arm.MAX_ASSET_BYTES:
        raise ValueError("data_preflight_result_size_limit")
    arm.write(args.directory / "pack.json", {"cipher_sha256": arm.sha(args.directory / "result.enc")})


def upload(args):
    if not (args.directory / "pack.json").is_file():
        return
    cipher = args.directory / "result.enc"
    if arm.load(args.directory / "pack.json")["cipher_sha256"] != arm.sha(cipher):
        raise ValueError("sealed_preflight_cipher_changed")
    name = "epoch8-economic-data-preflight-" + args.run_id + ".enc"
    with cipher.open("rb") as stream:
        request = urllib.request.Request(f"https://uploads.github.com/repos/{arm.REPOSITORY}/releases/420970222/assets?name={name}",
            data=stream, method="POST", headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"],
                "Content-Type": "application/octet-stream", "Content-Length": str(cipher.stat().st_size)})
        with urllib.request.urlopen(request, timeout=120) as response:
            asset = json.load(response)
    if asset.get("name") != name or asset.get("size") != cipher.stat().st_size:
        raise ValueError("preflight_upload_unknown")


def compare(args):
    import re
    local, remote = arm.load(args.local_result), arm.load(args.remote_result)
    expected = {f"{family}/{symbol}/{tf}" for family in ("historical_parent", "minute_execution")
        for symbol in ("BTCUSDT", "ETHUSDT") for tf in ("1h", "4h", "1d")}
    for value in (local, remote):
        rows = value.get("cells", [])
        if (value.get("schema_version") != 1 or value.get("status") != "DATA_HASHES_ONLY_NO_ECONOMICS"
                or value.get("snapshot_sha256") != SNAPSHOT_SHA or value.get("probe_sha256") != PROBE_SHA
                or value.get("data_source_sha256") != "edb6db7731871f485d16f21e8abe76bbe835ccc65d6d21eac4cd60b246f786f6"
                or value.get("economics_source_sha256") != "6f47ecf5a6168b91383ff1d0338f3afbd3c0f3cb3e3431b8b07465c6b54917ed"
                or type(value.get("native_calls")) is not int or value["native_calls"] != 0
                or value.get("selection_read") is not False or value.get("historical_daily_loaded_for_parser_check_only") is not True
                or len(rows) != 12 or {row.get("cell", {}).get("id") for row in rows} != expected
                or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", value.get("python", ""))
                or set(value.get("packages", {})) != {"numpy", "pandas"}):
            raise ValueError("complete_original_twelve_cell_evidence_required")
        for row in rows:
            hashes = row.get("hashes", {})
            if (set(hashes) != {"parent", "funding_observed", "execution"}
                    or any(not re.fullmatch(r"[a-f0-9]{64}", hashes.get(name, "")) for name in ("parent", "funding_observed"))
                    or (row["cell"]["execution"] and not re.fullmatch(r"[a-f0-9]{64}", hashes.get("execution", "")))
                    or (not row["cell"]["execution"] and hashes.get("execution") is not None)):
                raise ValueError("complete_cell_frame_hashes_required")
    keys = ("schema_version", "status", "cells", "snapshot_sha256", "data_source_sha256", "economics_source_sha256",
            "probe_sha256", "python", "packages", "native_calls", "selection_read", "historical_daily_loaded_for_parser_check_only")
    if (local.get("system") != "Darwin" or remote.get("system") != "Linux"
            or remote.get("machine") not in ("aarch64", "arm64")
            or any(local.get(k) != remote.get(k) for k in keys)):
        raise ValueError("cross_os_original_loader_hash_mismatch")
    with args.output.open("x") as stream:
        json.dump({"status": "EXACT_12CELL_DATA_HASH_MATCH_NOT_ECONOMIC_COMPLETION",
            "local_sha256": arm.sha(args.local_result), "remote_sha256": arm.sha(args.remote_result)}, stream)
    args.output.chmod(0o600)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("build", "validate", "prepare", "dependencies", "probe", "pack", "upload", "compare"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--run-id", default="")
    for name in ("snapshot", "probe", "crypto", "local-result", "remote-result", "output"):
        parser.add_argument("--" + name, type=Path)
    for name in ("crypto-sha256", "data-url", "data-sha256"):
        parser.add_argument("--" + name, default="")
    args = parser.parse_args()
    args.directory = args.directory.resolve()
    if args.action in ("build", "compare"):
        globals()[args.action](args)
        return
    identity(arm.load(os.environ["GITHUB_EVENT_PATH"]), os.environ)
    if args.run_id != os.environ["GITHUB_RUN_ID"]:
        raise ValueError("actual_workflow_run_required")
    try:
        if args.action == "validate":
            configured(args)
        elif args.action == "dependencies":
            arm.dependencies(args)
        else:
            globals()[args.action](args)
    except BaseException as error:
        if args.directory.is_dir():
            arm.write(args.directory / "failure.json", {"action": args.action, "error_type": type(error).__name__, "private_only": True})
        raise


if __name__ == "__main__":
    try:
        main()
    except BaseException as error:
        print("economic data preflight failed: " + type(error).__name__, file=sys.stderr)
        raise SystemExit(1) from None

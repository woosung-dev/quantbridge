"""봉인된 경제 payload만 무료 공개 ARM runner에서 실행한다. 평가 수식은 없다."""

from __future__ import annotations

import argparse
import base64
from datetime import UTC, datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tarfile
import urllib.request

BASE_HELPER = Path(__file__).with_name("sol_arm_bootstrap.py")
BASE_HELPER_SHA = "b1bff43186779d21772cbf6af4a8724313a9126ef80bfd5c5401f8b0b4eb6c2b"
if hashlib.sha256(BASE_HELPER.read_bytes()).hexdigest() != BASE_HELPER_SHA:
    raise RuntimeError("reviewed_semantic_bootstrap_changed")
_spec = importlib.util.spec_from_file_location("economic_shared_arm_bootstrap", BASE_HELPER)
arm = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(arm)

RELEASE_PREFIX = "https://github.com/woosung-dev/quantbridge/releases/download/sol-research-epoch7-20261023/"
BASE_URL = RELEASE_PREFIX + "input.enc"
BASE_SHA = "d5c85d3fd8bb1c9788d00f43692dea1244ba0066575b0acdab7131394a910f39"
REVISION_URL = RELEASE_PREFIX + "revision-v8-freq1h.enc"
REVISION_SHA = "04e721d0636bf6a3beb9cb9e93d69a06fec1f73e9df8896527a39387f963150a"
QUALITY_SHA = "edd82481441eace519b9a5ab0137e21c79586e4f584b24ac9114cf9c8e224c62"
SNAPSHOT_SHA = "37c603f7bd3c0dbcc384ca3678eaf27e44d4750dc57562024e37cca31f3fd6f1"
RUNNER_FILES = {"economic_protocol.py", "worker.py", "adapter.py", "portable_bundle.py", "finalize.py"}
DIAGNOSTICS = (
    "worker-exit.json", "cleanup.json", "claim.json", "prepared.json",
    "private-worker.log", "private-dependencies.log", "bootstrap-failure.json", "owned-runtime.json",
)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str, allow_nan=False).encode()).hexdigest()


def validate_identity(event, environment):
    request = event.get("pull_request", {})
    if (environment.get("GITHUB_REPOSITORY") != arm.REPOSITORY
            or environment.get("GITHUB_ACTOR") != "woosung-dev"
            or environment.get("GITHUB_RUN_ATTEMPT") != "1"
            or environment.get("GITHUB_EVENT_NAME") != "pull_request"
            or environment.get("RUNNER_ENVIRONMENT") != "github-hosted"
            or event.get("repository", {}).get("private") is not False
            or event.get("action") != "labeled"
            or event.get("label", {}).get("name") != "sol-research-economics-execute"
            or event.get("number") != 925 or request.get("number") != 925
            or request.get("user", {}).get("login") != "woosung-dev"
            or request.get("head", {}).get("repo", {}).get("full_name") != arm.REPOSITORY
            or request.get("head", {}).get("ref") != "stage/sol-research-arm-runners"
            or request.get("base", {}).get("ref") != "stage/sol-strategy-lab"):
        raise ValueError("public_owner_pr925_attempt1_economic_label_required")


def configured(url, checksum):
    if (not isinstance(url, str) or not url.startswith(RELEASE_PREFIX)
            or not isinstance(checksum, str) or not re.fullmatch(r"[a-f0-9]{64}", checksum)
            or checksum == "0" * 64):
        raise ValueError("reviewed_economic_and_semantic_overlay_pins_required")


def validate(args):
    configured(args.economic_url, args.economic_sha256)
    configured(args.overlay_url, args.overlay_sha256)
    if (args.url != BASE_URL or args.sha256 != BASE_SHA
            or args.revision_url != REVISION_URL or args.revision_sha256 != REVISION_SHA):
        raise ValueError("fixed_base_and_v8_revision_required")


def safe_name(name):
    value = Path(name)
    return bool(name) and not value.is_absolute() and ".." not in value.parts and str(value) == name


def merge_economic(base, archive, destination):
    """인증한 delta의 고정25파일만 새 source/inputs 사본에 추가한다."""
    with tarfile.open(archive, "r:*") as bundle:
        members = bundle.getmembers()
        if (len(members) != 25 or len({m.name for m in members}) != 25
                or any(not m.isfile() or not safe_name(m.name) for m in members)
                or sum(m.size for m in members) > 8 * 1024**3):
            raise ValueError("closed_economic_delta_members_required")
        by_name = {m.name: m for m in members}
        snapshot_member = by_name.get("data/snapshot.json")
        if snapshot_member is None or snapshot_member.size > 16 * 1024**2:
            raise ValueError("economic_snapshot_required")
        raw_snapshot = bundle.extractfile(snapshot_member).read()
        if hashlib.sha256(raw_snapshot).hexdigest() != SNAPSHOT_SHA:
            raise ValueError("original_economic_snapshot_required")
        snapshot = json.loads(raw_snapshot)
        data_files = {"data/snapshot.json", "data/parent-manifest.json", "data/execution-manifest.json"}
        if len(snapshot.get("files", [])) != 10 or set(snapshot.get("sources", {})) != {"parent", "execution"}:
            raise ValueError("original_ten_csv_two_manifests_required")
        for item in snapshot["files"]:
            if not safe_name(item["snapshot_path"]):
                raise ValueError("economic_data_path_escape")
            data_files.add("data/" + item["snapshot_path"])
        quality_files = {f"inputs/{folder}/{name}" for folder in ("quality-origin", "economic-sealed")
                         for name in ("quality.json", "quality.selection.json", "quality.artifacts.json")}
        expected = data_files | quality_files | {"runner/" + name for name in RUNNER_FILES} | {"economic-dispatch.json"}
        if len(data_files) != 13 or set(by_name) != expected:
            raise ValueError("economic_delta_allowlist_mismatch")
        plan = json.loads(bundle.extractfile(by_name["economic-dispatch.json"]).read())
        quality = plan.get("quality_exit_evidence", {})
        report = json.loads(bundle.extractfile(by_name["inputs/economic-sealed/quality.json"]).read())
        if (plan.get("epoch_id") != "economics-distributed-v8" or plan.get("cold") is not True
                or plan.get("automatic_resume") is not False
                or quality.get("quality_driver_sha256") != QUALITY_SHA
                or quality.get("input_provider_revision", {}).get("epoch") != 8
                or report.get("complete") is not True or report.get("final_selection_allowed") is not True
                or report.get("expected_artifacts") != 1350):
            raise ValueError("actual_quality_seal_before_economics_required")
        references = plan["base_reference"]
        if (references["pending_sha256"] != arm.sha(base / "inputs/pending.json")
                or references["generation_manifest_sha256"] != arm.sha(base / "inputs/generation-manifest.json")):
            raise ValueError("base_revision_execute_overlay_mismatch")
        if len(plan.get("jobs", [])) != 1440:
            raise ValueError("economic_exact1440_required")
        destination.mkdir(mode=0o700)
        for folder in ("source", "inputs"):
            if any(p.is_symlink() for p in (base / folder).rglob("*")):
                raise ValueError("base_symlink_forbidden")
            shutil.copytree(base / folder, destination / folder)
        if any((destination / name).exists() for name in expected):
            raise ValueError("economic_merge_never_overwrites_base")
        for member in members:
            path = destination / member.name
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            with path.open("xb") as output, bundle.extractfile(member) as incoming:
                shutil.copyfileobj(incoming, output)
            path.chmod(0o600)
    for name, checksum in plan["input_files"].items():
        if not safe_name(name) or arm.sha(destination / name) != checksum:
            raise ValueError("economic_input_inventory_hash")
    for name, checksum in plan["helper_hashes"].items():
        if name not in RUNNER_FILES or arm.sha(destination / "runner" / name) != checksum:
            raise ValueError("economic_helper_hash")
    epoch = arm.load(base / "epoch.json")
    if plan["image_ids"] != epoch["image_ids"] or len(plan["image_ids"]) != 3:
        raise ValueError("exact_three_economic_images_required")
    return plan


def prepare(args):
    validate(args)  # 미설정이면 디렉터리 생성·통신·복호화를 시작하지 않는다.
    args.directory.mkdir(mode=0o700)
    base = args.directory / "bundle"
    base.mkdir(mode=0o700)
    for label, url, checksum, context in (
        ("base", args.url, args.sha256, "input-v7"),
        ("revision", args.revision_url, args.revision_sha256, "input-revision-v8"),
        ("overlay", args.overlay_url, args.overlay_sha256, "input-v8-overlay"),
        ("economic", args.economic_url, args.economic_sha256, "economic-input-v8"),
    ):
        cipher, archive = args.directory / (label + ".enc"), args.directory / (label + ".tar")
        arm.download(url, checksum, cipher)
        arm.crypto(args, "decrypt", cipher, archive, context)
        if label == "base":
            arm.safe_extract(archive, base)
        elif label == "revision":
            arm.apply_revision(base, archive, BASE_SHA)
        elif label == "overlay":
            arm.apply_overlay(base, archive)
    plan = merge_economic(base, args.directory / "economic.tar", args.directory / "economic-bundle")
    arm.write(args.directory / "prepared.json", {
        "status": "ECONOMIC_INPUT_AUTHENTICATED", "plan_sha256": digest(plan),
        "base_cipher_sha256": BASE_SHA, "revision_cipher_sha256": REVISION_SHA,
        "semantic_overlay_sha256": args.overlay_sha256, "economic_payload_sha256": args.economic_sha256,
        "host": f"remote-{args.shard + 1:02}", "run_id": args.run_id,
        "bootstrap_sha256": arm.sha(__file__), "shared_bootstrap_sha256": BASE_HELPER_SHA,
        "observed_utc": datetime.now(UTC).isoformat()})


def claim(args):
    prepared = arm.load(args.directory / "prepared.json")
    name = f"epoch8-economic-remote-{args.shard + 1:02}.claim.json"
    body = {**prepared, "mode": "economic_execute", "schema_version": 1}
    request = urllib.request.Request(
        f"https://uploads.github.com/repos/{arm.REPOSITORY}/releases/{args.release_id}/assets?name={name}",
        data=json.dumps(body).encode(), method="POST",
        headers={"Authorization": "Bearer " + os.environ["GH_TOKEN"], "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=30) as response:
        asset = json.load(response)
    if asset.get("name") != name or type(asset.get("id")) is not int:
        raise ValueError("immutable_claim_response_mismatch")
    arm.write(args.directory / "claim.json", {**body, "asset_id": asset["id"], "name": name})


def run(args):
    prepared = arm.load(args.directory / "prepared.json")
    reservation = arm.load(args.directory / "claim.json")
    if any(reservation.get(k) != v for k, v in prepared.items()):
        raise ValueError("exact_immutable_economic_claim_required")
    if prepared["host"] != f"remote-{args.shard + 1:02}" or prepared["run_id"] != args.run_id:
        raise ValueError("economic_claim_run_host_mismatch")
    root, output = args.directory / "economic-bundle", args.directory / "result"
    empty, config = args.directory / "empty", args.directory / "empty-docker-config"
    empty.mkdir(mode=0o700)
    config.mkdir(mode=0o700)
    environment = {"PATH": os.environ["PATH"], "PYTHONPATH": f"{root / 'source'}:{root / 'source/apps/api'}",
        "PYTHONDONTWRITEBYTECODE": "1", "DOCKER_HOST": "unix:///var/run/docker.sock",
        "DOCKER_CONFIG": str(config), "TZ": "UTC", "LANG": "C.UTF-8",
        "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
        "TRADING_ENCRYPTION_KEYS": base64.urlsafe_b64encode(os.urandom(32)).decode()}
    command = [str(args.directory / "venv/bin/python"), "-B", str(root / "runner/worker.py"),
               "--bundle", str(root), "--output", str(output), "--host", prepared["host"], "--execute"]
    child, code, waited = None, None, False
    try:
        with (args.directory / "private-worker.log").open("xb") as log:
            child = subprocess.Popen(command, cwd=empty, env=environment,
                stdout=log, stderr=log, start_new_session=True)
            code = child.wait()
            waited = True
        if code:
            raise RuntimeError("economic_worker_failed")
    except BaseException:
        if child is not None and child.poll() is None:
            if os.getpgid(child.pid) != child.pid:
                raise RuntimeError("owned_worker_process_group_unknown") from None
            os.killpg(child.pid, signal.SIGTERM)
            try:
                code = child.wait(timeout=15)
            except subprocess.TimeoutExpired:
                if child.poll() is None and os.getpgid(child.pid) == child.pid:
                    os.killpg(child.pid, signal.SIGKILL)
                code = child.wait(timeout=15)
            waited = True
        raise
    finally:
        arm.write(args.directory / "worker-exit.json", {"returncode": code,
            "actual_wait_observed": waited, "worker_started": child is not None,
            "worker_pid": child.pid if child is not None else None})


def cleanup(args):
    exit_path = args.directory / "worker-exit.json"
    if exit_path.exists():
        state = arm.load(exit_path)
        if state["worker_started"] and not state["actual_wait_observed"]:
            raise RuntimeError("worker_wait_unknown_cleanup_refused")
        if state["worker_started"]:
            try:
                os.killpg(state["worker_pid"], 0)
            except ProcessLookupError:
                pass
            else:
                raise RuntimeError("worker_group_still_present_cleanup_refused")
    arm.cleanup(args)


def pack(args):
    if not args.directory.is_dir():
        return
    archive = args.directory / "economic-result.tar.gz"
    with archive.open("xb") as stream, tarfile.open(fileobj=stream, mode="w:gz", compresslevel=1) as bundle:
        for name in ("result", *DIAGNOSTICS):
            path = args.directory / name
            if path.exists():
                if path.is_symlink() or any(p.is_symlink() for p in path.rglob("*")):
                    raise ValueError("result_symlink_forbidden")
                bundle.add(path, arcname=name, recursive=True)
    if archive.stat().st_size > arm.MAX_ASSET_BYTES:
        raise ValueError("compressed_economic_result_too_large_no_files_removed")
    target = args.directory / "result.enc"
    arm.crypto(args, "encrypt", archive, target, f"result-v8-economic-{args.shard}")
    if target.stat().st_size > arm.MAX_ASSET_BYTES:
        raise ValueError("encrypted_economic_result_too_large_no_files_removed")
    arm.write(args.directory / "pack-ready.json", {
        "status": "ENCRYPTED_ECONOMIC_RESULT_READY", "sha256": arm.sha(target),
        "bytes": target.stat().st_size, "run_id": args.run_id, "shard": args.shard,
        "asset_name": f"epoch8-economic-{args.shard}-{args.run_id}.enc",
        "context": f"result-v8-economic-{args.shard}"})


def upload(args):
    path = args.directory / "pack-ready.json"
    if not path.exists():
        return
    proof, cipher = arm.load(path), args.directory / "result.enc"
    expected = f"epoch8-economic-{args.shard}-{args.run_id}.enc"
    if (proof.get("status") != "ENCRYPTED_ECONOMIC_RESULT_READY"
            or proof.get("asset_name") != expected or proof.get("run_id") != args.run_id
            or proof.get("shard") != args.shard or proof.get("sha256") != arm.sha(cipher)
            or proof.get("bytes") != cipher.stat().st_size or cipher.stat().st_size > arm.MAX_ASSET_BYTES):
        raise ValueError("sealed_ciphertext_upload_proof_mismatch")
    with cipher.open("rb") as stream:
        request = urllib.request.Request(
            f"https://uploads.github.com/repos/{arm.REPOSITORY}/releases/{args.release_id}/assets?name={expected}",
            data=stream, method="POST", headers={
                "Authorization": "Bearer " + os.environ["GH_TOKEN"],
                "Content-Type": "application/octet-stream", "Content-Length": str(cipher.stat().st_size)})
        with urllib.request.urlopen(request, timeout=600) as response:
            asset = json.load(response)
    if asset.get("name") != expected or asset.get("size") != cipher.stat().st_size:
        raise ValueError("ciphertext_upload_response_unknown")
    arm.write(args.directory / "upload.json", {"asset_id": asset["id"], "name": expected, "sha256": proof["sha256"]})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("validate", "prepare", "dependencies", "runtime", "claim", "run", "cleanup", "pack", "upload"))
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--shard", type=int, choices=range(16), required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--release-id", type=int, default=420970222)
    for name, default in (("url", BASE_URL), ("sha256", BASE_SHA), ("revision-url", REVISION_URL),
                          ("revision-sha256", REVISION_SHA), ("overlay-url", ""), ("overlay-sha256", ""),
                          ("economic-url", ""), ("economic-sha256", "")):
        parser.add_argument("--" + name, default=default)
    parser.add_argument("--crypto", type=Path)
    parser.add_argument("--crypto-sha256")
    args = parser.parse_args()
    args.directory = args.directory.resolve()
    validate_identity(arm.load(os.environ["GITHUB_EVENT_PATH"]), os.environ)
    if args.run_id != os.environ["GITHUB_RUN_ID"] or args.release_id != 420970222:
        raise ValueError("fixed_release_and_actual_run_required")
    def interrupted(*_):
        raise KeyboardInterrupt("economic_bootstrap_interrupted")
    signal.signal(signal.SIGTERM, interrupted)
    try:
        if args.action in ("dependencies", "runtime"):
            getattr(arm, args.action)(args)
        else:
            globals()[args.action](args)
    except BaseException as error:
        if args.directory.is_dir():
            arm.write(args.directory / "bootstrap-failure.json", {
                "action": args.action, "error_type": type(error).__name__,
                "last_observation": arm.LAST_OBSERVATION,
                "runtime_observation": arm.RUNTIME_OBSERVATION,
                "private_encrypted_only": True})
        print("economic bootstrap failed: " + type(error).__name__, file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()

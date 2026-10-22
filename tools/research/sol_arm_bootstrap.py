"""암호화된 연구 bundle을 일회용 ARM runner에서만 준비한다. 평가 수식은 포함하지 않는다."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request
from pathlib import Path

REPOSITORY = "woosung-dev/quantbridge"
MAX_ASSET_BYTES = 2 * 1024**3 - 1
LAST_OBSERVATION = {}


def sha(path):
    value = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def checked(command, *, env=None, cwd=None):
    if env is None:
        env = {
            "PATH": os.environ["PATH"],
            "LANG": "C.UTF-8",
            "TZ": "UTC",
            "DOCKER_HOST": "unix:///var/run/docker.sock",
        }
    result = subprocess.run(command, env=env, cwd=cwd, capture_output=True, timeout=900)
    def private_text(raw):
        value = raw.decode(errors="replace")[-32768:]
        for name in ("SOL_RESEARCH_EPOCH7_KEY", "GH_TOKEN"):
            secret = os.environ.get(name)
            if secret:
                value = value.replace(secret, "<redacted>")
        return value
    LAST_OBSERVATION.clear()
    LAST_OBSERVATION.update(command=command, returncode=result.returncode,
                            stdout=private_text(result.stdout), stderr=private_text(result.stderr))
    if result.returncode:
        raise RuntimeError("bootstrap_subprocess_failed")
    return result.stdout.decode().strip()


def load(path):
    return json.loads(Path(path).read_text())


def write(path, value):
    Path(path).write_text(json.dumps(value, sort_keys=True) + "\n")


def download(url, expected, destination):
    if not re.fullmatch(r"[a-f0-9]{64}", expected) or expected == "0" * 64:
        raise ValueError("unconfigured_download_pin")
    prefix = f"https://github.com/{REPOSITORY}/releases/download/"
    if not url.startswith(prefix):
        raise ValueError("release_origin_not_allowed")
    with (
        urllib.request.urlopen(url, timeout=120) as response,
        Path(destination).open("xb") as out,
    ):
        total = 0
        for chunk in iter(lambda: response.read(1024 * 1024), b""):
            total += len(chunk)
            if total > MAX_ASSET_BYTES:
                raise ValueError("input_asset_too_large")
            out.write(chunk)
    if sha(destination) != expected:
        raise ValueError("ciphertext_sha_mismatch")


def safe_extract(archive, destination):
    """링크·device·중복·경로 이탈을 거절하고 일반 파일만 직접 쓴다."""
    root = Path(destination).resolve()
    seen = set()
    with tarfile.open(archive, "r:*") as bundle:
        members = bundle.getmembers()
        if sum(item.size for item in members) > 8 * 1024**3:
            raise ValueError("bundle_expansion_too_large")
        for item in members:
            name = Path(item.name)
            target = (root / name).resolve()
            if (
                name.is_absolute()
                or ".." in name.parts
                or not target.is_relative_to(root)
            ):
                raise ValueError("unsafe_bundle_path")
            if item.name in seen or not (item.isfile() or item.isdir()):
                raise ValueError("unsafe_bundle_member")
            seen.add(item.name)
        for item in members:
            target = root / item.name
            if item.isdir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as out, bundle.extractfile(item) as stream:
                    shutil.copyfileobj(stream, out)
                target.chmod(0o700 if item.mode & 0o111 else 0o600)


def crypto(args, action, source, destination, context):
    if sha(args.crypto) != args.crypto_sha256 or args.crypto_sha256 == "0" * 64:
        raise ValueError("crypto_source_pin_mismatch")
    checked(
        [
            sys.executable,
            str(args.crypto),
            action,
            "--input",
            str(source),
            "--output",
            str(destination),
            "--key-env",
            "SOL_RESEARCH_EPOCH7_KEY",
            "--context",
            context,
        ],
        env={
            "PATH": os.environ["PATH"],
            "PYTHONDONTWRITEBYTECODE": "1",
            "SOL_RESEARCH_EPOCH7_KEY": os.environ["SOL_RESEARCH_EPOCH7_KEY"],
        },
    )


def apply_overlay(root, overlay):
    """인계 후 pending 하나만 대체한다. 다른 파일은 overlay에 들어갈 수 없다."""
    target = Path(root) / "inputs/pending.json"
    with tarfile.open(overlay, "r:*") as bundle:
        members = bundle.getmembers()
        if (
            len(members) != 1
            or members[0].name != "inputs/pending.json"
            or not members[0].isfile()
        ):
            raise ValueError("overlay_must_only_replace_pending")
        if members[0].size > 16 * 1024**2:
            raise ValueError("overlay_too_large")
        value = bundle.extractfile(members[0]).read()
        json.loads(value)
        target.write_bytes(value)


def prepare(args):
    args.directory.mkdir(mode=0o700)
    encrypted, archive = args.directory / "input.enc", args.directory / "input.tar"
    download(args.url, args.sha256, encrypted)
    crypto(args, "decrypt", encrypted, archive, "input-v7")
    root = args.directory / "bundle"
    root.mkdir(mode=0o700)
    safe_extract(archive, root)
    if args.mode == "execute":
        if not args.overlay_url or not args.overlay_sha256:
            raise ValueError("execute_requires_cutover_overlay")
        overlay_cipher, overlay = (
            args.directory / "overlay.enc",
            args.directory / "overlay.tar",
        )
        download(args.overlay_url, args.overlay_sha256, overlay_cipher)
        crypto(args, "decrypt", overlay_cipher, overlay, "input-v7-overlay")
        apply_overlay(root, overlay)
    # 원 bundle 전송·복호화가 끝나도 설정/모델/실제 평가 함수는 여기서 부르지 않는다.
    write(
        args.directory / "prepared.json",
        {
            "mode": args.mode,
            "cipher_sha256": args.sha256,
            "overlay_sha256": args.overlay_sha256,
            "pending_sha256": sha(root / "inputs/pending.json"),
        },
    )


def dependencies(args):
    requirements = args.directory / "bundle/host-requirements.txt"
    lines = requirements.read_text().splitlines()
    version = load(args.directory / "bundle/inputs/pending.json")["python_version"]
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", version):
        raise ValueError("exact_host_python_required")
    if not lines or any(
        not re.fullmatch(r"[A-Za-z0-9_.-]+==[A-Za-z0-9_.+!-]+", line) for line in lines
    ):
        raise ValueError("exact_host_requirements_required")
    # 제품 mise 기본값을 바꾸지 않고 실험 관측 patch와 package 원문 pin을 사용한다.
    environment = {
        "PATH": os.environ["PATH"],
        "LANG": "C.UTF-8",
        "UV_NO_CACHE": "1",
        "UV_PYTHON_INSTALL_DIR": str(args.directory / "managed-python"),
        "UV_CACHE_DIR": str(args.directory / "private-uv-cache"),
    }
    worker_python = args.directory / "venv/bin/python"
    with (args.directory / "private-dependencies.log").open("xb") as log:
        commands = [
            ["uv", "venv", "--python", version, str(args.directory / "venv")],
            [
                "uv",
                "pip",
                "install",
                "--python",
                str(worker_python),
                "--no-deps",
                "--requirement",
                str(requirements),
            ],
        ]
        for command in commands:
            code = subprocess.run(
                command, env=environment, stdout=log, stderr=log, timeout=600
            ).returncode
            if code:
                raise RuntimeError("host_dependency_install_failed")


def runtime(args):
    root = args.directory / "bundle"
    epoch = load(root / "epoch.json")
    if checked(["uname", "-m"]) not in {"aarch64", "arm64"}:
        raise ValueError("arm_host_required")
    info = json.loads(checked(["docker", "info", "--format", "{{json .}}"]))
    if info["NCPU"] != 4 or info["MemTotal"] < 14 * 1024**3:
        raise ValueError("standard_arm_resource_mismatch")
    if checked(["docker", "ps", "-aq"]):
        raise ValueError("runner_must_start_without_containers")
    runtime_files = epoch["runtime_files"]
    if "runsc" not in runtime_files or not runtime_files:
        raise ValueError("runtime_manifest_required")
    for name, expected in runtime_files.items():
        relative = Path(name)
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or not (name == "runsc" or name.startswith("gvisor-bin/"))
        ):
            raise ValueError("runtime_file_not_allowed")
        source = root / "runtime" / relative
        if not source.is_file() or sha(source) != expected:
            raise ValueError("runtime_source_sha_mismatch")
        checked(
            [
                "sudo",
                "install",
                "-D",
                "-m",
                "0755",
                str(source),
                str(Path("/usr/local/bin") / relative),
            ]
        )
    # 일회용 remote daemon만 바꾼다. 기존 앱/로컬 Docker endpoint를 받지 않는다.
    config = args.directory / "daemon.json"
    current = Path("/etc/docker/daemon.json")
    value = load(current) if current.exists() else {}
    value.setdefault("runtimes", {})["runsc"] = {"path": "/usr/local/bin/runsc"}
    write(config, value)
    checked(["sudo", "install", "-m", "0644", str(config), str(current)])
    checked(["sudo", "systemctl", "reload", "docker"])
    if sha(root / "images.tar") != epoch["images_tar_sha256"]:
        raise ValueError("image_archive_sha_mismatch")
    checked(["docker", "image", "load", "--input", str(root / "images.tar")])
    if len(epoch["image_ids"]) != 3:
        raise ValueError("exact_three_images_required")
    for tag, expected in epoch["image_ids"].items():
        actual = json.loads(checked(["docker", "image", "inspect", tag]))[0]
        if actual["Id"] != expected or actual["Architecture"] != "arm64":
            raise ValueError("native_image_identity_mismatch")
    write(
        args.directory / "owned-runtime.json",
        {
            "baseline_containers_empty": True,
            "image_ids": epoch["image_ids"],
            "runtime_files": runtime_files,
        },
    )


def claim(args):
    host = f"remote-{args.shard + 1:02}"
    pending_sha = sha(args.directory / "bundle/inputs/pending.json")
    body = json.dumps(
        {
            "host": host,
            "pending_sha256": pending_sha,
            "run_id": args.run_id,
            "mode": "execute",
            "schema_version": 1,
            "worker_sha256": sha(args.directory / "bundle/runner/worker.py"),
            "epoch_sha256": sha(args.directory / "bundle/epoch.json"),
            "python_version": sys.version.split()[0],
        }
    ).encode()
    token = os.environ["GH_TOKEN"]
    name = f"epoch7-{host}.claim.json"
    request = urllib.request.Request(
        f"https://uploads.github.com/repos/{REPOSITORY}/releases/{args.release_id}/assets?name={name}",
        data=body,
        method="POST",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.github+json",
        },
    )
    # 같은 asset의 422·통신 불명도 재시도하지 않는다. 성공 receipt 없이는 계산하지 않는다.
    with urllib.request.urlopen(request, timeout=30) as response:
        value = json.load(response)
    write(
        args.directory / "claim.json",
        {
            "asset_id": value["id"],
            "name": name,
            "pending_sha256": pending_sha,
            "host": host,
        },
    )


def run(args):
    if args.mode == "execute" and not (args.directory / "claim.json").is_file():
        raise ValueError("immutable_claim_required")
    root = args.directory / "bundle"
    result = args.directory / "result"
    # 워커에 GitHub 인증·bundle 복호화 키·사용자 환경을 전달하지 않는다.
    from cryptography.fernet import Fernet

    empty = args.directory / "empty"
    empty.mkdir(mode=0o700)
    docker_config = args.directory / "empty-docker-config"
    docker_config.mkdir(mode=0o700)
    environment = {
        "PATH": os.environ["PATH"],
        "PYTHONPATH": f"{root / 'source'}:{root / 'source/apps/api'}",
        "PYTHONDONTWRITEBYTECODE": "1",
        "DOCKER_HOST": "unix:///var/run/docker.sock",
        "DOCKER_CONFIG": str(docker_config),
        "TZ": "UTC",
        "LANG": "C.UTF-8",
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "TRADING_ENCRYPTION_KEYS": Fernet.generate_key().decode(),
    }
    command = [
        str(args.directory / "venv/bin/python"),
        str(root / "runner/worker.py"),
        "--bundle-root",
        str(root),
        "--host",
        f"remote-{args.shard + 1:02}",
        "--output",
        str(result),
    ]
    if args.mode == "execute":
        command.append("--execute")
    with (args.directory / "private-worker.log").open("xb") as log:
        code = subprocess.run(
            command, env=environment, cwd=empty, stdout=log, stderr=log
        ).returncode
    write(
        args.directory / "worker-exit.json",
        {"returncode": code, "actual_wait_observed": True},
    )
    if code:
        raise RuntimeError("remote_worker_failed")


def cleanup(args):
    if not (args.directory / "owned-runtime.json").exists():
        return
    rows = checked(["docker", "ps", "-a", "--format", "{{.ID}} {{.Names}}"])
    ids = []
    for row in rows.splitlines():
        identity, name = row.split()
        if not re.fullmatch(r"qb-python-[a-f0-9]{32}", name):
            raise ValueError("unknown_container_cleanup_refused")
        ids.append(identity)
    if ids:
        checked(["docker", "rm", "--force", *ids])
    if checked(["docker", "ps", "-aq"]):
        raise ValueError("remote_guest_cleanup_incomplete")
    write(
        args.directory / "cleanup.json",
        {"remaining_guests": 0, "removed_owned_containers": len(ids)},
    )


def pack(args):
    archive = args.directory / "result.tar"
    with tarfile.open(archive, "w") as out:
        for name in (
            "result",
            "worker-exit.json",
            "cleanup.json",
            "claim.json",
            "prepared.json",
            "private-worker.log",
            "private-dependencies.log",
            "bootstrap-failure.json",
            "owned-runtime.json",
        ):
            item = args.directory / name
            if item.exists():
                out.add(item, arcname=name, recursive=True)
    crypto(
        args,
        "encrypt",
        archive,
        args.directory / "result.enc",
        f"result-v7-{args.shard}",
    )
    if (args.directory / "result.enc").stat().st_size > MAX_ASSET_BYTES:
        raise ValueError("result_asset_too_large")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=[
            "prepare",
            "dependencies",
            "runtime",
            "claim",
            "run",
            "cleanup",
            "pack",
        ],
    )
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--mode", choices=["preflight", "execute"], default="preflight")
    parser.add_argument("--shard", type=int, choices=range(8), default=0)
    parser.add_argument("--url")
    parser.add_argument("--sha256")
    parser.add_argument("--overlay-url")
    parser.add_argument("--overlay-sha256")
    parser.add_argument("--crypto", type=Path)
    parser.add_argument("--crypto-sha256")
    parser.add_argument("--release-id", type=int)
    parser.add_argument("--run-id")
    args = parser.parse_args()
    args.directory = args.directory.resolve()
    try:
        globals()[args.action](args)
    except BaseException as error:
        if args.directory.is_dir():
            write(args.directory / "bootstrap-failure.json", {
                "schema_version": 1, "action": args.action,
                "error_type": type(error).__name__,
                "error_code": str(error) if type(error) in (ValueError, RuntimeError) else None,
                "last_observation": LAST_OBSERVATION,
                "private_encrypted_diagnostic_only": True,
            })
        # 원문·SDK 응답·예외 메시지를 공개 로그에 출력하지 않는다.
        print(f"remote bootstrap failed: {type(error).__name__}", file=sys.stderr)
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()

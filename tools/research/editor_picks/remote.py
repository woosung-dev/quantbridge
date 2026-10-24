"""일회용 ARM 연구 runner의 암호문 입력·실행·수거. 운영 호스트는 받지 않는다."""

from __future__ import annotations

import argparse
import base64
import json
import os
import platform
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

from tools.research.editor_picks.common import ROOT, checked_file, now, read, sha, write
from tools.research.editor_picks.crypto import transform

CONTEXT = "editor-picks-20261024"


def safe_extract(archive: Path, destination: Path) -> None:
    destination = destination.resolve()
    with tarfile.open(archive, "r:*") as bundle:
        members = bundle.getmembers()
        if sum(member.size for member in members) > 8 * 1024**3:
            raise ValueError("연구 번들 크기 제한 초과")
        seen = set()
        for member in members:
            path = Path(member.name)
            if (
                not member.isfile()
                or path.is_absolute()
                or ".." in path.parts
                or not (destination / path).resolve().is_relative_to(destination)
                or member.name in seen
            ):
                raise ValueError("링크·중복·일반 파일 밖의 연구 번들은 거부합니다")
            seen.add(member.name)
        for member in members:
            path = destination / member.name
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("xb") as target, bundle.extractfile(member) as source:
                shutil.copyfileobj(source, target)
            path.chmod(0o600)


def pack(root: Path, archive: Path) -> None:
    allowed = {
        "data",
        "runtime",
        "sources",
        "adapted",
        "generation",
        "native",
        "reviews",
    }
    with tarfile.open(archive, "w:gz", compresslevel=1) as output:
        for path in sorted(root.rglob("*")):
            relative = path.relative_to(root)
            if not path.is_file() or path.is_symlink():
                continue
            if relative.parts[0] not in allowed and path.name not in {
                "pilot-cohort.json",
                "cohort.json",
                "pilot-plan.json",
                "full-plan.json",
            }:
                continue
            if relative.parts[:2] == ("data", "pages") or path.name in {
                ".lock",
                "request.json.tmp",
            }:
                continue
            output.add(path, arcname=str(relative), recursive=False)


def install_runtime(root: Path) -> dict:
    # 로컬/운영 Docker를 변경하지 않는다. GitHub 일회용 runner의 고정 작업 경로만 허용한다.
    if (
        platform.system() != "Linux"
        or platform.machine() not in {"aarch64", "arm64"}
        or not str(ROOT).startswith("/home/runner/work/")
    ):
        raise ValueError("일회용 GitHub ARM runner에서만 runtime을 설치합니다")
    manifest = read(root / "runtime/manifest.json")
    for name, digest in manifest["files"].items():
        source = checked_file(root / "runtime", name, digest)
        if name != "runsc" and not name.startswith("gvisor-bin/"):
            raise ValueError("허용하지 않은 runtime 파일")
        subprocess.run(
            [
                "sudo",
                "install",
                "-D",
                "-m",
                "0755",
                str(source),
                f"/usr/local/bin/{name}",
            ],
            check=True,
        )
    daemon = root / "daemon.json"
    write(
        daemon,
        {
            "runtimes": {"runsc": {"path": "/usr/local/bin/runsc"}},
            "features": {"containerd-snapshotter": True},
        },
    )
    subprocess.run(
        ["sudo", "install", "-m", "0644", str(daemon), "/etc/docker/daemon.json"],
        check=True,
    )
    subprocess.run(["sudo", "systemctl", "restart", "docker"], check=True)
    archive = checked_file(
        root / "runtime", "images.tar", manifest["images_tar_sha256"]
    )
    subprocess.run(
        ["docker", "image", "load", "--input", str(archive)],
        check=True,
        capture_output=True,
    )
    images = {}
    for tag, expected in manifest["image_ids"].items():
        image = subprocess.run(
            ["docker", "image", "inspect", tag],
            capture_output=True,
            check=True,
            text=True,
        )
        value = json.loads(image.stdout)[0]
        if value["Id"] != expected or value["Architecture"] != "arm64":
            raise ValueError("원본 이미지 ID/아키텍처 불일치")
        images[tag] = expected
    proof = {
        "observed_at": now(),
        "images": images,
        "runtime": manifest["files"],
        "source_proof": read(root / "runtime/source-proof.json"),
    }
    write(root / "runtime-installed.json", proof)
    return proof


def worker(root: Path, plan: Path, shard: int, shards: int) -> int:
    env = {
        key: value
        for key, value in os.environ.items()
        if key in {"PATH", "HOME", "LANG"}
    }
    env["TRADING_ENCRYPTION_KEYS"] = base64.urlsafe_b64encode(os.urandom(32)).decode()
    env["PINE_AST_CACHE_DIR"] = ""
    command = [
        sys.executable,
        "-m",
        "tools.research.editor_picks",
        "--run-dir",
        str(root),
        "execute",
        "--plan",
        str(plan),
        "--shard",
        str(shard),
        "--shards",
        str(shards),
    ]
    with (root / f"worker-{shard}.log").open("w") as output:
        result = subprocess.run(
            command, env=env, cwd=ROOT, stdout=output, stderr=subprocess.STDOUT
        )
    write(
        root / f"terminal-{shard}.json",
        {
            "actual_returncode": result.returncode,
            "shard": shard,
            "shards": shards,
            "observed_at": now(),
        },
    )
    return result.returncode


def pack_result(root: Path, archive: Path, shard: int) -> None:
    with tarfile.open(archive, "w:gz", compresslevel=1) as output:
        for path in sorted((root / "results").rglob("*")):
            if path.is_file() and path.name != ".lock":
                output.add(path, arcname=str(path.relative_to(root)), recursive=False)
        for name in [
            f"terminal-{shard}.json",
            f"worker-{shard}.log",
            "runtime-installed.json",
        ]:
            path = root / name
            if path.exists():
                output.add(path, arcname=f"remote/{shard}/{name}", recursive=False)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=("pack", "prepare", "runtime", "worker", "finish", "collect")
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--archive", type=Path)
    parser.add_argument("--cipher", type=Path)
    parser.add_argument("--sha256")
    parser.add_argument("--key-file", type=Path)
    parser.add_argument("--key-env")
    parser.add_argument("--plan", default="pilot-plan.json")
    parser.add_argument("--shard", type=int, default=0)
    parser.add_argument("--shards", type=int, default=8)
    args = parser.parse_args()
    root = args.run_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    if args.action == "runtime":
        install_runtime(root)
    elif args.action == "worker":
        return worker(root, root / args.plan, args.shard, args.shards)
    else:
        key = (
            args.key_file.read_bytes()
            if args.key_file
            else base64.b64decode(
                os.environ[args.key_env], altchars=b"-_", validate=True
            )
        )
        if args.action == "pack":
            pack(root, args.archive)
            transform("encrypt", args.archive, args.cipher, key, CONTEXT)
            write(
                args.cipher.with_suffix(".proof.json"),
                {
                    "context": CONTEXT,
                    "sha256": sha(args.cipher.read_bytes()),
                    "bytes": args.cipher.stat().st_size,
                },
            )
        elif args.action == "prepare":
            if sha(args.cipher.read_bytes()) != args.sha256:
                raise ValueError("암호문 SHA256 불일치")
            transform("decrypt", args.cipher, args.archive, key, CONTEXT)
            safe_extract(args.archive, root)
        elif args.action == "finish":
            pack_result(root, args.archive, args.shard)
            transform(
                "encrypt",
                args.archive,
                args.cipher,
                key,
                f"{CONTEXT}/result/{args.shard}",
            )
        elif args.action == "collect":
            transform(
                "decrypt",
                args.cipher,
                args.archive,
                key,
                f"{CONTEXT}/result/{args.shard}",
            )
            # 기존 완료 파일은 덮지 않는다. 각 shard는 별도 수신 디렉터리에 수거한다.
            safe_extract(args.archive, root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

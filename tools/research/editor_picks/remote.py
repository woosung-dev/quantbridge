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
import tempfile
from pathlib import Path

from tools.research.editor_picks.common import (
    ROOT,
    checked_file,
    identity,
    now,
    read,
    sha,
    write,
)
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
                or str(path) in seen
                or (destination / path).exists()
                or (destination / path).is_symlink()
            ):
                raise ValueError("링크·중복·일반 파일 밖의 연구 번들은 거부합니다")
            seen.add(str(path))
        if any(str(parent) in seen for name in seen for parent in Path(name).parents):
            raise ValueError("일반 파일을 상위 디렉터리로 사용하는 번들은 거부합니다")
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
    required = {"runsc"} | {
        f"gvisor-bin/{name}"
        for name in (
            "checkpointgofer",
            "gvisor-sentry-prewarmer",
            "gvisor_sentry",
            "runsc-fd-parking",
            "runsc-metric-server",
        )
    }
    if set(manifest["files"]) != required:
        raise ValueError("고정 runtime 파일 목록 불일치")
    sources = {
        name: checked_file(root / "runtime", name, digest)
        for name, digest in manifest["files"].items()
    }
    archive = checked_file(
        root / "runtime", "images.tar", manifest["images_tar_sha256"]
    )
    for name, source in sources.items():
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
    if not 0 <= shard < shards:
        raise ValueError("잘못된 shard 배정")
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
            "plan_sha256": identity(read(plan)),
        },
    )
    return result.returncode


def pack_result(root: Path, archive: Path, shard: int, provenance: dict) -> None:
    paths = {}
    for path in sorted((root / "results").rglob("*")):
        if path.is_file() and not path.is_symlink() and path.name != ".lock":
            paths[str(path.relative_to(root))] = path
    phase = read(root / provenance["plan"])["phase"]
    for name in [
        f"terminal-{shard}.json",
        f"worker-{shard}.log",
        f"worker-{phase}-{shard}.json",
        f"runtime-blocked-{shard}.json",
        "runtime-installed.json",
    ]:
        path = root / name
        if path.is_file() and not path.is_symlink():
            paths[f"remote/{shard}/{name}"] = path
    envelope = {
        **provenance,
        "files": {name: sha(path.read_bytes()) for name, path in paths.items()},
    }
    envelope_path = root / f"envelope-{shard}.json"
    write(envelope_path, envelope)
    with tarfile.open(archive, "w:gz", compresslevel=1) as output:
        for name, path in paths.items():
            output.add(path, arcname=name, recursive=False)
        output.add(envelope_path, arcname=f"remote/{shard}/envelope.json")


def collect_result(archive: Path, root: Path, expected: dict) -> None:
    # 전체 인증·경로·해시·충돌을 먼저 확인한 다음 불변 파일만 병합한다.
    with tempfile.TemporaryDirectory() as directory:
        incoming = Path(directory)
        safe_extract(archive, incoming)
        envelope_name = f"remote/{expected['shard']}/envelope.json"
        envelope = read(incoming / envelope_name)
        if {key: envelope.get(key) for key in expected} != expected:
            raise ValueError("결과 provenance 불일치")
        files = envelope["files"]
        actual = {
            str(path.relative_to(incoming))
            for path in incoming.rglob("*")
            if path.is_file()
        }
        if actual != set(files) | {envelope_name}:
            raise ValueError("결과 파일 목록 불일치")
        paths = {}
        for name, digest in {
            **files,
            envelope_name: sha((incoming / envelope_name).read_bytes()),
        }.items():
            path = checked_file(incoming, name, digest)
            if not (
                name.startswith("results/")
                or name.startswith(f"remote/{expected['shard']}/")
            ):
                raise ValueError("결과 경로 밖의 파일")
            target = root / name
            if (
                not target.resolve().is_relative_to(root.resolve())
                or target.is_symlink()
            ):
                raise ValueError("결과 목적지 경로 불일치")
            if target.exists() and sha(target.read_bytes()) != digest:
                raise ValueError("기존 연구 결과 충돌")
            paths[target] = path
        for target, path in paths.items():
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as output:
                    output.write(path.read_bytes())
                target.chmod(0o600)


def finalize(root: Path, plan: Path, expected: dict) -> dict:
    from tools.research.editor_picks.report import build

    frozen = read(plan)
    failures = []
    for shard in range(expected["shards"]):
        folder = root / "remote" / str(shard)
        try:
            envelope = read(folder / "envelope.json")
            provenance = {**expected, "shard": shard}
            if any(envelope.get(key) != value for key, value in provenance.items()):
                raise ValueError("provenance 불일치")
            for name, digest in envelope["files"].items():
                checked_file(root, name, digest)
            terminal = read(folder / f"terminal-{shard}.json")
            allocation = read(folder / f"worker-{frozen['phase']}-{shard}.json")
            if (
                terminal["actual_returncode"] != 0
                or terminal["plan_sha256"] != expected["plan_sha256"]
            ):
                raise ValueError("실제 실행 종료 실패")
            if (
                allocation["status"] != "finished"
                or allocation["plan_sha256"] != expected["plan_sha256"]
                or allocation["shard"] != shard
                or allocation["shards"] != expected["shards"]
                or allocation["jobs_consumed"]
                != len(frozen["jobs"][shard :: expected["shards"]])
            ):
                raise ValueError("셀 배정 소비 증거 불일치")
        except (OSError, ValueError, KeyError) as error:
            failures.append({"shard": shard, "error": str(error)})
    report = build(root, plan)
    result = {
        "provenance": expected,
        "failures": failures,
        "complete": not failures and report["complete"],
    }
    write(root / "remote/finalization.json", result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=(
            "pack",
            "prepare",
            "runtime",
            "worker",
            "finish",
            "collect",
            "finalize",
        ),
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
    parser.add_argument("--head")
    parser.add_argument("--run-id")
    parser.add_argument("--attempt")
    parser.add_argument("--input-sha")
    args = parser.parse_args()
    root = args.run_dir.resolve()
    root.mkdir(parents=True, exist_ok=True)
    provenance = None
    if args.action in {"finish", "collect", "finalize"}:
        if (
            not all((args.head, args.run_id, args.attempt, args.input_sha))
            or not 0 <= args.shard < args.shards
        ):
            raise ValueError("명시적인 원격 실행 provenance가 필요합니다")
        provenance = {
            "head": args.head,
            "run_id": args.run_id,
            "attempt": args.attempt,
            "input_sha256": args.input_sha,
            "plan": args.plan,
            "plan_sha256": identity(read(root / args.plan)),
            "shards": args.shards,
        }
    if args.action == "finalize":
        return 0 if finalize(root, root / args.plan, provenance)["complete"] else 1
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
            pack_result(
                root, args.archive, args.shard, {**provenance, "shard": args.shard}
            )
            transform(
                "encrypt",
                args.archive,
                args.cipher,
                key,
                f"{CONTEXT}/result/{identity({**provenance, 'shard': args.shard})}",
            )
        elif args.action == "collect":
            transform(
                "decrypt",
                args.cipher,
                args.archive,
                key,
                f"{CONTEXT}/result/{identity({**provenance, 'shard': args.shard})}",
            )
            collect_result(args.archive, root, {**provenance, "shard": args.shard})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

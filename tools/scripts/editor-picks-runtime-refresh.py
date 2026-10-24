"""일회용 ARM에서 고정 Pine 부모에 바뀐 계산 파일을 덧입히고 검증한다.

기존 암호 입력 prepare와 remote runtime 설치 후 호출한다. create/export만 사용해
컨테이너·생성 전략을 실행하지 않으며 새 runtime 전용 번들만 암호화한다.
"""

from __future__ import annotations

import argparse
import ast
import base64
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.research.editor_picks.common import checked_file, now, read, sha, write  # noqa: E402
from tools.research.editor_picks.crypto import transform  # noqa: E402
from tools.research.editor_picks.remote import CONTEXT  # noqa: E402

PINE_TAG = "quantbridge-pine-runner:local"
STDLIB = "apps/api/src/strategy/pine_v2/stdlib.py"
PINE_DIRECTORY = "apps/api/src/strategy/pine_v2"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def computation_hash(source: bytes) -> str:
    nodes = [
        node
        for node in ast.parse(source).body
        if isinstance(node, ast.ClassDef) and node.name == "_PineInterpreterTransport"
    ]
    if len(nodes) != 1:
        raise ValueError("Pine 계산 class 하나를 확인할 수 없습니다")
    return sha(ast.dump(nodes[0]).encode())


def archive_files(archive: Path, paths: list[str], sdk: bool = False) -> dict[str, bytes]:
    with tarfile.open(archive) as bundle:
        members = {
            member.name.lstrip("./"): member for member in bundle.getmembers() if member.isfile()
        }
        if sdk:
            matches = [
                name for name in members if name.endswith("/site-packages/quantbridge_sdk.py")
            ]
            if len(matches) != 1:
                raise ValueError("실제 Python image의 SDK 파일이 고유하지 않습니다")
            paths = [*paths, matches[0]]
        result = {}
        for name in paths:
            with bundle.extractfile(members[name]) as stream:
                result["sdk" if sdk and name in matches else name] = stream.read()
        return result


def require_arm() -> None:
    if (
        platform.system() != "Linux"
        or platform.machine() not in {"arm64", "aarch64"}
        or not str(ROOT).startswith("/home/runner/work/")
    ):
        raise ValueError("일회용 GitHub ARM runner에서만 runtime을 갱신합니다")


def refresh(args) -> dict:
    require_arm()
    head = subprocess.run(
        ["/usr/bin/git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    ).stdout.strip()
    if not re.fullmatch(r"[a-f0-9]{40}", args.head) or head != args.head:
        raise ValueError("요청한 checkout head와 다릅니다")
    root, output = args.run_dir.resolve(), args.output_dir.resolve()
    if output == root or output.is_relative_to(root) or (output.exists() and any(output.iterdir())):
        raise ValueError("원본 입력과 분리된 빈 output 디렉터리가 필요합니다")
    runtime = output / "runtime"
    if args.archive.resolve().is_relative_to(runtime) or args.cipher.resolve().is_relative_to(
        runtime
    ):
        raise ValueError("번들·암호문은 runtime 밖의 새 파일에 저장합니다")
    old = read(root / "runtime/manifest.json")
    old_proof = read(root / "runtime/source-proof.json")
    checked_file(root / "runtime", "images.tar", old["images_tar_sha256"])
    pine_paths = sorted((ROOT / "apps/api/src/strategy/pine_v2").rglob("*.py"))
    expected = {str(path.relative_to(ROOT)): digest(path) for path in pine_paths}
    if len(expected) != 25 or set(expected) != set(old_proof["pine_files"]):
        raise ValueError("고정 Pine 계산 파일 25개의 범위가 다릅니다")
    changed = {
        name: {"parent_sha256": old_proof["pine_files"][name], "sha256": value}
        for name, value in expected.items()
        if value != old_proof["pine_files"][name]
    }
    if not changed:
        raise ValueError("부모와 달라진 Pine 계산 소스가 없습니다")
    commands = []
    env = {key: value for key, value in os.environ.items() if key in {"PATH", "HOME", "LANG"}}

    def docker(*arguments):
        command = ["/usr/bin/docker", *map(str, arguments)]
        commands.append(command)
        return subprocess.run(command, env=env, check=True, capture_output=True, text=True)  # noqa: S603 — 고정 Docker 동작·검증된 파일 경로만 전달

    def inspect(tag):
        return json.loads(docker("image", "inspect", tag).stdout)[0]

    for tag, image_id in old["image_ids"].items():
        image = inspect(tag)
        if image["Id"] != image_id or image["Architecture"] != "arm64":
            raise ValueError("기존 remote runtime 설치의 image ID·ARM 아키텍처가 다릅니다")
    parent = inspect(PINE_TAG)
    parent_tag = "quantbridge-pine-runner:runtime-parent-" + parent["Id"].removeprefix("sha256:")
    docker("image", "tag", parent["Id"], parent_tag)
    with tempfile.TemporaryDirectory(prefix="editor-runtime-refresh-") as temporary:
        context = Path(temporary)
        overlay = context / "pine_overlay"
        for name in changed:
            destination = overlay / Path(name).relative_to(PINE_DIRECTORY)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, destination)
        recipe = f"FROM {parent_tag}\nCOPY pine_overlay/ /runner/src/strategy/pine_v2/\n"
        (context / "Dockerfile").write_text(recipe)
        docker("build", "--pull=false", "--network=none", "--no-cache", "--tag", PINE_TAG, context)
        child = inspect(PINE_TAG)
        parent_layers, child_layers = parent["RootFS"]["Layers"], child["RootFS"]["Layers"]
        if (
            child["Id"] == parent["Id"]
            or child["Architecture"] != "arm64"
            or child_layers[:-1] != parent_layers
        ):
            raise ValueError("고정 부모 위의 단일 COPY layer를 확인할 수 없습니다")
        if any(
            child["Config"].get(key) != parent["Config"].get(key)
            for key in (
                "User",
                "Entrypoint",
                "Cmd",
                "WorkingDir",
                "Env",
                "Volumes",
                "ExposedPorts",
                "Healthcheck",
                "StopSignal",
                "Shell",
            )
        ):
            raise ValueError("Pine 계산 파일 외에 image 실행 설정이 바뀌었습니다")

        def exported(tag, paths, sdk=False):
            container = docker("create", "--entrypoint", "/bin/false", tag).stdout.strip()
            if not re.fullmatch(r"[a-f0-9]{64}", container):
                raise ValueError("새 검증 container ID가 올바르지 않습니다")
            try:
                archive = context / "filesystem.tar"
                docker("export", "--output", archive, container)
                return archive_files(archive, paths, sdk)
            finally:
                docker("rm", container)

        worker = "apps/api/src/strategy/code_runtime/pine_worker.py"
        pine_class = "apps/api/src/strategy/code_runtime/pine.py"
        locations = {
            name: "runner/" + name.removeprefix("apps/api/")
            for name in (*expected, worker, pine_class)
        }
        actual = exported(PINE_TAG, list(locations.values()))
        for name in (*expected, worker):
            if sha(actual[locations[name]]) != digest(ROOT / name):
                raise ValueError(f"실제 Pine image의 계산 파일 SHA가 다릅니다: {name}")
        computation = computation_hash(actual[locations[pine_class]])
        if computation != computation_hash((ROOT / pine_class).read_bytes()):
            raise ValueError("실제 Pine image의 계산 class가 다릅니다")
        python = exported("quantbridge-python-runner:local", ["runner/main.py"], sdk=True)
        loader = "infra/python-runner/main.py"
        if sha(python["runner/main.py"]) != digest(ROOT / loader) or sha(python["sdk"]) != digest(
            ROOT / "apps/api/src/strategy/python_runtime/sdk.py"
        ):
            raise ValueError("실제 Python image의 loader·SDK가 다릅니다")
    runtime.mkdir(parents=True)
    for name, expected_hash in old["files"].items():
        source = checked_file(root / "runtime", name, expected_hash)
        destination = runtime / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    images = {**old["image_ids"], PINE_TAG: child["Id"]}
    docker("image", "save", "--output", runtime / "images.tar", *images)
    archive_hash = digest(runtime / "images.tar")
    write(
        runtime / "manifest.json", {**old, "image_ids": images, "images_tar_sha256": archive_hash}
    )
    proof = {
        "observed_at": now(),
        "checkout_head": head,
        "pine_files": expected,
        "image_archive_sha256": archive_hash,
        worker: digest(ROOT / worker),
        loader: digest(ROOT / loader),
        "sdk_sha256": sha(python["sdk"]),
        "pine_computation_class_ast_sha256": computation,
        "status": "computation_source_matches_current_checkout",
        "scope": old_proof["scope"],
        "parent_pine_image_id": parent["Id"],
        "pine_image_id": child["Id"],
        "parent_archive_sha256": old["images_tar_sha256"],
        "parent_source_proof_sha256": digest(root / "runtime/source-proof.json"),
        "overlay": {"files": changed},
        "dockerfile": recipe,
        "docker_commands": commands,
        "generated_strategy_executed": False,
    }
    write(runtime / "source-proof.json", proof)
    with tarfile.open(args.archive, "x:gz", compresslevel=1) as bundle:
        for path in sorted(runtime.rglob("*")):
            if path.is_file():
                bundle.add(path, arcname=str(path.relative_to(output)), recursive=False)
    key = base64.b64decode(os.environ[args.key_env], altchars=b"-_", validate=True)
    transform("encrypt", args.archive, args.cipher, key, CONTEXT)
    result = {
        "context": CONTEXT,
        "sha256": digest(args.cipher),
        "bytes": args.cipher.stat().st_size,
        "checkout_head": head,
        "parent_pine_image_id": parent["Id"],
        "pine_image_id": child["Id"],
    }
    write(args.cipher.with_suffix(".proof.json"), result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("run-dir", "output-dir", "archive", "cipher"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--key-env", required=True)
    args = parser.parse_args()
    result = refresh(args)
    print(json.dumps(result))


if __name__ == "__main__":
    main()

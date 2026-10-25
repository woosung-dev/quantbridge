"""COPY-only ARM 준비의 부모·실제 소스 검증과 암호문 출력 계약을 확인한다."""

import argparse
import base64
import importlib.util
import io
import json
import sys
import tarfile
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT))

from tools.research.editor_picks.common import read, sha, write  # noqa: E402
from tools.research.editor_picks.crypto import transform  # noqa: E402

spec = importlib.util.spec_from_file_location(
    "runtime_refresh", ROOT / "tools/scripts/editor-picks-runtime-refresh.py"
)
refresh = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh)


def test_local_runtime_refresh_is_refused_before_any_docker_call(tmp_path, monkeypatch):
    monkeypatch.setattr(refresh, "ROOT", tmp_path)
    monkeypatch.setattr(
        refresh.subprocess, "run", lambda *_args, **_kwargs: pytest.fail("로컬 실행 금지")
    )
    with pytest.raises(ValueError, match="일회용 GitHub ARM"):
        refresh.refresh(argparse.Namespace())


def test_refresh_pins_parent_verifies_exported_files_and_emits_only_encrypted_bundle(
    tmp_path, monkeypatch
):
    checkout, source = tmp_path / "checkout", tmp_path / "input"
    paths = [refresh.STDLIB, *[f"apps/api/src/strategy/pine_v2/file_{i}.py" for i in range(24)]]
    for relative in paths:
        path = checkout / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("value = 1\n")
    parent_hashes = {name: sha((checkout / name).read_bytes()) for name in paths}
    (checkout / refresh.STDLIB).write_text("value = 2\n")
    (checkout / paths[1]).write_text("other_value = 3\n")
    files = {
        "apps/api/src/strategy/code_runtime/pine_worker.py": "worker = 1\n",
        "apps/api/src/strategy/code_runtime/pine.py": "class _PineInterpreterTransport:\n    pass\n",
        "infra/python-runner/main.py": "loader = 1\n",
        "apps/api/src/strategy/python_runtime/sdk.py": "sdk = 1\n",
    }
    for name, body in files.items():
        path = checkout / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    write(
        source / "runtime/source-proof.json",
        {"pine_files": parent_hashes, "scope": "calculation files only"},
    )
    binary = source / "runtime/runsc"
    binary.write_bytes(b"runtime binary")
    old_archive = source / "runtime/images.tar"
    old_archive.write_bytes(b"old images")
    tags = [
        "quantbridge-python-runner:local",
        "quantbridge-typescript-runner:local",
        refresh.PINE_TAG,
    ]
    ids = {tag: "sha256:" + str(index + 1) * 64 for index, tag in enumerate(tags)}
    write(
        source / "runtime/manifest.json",
        {
            "schema_version": 1,
            "files": {"runsc": sha(binary.read_bytes())},
            "images_tar_sha256": sha(old_archive.read_bytes()),
            "image_ids": ids,
        },
    )
    commands, containers = [], {}
    built = False

    def run(command, **kwargs):
        nonlocal built
        if command[0] == "/usr/bin/git":
            return SimpleNamespace(stdout="a" * 40 + "\n")
        assert "TEST_RUNTIME_KEY" not in kwargs["env"]
        commands.append(command)
        args = command[1:]
        if args[:2] == ["image", "inspect"]:
            tag = args[2]
            value = {
                "Id": "sha256:" + "9" * 64 if built and tag == refresh.PINE_TAG else ids[tag],
                "Architecture": "arm64",
                "Config": {"User": "10001:10001"},
                "RootFS": {
                    "Layers": ["base", "overlay"] if built and tag == refresh.PINE_TAG else ["base"]
                },
            }
            return SimpleNamespace(stdout=json.dumps([value]))
        if args[0] == "build":
            context = Path(args[-1])
            assert sorted(path.name for path in context.iterdir()) == [
                "Dockerfile",
                "strategy_overlay",
            ]
            overlay = context / "strategy_overlay/pine_v2"
            assert sorted(path.name for path in overlay.iterdir()) == ["file_0.py", "stdlib.py"]
            assert (overlay / "file_0.py").read_bytes() == (checkout / paths[1]).read_bytes()
            assert (overlay / "stdlib.py").read_bytes() == (checkout / refresh.STDLIB).read_bytes()
            assert "RUN " not in (context / "Dockerfile").read_text()
            assert (
                ids[refresh.PINE_TAG].removeprefix("sha256:")
                in (context / "Dockerfile").read_text()
            )
            built = True
        elif args[0] == "create":
            container = str(len(containers) + 1) * 64
            containers[container] = args[-1]
            return SimpleNamespace(stdout=container + "\n")
        elif args[0] == "export":
            if containers[args[-1]] == refresh.PINE_TAG:
                contents = {
                    "runner/" + name.removeprefix("apps/api/"): (checkout / name).read_bytes()
                    for name in [
                        *paths,
                        *[
                            key
                            for key in files
                            if key.startswith("apps/api/src/strategy/code_runtime/")
                        ],
                    ]
                }
            else:
                contents = {
                    "runner/main.py": (checkout / "infra/python-runner/main.py").read_bytes(),
                    "usr/local/lib/python3.12/site-packages/quantbridge_sdk.py": (
                        checkout / "apps/api/src/strategy/python_runtime/sdk.py"
                    ).read_bytes(),
                }
            with tarfile.open(args[2], "w") as output:
                for name, body in contents.items():
                    member = tarfile.TarInfo(name)
                    member.size = len(body)
                    output.addfile(member, io.BytesIO(body))
        elif args[:2] == ["image", "save"]:
            Path(args[3]).write_bytes(b"new three-image archive")
        return SimpleNamespace(stdout="")

    monkeypatch.setattr(refresh, "ROOT", checkout)
    monkeypatch.setattr(refresh, "require_arm", lambda: None)
    monkeypatch.setattr(refresh.subprocess, "run", run)
    key = bytes(range(32))
    monkeypatch.setenv("TEST_RUNTIME_KEY", base64.b64encode(key).decode())
    args = argparse.Namespace(
        run_dir=source,
        output_dir=tmp_path / "output",
        archive=tmp_path / "runtime.tar.gz",
        cipher=tmp_path / "runtime.enc",
        head="a" * 40,
        key_env="TEST_RUNTIME_KEY",
    )
    result = refresh.refresh(args)
    assert result["parent_pine_image_id"] == ids[refresh.PINE_TAG]
    assert result["pine_image_id"] == "sha256:" + "9" * 64
    assert old_archive.read_bytes() == b"old images"
    proof = read(args.output_dir / "runtime/source-proof.json")
    assert len(proof["pine_files"]) == 25 and proof["generated_strategy_executed"] is False
    assert set(proof["overlay"]["files"]) == {refresh.STDLIB, paths[1], *refresh.CORE_FILES}
    for name in (refresh.STDLIB, paths[1]):
        hashes = proof["overlay"]["files"][name]
        assert hashes == {
            "parent_sha256": parent_hashes[name],
            "sha256": sha((checkout / name).read_bytes()),
        }
    assert proof["core_files"] == {
        name: sha((checkout / name).read_bytes()) for name in refresh.CORE_FILES
    }
    assert not any(command[1] in {"run", "start", "exec"} for command in commands)
    plaintext = tmp_path / "recovered.tar.gz"
    transform("decrypt", args.cipher, plaintext, key, refresh.CONTEXT)
    with tarfile.open(plaintext) as bundle:
        assert all(member.name.startswith("runtime/") for member in bundle.getmembers())
        assert "runtime/images.tar" in bundle.getnames()

"""일회용 public ARM runner의 파일 검증·원래 런타임 설치만 담당한다."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import shutil
import subprocess
import tarfile


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def call(argv):
    return subprocess.run(argv, check=True, capture_output=True, text=True).stdout.strip()


def safe_extract(archive, root):
    root = root.resolve()
    root.mkdir(mode=0o700, exist_ok=False)
    with tarfile.open(archive) as stream:
        members = stream.getmembers()
        targets = [(root / m.name).resolve() for m in members]
        assert len(targets) == len(set(targets)) and sum(m.size for m in members) <= 8 * 1024**3
        for member, target in zip(members, targets, strict=True):
            assert member.isfile() and target.is_relative_to(root) and not Path(member.name).is_absolute()
            assert not any(p.startswith(".env") for p in Path(member.name).parts)
        for member, target in zip(members, targets, strict=True):
            target.parent.mkdir(parents=True, exist_ok=True)
            with stream.extractfile(member) as source, target.open("xb") as dest:
                shutil.copyfileobj(source, dest)


def verify_files(root):
    root = root.resolve()
    manifest = json.loads((root / "pilot.json").read_bytes())
    actual = {str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()}
    assert actual == set(manifest["files"]) | {"pilot.json"}
    for relative, expected in manifest["files"].items():
        candidate = root / relative
        path = candidate.resolve()
        assert not candidate.is_symlink() and path.is_relative_to(root) and path.is_file() and sha(path) == expected
        assert not any(p.startswith(".env") for p in Path(relative).parts)
        assert not relative.startswith("input-run/cells/") and "result-" not in relative and "latest.json" not in relative
    return manifest


def main():
    if not __debug__:
        raise SystemExit("optimized_python_not_allowed")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", type=Path)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--directory", type=Path, required=True)
    args = parser.parse_args()
    assert platform.machine() in {"aarch64", "arm64"} and sha(args.archive) == args.sha256
    root = args.directory.resolve()
    safe_extract(args.archive, root)
    manifest = verify_files(root)
    info = json.loads(call(["docker", "info", "--format", "{{json .}}"] ))
    assert info["NCPU"] == 4 and info["MemTotal"] >= 14 * 1024**3
    assert not call(["docker", "ps", "-aq"])
    for relative, expected in manifest["runtime_files"].items():
        source = root / "runtime" / relative
        assert sha(source) == expected
        call(["sudo", "install", "-D", "-m", "0755", str(source), "/usr/local/bin/" + relative])
    cfg = Path("/etc/docker/daemon.json")
    value = json.loads(cfg.read_text()) if cfg.exists() else {}
    value.setdefault("runtimes", {})["runsc"] = {"path": "/usr/local/bin/runsc"}
    value.setdefault("features", {})["containerd-snapshotter"] = True
    config = root / "daemon.json"
    config.write_text(json.dumps(value))
    call(["sudo", "install", "-m", "0644", str(config), str(cfg)])
    call(["sudo", "systemctl", "restart", "docker"])
    call(["docker", "image", "load", "--input", str(root / "images.tar")])
    for language, expected in manifest["image_ids"].items():
        actual = json.loads(call(["docker", "image", "inspect", f"quantbridge-{language}-runner:local"]))[0]
        assert actual["Id"] == expected and actual["Architecture"] == "arm64"
    assert sha(Path("/usr/local/bin/runsc")) == manifest["runtime_files"]["runsc"]
    (root / "runtime-observation.json").write_text(json.dumps({"runsc_version": call(["/usr/local/bin/runsc", "--version"]), "runsc_sha256": sha(Path("/usr/local/bin/runsc")), "installed_images_exact": True}) + "\n")


if __name__ == "__main__":
    main()

"""검토한 파일 목록만 tar에 넣는다. 이미지 저장·모델·전략 실행·외부 전송은 없다."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main():
    if not __debug__:
        raise SystemExit("optimized_python_not_allowed")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--runtime", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_bytes())
    manifest = {k: v for k, v in plan.items() if k != "local_files"}
    entries = [(Path(x["source"]), x["member"], x["sha256"]) for x in plan["local_files"]]
    entries += [(args.images, "images.tar", sha(args.images))]
    entries += [(args.runtime / name, "runtime/" + name, expected) for name, expected in plan["runtime_files"].items()]
    manifest["files"] = {name: expected for _, name, expected in entries}
    assert len(entries) == len(manifest["files"]) and not args.output.exists()
    for source, name, expected in entries:
        assert source.is_file() and not source.is_symlink() and sha(source) == expected
        p = Path(name)
        assert not p.is_absolute() and ".." not in p.parts and not any(x.startswith(".env") for x in p.parts)
        assert not name.startswith("input-run/cells/") and "result-" not in name and "latest.json" not in name
    with tarfile.open(args.output, "x") as archive:
        for source, name, _ in entries:
            archive.add(source, arcname=name, recursive=False)
        data = (json.dumps(manifest, ensure_ascii=False, sort_keys=True) + "\n").encode()
        info = tarfile.TarInfo("pilot.json")
        info.size = len(data)
        info.mode = 0o600
        archive.addfile(info, io.BytesIO(data))
    print(json.dumps({"package_sha256": sha(args.output), "bytes": args.output.stat().st_size, "cases": 3, "baseline_result_bytes_included": False}))


if __name__ == "__main__":
    main()

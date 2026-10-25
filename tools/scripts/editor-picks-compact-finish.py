"""일회용 ARM의 원시 결과를 분할 보존한 뒤 작은 인증 증거를 업로드한다."""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
import platform
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "apps/api")]

from tools.research.editor_picks import compact  # noqa: E402
from tools.research.editor_picks.common import identity, read  # noqa: E402
from tools.research.editor_picks.crypto import transform  # noqa: E402
from tools.research.editor_picks.remote import CONTEXT, pack_result  # noqa: E402
from tools.research.editor_picks.verification import frozen_inputs  # noqa: E402

REPO = "woosung-dev/quantbridge"
TAG = "editor-picks-research-20261024"


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def require_runner(root: Path, head: str, run: str) -> Path:
    if (
        platform.system() != "Linux"
        or platform.machine() not in {"arm64", "aarch64"}
        or not str(ROOT).startswith("/home/runner/work/")
        or os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("GITHUB_REPOSITORY") != REPO
        or os.environ.get("GITHUB_RUN_ID") != run
        or not root.is_relative_to(ROOT / "runs")
    ):
        raise ValueError("owner 일회용 ARM 연구 runner만 허용합니다")
    actual = subprocess.check_output(
        ["/usr/bin/git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    if actual != head:
        raise ValueError("업로드 코드 checkout이 요청 head와 다릅니다")
    return Path(os.environ["RUNNER_TEMP"]).resolve()


def upload(cipher: Path, descriptor: Path) -> dict:
    subprocess.run(  # noqa: S603 — 동결 uploader와 검증한 runner 임시 파일만 인자로 전달한다.
        [
            sys.executable,
            str(ROOT / "tools/scripts/editor-picks-result-upload.py"),
            "--input",
            str(cipher),
            "--output",
            str(descriptor),
            "--repo",
            REPO,
            "--tag",
            TAG,
            "--asset-name",
            cipher.name,
        ],
        cwd=ROOT,
        check=True,
    )
    result = read(descriptor)
    if result["sha256"] != digest(cipher) or result["bytes"] != cipher.stat().st_size:
        raise ValueError("분할 보존 descriptor의 원본 암호문이 다릅니다")
    return result


def finish(args) -> dict:
    root = args.run_dir.resolve()
    if (
        not re.fullmatch(r"[a-f0-9]{40}", args.head)
        or not re.fullmatch(r"[0-9]+", args.run_id)
        or not re.fullmatch(r"[1-9][0-9]*", args.attempt)
        or not re.fullmatch(r"[a-f0-9]{64}", args.input_sha)
        or not 0 <= args.shard < args.shards <= 256
        or args.plan not in {"full-plan.json", "pilot-plan.json"}
    ):
        raise ValueError("명시한 연구 provenance 형식이 다릅니다")
    temporary = require_runner(root, args.head, args.run_id)
    archive, cipher = args.archive.resolve(), args.cipher.resolve()
    expected_name = f"result-{args.run_id}-{args.attempt}-{args.shard}.enc"
    if (
        cipher.name != expected_name
        or archive == cipher
        or any(not path.is_relative_to(temporary) or path.exists() for path in (archive, cipher))
    ):
        raise ValueError("새 runner 임시 출력만 허용합니다")
    frozen = read(root / args.plan)
    frozen_inputs(root, frozen)
    provenance = {
        "head": args.head,
        "run_id": args.run_id,
        "attempt": args.attempt,
        "input_sha256": args.input_sha,
        "plan": args.plan,
        "plan_sha256": identity(frozen),
        "shards": args.shards,
        "shard": args.shard,
    }
    key = base64.b64decode(os.environ[args.key_env], altchars=b"-_", validate=True)
    if len(key) != 32:
        raise ValueError("연구 인증 키 길이가 다릅니다")
    pack_result(root, archive, args.shard, provenance)
    with tempfile.TemporaryDirectory(prefix="editor-picks-compact-", dir=temporary) as folder:
        stage = Path(folder) / "stage"
        compact.prepare(archive, provenance, stage)
        transform("encrypt", archive, cipher, key, f"{CONTEXT}/result/{identity(provenance)}")
        # 직접 만든 임시 평문 tar만 제거한다. 원시 결과·전체 암호문은 유지한다.
        archive.unlink()
        descriptor = Path(folder) / "full-parts.json"
        full = upload(cipher, descriptor)
        compact_archive = Path(folder) / "compact.tar.gz"
        compact.seal(stage, full, compact_archive)
        compact_cipher = temporary / ("compact-" + expected_name)
        transform(
            "encrypt",
            compact_archive,
            compact_cipher,
            key,
            f"{CONTEXT}/compact-result/{identity(provenance)}",
        )
        if compact_cipher.stat().st_size > 1024**3:
            raise ValueError("작은 인증 증거 번들이 단일 part 한도를 넘었습니다")
        small = upload(compact_cipher, Path(folder) / "compact-parts.json")
    return {
        "provenance": provenance,
        "storage": "authenticated_remote_full_payloads",
        "full_cipher": full,
        "compact_cipher": small,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("run-dir", "archive", "cipher"):
        parser.add_argument(f"--{name}", required=True, type=Path)
    for name in ("head", "run-id", "attempt", "input-sha", "key-env"):
        parser.add_argument(f"--{name}", required=True)
    parser.add_argument("--plan", default="full-plan.json")
    parser.add_argument("--shard", type=int, required=True)
    parser.add_argument("--shards", type=int, required=True)
    args = parser.parse_args()
    result = finish(args)
    print(f"authenticated compact shard {result['provenance']['shard']} preserved")


if __name__ == "__main__":
    main()

"""인증된 이전 shard 결과 중 현재 shard 소유의 종결 기록만 재사용한다."""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "apps/api")]

from tools.research.editor_picks.common import identity, read, write  # noqa: E402
from tools.research.editor_picks.crypto import transform  # noqa: E402
from tools.research.editor_picks.execution import require_runtime  # noqa: E402
from tools.research.editor_picks.remote import CONTEXT, collect_result  # noqa: E402
from tools.research.editor_picks.verification import receipts  # noqa: E402


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def resume(args: argparse.Namespace) -> dict:
    root = args.run_dir.resolve()
    if (
        not 0 <= args.shard < args.shards
        or not 0 <= args.source_shard < args.source_shards
    ):
        raise ValueError("잘못된 shard 배정")
    plan_path = (root / args.plan).resolve()
    if not plan_path.is_relative_to(root):
        raise ValueError("계획 경로가 run 디렉터리 밖입니다")
    frozen = read(plan_path)
    expected = {
        "head": args.source_head,
        "run_id": args.source_run_id,
        "attempt": args.source_attempt,
        "input_sha256": args.source_input_sha,
        "plan": args.plan,
        "plan_sha256": identity(frozen),
        "shards": args.source_shards,
        "shard": args.source_shard,
    }
    key = base64.b64decode(os.environ[args.key_env], altchars=b"-_", validate=True)
    images = require_runtime()
    source_digest = digest(args.cipher)
    assigned = {identity(job): index for index, job in enumerate(frozen["jobs"])}
    if len(assigned) != len(frozen["jobs"]):
        raise ValueError("계획에 중복 셀이 있습니다")
    report_path = root / "results" / f"resume-cache-{args.shard}.json"
    header = {
        "schema_version": 1,
        "helper_sha256": digest(Path(__file__)),
        "plan_sha256": identity(frozen),
        "shard": args.shard,
        "shards": args.shards,
        "execution_images": images,
    }
    if not report_path.resolve().is_relative_to(root) or report_path.is_symlink():
        raise ValueError("resume 감사 목적지 경로가 다릅니다")
    report = {**header, "sources": {}}
    if report_path.exists():
        report = read(report_path)
        if any(report.get(name) != value for name, value in header.items()):
            raise ValueError("기존 resume 감사의 계획·구현·이미지가 다릅니다")
    skipped = 0
    with tempfile.TemporaryDirectory(prefix="editor-picks-resume-") as directory:
        temporary = Path(directory)
        archive, incoming = temporary / "result.tar.gz", temporary / "validated"
        transform(
            "decrypt",
            args.cipher,
            archive,
            key,
            f"{CONTEXT}/result/{identity(expected)}",
        )
        collect_result(archive, incoming, expected)
        # 중단 도중 request/receipt/원시 근거가 덜 저장된 폴더는 완료로 취급하지 않는다.
        for folder in (incoming / "results").glob("*"):
            if not folder.is_dir():
                continue
            request_path, receipt_path = (
                folder / "request.json",
                folder / "receipt.json",
            )
            incomplete = not request_path.is_file() or not receipt_path.is_file()
            if not incomplete:
                request, value = read(request_path), read(receipt_path)
                if request.get("plan") != identity(frozen):
                    raise ValueError("캐시의 계획 SHA가 다릅니다")
                required = {"request.json"}
                if value.get("status") == "completed":
                    required |= {"result.json.gz", "signals.json.gz"}
                incomplete = (
                    value.get("status") not in {"completed", "failed", "not_available"}
                    or not required <= value.get("files", {}).keys()
                    or any(
                        not (folder / name).is_file() for name in value.get("files", {})
                    )
                )
            if incomplete:
                shutil.rmtree(folder)
                skipped += 1
        completed = receipts(incoming, frozen)
        copies = {}
        selected = 0
        for job_key, row in completed.items():
            if assigned[job_key] % args.source_shards != args.source_shard:
                raise ValueError("이전 결과가 source shard 배정과 다릅니다")
            if row["execution_images"] != images:
                raise ValueError("캐시 실행 이미지가 현재 runtime과 다릅니다")
            if assigned[job_key] % args.shards != args.shard:
                continue
            folder = Path(row["evidence_folder"])
            request = read(folder / "request.json")
            if folder.name != identity(request):
                raise ValueError("캐시 결과 디렉터리가 요청 identity와 다릅니다")
            selected += 1
            for name in {"receipt.json", *row["files"]}:
                source = folder / name
                target = root / "results" / folder.name / name
                if not target.resolve().is_relative_to(root) or target.is_symlink():
                    raise ValueError("캐시 목적지 경로가 다릅니다")
                if target.exists() and (
                    not target.is_file() or digest(target) != digest(source)
                ):
                    raise ValueError("기존 캐시 파일 충돌")
                copies[target] = source
        entry = {
            "source_provenance": expected,
            "source_cipher_sha256": source_digest,
            "cached_records": selected,
            "cached_files": len(copies),
            "skipped_incomplete_folders": skipped,
        }
        previous = report["sources"].get(str(args.source_shard))
        if previous is not None and previous != entry:
            raise ValueError("같은 source shard의 재사용 근거가 다릅니다")
        if not report_path.resolve().is_relative_to(root) or report_path.is_symlink():
            raise ValueError("resume 감사 목적지 경로가 다릅니다")
        # 모든 충돌을 먼저 검사한 뒤 복사하며 native-checks·terminal은 건드리지 않는다.
        for target, source in copies.items():
            if not target.exists():
                target.parent.mkdir(parents=True, exist_ok=True)
                with target.open("xb") as output, source.open("rb") as stream:
                    shutil.copyfileobj(stream, output)
                target.chmod(0o600)
        report["sources"][str(args.source_shard)] = entry
        write(report_path, report)
    return entry


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--plan", required=True)
    parser.add_argument("--shard", type=int, required=True)
    parser.add_argument("--shards", type=int, required=True)
    parser.add_argument("--cipher", type=Path, required=True)
    parser.add_argument("--source-head", required=True)
    parser.add_argument("--source-run-id", required=True)
    parser.add_argument("--source-attempt", required=True)
    parser.add_argument("--source-input-sha", required=True)
    parser.add_argument("--source-shard", type=int, required=True)
    parser.add_argument("--source-shards", type=int, required=True)
    parser.add_argument("--key-env", required=True)
    try:
        result = resume(parser.parse_args())
    except Exception as error:
        # 외부 예외 본문·환경 값·키를 traceback에 노출하지 않는다.
        raise SystemExit(f"resume_cache_failed: {type(error).__name__}") from None
    print(
        f"cached_records={result['cached_records']} cached_files={result['cached_files']}"
    )


if __name__ == "__main__":
    main()

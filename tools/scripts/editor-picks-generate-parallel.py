"""기존 구독 생성 계약으로 독립 원문을 최대 여섯 개씩 병렬 처리한다."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "apps/api")]

from tools.research.editor_picks.common import (  # noqa: E402
    MODELS,
    identity,
    immutable,
    now,
    read,
    receipt,
    run_dir,
    sha,
    write,
)
from tools.research.editor_picks.execution import artifact  # noqa: E402
from tools.research.editor_picks.generation import generate  # noqa: E402


def dispatch(args: argparse.Namespace) -> dict:
    if args.arm not in MODELS or not 1 <= args.workers <= 6 or args.limit < 1 or args.timeout < 1:
        raise ValueError("모델·동시성·개수·제한 시간을 확인하세요")
    root = args.run_dir.resolve()
    cohort_path = root / ("pilot-cohort.json" if args.pilot else "cohort.json")
    cohort = read(cohort_path)
    identifiers = [item["id"] for item in cohort["items"]]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("같은 원문 ID를 두 번 호출할 수 없습니다")
    items = cohort["items"][: args.limit]
    request = {
        "schema_version": 1,
        "created_at": now(),
        "arm": args.arm,
        "requested_model": MODELS[args.arm],
        "workers": args.workers,
        "limit": args.limit,
        "timeout_seconds": args.timeout,
        "cohort_file": cohort_path.name,
        "cohort_sha256": sha(cohort_path.read_bytes()),
        "dispatcher_sha256": sha(Path(__file__).read_bytes()),
        "sources": [{"id": item["id"], "source_sha256": item["source_sha256"]} for item in items],
    }
    folder = root / "generation-dispatch" / identity(request)
    immutable(folder / "request.json", request)

    def worker(item):
        try:
            artifact(root, item, args.arm)
        except ValueError:
            result = generate(root, item, args.arm, timeout=args.timeout)
            return {
                "id": item["id"],
                "source_sha256": item["source_sha256"],
                "status": result["status"],
                "artifact_reused": False,
            }
        return {
            "id": item["id"],
            "source_sha256": item["source_sha256"],
            "status": "completed",
            "artifact_reused": True,
        }

    rows = []
    consecutive = 0
    stopped = False
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        for start in range(0, len(items), args.workers):
            batch = list(pool.map(worker, items[start : start + args.workers]))
            for row in batch:
                rows.append(row)
                print(json.dumps(row), flush=True)
                consecutive = (
                    consecutive + 1 if row["status"] in {"timeout", "interrupted", "blocked"} else 0
                )
                stopped = stopped or consecutive >= 2
            if stopped:
                break
    summary = {
        "rows": rows,
        "counts": dict(Counter(row["status"] for row in rows)),
        "consumed": len(rows),
        "selected": len(items),
        "stopped_after_batch": stopped,
        "reason": "two_consecutive_incomplete_calls" if stopped else None,
    }
    write(folder / "summary.json", summary)
    return receipt(
        folder,
        request,
        "blocked" if stopped else "completed",
        **summary,
        summary_file=str((folder / "summary.json").relative_to(root)),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--arm", required=True, choices=tuple(MODELS))
    parser.add_argument("--pilot", action="store_true")
    parser.add_argument("--workers", type=int, choices=(1, 2, 3, 4, 5, 6), default=3)
    parser.add_argument("--limit", type=int, default=200)
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()
    args.run_dir = run_dir(args.run_dir)
    result = dispatch(args)
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())

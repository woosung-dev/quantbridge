"""내부 연구 CLI. DB·Celery·거래소 주문을 호출하지 않는다."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from tools.research.editor_picks.common import MODELS, ROOT, read, run_dir, write

sys.path.insert(0, str(ROOT / "apps/api"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("ingest")
    scan = commands.add_parser("screen")
    scan.add_argument("--timeout", type=int, default=15)
    one = commands.add_parser("screen-one")
    one.add_argument("--id", required=True)
    seal = commands.add_parser("seal")
    seal.add_argument("--pilot", action="store_true")
    seal.add_argument("--allow-partial", action="store_true")
    generation = commands.add_parser("generate")
    generation.add_argument("--pilot", action="store_true")
    generation.add_argument("--arm", choices=tuple(MODELS))
    generation.add_argument("--limit", type=int, default=200)
    generation.add_argument("--timeout", type=int, default=180)
    freeze = commands.add_parser("freeze")
    freeze.add_argument("--end", required=True)
    freeze.add_argument("--warmup", type=int, default=1000)
    commands.add_parser("validate-data")
    planning = commands.add_parser("plan")
    planning.add_argument("--pilot", action="store_true")
    execution = commands.add_parser("execute")
    execution.add_argument("--plan", required=True)
    execution.add_argument("--shard", type=int, default=0)
    execution.add_argument("--shards", type=int, default=1)
    execution.add_argument("--workers", type=int, choices=(1, 2), default=1)
    for name in ("report", "verify", "export"):
        cmd = commands.add_parser(name)
        cmd.add_argument("--plan", required=True)
        if name == "verify":
            cmd.add_argument("--id", required=True)
    args = parser.parse_args()
    root = run_dir(args.run_dir)
    if args.command in {"ingest", "screen", "screen-one", "seal"}:
        from tools.research.editor_picks import catalogue

        if args.command == "ingest":
            value = catalogue.ingest(root)
            result = {"captured": len(value["items"])}
        elif args.command == "screen":
            result = dict(
                Counter(row["status"] for row in catalogue.screen(root, args.timeout))
            )
        elif args.command == "screen-one":
            result = catalogue.screen_one(root, args.id)
            write(root / "screening" / f"{args.id}.json", result)
        else:
            result = catalogue.seal(root, 6 if args.pilot else 200, args.pilot, args.allow_partial)
            result = {
                "source_count": result["source_count"],
                "execution_verified": False,
            }
    elif args.command == "generate":
        from tools.research.editor_picks.generation import generate

        cohort = read(root / ("pilot-cohort.json" if args.pilot else "cohort.json"))

        def worker(arm):
            from tools.research.editor_picks.execution import artifact

            counts = Counter()
            consecutive_timeouts = 0
            for item in cohort["items"][:args.limit]:
                try:
                    artifact(root, item, arm)
                    result = {"status": "completed"}
                except ValueError:
                    result = generate(root, item, arm, timeout=args.timeout)
                counts[result["status"]] += 1
                print(json.dumps({"id": item["id"], "arm": arm, "status": result["status"]}), flush=True)
                consecutive_timeouts = consecutive_timeouts + 1 if result["status"] in {"timeout", "interrupted", "blocked"} else 0
                if consecutive_timeouts >= 2:
                    write(root / "generation" / f"{arm}-blocked.json", {"reason": "two_consecutive_incomplete_calls", "counts": dict(counts)})
                    break
            return {arm: dict(counts)}

        arms = (args.arm,) if args.arm else tuple(MODELS)
        with ThreadPoolExecutor(max_workers=len(arms)) as pool:
            result = list(pool.map(worker, arms))
    elif args.command in {"freeze", "validate-data"}:
        import pandas as pd
        from tools.research.editor_picks import dataset

        result = (
            dataset.freeze(root, pd.Timestamp(args.end, tz="UTC"), args.warmup)
            if args.command == "freeze"
            else dataset.validate(root)
        )
    elif args.command == "plan":
        from tools.research.editor_picks.execution import plan

        value = plan(root, args.pilot)
        result = {"expected_cells": value["expected_cells"], "phase": value["phase"]}
    elif args.command == "execute":
        from tools.research.editor_picks.execution import execute

        result = execute(root, Path(args.plan), args.shard, args.shards, workers=args.workers)
    elif args.command == "report":
        from tools.research.editor_picks.report import build

        result = build(root, Path(args.plan))
    else:
        from tools.research.editor_picks.verification import export, verify

        result = (
            verify(root, args.id, Path(args.plan))
            if args.command == "verify"
            else export(root, Path(args.plan))
        )
    print(json.dumps(result, ensure_ascii=False, default=str))
    return 1 if isinstance(result, dict) and result.get("status") == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())

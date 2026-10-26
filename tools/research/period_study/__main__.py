"""고정 코호트 연구의 명시적 수집·생성·실행·집계 명령."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--catalogue", type=Path)
    parser.add_argument("--source-root", type=Path)
    commands = parser.add_subparsers(dest="command", required=True)
    freeze = commands.add_parser("freeze-data")
    freeze.add_argument("--seed-dir", type=Path)
    freeze.add_argument("--warmup-bars", type=int, default=1000)
    extend = commands.add_parser("extend-data")
    extend.add_argument("--warmup-bars", type=int, required=True)
    extend.add_argument("--period", choices=("P1", "P2", "P3", "P4", "P5"), required=True)
    extend.add_argument("--timeframe", choices=("1h", "4h", "1d"), required=True)
    restore = commands.add_parser("restore-result")
    restore.add_argument("--input", type=Path, required=True)
    restore.add_argument("--output", type=Path, required=True)
    commands.add_parser("plan")
    generate = commands.add_parser("generate")
    generate.add_argument("--limit", type=int)
    generate.add_argument("--id", action="append", dest="ids")
    generate.add_argument("--workers", type=int, choices=(1, 2, 3), default=3)
    execute = commands.add_parser("execute")
    execute.add_argument("--limit", type=int)
    execute.add_argument("--id", action="append", dest="ids")
    execute.add_argument("--shard", type=int, default=0)
    execute.add_argument("--shards", type=int, default=1)
    execute.add_argument("--period", choices=("P1", "P2", "P3", "P4", "P5"), action="append", dest="periods")
    execute.add_argument("--timeframe", choices=("1h", "4h", "1d"), action="append", dest="timeframes")
    execute.add_argument("--code-path", choices=("pine", "python"), action="append", dest="code_paths")
    commands.add_parser("status")
    commands.add_parser("export")
    args = parser.parse_args()
    args.run_dir = args.run_dir.resolve()
    args.run_dir.mkdir(parents=True, exist_ok=True)
    if args.command == "restore-result":
        from tools.research.period_study.encoding import restore as restore_payload
        from tools.research.period_study.state import read, write

        source = args.input if args.input.is_absolute() else args.run_dir / args.input
        output = args.output if args.output.is_absolute() else args.run_dir / args.output
        if output.exists():
            raise ValueError("기존 복원 파일을 덮어쓰지 않습니다")
        payload = restore_payload(read(source), args.run_dir / "data")
        write(output, payload)
        print(json.dumps({"status": "restored_and_canonical_hash_verified", "output": str(output), "rows": len(payload["equity_curve"])}))
        return
    if args.command in {"freeze-data", "extend-data"}:
        from tools.research.period_study.dataset import extend as extend_data
        from tools.research.period_study.dataset import freeze as freeze_data
        from tools.research.period_study.state import lock

        with lock(args.run_dir / "data/.freeze.lock"):
            if args.command == "extend-data":
                result = extend_data(args.run_dir / "data", args.period, args.timeframe, args.warmup_bars)
            else:
                result = freeze_data(args.run_dir / "data", warmup_bars=args.warmup_bars, seed_dir=args.seed_dir)
        print(json.dumps({"status": "completed", "result": result if args.command == "extend-data" else {"files": len(result["files"]) * 5}}))
        return
    from tools.research.period_study.controller import command

    result = command(args)
    print(json.dumps(result, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()

"""각 LLM 변환본을 고정 OHLCV로 실행하여 JSON 결과 저장.

Usage:
    uv run python scripts/run_variants.py --timeframe 1h           # 전체 엔진 × 1h
    uv run python scripts/run_variants.py --timeframe 4h           # 전체 엔진 × 4h
    uv run python scripts/run_variants.py --timeframe 1h e5-sonnet # 특정 엔진
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

EXP = Path(__file__).resolve().parents[1]
GEN = EXP / "generated"
OUT = EXP / "output"

VARIANTS = {
    "e5-sonnet": "e5-sonnet_i3_drfx.py",
    "e6-gpt5": "e6-gpt5_i3_drfx.py",
    "e7b-gemini-flash": "e7b-gemini-flash_i3_drfx.py",
}


def run_one(engine: str, fname: str, csv_path: Path) -> dict:
    py_path = GEN / fname
    if not py_path.exists():
        return {"engine": engine, "error": f"not found: {fname}"}

    try:
        proc = subprocess.run(
            ["uv", "run", "python", str(py_path), str(csv_path)],
            cwd=str(EXP),
            capture_output=True,
            text=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return {"engine": engine, "error": "timeout"}

    stdout = proc.stdout.strip()
    stderr_tail = proc.stderr.strip().splitlines()[-5:] if proc.stderr else []

    # stdout에서 마지막 JSON 블록 추출
    data: dict = {}
    parse_err = None
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if line.startswith("{") and line.endswith("}"):
            try:
                data = json.loads(line)
                break
            except json.JSONDecodeError as e:
                parse_err = str(e)

    return {
        "engine": engine,
        "returncode": proc.returncode,
        "stderr_tail": stderr_tail,
        "parse_error": parse_err,
        "result": data if data else None,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--timeframe", default="1h", choices=["1h", "4h", "1d"])
    ap.add_argument("engine", nargs="?", default=None)
    args = ap.parse_args()

    csv_path = EXP / "ohlcv" / f"btc_usdt_{args.timeframe}_frozen.csv"
    if not csv_path.exists():
        print(f"missing: {csv_path}")
        sys.exit(1)

    targets = VARIANTS
    if args.engine:
        if args.engine in VARIANTS:
            targets = {args.engine: VARIANTS[args.engine]}
        else:
            print(f"unknown engine: {args.engine}. Choices: {list(VARIANTS.keys())}")
            sys.exit(1)

    results = []
    for engine, fname in targets.items():
        print(f"=== {engine} ({args.timeframe}) ===")
        rec = run_one(engine, fname, csv_path)
        print(json.dumps(rec.get("result", {}), indent=2, ensure_ascii=False) if rec.get("result") else f"FAIL: rc={rec.get('returncode')}  stderr={rec.get('stderr_tail')}")
        print()
        rec["timeframe"] = args.timeframe
        results.append(rec)

        # 개별 엔진 결과 파일 저장
        if rec.get("result"):
            out_file = OUT / f"{engine}_i3_drfx_{args.timeframe}.json"
            payload = {
                "engine": engine,
                "script": "i3_drfx",
                "timeframe": args.timeframe,
                "ohlcv_source": str(csv_path),
                **rec["result"],
            }
            out_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False))

    # 전체 요약
    summary_file = OUT / f"llm_variants_run_summary_{args.timeframe}.json"
    summary_file.write_text(json.dumps(results, indent=2, ensure_ascii=False))
    print(f"summary: {summary_file.relative_to(EXP)}")


if __name__ == "__main__":
    main()

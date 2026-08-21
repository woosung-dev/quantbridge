#!/usr/bin/env python3
# 하네스 BE lane 의 AC 판정기 — coverage.py 가 남긴 JSON 을 읽어 **파일별** 커버리지를 rc 로 답한다.
#
# 왜 필요한가: pytest-cov 의 `--cov-fail-under` 는 **합계 하나**만 본다. 대상 파일 셋 중 둘이
# 100% 이고 하나가 0% 여도 합계는 통과할 수 있다 — 그러면 「대상에 닿지 않아도 참」인 AC 다.
# ★`--cov=<파일.py>` 는 유효한 source 스펙이 아니라 **데이터를 한 건도 수집하지 않는다**
#   (2026-08-21 실측 · [LESSON-125]). 디렉터리/패키지를 `--cov` 로 주고 판정은 여기서 해라.
# ★`--cov-config` 로 `concurrency = greenlet,thread` 를 주지 않으면 async 레포의 커버리지는
#   거짓이다 — SQLAlchemy greenlet 전환 뒤의 줄이 전부 미커버로 나온다.
#
# 이 스크립트는 **아무것도 실행하지 않는다** — 앞선 AC(pytest)가 만든 JSON 을 읽을 뿐이다.
#
# 사용:
#   python3 tools/harness/assert_be.py <coverage.json> --target src/tasks/celery_app.py --min-cov 85 \
#                                                      [--target ... --min-cov ...]

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description="BE lane AC 판정 (실행하지 않는다 — 판정만)")
    p.add_argument("report", type=Path, help="coverage.py 의 --cov-report=json 산출물")
    p.add_argument("--target", action="append", required=True, help="파일 경로(리포트 키 접미사)")
    p.add_argument("--min-cov", action="append", type=float, required=True, help="--target 과 짝")
    args = p.parse_args()

    if len(args.target) != len(args.min_cov):
        sys.exit("✗ --target 과 --min-cov 의 개수가 다르다")
    if not args.report.is_file():
        sys.exit(f"✗ 커버리지 리포트가 없다: {args.report} — 앞선 AC(pytest)가 만들었어야 한다")

    try:
        data = json.loads(args.report.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"✗ {args.report} 를 JSON 으로 못 읽는다: {exc}")

    files = data.get("files") or {}
    if not files:
        sys.exit("✗ 리포트의 files 가 비었다 — `--cov` 스펙이 데이터를 한 건도 수집하지 못했다")

    problems: list[str] = []
    for tgt, floor in zip(args.target, args.min_cov, strict=True):
        hits = [k for k in files if k.replace("\\", "/").endswith(tgt)]
        if not hits:
            keys = "\n    ".join(sorted(files)[:20])
            sys.exit(f"✗ 리포트에 대상이 없다: {tgt}\n  리포트에 있는 키(앞 20):\n    {keys}")
        if len(hits) > 1:
            sys.exit(f"✗ 대상 접미사가 {len(hits)}개 파일에 맞는다 — 경로를 더 길게 줘라: {hits}")
        s = files[hits[0]]["summary"]
        pct = float(s["percent_covered"])
        mark = "✓" if pct >= floor else "✗"
        print(f"{mark} {tgt}: {pct:.2f}% (하한 {floor}%) · 미커버 {s['missing_lines']}줄")
        if pct < floor:
            problems.append(f"{tgt} {pct:.2f}% < 하한 {floor}%")

    if problems:
        print("\n✗ FAIL")
        for why in problems:
            print(f"  - {why}")
        return 1
    print("\n✓ PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

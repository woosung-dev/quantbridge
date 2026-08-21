#!/usr/bin/env python3
# 하네스 FE lane 의 AC 판정기 — vitest 가 남긴 산출물 두 개를 읽어 rc 로만 답한다.
#
# 왜 스크립트인가: AC 는 「그 프로젝트의 표준 러너」만 써야 하는데(harness.md §2), vitest 는
# 「케이스가 몇 개인가」와 「그 파일이 몇 % 덮였나」를 exit code 로 답해 주지 않는다. 이 스크립트는
# **아무것도 실행하지 않는다** — 앞선 AC 가 만든 JSON 을 읽어 판정만 한다. 실행과 판정을 한
# 스크립트에 합치면 「대상에 닿지 않아도 참」인 AC 가 된다(레포에서 반복해 밟은 함정).
#
# ★fail-closed 가 이 파일의 계약이다. 입력이 없거나·비었거나·대상이 리포트에 없으면 **rc≠0**.
#   「0건이니 통과」로 새는 판정기를 이 레포는 여러 번 만들었다([LESSON-087] 계열).
#
# 사용:
#   python3 tools/harness/assert_fe.py <report-dir> --min-cases N \
#       --target <경로> --min-cov P [--target <경로2> --min-cov P2 ...]
#
#   <report-dir> 는 vitest 가 다음 둘을 남긴 디렉터리다:
#     coverage-summary.json  (--coverage.reporter=json-summary --coverage.reportsDirectory=<dir>)
#     results.json           (--reporter=json --outputFile=<dir>/results.json)

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _load(path: Path) -> dict:
    if not path.is_file():
        sys.exit(f"✗ 산출물이 없다: {path} — 앞선 AC(vitest)가 이 파일을 만들었어야 한다")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        sys.exit(f"✗ {path} 를 JSON 으로 못 읽는다: {exc}")
    if not isinstance(data, dict) or not data:
        sys.exit(f"✗ {path} 가 비었다 — 빈 입력을 통과로 읽지 않는다")
    return data


def _cov_pct(summary: dict, target: str) -> float:
    """coverage-summary.json 에서 target 의 statements pct 를 찾는다.

    키는 절대경로다. 접미사 일치로 찾되 **정확히 하나**여야 한다 — 둘 이상 맞으면
    어느 쪽을 잰 것인지 모른 채 통과할 수 있다.
    """
    hits = [k for k in summary if k != "total" and k.replace("\\", "/").endswith(target)]
    if not hits:
        keys = "\n    ".join(sorted(k for k in summary if k != "total")[:20])
        sys.exit(f"✗ 커버리지 리포트에 대상이 없다: {target}\n  리포트에 있는 키:\n    {keys}")
    if len(hits) > 1:
        sys.exit(f"✗ 대상 접미사가 {len(hits)}개 파일에 맞는다 — 경로를 더 길게 줘라: {hits}")
    return float(summary[hits[0]]["statements"]["pct"])


def main() -> int:
    p = argparse.ArgumentParser(description="FE lane AC 판정 (실행하지 않는다 — 판정만)")
    p.add_argument("report_dir", type=Path)
    p.add_argument("--min-cases", type=int, required=True, help="통과한 테스트 케이스 하한")
    p.add_argument("--target", action="append", default=[], help="커버리지를 잴 소스 경로(접미사)")
    p.add_argument("--min-cov", action="append", type=float, default=[], help="--target 과 짝")
    args = p.parse_args()

    if len(args.target) != len(args.min_cov):
        sys.exit("✗ --target 과 --min-cov 의 개수가 다르다")

    results = _load(args.report_dir / "results.json")
    total = int(results.get("numTotalTests", 0))
    passed = int(results.get("numPassedTests", 0))
    failed = int(results.get("numFailedTests", 0))

    problems: list[str] = []
    if failed:
        problems.append(f"실패한 케이스 {failed}건")
    if passed != total:
        problems.append(f"통과 {passed} ≠ 전체 {total} (skip·todo 도 통과가 아니다)")
    if passed < args.min_cases:
        problems.append(f"케이스 {passed} < 하한 {args.min_cases}")

    print(f"cases: {passed}/{total} passed (하한 {args.min_cases})")

    if args.target:
        summary = _load(args.report_dir / "coverage-summary.json")
        for tgt, floor in zip(args.target, args.min_cov, strict=True):
            pct = _cov_pct(summary, tgt)
            mark = "✓" if pct >= floor else "✗"
            print(f"cov {mark} {tgt}: {pct:.2f}% (하한 {floor}%)")
            if pct < floor:
                problems.append(f"{tgt} 커버리지 {pct:.2f}% < 하한 {floor}%")

    if problems:
        print("\n✗ FAIL")
        for why in problems:
            print(f"  - {why}")
        return 1
    print("\n✓ PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

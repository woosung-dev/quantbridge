#!/usr/bin/env python3
# 하네스 debt lane 의 AC 판정기 — 담당 범위의 「꺼 둔 규칙」 위반이 0인지 rc 로 답한다.
#
# 왜 스크립트인가: `biome lint --only=<규칙> <경로>` 는 위반이 있으면 rc=1, 없으면 rc=0 을
# 이미 낸다(실측 확인). 그것만으로 AC 를 쓰면 **경로 오타로 0파일을 검사해도 rc=0** 이다 —
# 「0건이니 통과」가 대상에 닿지 않아도 참이 되는 그 구멍이다. 이 스크립트가 더하는 것은
# **검사한 파일 수 하한**(양성 대조) 하나다.
#
# 사용:
#   python3 tools/harness/assert_biome.py --min-files 100 --rules <규칙,규칙,...> -- <경로> [<경로>...]
#
#   규칙은 biome 의 `--only` 값 형식이다: `a11y/noSvgWithoutTitle` · `suspicious/noConsole` …
#   cwd 는 `apps/web` 이어야 한다(biome.jsonc 가 그 자리에 있다).

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys


def main() -> int:
    p = argparse.ArgumentParser(description="debt lane AC 판정 — 위반 0 + 검사 파일 수 하한")
    p.add_argument("--rules", required=True, help="쉼표로 구분한 biome 규칙 목록")
    p.add_argument("--min-files", type=int, required=True, help="검사된 파일 수 하한(양성 대조)")
    p.add_argument("paths", nargs="+", help="검사할 경로")
    args = p.parse_args()

    if shutil.which("pnpm") is None:
        sys.exit("✗ pnpm 이 PATH 에 없다 — cwd 가 apps/web 인지, mise shim 이 앞에 있는지 봐라")

    rules = [r.strip() for r in args.rules.split(",") if r.strip()]
    if not rules:
        sys.exit("✗ --rules 가 비었다")

    cmd = ["pnpm", "exec", "biome", "lint", "--reporter=summary"]
    cmd += [f"--only={r}" for r in rules]
    cmd += args.paths

    proc = subprocess.run(cmd, capture_output=True, text=True)
    out = proc.stdout + proc.stderr

    m = re.search(r"Checked (\d+) files?", out)
    if not m:
        print(out[-2000:])
        sys.exit("✗ biome 출력에서 'Checked N files' 를 못 찾았다 — 명령이 실패했다고 본다")
    checked = int(m.group(1))

    # 규칙별 위반 수 — summary 리포터가 내는 표를 그대로 읽는다.
    violations = {
        mm.group(1): int(mm.group(2))
        for mm in re.finditer(r"lint/(\S+)\s+(\d+)\s+\(", out)
    }
    total = sum(violations.values())

    print(f"checked: {checked} files (하한 {args.min_files})")
    print(f"rules:   {len(rules)}종")
    if violations:
        for r, n in sorted(violations.items(), key=lambda x: -x[1]):
            print(f"  ✗ lint/{r}: {n}")
    else:
        print("  위반 0")

    problems: list[str] = []
    if checked < args.min_files:
        problems.append(
            f"검사된 파일 {checked} < 하한 {args.min_files} — 경로가 대상에 닿지 않았다고 본다"
        )
    if total:
        problems.append(f"위반 {total}건이 남아 있다")

    if problems:
        print("\n✗ FAIL")
        for why in problems:
            print(f"  - {why}")
        return 1
    print("\n✓ PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())

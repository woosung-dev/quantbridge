#!/usr/bin/env bash
# 컨텍스트 예산 계측기 — "문서를 읽는 비용" 을 재는 자.
#
# 왜 있나
#   압축 전후를 **같은 자로** 재기 위해서다. 손으로 `wc -c` 를 세면 회차마다 다른 것을 세게 되고
#   (바이트/문자/토큰이 한국어에서 전부 다르다), 「줄었다」가 증명이 아니라 인상이 된다.
#
# 무엇을 재나
#   1) 고정비  — 매 세션 자동으로 컨텍스트에 들어가는 것 (CLAUDE.md 체인 + 개인 CLAUDE.md + MEMORY.md)
#   2) 파일비  — 지정 문서의 bytes / chars / lines / est_tokens
#   3) 줄길이  — avg / max / 상한 초과 줄 수. ★grep 한 줄이 5KB 면 grep 이 곧 대량 읽기다.
#
# ★토큰 환산비는 추정이 아니라 실측이다 (2026-08-02, context-budget-repair 회차)
#   직전 3회차 CONTROL 트랜스크립트(80dcce10 / 48be44f4 / 8cc0bf0f)에서 **단일 tool_result 만 들어간
#   턴**을 골라 Δ(input+cache_creation+cache_read) − 직전 턴 output_tokens 를 그 tool_result 의
#   토큰으로 역산했다. 한국어 md 표본 16건 110,395자 → 81,218 tok = **0.736 tok/자**.
#   (참고: 코드 0.445 · Bash 출력 0.587 — 이 스크립트는 md 만 다루므로 0.736 만 쓴다.)
#   ★★**계수는 실측이지만 파일별 토큰 수는 「문자수 × 상수」 = 추정이다.** 둘을 섞어 부르지 마라.
#     압축 전후로 링크·표·식별자 비중이 달라지면 같은 상수를 곱한 값의 감소율이 실제 토큰 감소율과
#     어긋날 수 있다(codex MINOR, 2026-08-02). 그래서 출력 컬럼 이름이 `~tok`(estimated)다.
#
# 사용법
#   bash scripts/context-budget.sh              # 사람이 읽는 표
#   bash scripts/context-budget.sh --json       # 기계 대조용 (before/after diff)
#   bash scripts/context-budget.sh --memory <path>   # MEMORY.md 경로 직접 지정

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"

JSON=0
MEMORY_OVERRIDE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --json) JSON=1; shift ;;
    --memory) [ $# -ge 2 ] || { echo "--memory 에 값이 필요하다" >&2; exit 1; }; MEMORY_OVERRIDE="$2"; shift 2 ;;
    -h|--help) sed -n '2,25p' "$0"; exit 0 ;;
    *) echo "알 수 없는 인자: $1" >&2; exit 1 ;;
  esac
done

# ★워크트리에서도 개인 메모리는 **메인 체크아웃 경로**의 슬러그를 쓴다.
#   git-common-dir 로 메인 레포 루트를 되찾아 슬러그를 만든다.
if [ -n "$MEMORY_OVERRIDE" ]; then
  MEMORY_PATH="$MEMORY_OVERRIDE"
else
  COMMON_DIR="$(git -C "$ROOT" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || echo "")"
  MAIN_ROOT="${COMMON_DIR%/.git}"
  [ -n "$MAIN_ROOT" ] && [ -d "$MAIN_ROOT" ] || MAIN_ROOT="$ROOT"
  SLUG="$(printf '%s' "$MAIN_ROOT" | tr '/.' '--')"
  MEMORY_PATH="$HOME/.claude/projects/$SLUG/memory/MEMORY.md"
fi

python3 - "$ROOT" "$MEMORY_PATH" "$JSON" <<'PY'
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

root = Path(sys.argv[1])
memory_path = Path(sys.argv[2])
as_json = sys.argv[3] == "1"

# ★실측 계수. 출처는 이 파일 머리 주석. 하드코딩된 마법 상수를 남기지 않는다.
TOK_PER_CHAR = 0.736
TOK_SOURCE = "실측 (2026-08-02, 트랜스크립트 역산 md 표본 16건 110,395자→81,218 tok)"

# 줄 길이 상한 — docs-audit.sh 의 게이트와 같은 값을 쓴다. 바꾸려면 두 곳을 함께 바꾼다.
LINE_CAPS = {
    "docs/dev-log/INDEX.md": 300,
    "docs/backlog.md": 1000,
    "docs/roadmap.md": 1000,
}

# 고정비 = 자동으로 컨텍스트에 들어가는 것.
#   ★`CONTEXT.md` 는 **여기 없다** — CLAUDE.md 가 import 하지 않아 자동 로드가 아니다. 변동비다.
#   ★`.claude/rules/*.md` 는 셋 다 아니다 — `paths` glob 매칭 파일을 여는 순간에만 로드되는
#     조건부 비용이다(ADR-026, Claude Code v2.0.64+). 여기서는 측정하지 않는다.
IMPORT_RE = re.compile(r"^@(\S+)\s*$", re.MULTILINE)


def measure(path: Path, label: str | None = None) -> dict | None:
    if not path.exists():
        return None
    raw = path.read_bytes()
    text = raw.decode("utf-8", errors="replace")
    lines = text.split("\n")
    lengths = [len(line) for line in lines]
    chars = len(text)
    rel = label or (str(path.relative_to(root)) if path.is_relative_to(root) else str(path))
    cap = LINE_CAPS.get(rel)
    return {
        "file": rel,
        "bytes": len(raw),
        "chars": chars,
        "lines": len(lines),
        "est_tokens": round(chars * TOK_PER_CHAR),
        "avg_line": round(sum(lengths) / max(len(lengths), 1)),
        "max_line": max(lengths) if lengths else 0,
        "over_300": sum(1 for n in lengths if n > 300),
        "over_1000": sum(1 for n in lengths if n > 1000),
        "cap": cap,
        "over_cap": (sum(1 for n in lengths if n > cap) if cap else None),
    }


def resolve_chain(entry: Path, seen: set[Path]) -> list[Path]:
    """CLAUDE.md 의 `@파일` import 를 재귀적으로 펼친다.

    ★가드 2종 (codex NIT, 2026-08-02):
      - **레포 밖 import 는 거부**한다. `@../../secret.md` 같은 경로가 고정비에 섞이면
        「자동 로드분」이 임의로 부풀거나 줄어든다.
      - **없는 import 는 조용히 넘기지 않고 경고**한다. 조용한 누락은 과소계상이 된다.
    """
    if entry in seen:
        return []
    if not entry.exists():
        print(f"  ! import 대상 없음 — 고정비에서 누락됨: {entry}", file=sys.stderr)
        return []
    seen.add(entry)
    out = [entry]
    for target in IMPORT_RE.findall(entry.read_text(encoding="utf-8", errors="replace")):
        resolved = (entry.parent / target).resolve()
        if not resolved.is_relative_to(root):
            print(f"  ! 레포 밖 import 는 세지 않는다: {resolved}", file=sys.stderr)
            continue
        out.extend(resolve_chain(resolved, seen))
    return out


fixed_files: list[dict] = []
seen: set[Path] = set()
for path in resolve_chain(root / "CLAUDE.md", seen):
    row = measure(path)
    if row:
        fixed_files.append(row)
for extra in (Path.home() / ".claude" / "CLAUDE.md", memory_path):
    row = measure(extra, label=str(extra).replace(str(Path.home()), "~"))
    if row:
        fixed_files.append(row)

VARIABLE = [
    "CONTEXT.md",
    "docs/status.md",
    "docs/roadmap.md",
    "docs/backlog.md",
    "docs/dev-log/INDEX.md",
    "docs/reference/operations/gates-and-traps.md",
    "docs/reference/operations/workflows/generator-evaluator-pipeline.md",
    "docs/lessons.md",
]
variable_files = [row for name in VARIABLE if (row := measure(root / name))]

fixed_total = sum(row["est_tokens"] for row in fixed_files)
payload = {
    "tok_per_char": TOK_PER_CHAR,
    "tok_source": TOK_SOURCE,
    "fixed_total_tokens": fixed_total,
    "fixed": fixed_files,
    "variable": variable_files,
    "cap_violations": {
        row["file"]: row["over_cap"]
        for row in fixed_files + variable_files
        if row["over_cap"]
    },
}

if as_json:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    sys.exit(0)


def table(title: str, rows: list[dict]) -> None:
    print(f"\n── {title} " + "─" * max(0, 66 - len(title)))
    print(f"{'file':<46}{'bytes':>9}{'chars':>9}{'~tok':>9}{'lines':>7}{'avg':>6}{'max':>7}{'>cap':>6}")
    for row in rows:
        cap = "-" if row["over_cap"] is None else str(row["over_cap"])
        print(
            f"{row['file'][-46:]:<46}{row['bytes']:>9,}{row['chars']:>9,}"
            f"{row['est_tokens']:>9,}{row['lines']:>7,}{row['avg_line']:>6}{row['max_line']:>7,}{cap:>6}"
        )


print("══ context-budget ══")
print(f"  토큰 환산비 = {TOK_PER_CHAR} tok/자  ← {TOK_SOURCE}")
table(f"고정비 — 자동 로드 (합계 {fixed_total:,} tok)", fixed_files)
table("변동비 — 손으로 여는 문서 (★자동 로드 아님)", variable_files)
if payload["cap_violations"]:
    print("\n★줄 길이 상한 초과:")
    for name, count in payload["cap_violations"].items():
        print(f"    {name}: {count}줄 (상한 {LINE_CAPS[name]}자)")
else:
    print("\n✓ 줄 길이 상한 초과 없음")
PY

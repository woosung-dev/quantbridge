#!/usr/bin/env bash
# header-audit — 소스 파일 첫 3줄 안에 "한국어 주석"이 있는지 감사한다. [BL-307]
#
# 무엇을 재는가
#   대상: `apps/api/src/**/*.py` · `apps/web/src/**/*.{ts,tsx}` (다른 확장자는 대상 아님).
#   위반: 파일 첫 3줄 안, **주석/독스트링 영역**에 한글(U+AC00~U+D7A3)이 1자 이상 없다.
#   근거: 루트 `AGENTS.md:23` (「사고/계획/대화/문서/주석 = 한국어」).
#
# ★핵심 ① — 한글 "존재" 검사가 아니라 한글 "주석" 검사다.
#   `MESSAGE = "백테스트 실패"` 처럼 한글이 문자열 리터럴에만 있으면 그건 위반이다.
#   그래서 각 줄에서 주석/독스트링 **구간만** 떼어 검사한다. 코드 구간은 절대 안 본다 —
#   `head -3 | grep '[가-힣]'` 로 짜면 이 구분이 통째로 사라진다.
#   ★토큰 집합은 **언어별로 나누지 않고 합집합**(`#` `//` `/*` `"""` `'''`)이다. `.py` 안의
#     `// 한국어` 도 통과한다는 뜻이고, 의도한 관대함이다 — 이 감사기는 「헤더가 한국어인가」를
#     재지 「주석 문법이 그 언어에 맞는가」를 재지 않는다. 후자는 ruff·tsc 가 이미 잡는다.
#
# ★핵심 ② — 판정은 **python3** 가 한다. 셸의 `grep '[가-힣]'` 이 아니다.
#   2026-08-10 CI 실패로 확정된 사실이다: **GNU grep 은 `LANG=C.UTF-8` 에서 범위 표현식
#   `[가-힣]` 을 거부한다** (`grep: Invalid collation character`). 대괄호 범위는 collation
#   순서로 해석되는데 C.UTF-8 에 그 정의가 없다. 그리고 이 고장은 **로컬에서 재현되지 않는다** —
#   macOS BSD grep 은 같은 로케일에서 멀쩡히 통과한다.
#   ⇒ 우회로 셋을 실측해 전부 기각했다:
#     ⑴ UTF-8 바이트 범위(`\xed[\x80-\x9e]…`) — grep 종류마다 다르게 깨진다(BSD 에서 미매치).
#     ⑵ UTF-8 로케일 강제 — CI 가 이미 C.UTF-8 이고 그게 실패한 로케일이다.
#     ⑶ 「비ASCII 문자면 한국어」 — ★**절대 안 된다.** 이 레포 영문 헤더는 em-dash(`—`)를
#        쓰므로 `Provider registry — Sprint 47` 이 통과해 **거짓 초록**이 된다.
#   python3 의 `str` 은 유니코드라 로케일과 무관하고, 실측상 750파일 전량 판정이 **0.06초**로
#   종전 per-line grep(1.6초)보다도 빠르다.
#
# 면제 (`docs/backlog.md` BL-307 원장의 exempt list + 벤더 디렉터리)
#   `apps/web/src/components/ui/**` (shadcn 벤더 — `apps/web/AGENTS.md:232` 가 직접 수정 금지.
#     면제하지 않으면 이 게이트가 **금지된 수정을 영구히 강제**하고, `shadcn add` 재설치 한 번에
#     헤더가 사라져 CI 가 빨개진다), 경로에 `/tests/`·`/__tests__/`·`config`·`/generated/` 포함,
#   또는 파일명이 `test_*.py`·`*_test.py`·`conftest.py`·`*.test.ts(x)`·`*.spec.ts(x)`·
#   `__init__.py`·`index.ts`·`index.tsx`·`*.d.ts`·`*.generated.*`.
#
# 종료 코드: 위반 0건 → 0 / 1건 이상 → 1 / 판별력 자기검사 실패·python3 부재 → 3.
# 인자: 없음 = 사람이 읽는 요약 + 위반 경로. `--list` = 위반 경로만 한 줄에 하나씩(그 외 출력 없음).
#
# 사용법: tools/scripts/header-audit.sh [--list]
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
# ★`QB_HEADER_AUDIT_ROOT` — 검사 대상 트리를 갈아끼운다. pre-commit 훅이 **index 를 실체화한
#   트리**를 넘기려고 쓴다. 훅이 작업 트리를 재면 「스테이징된 위반 + 언스테이지된 수정」이
#   조용히 통과하고, 반대로 무관한 언스테이지 위반이 정상 커밋을 막는다 —
#   `apps/api/AGENTS.md` §10.1 「검사기가 보는 표면 ≠ 실제 실패 표면」 그대로다.
#   (2026-08-10 `/code-review` Spec 축 (c)1 검출.)
[ -n "${QB_HEADER_AUDIT_ROOT:-}" ] && ROOT="$QB_HEADER_AUDIT_ROOT"

LIST=0
case "${1:-}" in
  "") ;;
  --list) LIST=1 ;;
  *) echo "알 수 없는 인자: $1 (지원: --list)" >&2; exit 1 ;;
esac

command -v python3 >/dev/null 2>&1 || {
  echo "✗ python3 를 찾을 수 없다 — 이 감사기의 판정은 python3 가 한다 (셸 grep 은 로케일에 따라 한글 범위를 거부한다)." >&2
  echo "  판정을 포기한다 — 초록을 내면 거짓 통과가 된다." >&2
  exit 3
}

ROOT="$ROOT" LIST="$LIST" python3 - <<'PY'
# -*- coding: utf-8 -*-
"""소스 첫 3줄 한국어 헤더 감사 — 판정 본체. [BL-307]"""
import os
import re
import sys

ROOT = os.environ["ROOT"]
LIST = os.environ["LIST"] == "1"

HANGUL = re.compile(r"[가-힣]")

# ── 판별력 자기검사 ──────────────────────────────────────────────
# ★양성 하나로는 부족하다. 「비ASCII 면 한국어」로 퇴화한 구현도 양성은 통과하기 때문이다.
#   그래서 em-dash 를 **음성 대조**로 세운다 — 이 레포 영문 헤더가 실제로 쓰는 문자이고,
#   그 퇴화가 만드는 거짓 초록이 정확히 이 감사기가 막으려는 것이다.
if not HANGUL.search("한") or HANGUL.search("a") or HANGUL.search("—"):
    sys.stderr.write("✗ 한글 판별기가 고장났다 (양성 '한' / 음성 'a'·em-dash 대조 실패).\n")
    sys.stderr.write("  판정을 포기한다 — 초록을 내면 거짓 통과가 된다.\n")
    sys.exit(3)

TARGETS = (("apps/api/src", (".py",)), ("apps/web/src", (".ts", ".tsx")))

EXEMPT_BASENAMES = {"conftest.py", "__init__.py", "index.ts", "index.tsx"}
EXEMPT_PATH_PARTS = ("/tests/", "/__tests__/", "/generated/")


def is_exempt(rel: str) -> bool:
    base = rel.rsplit("/", 1)[-1]
    # shadcn 벤더 — apps/web/AGENTS.md:232 가 직접 수정을 금지한다.
    if rel.startswith("apps/web/src/components/ui/"):
        return True
    probe = "/" + rel
    if any(part in probe for part in EXEMPT_PATH_PARTS):
        return True
    if "config" in rel:
        return True
    if base in EXEMPT_BASENAMES:
        return True
    if base.endswith((".d.ts", ".test.ts", ".test.tsx", ".spec.ts", ".spec.tsx", "_test.py")):
        return True
    if base.startswith("test_") and base.endswith(".py"):
        return True
    if ".generated." in base:
        return True
    return False


def comment_text(lines):
    """첫 3줄에서 **주석/독스트링 구간만** 이어붙여 돌려준다.

    한 줄 안에 주석 구간이 **여러 번** 나올 수 있다(`/* eslint-disable */ // 한국어`).
    그래서 줄을 소진할 때까지 돈다. 코드 구간을 만나면 그 줄은 거기서 끝낸다 —
    문자열 리터럴 안 한글을 헤더로 세지 않기 위해서다.
    """
    out = []
    in_block = False
    block_end = ""
    for line in lines:
        rest = line
        while rest:
            if in_block:
                idx = rest.find(block_end)
                if idx >= 0:
                    out.append(rest[:idx])
                    rest = rest[idx + len(block_end):]
                    in_block = False
                else:
                    out.append(rest)
                    rest = ""
                continue

            trimmed = rest.lstrip()
            if not trimmed:
                rest = ""
                continue

            if trimmed.startswith("#") or trimmed.startswith("//"):
                out.append(trimmed)          # 줄 끝까지 주석
                rest = ""
            elif trimmed.startswith('"""') or trimmed.startswith("'''"):
                q = trimmed[:3]
                tail = trimmed[3:]
                idx = tail.find(q)
                if idx >= 0:
                    out.append(tail[:idx])
                    rest = tail[idx + 3:]
                else:
                    out.append(tail)
                    rest = ""
                    in_block, block_end = True, q
            elif trimmed.startswith("/*"):
                tail = trimmed[2:]
                idx = tail.find("*/")
                if idx >= 0:
                    out.append(tail[:idx])
                    rest = tail[idx + 2:]
                else:
                    out.append(tail)
                    rest = ""
                    in_block, block_end = True, "*/"
            else:
                rest = ""                    # 코드 구간 — 여기는 절대 안 본다
    return "".join(out)


def has_korean_header(path: str) -> bool:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            lines = []
            for _ in range(3):
                line = fh.readline()
                if not line:
                    break
                lines.append(line.rstrip("\n"))
    except OSError:
        return False
    return bool(HANGUL.search(comment_text(lines)))


violations = []
total = checked = exempted = 0
per_scope = {}

for scope, exts in TARGETS:
    base_dir = os.path.join(ROOT, scope)
    count = 0
    for dirpath, _dirnames, filenames in os.walk(base_dir):
        for name in sorted(filenames):
            if not name.endswith(exts):
                continue
            count += 1
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, ROOT)
            if is_exempt(rel):
                exempted += 1
                continue
            checked += 1
            if not has_korean_header(full):
                violations.append(rel)
    per_scope[scope] = count
    total += count

violations.sort()

if LIST:
    for rel in violations:
        print(rel)
else:
    print("══ header-audit  root=%s ══" % ROOT)
    print("  대상: apps/api/src/**/*.py + apps/web/src/**/*.{ts,tsx}")
    print(
        "  스캔 %d건 (BE .py %d + FE .ts/.tsx %d) · 면제 %d건 · 검사 %d건"
        % (total, per_scope["apps/api/src"], per_scope["apps/web/src"], exempted, checked)
    )
    if total == 0:
        print("  ⚠ 대상 확장자 파일이 0건이다 — ROOT 판정이 잘못됐을 수 있다 (ROOT=%s)" % ROOT)
    print("")
    print("▶ 위반 — 첫 3줄에 한국어 주석 없음 (%d건)" % len(violations))
    if not violations:
        print("  없음")
    else:
        for rel in violations:
            print("  %s" % rel)
    print("")
    print("✓ 위반 0건" if not violations else "✗ 위반 %d건" % len(violations))

sys.exit(1 if violations else 0)
PY

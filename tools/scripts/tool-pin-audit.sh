#!/usr/bin/env bash
# tool-pin-audit — 셸 스크립트가 `pnpm`·`uv`·`node`·`npx` 를 **핀 밖에서** 부르는지 감사한다. [BL-785]
#
# 무엇을 재는가
#   대상: `tools/scripts/**/*.sh` + `.husky/pre-commit` · `.husky/pre-push`.
#   위반: 그 스크립트가 위 4종 중 하나를 **명령 위치**에서 부르는데 도구 버전 핀이 없다.
#   핀 = ⑴ `lib/mise-shim-path.sh` 를 소싱하고 `qb_pin_tool_path` 를 부른다, 또는
#        ⑵ mise shim 디렉터리를 PATH 앞에 세우는 줄이 있다(훅 2종이 쓰는 인라인 형태), 또는
#        ⑶ 그 호출이 전부 `mise exec -- <도구>` 다.
#   근거: [ADR-036] — 도구 버전 SSOT 는 루트 `mise.toml` 하나다. 스크립트는 「터미널에서 직접
#   칠 때만 `mise activate` 가 필요하다」는 예외에 안 들어간다.
#
# ★핵심 ① — 「직접 호출 0건」은 **텍스트 0건이 아니라 핀 밖 0건**이다.
#   수리를 PATH 핀으로 했으므로 `uv run ruff check .` 이라는 문자열은 그대로 남는다.
#   그 문자열이 어느 uv 로 가는지를 정하는 것이 핀이고, 이 감사기가 재는 것도 그것이다.
#
# ★핵심 ② — **서버에서 도는 스크립트는 대상이 아니다.**
#   `soak-*.sh` 6종은 `truewords-oracle` 에서 `ssh ... bash -lc` 또는 systemd user unit 으로
#   돈다(`docs/status.md:107` · `docs/reference/operations/frontend-deploy.md:114`).
#   그 환경에 mise 가 있는지 확인된 바 없고, 서버 접속은 금지 사항이라 확인할 수도 없다.
#   확인 못 한 것을 고치면 **소크 창을 죽인다** — 면제하고 이유를 여기에 적어 둔다.
#
# ★핵심 ③ — 명령 위치 판정이 본체다. `echo "cd apps/web && pnpm e2e"` 같은 **안내문**과
#   `bash -c 'cd "$0/apps/web" && pnpm test'` 같은 **진짜 호출**은 둘 다 따옴표 안에 있어
#   따옴표로는 못 가른다. 그래서 가르는 축을 둘 둔다: 히어독 본문 제외 + 그 줄의 **첫 명령**이
#   `echo`/`printf` 면 제외. 나머지는 명령 위치(줄머리 · `;` · `&&` · `||` · `|` · `(` · `` ` ``
#   · `$(` · `then`/`do`/`else` 뒤)에서만 도구 이름을 센다.
#
# 종료 코드: 위반 0건 → 0 / 1건 이상 → 1 / 판별력 자기검사 실패·python3 부재 → 3.
# 인자: 없음 = 사람이 읽는 요약. `--list` = 위반 스크립트 경로만 한 줄에 하나씩.
#
# 사용법: tools/scripts/tool-pin-audit.sh [--list]
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
# ★검사 대상 트리 교체 seam — 하네스가 fixture 트리를 넘긴다(`header-audit.sh` 선례).
[ -n "${QB_TOOL_PIN_ROOT:-}" ] && ROOT="$QB_TOOL_PIN_ROOT"

LIST=0
case "${1:-}" in
  "") ;;
  --list) LIST=1 ;;
  *) echo "알 수 없는 인자: $1 (지원: --list)" >&2; exit 1 ;;
esac

command -v python3 >/dev/null 2>&1 || {
  echo "✗ python3 를 찾을 수 없다 — 이 감사기의 판정은 python3 가 한다." >&2
  echo "  판정을 포기한다 — 초록을 내면 거짓 통과가 된다." >&2
  exit 3
}

ROOT="$ROOT" LIST="$LIST" python3 - <<'PY'
# -*- coding: utf-8 -*-
"""셸 스크립트 도구 버전 핀 감사 — 판정 본체. [BL-785]"""
import os
import re
import sys
from pathlib import Path

ROOT = Path(os.environ["ROOT"])
LIST = os.environ["LIST"] == "1"

TOOLS = ("pnpm", "uv", "node", "npx")

# ── 서버에서 도는 스크립트 — 면제. 값은 「왜」다(보고서가 이 문자열을 그대로 쓴다).
SERVER_SCRIPTS = {
    "tools/scripts/soak-gate.sh": "ssh truewords-oracle 'bash -lc ...' (status.md:107)",
    "tools/scripts/soak-stack.sh": "서버 소크 compose 조작 (ci-cd.md:254 'SSH')",
    "tools/scripts/soak-restart.sh": "서버 소크 재기동 8단계",
    "tools/scripts/soak-observe.sh": "서버 일일 원장 대조",
    "tools/scripts/soak-watch.sh": "서버 systemd user timer (soak-watch.timer)",
    "tools/scripts/soak-logs-follow.sh": "서버 systemd user unit (gates-and-traps.md:459)",
}

# ── 도구 이름을 **데이터로** 갖는 파일 — 이 감사기와 그 하네스뿐이다. 값은 끄는 축이다.
#   "interp" = 인터프리터 히어독 축만 끈다. 셸 명령 위치 축은 살아 있어서, 이 감사기 안에
#             진짜 `pnpm` 호출을 넣으면 **자기가 자기를 잡는다**(표적 변이 ③).
#   "all"    = 파일 전체. 하네스의 fixture 본문은 셸 스니펫 그 자체라 명령 위치 축으로
#             가릴 방법이 없다. 대신 이 파일은 도구를 부를 일이 구조적으로 없다.
DATA_ONLY = {
    "tools/scripts/tool-pin-audit.sh": "interp",
    "tools/scripts/tool-pin-audit-test.sh": "all",
}

# 명령 위치 = 줄머리 또는 구분자 뒤. 그 앞에 `VAR=값` 접두와 **명령 래퍼**가 몇 개 붙어도
# 명령 위치다. ★래퍼를 빼먹으면 `timeout 120 uv run python` 이 통째로 안 잡힌다 —
#   2026-08-17 초판이 실제로 그랬고, 이 레포에 그 형태가 3곳 있다.
_SEP = r"(?:^|[;&|(){}`]|&&|\|\||\bthen\b|\bdo\b|\belse\b|\$\()"
_ASSIGN = r"(?:[A-Za-z_][A-Za-z0-9_]*=(?:\"[^\"]*\"|'[^']*'|[^\s]*)\s+)*"
_WRAP = r"(?:(?:timeout|nohup|exec|env|command|sudo)\s+(?:-\S+\s+|\d+\S*\s+)*)*"
CALL_RE = re.compile(
    _SEP + r"\s*" + _ASSIGN + _WRAP + _ASSIGN + r"(" + "|".join(TOOLS) + r")(?=\s|$)"
)
# 히어독으로 인터프리터에 넘기는 코드 안의 호출 — 셸 명령 위치 문법이 통하지 않는다.
# `docs-audit.sh` 의 `shutil.which("node")` 가 그 모양이다. 문자열 리터럴로만 잡는다.
INTERP_HEREDOC_RE = re.compile(r"\b(?:python3?|node|ruby|perl)\b[^\n]*<<-?\s*['\"]?[A-Za-z_]")
INTERP_CALL_RE = re.compile(r"['\"](" + "|".join(TOOLS) + r")['\"]")
# `mise exec -- <도구>` 는 이미 핀을 통과한 호출이다.
MISE_EXEC_RE = re.compile(r"\bmise\s+exec\b[^\n]*?--\s+(?:" + "|".join(TOOLS) + r")\b")
LEAD_ECHO_RE = re.compile(r"^\s*(?:echo|printf)\b")
HEREDOC_RE = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")

# ★핀 판정은 **명령 위치**로 한다. 「파일 어딘가에 그 문자열이 있다」로 짜면 이 감사기 자신의
#   고치는 법 안내문이 자기를 핀으로 만든다 — 2026-08-17 초판이 실제로 그랬다.
PIN_SOURCE_RE = re.compile(r"^\s*(?:\.|source)\s+\S*lib/mise-shim-path\.sh", re.MULTILINE)
PIN_CALL_RE = re.compile(r"^\s*qb_pin_tool_path\b", re.MULTILINE)
PIN_INLINE_RE = re.compile(
    r'^\s*PATH="?\$\{?(?:HOME|MISE_DATA_DIR)[^"\n]*/shims:\$PATH', re.MULTILINE
)


def strip_comment(line: str) -> str:
    """따옴표 밖 `#` 부터 잘라낸다. 셸 파서가 아니라 근사치다 — 그래서 자기검사가 있다."""
    out = []
    quote = ""
    i = 0
    while i < len(line):
        ch = line[i]
        if quote:
            out.append(ch)
            if ch == quote:
                quote = ""
        elif ch in "\"'":
            quote = ch
            out.append(ch)
        elif ch == "#" and (i == 0 or line[i - 1].isspace()):
            break
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def calls_in(text: str, skip_interp: bool = False):
    """(줄번호, 도구, 원본줄) 목록. 히어독 본문·안내문(echo/printf)은 세지 않는다.

    skip_interp=True 면 인터프리터 히어독 본문의 문자열 리터럴 축을 끈다(DATA_ONLY 전용).
    셸 명령 위치 축은 **그대로 산다** — 그래야 면제 파일이 진짜 호출을 숨기지 못한다.
    """
    hits = []
    pending = None  # 히어독 종료 구분자
    interp = False  # 그 히어독이 인터프리터에 들어가는가
    for no, raw in enumerate(text.splitlines(), 1):
        if pending is not None:
            if raw.strip() == pending:
                pending = None
                interp = False
            elif interp and not skip_interp:
                for hit in INTERP_CALL_RE.finditer(strip_comment(raw)):
                    hits.append((no, hit.group(1), raw.strip()))
            continue
        line = strip_comment(raw)
        if not line.strip():
            continue
        m = HEREDOC_RE.search(line)
        if m:
            pending = m.group(2)
            interp = bool(INTERP_HEREDOC_RE.search(line))
        if LEAD_ECHO_RE.match(line):
            continue
        probe = MISE_EXEC_RE.sub(" ", line)
        for hit in CALL_RE.finditer(probe):
            hits.append((no, hit.group(1), raw.strip()))
    return hits


def is_pinned(text: str) -> bool:
    if PIN_INLINE_RE.search(text):
        return True
    return bool(PIN_SOURCE_RE.search(text) and PIN_CALL_RE.search(text))


# ── 판별력 자기검사 ──────────────────────────────────────────────
# ★양성 하나로는 부족하다. 「도구 이름이 파일 어디에든 있으면 호출」로 퇴화한 구현도 양성은
#   통과하기 때문이다. 그 퇴화가 만드는 거짓 red 가 정확히 이 감사기를 못 쓰게 만든다.
_POS = 'cd apps/web && pnpm test\n'
_NEG_COMMENT = '# pnpm test 를 여기서 돌린다\n'
_NEG_ECHO = 'echo "  E2E   cd apps/web && pnpm e2e"\n'
_NEG_HEREDOC = "cat <<'EOF'\n  cd apps/api && uv run pytest\nEOF\n"
_NEG_MISE = 'cd "$WEB" && mise exec -- pnpm build\n'
_POS_WRAP = 'timeout 120 uv run python -c "pass"\n'
_POS_INTERP = 'python3 - <<\'PY\'\nnode = shutil.which("node")\nPY\n'
_NEG_INTERP_WORD = "python3 - <<'PY'\nfor node in graph.nodes:\n    pass\nPY\n"
_selftest = [
    ("양성 명령 위치", _POS, True),
    ("양성 래퍼(timeout)", _POS_WRAP, True),
    ("양성 인터프리터 히어독", _POS_INTERP, True),
    ("음성 주석", _NEG_COMMENT, False),
    ("음성 안내문(echo)", _NEG_ECHO, False),
    ("음성 히어독 본문", _NEG_HEREDOC, False),
    ("음성 인터프리터 히어독 안 동명 변수", _NEG_INTERP_WORD, False),
    ("음성 mise exec 경유", _NEG_MISE, False),
]
_bad = [name for name, body, want in _selftest if bool(calls_in(body)) is not want]
if _bad:
    sys.stderr.write("✗ 호출 판별기가 고장났다: " + ", ".join(_bad) + "\n")
    sys.stderr.write("  판정을 포기한다 — 초록을 내면 거짓 통과가 된다.\n")
    sys.exit(3)
_PIN_POS = '. "$ROOT/tools/scripts/lib/mise-shim-path.sh"\nqb_pin_tool_path || true\n'
_PIN_NEG_MENTION = (
    'echo "  고치는 법: . tools/scripts/lib/mise-shim-path.sh 뒤에 qb_pin_tool_path"\n'
)
if not is_pinned(_PIN_POS) or is_pinned(_POS) or is_pinned(_PIN_NEG_MENTION):
    sys.stderr.write("✗ 핀 판별기가 고장났다 (양성 = lib 소싱 / 음성 = 핀 없음·안내문 언급).\n")
    sys.stderr.write("  판정을 포기한다 — 초록을 내면 거짓 통과가 된다.\n")
    sys.exit(3)

# ── 대상 수집 ────────────────────────────────────────────────────
targets = sorted(p for p in (ROOT / "tools" / "scripts").rglob("*.sh"))
for hook in ("pre-commit", "pre-push"):
    p = ROOT / ".husky" / hook
    if p.is_file():
        targets.append(p)

violations = []
exempt_seen = []
pinned_seen = []
for path in targets:
    rel = str(path.relative_to(ROOT))
    axis_off = DATA_ONLY.get(rel)
    if axis_off == "all":
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    hits = calls_in(text, skip_interp=axis_off == "interp")
    if not hits:
        continue
    if rel in SERVER_SCRIPTS:
        exempt_seen.append((rel, len(hits), SERVER_SCRIPTS[rel]))
        continue
    if is_pinned(text):
        pinned_seen.append((rel, len(hits)))
        continue
    violations.append((rel, hits))

if LIST:
    for rel, _hits in violations:
        print(rel)
    sys.exit(1 if violations else 0)

print(f"▶ 도구 버전 핀 감사 — 대상 {len(targets)}개 스크립트 ({' · '.join(TOOLS)})")
for rel, n in pinned_seen:
    print(f"  ✓ {rel}  (호출 {n}건 · 핀 있음)")
for rel, n, why in exempt_seen:
    print(f"  – {rel}  (호출 {n}건 · 서버 실행이라 면제 — {why})")

if not violations:
    print(f"\n✓ 핀 밖 직접 호출 0건 (핀 {len(pinned_seen)}개 · 면제 {len(exempt_seen)}개)")
    sys.exit(0)

print(f"\n✗ 핀 밖에서 도구를 부르는 스크립트 {len(violations)}개")
for rel, hits in violations:
    print(f"  {rel}")
    for no, tool, line in hits:
        print(f"    :{no}  [{tool}]  {line[:100]}")
print()
print("  고치는 법 — 스크립트 진입부(ROOT 확정 직후)에 두 줄을 넣어라:")
print('    . "$ROOT/tools/scripts/lib/mise-shim-path.sh"')
print("    qb_pin_tool_path || true")
print("  서버에서만 도는 스크립트라면 고치지 말고 tool-pin-audit.sh 의 SERVER_SCRIPTS 에 이유와 함께 등록해라.")
sys.exit(1)
PY

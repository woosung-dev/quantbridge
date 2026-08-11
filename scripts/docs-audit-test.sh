#!/usr/bin/env bash
#
# `docs-audit.sh` 의 **⓪ 표 정체성 축** 판별력 하네스 ([BL-702]).
#
# 왜 있나 — `bl-audit-test.sh`·`header-audit-test.sh` 가 붙은 이유와 같다(BL-569 계열):
#   레포의 ⓪ 표가 이미 원장과 일치하므로, 정체성 판정 로직을 **통째로 지워도** 「문서 감사」는
#   초록이다. 실제 사고를 막는 코드인데 되돌려도 아무도 못 잡는다.
#   ★그리고 이 축이 막으려는 사고는 정확히 **빈 입력이 「일치」로 새는 것**이다 — 이 레포가
#   2026-08-10 에 두 번 밟았다. 그 rc=3 경로를 여기서 **실제로 발화시킨다.**
#
# 사용법: scripts/docs-audit-test.sh
#
# ★진짜 `docs-audit.sh` 를 겨눈다 — 사본이 아니다. 임시 트리에 **스텁 `bl-audit.sh`** 와
#   최소 `docs/` 를 세우고, 진짜 스크립트를 그 위에서 돌린다(`soak-watch-test.sh` 와 같은 수법).
#   실제 `docs/` 는 1바이트도 건드리지 않는다.
# ★기대 rc 를 **케이스마다 명시**한다. 「아무튼 실패했다」로는 판별력을 못 잰다 —
#   ABORT(3) 와 불일치(1) 를 구분하지 못하면 빈 입력이 다시 샌다.

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd -P)"
SB="$(mktemp -d "${TMPDIR:-/tmp}/docs-audit-test.XXXXXX")"
trap 'rm -rf "$SB"' EXIT

mkdir -p "$SB/scripts" "$SB/docs"
cp "$ROOT/scripts/docs-audit.sh" "$SB/scripts/" || { echo "✗ docs-audit.sh 를 못 읽었다"; exit 2; }

# 스텁 원장 — `CASE` 로 ACTIVE 집합을 바꾼다. 진짜 bl-audit 은 부르지 않는다(느리고, 실제 원장에 의존한다).
cat > "$SB/scripts/bl-audit.sh" <<'STUB'
#!/usr/bin/env bash
# $1 = --list, $2 = 판정어
case "${CASE:-empty}" in
  empty)  : ;;                                             # ACTIVE·PARTIAL 전부 공집합
  ledger) [ "${2:-}" = "ACTIVE" ] && printf 'BL-999\tP1\t:1\n' ;;
esac
exit 0
STUB
chmod +x "$SB/scripts/bl-audit.sh"
printf '# stub\n\n### BL-999\n\n**상태:** Open\n**트리거 판정:** 도래 — stub\n' \
  > "$SB/docs/backlog.md"

# ⓪ 표 = 취소선 3행(계약 ≥3 을 채운다) + 선택적 살아 있는 1행.
mk_status() {
  {
    printf '# stub status\n\n## 다음 스프린트\n\n### ⓪ 다음 후보\n\n'
    printf '| # | 후보 | P |\n| --- | --- | --- |\n'
    printf '| **A** | ~~[BL-111] 끝난 것~~ → 종결 | — |\n'
    printf '| **B** | ~~[BL-222] 끝난 것~~ → 종결 | — |\n'
    printf '| **C** | ~~[BL-333] 끝난 것~~ → 종결 | — |\n'
    [ -n "${1:-}" ] && printf '| **D** | [%s] 살아 있는 후보 | P1 |\n' "$1"
    printf '\n'
  } > "$SB/docs/status.md"
}

FAIL=0
run() {  # $1=CASE  $2=기대 rc  $3=정체성 축이 말해야 하나(yes/no)  $4=설명
  CASE="$1" bash "$SB/scripts/docs-audit.sh" > "$SB/out.txt" 2>&1
  local rc=$? spoke=no
  grep -q "⓪ 표 정체성" "$SB/out.txt" && spoke=yes
  if [ "$rc" = "$2" ] && [ "$spoke" = "$3" ]; then
    printf '  ✓ %s\n' "$4"
  else
    printf '  ✗ %s\n      rc=%s (기대 %s) · 정체성축발화=%s (기대 %s)\n' "$4" "$rc" "$2" "$spoke" "$3"
    sed 's/^/      | /' "$SB/out.txt" | head -6
    FAIL=1
  fi
}

echo "▶ docs-audit ⓪ 표 정체성 축 — 판별력 4케이스"

# ⑴ ★음성 대조가 아니라 **ABORT 대조**다. 양쪽이 비면 초록도 빨강도 내지 않는다.
mk_status "";       run empty  3 yes "양쪽 공집합 → rc=3 ABORT (빈 입력을 「일치」로 통과시키지 않는다)"

# ⑵ 원장에는 있는데 표에 없다 — 다음 회차가 그 항목을 **볼 수 없는** 상태.
mk_status "";       run ledger 1 yes "원장 ACTIVE BL-999 · 표에 살아 있는 행 없음 → 불일치(missing)"

# ⑶ 표에는 살아 있는데 원장이 아니다 — 2026-08-10 에 실제로 난 사고(종결된 BL 이 최상위 추천).
mk_status "BL-888"; run empty  1 yes "표에 살아 있는 BL-888 · 원장 공집합 → 불일치(extra)"

# ⑷ ★양성 대조 — 일치하면 이 축은 **침묵**해야 한다. rc 는 스텁 트리의 다른 축 때문에 1 이지만
#   「⓪ 표 정체성」 줄이 나오면 이 검사기는 상시 빨강이고 판별력이 0 이다.
mk_status "BL-999"; run ledger 1 no  "양성 대조: 원장 == 표 → 정체성 축 침묵"

if [ "$FAIL" != 0 ]; then
  echo "✗ docs-audit 하네스 실패 — ⓪ 표 정체성 축이 판별력을 잃었다"
  exit 1
fi
echo "✓ docs-audit 하네스 4/4 — ABORT · missing · extra · 양성 대조"

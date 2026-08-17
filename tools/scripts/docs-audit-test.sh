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
# 사용법: tools/scripts/docs-audit-test.sh
#
# ★진짜 `docs-audit.sh` 를 겨눈다 — 사본이 아니다. 임시 트리에 **스텁 `bl-audit.sh`** 와
#   최소 `docs/` 를 세우고, 진짜 스크립트를 그 위에서 돌린다(`soak-watch-test.sh` 와 같은 수법).
#   실제 `docs/` 는 1바이트도 건드리지 않는다.
# ★기대 rc 를 **케이스마다 명시**한다. 「아무튼 실패했다」로는 판별력을 못 잰다 —
#   ABORT(3) 와 불일치(1) 를 구분하지 못하면 빈 입력이 다시 샌다.

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
SB="$(mktemp -d "${TMPDIR:-/tmp}/docs-audit-test.XXXXXX")"
trap 'rm -rf "$SB"' EXIT

mkdir -p "$SB/tools/scripts/lib" "$SB/docs"
cp "$ROOT/tools/scripts/docs-audit.sh" "$SB/tools/scripts/" || { echo "✗ docs-audit.sh 를 못 읽었다"; exit 2; }
# ★lib 도 함께 옮긴다 — docs-audit 은 `dirname $0` 옆의 `lib/mise-shim-path.sh` 를 소싱하므로
#   ([BL-785]) 사본만 두면 임시 트리에서 `No such file or directory` 로 죽고, `set -e` 아래라
#   **19케이스가 전부 rc=1 로 뭉개진다**(2026-08-17 실측 — 표적 테스트로는 안 보였다).
#   선례 = soak-watch-test.sh:142 (2026-08-16 notify-telegram lib 추출 후속).
cp "$ROOT/tools/scripts/lib/mise-shim-path.sh" "$SB/tools/scripts/lib/" \
  || { echo "✗ lib/mise-shim-path.sh 를 못 읽었다"; exit 2; }
printf '# stub AGENTS\n' > "$SB/AGENTS.md"

# 스텁 원장 — `CASE` 로 ACTIVE/PARTIAL 집합을 바꾼다. 진짜 bl-audit 은 부르지 않는다
# (느리고, 실제 원장에 의존한다).
# ★PARTIAL 케이스 3종은 [BL-703] 이 추가했다 — 그전엔 스텁이 ACTIVE 만 낼 수 있어서
#   `PARTIAL ∧ 도래` 갈래와 PARTIAL 판정줄 의무를 **하네스가 한 번도 밟지 않았다.**
cat > "$SB/tools/scripts/bl-audit.sh" <<'STUB'
#!/usr/bin/env bash
# $1 = --list, $2 = 판정어
case "${CASE:-empty}" in
  empty)  : ;;                                             # ACTIVE·PARTIAL 전부 공집합
  ledger) [ "${2:-}" = "ACTIVE" ] && printf 'BL-999\tP1\t:1\n' ;;
  # ★아래 셋은 ACTIVE BL-999 를 **함께** 낸다. PARTIAL 만 내면 기대 집합이 비어
  #   rc=3 ABORT 가 먼저 걸려 재려던 축에 도달하지 못한다(설계 시 실제로 밟았다).
  partial_arrived)
    [ "${2:-}" = "ACTIVE" ]  && printf 'BL-999\tP1\t:1\n'
    [ "${2:-}" = "PARTIAL" ] && printf 'BL-777\tP1\t:10\n' ;;
  partial_waiting)
    [ "${2:-}" = "ACTIVE" ]  && printf 'BL-999\tP1\t:1\n'
    [ "${2:-}" = "PARTIAL" ] && printf 'BL-666\tP2\t:20\n' ;;
  partial_noverdict)
    [ "${2:-}" = "ACTIVE" ]  && printf 'BL-999\tP1\t:1\n'
    [ "${2:-}" = "PARTIAL" ] && printf 'BL-555\tP3\t:30\n' ;;
  # ── [BL-779] 다중 파일 축 ──────────────────────────────────────────
  # ★두 케이스 모두 **섹션이 `docs/backlog-resolved.md` 에만 있다.** 판정줄을 거기서
  #   못 읽으면 `resolved_verdict` 가 「0개」로 발화하고(위양성), 그러면 원장을 가른 것만으로
  #   게이트가 상시 red 가 된다. 반대로 `resolved_noverdict` 가 침묵하면 진짜 누락을 놓친다.
  resolved_verdict)
    [ "${2:-}" = "ACTIVE" ]   && printf 'BL-999\tP1\t:1\n'
    [ "${2:-}" = "DEFERRED" ] && printf 'BL-444\tP2\t:1\tbacklog-resolved.md\n' ;;
  resolved_noverdict)
    [ "${2:-}" = "ACTIVE" ]   && printf 'BL-999\tP1\t:1\n'
    [ "${2:-}" = "DEFERRED" ] && printf 'BL-445\tP2\t:8\tbacklog-resolved.md\n' ;;
  # ★정본이 죽은 상태. stdout 은 비고 rc 만 3 이다 — 종전 파서는 이것을 **공집합**으로 읽었다.
  audit_dead) echo '✗ ABORT — 원장이 비어 있다: docs/backlog-resolved.md' >&2; exit 3 ;;
esac
exit 0
STUB
chmod +x "$SB/tools/scripts/bl-audit.sh"
{
  printf '# stub\n\n'
  printf '### BL-999\n\n**상태:** Open\n**트리거 판정:** 도래 — stub\n\n'
  printf '### BL-777\n\n**상태:** 부분\n**트리거 판정:** 도래 — stub partial arrived\n\n'
  printf '### BL-666\n\n**상태:** 부분\n**트리거 판정:** 미도래 — stub partial waiting\n\n'
  # ★BL-555 는 판정줄이 **없다**. 이것이 [BL-703] 변경의 판별자다.
  printf '### BL-555\n\n**상태:** 부분\n'
} > "$SB/docs/backlog.md"

# 두 번째 원장 ([BL-779]). ★`""` 를 주면 **빈 파일**이 되어 ABORT 축을 잰다.
mk_resolved() {
  if [ "${1:-full}" = "empty" ]; then
    : > "$SB/docs/backlog-resolved.md"
    return
  fi
  {
    printf '# stub resolved\n\n'
    printf '### BL-444\n\n**상태:** ⏳ 대기\n**트리거 판정:** 미도래 — 두 번째 원장에만 있는 판정줄\n\n'
    # ★BL-445 는 판정줄이 **없다** — 두 번째 원장에서도 누락이 잡히는지의 판별자다.
    printf '### BL-445\n\n**상태:** ⏳ 대기\n'
  } > "$SB/docs/backlog-resolved.md"
}
mk_resolved full

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

# `lessons.md` 는 기본적으로 없다. BL-720 케이스만 필요한 최소 표/카드를 세워 각 축이
# 다른 축의 실제 문서 상태에 의존하지 않게 한다.
mk_lessons() {
  case "$1" in
    duplicate_id)
      {
        printf '# stub lessons\n\n## 영구 승격 완료\n\n'
        printf '| ID | 포인터 | 내용 |\n| --- | --- | --- |\n'
        printf '| LESSON-101 | `AGENTS.md` | 표에 이미 있는 ID |\n\n---\n\n'
        printf '### LESSON-101 — 카드가 같은 ID를 재사용\n'
      } > "$SB/docs/lessons.md"
      ;;
    ordered_ids)
      {
        printf '# stub lessons\n\n## 영구 승격 완료\n\n'
        printf '| ID | 포인터 | 내용 |\n| --- | --- | --- |\n'
        printf '| LESSON-004 | `AGENTS.md` | 승격된 ID |\n\n---\n\n'
        printf '### LESSON-087 — 첫 카드\n\n### LESSON-088 — 둘째 카드\n\n### LESSON-090 — 셋째 카드\n'
      } > "$SB/docs/lessons.md"
      ;;
    broken_pointer)
      {
        printf '# stub lessons\n\n## 영구 승격 완료\n\n'
        printf '| ID | 포인터 | 내용 |\n| --- | --- | --- |\n'
        printf '| LESSON-004 | `backend/AGENTS.md` | 옮겨져 사라진 포인터 |\n\n---\n'
      } > "$SB/docs/lessons.md"
      ;;
    live_pointers)
      {
        printf '# stub lessons\n\n## 영구 승격 완료\n\n'
        printf '| ID | 포인터 | 내용 |\n| --- | --- | --- |\n'
        printf '| LESSON-004 | `AGENTS.md` | 루트 파일 포인터 |\n'
        printf '| LESSON-005 | `tools/scripts/docs-audit.sh` | 스크립트 포인터 |\n\n---\n'
      } > "$SB/docs/lessons.md"
      ;;
    # ★★2026-08-14 적대 프로브 P1·P2 가 **실제로 뚫었던** 입력이다. 종전 정규식은
    #   `^### LESSON-(\d+)` / `^\|\s*LESSON-(\d+)\s*\|` 라 마크다운 장식이 붙으면 ID 를
    #   못 봤고, 그러면 중복이 그대로 통과했다 — 이 축이 막으려는 사고(`8abd0d67` 의 중복
    #   101)의 **서식만 바꾼 판**이다. 장식 허용을 되돌리면 이 둘이 red 가 된다.
    decorated_dup_table)
      {
        printf '# stub lessons\n\n## 영구 승격 완료\n\n'
        printf '| ID | 포인터 | 내용 |\n| --- | --- | --- |\n'
        printf '| **LESSON-101** | `AGENTS.md` | 표 ID 를 볼드로 감쌌다 |\n\n---\n\n'
        printf '### LESSON-101 — 카드가 같은 ID를 재사용\n'
      } > "$SB/docs/lessons.md"
      ;;
    decorated_dup_heading)
      {
        printf '# stub lessons\n\n## 영구 승격 완료\n\n'
        printf '| ID | 포인터 | 내용 |\n| --- | --- | --- |\n'
        printf '| LESSON-101 | `AGENTS.md` | 표 행 |\n\n---\n\n'
        printf '### [LESSON-101](#lesson-101) — 헤딩을 링크로 감쌌다\n'
      } > "$SB/docs/lessons.md"
      ;;
    # ★실제 `docs/lessons.md` 가 이 축의 첫 판에 낸 **오탐 3건**을 그대로 옮겼다
    #   (2026-08-14 실측 — LESSON-019·020·063 의 승격 위치 칸). 셋 다 `/` 를 품거나
    #   `.md` 로 끝나 보이지만 **경로가 아니다**. 배제 규칙을 되돌리면 여기서 red 가 난다.
    nonpath_spans)
      {
        printf '# stub lessons\n\n## 영구 승격 완료\n\n'
        printf '| ID | 포인터 | 내용 |\n| --- | --- | --- |\n'
        printf '| LESSON-004 | `AGENTS.md` | 살아 있는 포인터 (대조군) |\n'
        printf '| LESSON-019 | `tests/<domain>/test_*_commits.py` | 자리표시자 + 글롭 |\n'
        printf '| LESSON-020 | `asyncio.<Semaphore/Lock/Event/Queue>` | 코드 표현식 |\n'
        printf '| LESSON-063 | `/deepen-modules` | 슬래시 커맨드 |\n\n---\n'
      } > "$SB/docs/lessons.md"
      ;;
  esac
}

FAIL=0
AXIS="⓪ 표 정체성"   # run() 이 「말했나」를 재는 축. 케이스별로 바꾼다.
run() {  # $1=CASE  $2=기대 rc  $3=축이 말해야 하나(yes/no)  $4=설명
  CASE="$1" bash "$SB/tools/scripts/docs-audit.sh" > "$SB/out.txt" 2>&1
  local rc=$? spoke=no
  grep -q "$AXIS" "$SB/out.txt" && spoke=yes
  if [ "$rc" = "$2" ] && [ "$spoke" = "$3" ]; then
    printf '  ✓ %s\n' "$4"
  else
    printf '  ✗ %s\n      rc=%s (기대 %s) · %s축발화=%s (기대 %s)\n' "$4" "$rc" "$2" "$AXIS" "$spoke" "$3"
    sed 's/^/      | /' "$SB/out.txt" | head -6
    FAIL=1
  fi
}

echo "▶ docs-audit ⓪ 표 정체성 + 트리거 판정 줄 + BL-720 지식 정본 + BL-779 다중 파일 원장 축 — 판별력 19케이스"

# ⑴ ★음성 대조가 아니라 **ABORT 대조**다. 양쪽이 비면 초록도 빨강도 내지 않는다.
mk_status "";       run empty  3 yes "양쪽 공집합 → rc=3 ABORT (빈 입력을 「일치」로 통과시키지 않는다)"

# ⑵ 원장에는 있는데 표에 없다 — 다음 회차가 그 항목을 **볼 수 없는** 상태.
mk_status "";       run ledger 1 yes "원장 ACTIVE BL-999 · 표에 살아 있는 행 없음 → 불일치(missing)"

# ⑶ 표에는 살아 있는데 원장이 아니다 — 2026-08-10 에 실제로 난 사고(종결된 BL 이 최상위 추천).
mk_status "BL-888"; run empty  1 yes "표에 살아 있는 BL-888 · 원장 공집합 → 불일치(extra)"

# ⑷ ★양성 대조 — 일치하면 이 축은 **침묵**해야 한다. rc 는 스텁 트리의 다른 축 때문에 1 이지만
#   「⓪ 표 정체성」 줄이 나오면 이 검사기는 상시 빨강이고 판별력이 0 이다.
mk_status "BL-999"; run ledger 1 no  "양성 대조: 원장 == 표 → 정체성 축 침묵"

# ── [BL-703] PARTIAL 갈래 ─────────────────────────────────────────────
# ★⑸⑹ 이 재는 것은 `PARTIAL ∧ 도래` 라는 **술어의 오른쪽 항**이다. 2026-08-11 이전에는
#   PARTIAL 이 판정줄 의무 밖이라 그 항이 데이터로 채워질 수 없었고, 그래서 이 갈래는
#   **한 번도 실행된 적이 없었다.** 코드는 있고 경로는 죽어 있는 상태였다.

# ⑸ 도래한 PARTIAL 은 ACTIVE 와 똑같이 표에 있어야 한다.
mk_status "BL-999"; run partial_arrived 1 yes "PARTIAL BL-777 이 도래인데 표에 없음 → 불일치(missing)"

# ⑹ ★음성 대조 — **과다 포획** 검사. 미도래 PARTIAL 까지 요구하면 표가 원장 전량이 되어
#   「고르는 자리」라는 목적이 무너진다. 침묵해야 한다.
mk_status "BL-999"; run partial_waiting 1 no  "음성 대조: PARTIAL BL-666 은 미도래 → 표에 없어도 침묵"

# ⑺ ★[BL-703] 본체의 판별자. 이 케이스는 변경 **전에는 침묵**한다 —
#   종전 `if verdict != "PARTIAL"` 가 PARTIAL 을 의무 대상에서 빼고 있었기 때문이다.
#   되돌리면 여기서 red 가 나야 하고, 안 나면 그 면제는 아무도 안 지키는 규율로 돌아간다.
AXIS="트리거 판정 줄"
mk_status "BL-999"; run partial_noverdict 1 yes "PARTIAL BL-555 에 판정줄 0개 → 트리거 판정 줄 축 발화"
AXIS="⓪ 표 정체성"

# ── [BL-720] lessons.md 지식 정본 축 ──────────────────────────────────
# ⑻⑼은 카드 헤딩과 승격 표의 ID를 합쳐 보는지, 그리고 유일·오름차순일 때 침묵하는지를
# 함께 재한다. ⑽⑾은 표 안의 코드 스팬만 경로로 보고 살아 있는 포인터는 과다 포획하지 않는지 재한다.
mk_status "BL-999"; mk_lessons duplicate_id
AXIS="LESSON ID 유일성"
run ledger 1 yes "카드 LESSON-101 + 승격 표 LESSON-101 → LESSON ID 유일성 축 발화"

mk_status "BL-999"; mk_lessons ordered_ids
run ledger 1 no "양성 대조: 087·088·090 + 표 004는 유일·오름차순 → LESSON ID 유일성 축 침묵"

mk_status "BL-999"; mk_lessons broken_pointer
AXIS="승격 표 포인터"
run ledger 1 yes '승격 표 `backend/AGENTS.md` 가 없음 → 승격 표 포인터 축 발화'

mk_status "BL-999"; mk_lessons live_pointers
run ledger 1 no "음성 대조: AGENTS.md 등 살아 있는 승격 표 포인터만 → 승격 표 포인터 축 침묵"

# ⑿ ★두 번째 음성 대조 — **과다 포획**. 이 축의 첫 판이 실제 `lessons.md` 에서 낸 오탐 3건이
#   그대로 입력이다. 「`/` 를 포함하거나 `.md` 로 끝난다」만으로 후보를 고르면 자리표시자·
#   코드 표현식·슬래시 커맨드가 전부 「없는 파일」이 된다. 오탐이 나오는 검사기는 꺼진다.
mk_status "BL-999"; mk_lessons nonpath_spans
run ledger 1 no "음성 대조: 자리표시자·코드 표현식·슬래시 커맨드 → 승격 표 포인터 축 침묵"

# ⒀⒁ ★적대 프로브가 **실제로 뚫은** 입력 2종(2026-08-14). 마크다운 장식 하나로 ID 정규식을
#   비껴가면 중복이 초록으로 샜다 — 이 축이 막으려는 사고의 서식만 바꾼 판이다.
#   ⑿ 와 같은 규율: **뚫린 입력을 그대로 케이스로 심는다.** 장식 허용을 되돌리면 여기가 red.
AXIS="LESSON ID 유일성"
mk_status "BL-999"; mk_lessons decorated_dup_table
run ledger 1 yes "적대 P1: 표 ID 볼드 | **LESSON-101** | + 같은 번호 카드 → 발화"

mk_status "BL-999"; mk_lessons decorated_dup_heading
run ledger 1 yes "적대 P2: 헤딩 링크 ### [LESSON-101](...) + 표 같은 번호 → 발화"
AXIS="⓪ 표 정체성"

# ── [BL-779] 다중 파일 원장 축 ────────────────────────────────────────
# ★원장이 `backlog.md` + `backlog-resolved.md` 둘로 갈렸다. 두 번째 파일을 안 읽는 파서는
#   **양방향으로 틀린다**: 있는 판정줄을 「0개」로 세어 위양성을 내고(⒂), 없는 것은 그대로
#   놓친다(⒃). 그래서 양성·음성을 한 쌍으로 둔다 — 한쪽만 두면 판별력이 아니라 편향이다.
rm -f "$SB/docs/lessons.md"   # 앞 케이스의 lessons fixture 가 이 축의 rc 를 흐리지 않게 한다
AXIS="트리거 판정 줄"

# ⒂ 음성 대조 — 판정줄이 **두 번째 원장에** 있다. 그 파일을 읽으면 침묵해야 한다.
mk_status "BL-999"; mk_resolved full
run resolved_verdict 1 no "음성 대조: DEFERRED BL-444 의 판정줄이 backlog-resolved.md 에 있다 → 침묵"

# ⒃ 양성 — 두 번째 원장의 섹션에 판정줄이 **없다**. 읽고 있다면 발화해야 한다.
mk_status "BL-999"; mk_resolved full
run resolved_noverdict 1 yes "DEFERRED BL-445 가 backlog-resolved.md 에서 판정줄 0개 → 발화"

# ⒄ 두 번째 원장이 **빈 파일** → 초록도 빨강도 아니라 rc=3 ABORT.
AXIS="판정 포기"
mk_status "BL-999"; mk_resolved empty
run ledger 3 yes "원장 반쪽이 빈 파일 → rc=3 ABORT (「위반 0건」으로 통과시키지 않는다)"

# ⒅ 정본(`bl-audit`)이 rc≠0 으로 죽었다 → 빈 stdout 을 공집합으로 읽지 않고 ABORT.
mk_status "BL-999"; mk_resolved full
run audit_dead 3 yes "bl-audit 이 rc=3 으로 죽음 → 빈 stdout 을 공집합으로 읽지 않는다"

# ⒆ 정본 **스크립트 자체가 없다** → 이것도 ABORT. 파일 부재와 rc≠0 은 같은 사건이다.
#   ★2026-08-16 적대 리뷰 P1: 종전 `if bl_audit.exists():` 는 부재 시 두 축을 통째로 건너뛰고
#     「✓ … are clean」을 찍었다 — 검사기가 사라진 것을 「위반 없음」으로 보고한 셈이다.
mk_status "BL-999"; mk_resolved full
mv "$SB/tools/scripts/bl-audit.sh" "$SB/bl-audit.sh.bak"
run ledger 3 yes "정본 스크립트 부재 → rc=3 ABORT (부재를 「위반 0건」으로 읽지 않는다)"
mv "$SB/bl-audit.sh.bak" "$SB/tools/scripts/bl-audit.sh"
AXIS="⓪ 표 정체성"

if [ "$FAIL" != 0 ]; then
  echo "✗ docs-audit 하네스 실패 — ⓪ 표 정체성 / 트리거 판정 줄 / BL-720 지식 정본 / 다중 파일 원장 축이 판별력을 잃었다"
  exit 1
fi
echo "✓ docs-audit 하네스 19/19 — ABORT · missing · extra · 양성 대조 · PARTIAL 도래/미도래 · PARTIAL 판정줄 누락 · LESSON ID · 승격 표 포인터 · 비경로 스팬 과다포획 · 장식 우회 2종 · 다중 파일 원장 5종"

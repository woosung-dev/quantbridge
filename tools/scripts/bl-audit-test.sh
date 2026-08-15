#!/usr/bin/env bash
# bl-audit 중복 검사 하네스 — BL-569. 전건 통과 = 종료 코드 0.
#
# 왜 필요한가
#   `bl-audit.sh` 의 중복 검사는 **원장이 깨끗하면 아무 일도 하지 않는다.** 지금 3면이 정합이므로
#   중복 탐지 로직을 통째로 지워도 게이트는 초록이다 — 즉 실제 사고(`### BL-566` 두 벌이 조용히
#   exit 0 을 유지)를 막는 코드인데 **되돌려도 아무도 못 잡는다.** 스프린트 안에서 1회 돌린 수동
#   증명은 그 자리에서만 살아 있고 회귀를 막지 못한다.
#
# ★두 검사를 **서로 구분해서** 단언한다. 이게 이 하네스의 핵심이다 —
#   중복 섹션 헤더는 두 섹션이 각자 상태줄을 하나씩 가지므로 **중복 상태줄 검사에 안 걸린다.**
#   그게 정확히 BL-566 이 통과한 이유다. 그래서 케이스마다 "떠야 할 마커" 와 함께
#   **"뜨면 안 되는 마커"** 도 단언한다. 한쪽 검사가 다른 쪽을 대신 잡아주는 것처럼 보이면 red 다.
#
# ★fixture 는 임시 트리에 만든다 — 실제 `docs/` 를 절대 건드리지 않는다.
#   `bl-audit.sh` 는 `dirname $0/..` 를 ROOT 로 잡고 `docs/{backlog,roadmap}.md` 를 읽으므로,
#   스크립트 사본을 `$TMP/tree/tools/scripts/` 에 두면 그 옆의 fixture 원장을 읽는다.
#
# ★종료 코드가 판정이므로 **파이프 없이** 읽는다 (`| tail` 이 $? 를 가린다 — 실측 사고 이력).
#
# 사용법: tools/scripts/bl-audit-test.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
AUDIT="$ROOT/tools/scripts/bl-audit.sh"
[ -f "$AUDIT" ] || { echo "✗ 감사 스크립트가 없다: $AUDIT" >&2; exit 1; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

PASS=0
FAIL=0
OUT=""
RC=0

run_fixture() { # stdin = backlog 본문  → $OUT / $RC
  rm -rf "$TMP/tree"
  mkdir -p "$TMP/tree/tools/scripts" "$TMP/tree/docs"
  cp "$AUDIT" "$TMP/tree/tools/scripts/bl-audit.sh"
  cat >"$TMP/tree/docs/backlog.md"
  : >"$TMP/tree/docs/roadmap.md" # 체크박스 없음 = 로드맵 축 중립
  # ★파이프 없음. 명령 치환의 종료 코드가 곧 스크립트의 종료 코드다.
  OUT="$(bash "$TMP/tree/tools/scripts/bl-audit.sh" 2>&1)"
  RC=$?
}

report() { # report <label> <why(빈 문자열이면 통과)>
  if [ -n "$2" ]; then
    FAIL=$((FAIL + 1))
    printf '  ✗ %-46s %s\n' "$1" "$2"
    printf '%s\n' "$OUT" | sed 's/^/        | /'
  else
    PASS=$((PASS + 1))
    printf '  ✓ %-46s\n' "$1"
  fi
}

# ★"없어야 할 마커" 는 반드시 `▶ ` 블록 머리로 줘라. 실패 요약 줄은 네 카운터를 **전부**
#   이름으로 나열하므로(`… 중복 섹션 헤더 0 건 …`), 블록 머리 없이 이름만 찾으면 0 건일 때도
#   매치돼 항상 red 가 된다 — 이 하네스를 처음 돌렸을 때 실제로 그렇게 오탐했다.
assert_case() { # assert_case <label> <기대 rc> <있어야 할 마커|-> <없어야 할 마커(▶ 블록 머리)|->
  local why=""
  [ "$RC" -eq "$2" ] || why="${why}종료코드=$RC(기대 $2) "
  if [ "$3" != "-" ] && ! printf '%s' "$OUT" | grep -q "$3"; then
    why="${why}'$3' 마커 없음 "
  fi
  if [ "$4" != "-" ] && printf '%s' "$OUT" | grep -q "$4"; then
    why="${why}★'$4' 가 잘못 발화(검사가 뒤섞였다) "
  fi
  report "$1" "$why"
}

echo "══ bl-audit 중복 검사 하네스  (임시 트리 fixture · 실제 스크립트 실행) ══"
echo "  대상: $AUDIT"
echo

# ── ① 중복 섹션 헤더 — 두 섹션이 **각자** 상태줄을 하나씩 갖는다(= BL-566 의 모양) ──────
run_fixture <<'EOF'
### BL-001

**우선순위:** P3
**상태:** 🔴 **열려 있다** — fixture 첫 벌.

---

### BL-001

**우선순위:** P3
**상태:** 🔴 **열려 있다** — fixture 두 번째 벌.

---
EOF
assert_case "① 중복 섹션 헤더 → exit 1" 1 "▶ 중복 섹션 헤더" "▶ 중복 상태 줄"

# ── ② 중복 없음 → 통과. 가드가 상시 red 면 판별력이 0 이다 ─────────────────────────
run_fixture <<'EOF'
### BL-001

**우선순위:** P3
**상태:** 🔴 **열려 있다** — fixture.

---

### BL-002

**우선순위:** P3
**상태:** ✅ **Resolved** (fixture)

---
EOF
assert_case "② 중복 없음 → exit 0" 0 "3면" "▶ 중복"

# ── ③ 한 섹션에 상태줄 2개 — BL-564 가 세운 기존 검사가 살아 있는지 ────────────────
run_fixture <<'EOF'
### BL-001

**우선순위:** P3
**상태:** 🔴 **열려 있다** — 첫 상태줄.
**상태:** ✅ **Resolved** — 폐기됐어야 할 둘째 상태줄.

---
EOF
assert_case "③ 중복 상태 줄 → exit 1" 1 "▶ 중복 상태 줄" "▶ 중복 섹션 헤더"

# ── ④ 중복 섹션 헤더의 줄번호가 **첫 벌**을 가리키는가 (G6 MINOR[B]) ────────────────
#   id 단일 키로 되돌리면 `첫:` 이 두 번째 섹션 줄로 밀린다.
run_fixture <<'EOF'
### BL-001

**우선순위:** P3
**상태:** 🔴 **열려 있다** — fixture 첫 벌 (헤더 :1).

---

### BL-001

**우선순위:** P3
**상태:** 🔴 **열려 있다** — fixture 두 번째 벌 (헤더 :8).

---
EOF
_why=""
printf '%s' "$OUT" | grep -q '첫:1  중복 :8' || _why="'첫:1  중복 :8' 이 아니다 "
report "④ 중복 헤더가 첫 벌 줄번호를 가리킨다" "$_why"

# ── ⑤ 중복 상태줄의 줄번호가 **그 섹션**을 가리키는가 (G6 MINOR[B] 본체) ───────────
#   같은 id 섹션이 둘이고 **앞** 섹션에만 상태줄이 2개다. `dup`/`sec_line` 이 id 키면
#   뒤 섹션(:9)이 앞 섹션(:1)의 줄번호를 덮어써 엉뚱한 자리를 가리킨다.
run_fixture <<'EOF'
### BL-001

**우선순위:** P3
**상태:** 🔴 **열려 있다** — 첫 상태줄.
**상태:** ✅ **Resolved** — 둘째 상태줄.

---

### BL-001

**우선순위:** P3
**상태:** 🔴 **열려 있다** — 뒤 섹션(상태줄 1개).

---
EOF
_why=""
[ "$RC" -eq 1 ] || _why="${_why}종료코드=$RC(기대 1) "
printf '%s' "$OUT" | grep -q '중복 상태 줄' || _why="${_why}'중복 상태 줄' 마커 없음 "
printf '%s' "$OUT" | grep -q '섹션:1' || _why="${_why}★중복 상태줄이 섹션:1 이 아니다(id 단일 키 회귀) "
report "⑤ 중복 상태줄이 그 섹션 줄번호를 가리킨다" "$_why"

# ── ⑥ 새 어휘 DEFERRED 가 ACTIVE 와 **따로** 세어진다 (BL-694 계열, 2026-08-10) ──────────
#   ★이 하네스의 존재 이유와 같은 계약이다 — "수동으로 한 번 돌려 봤다" 는 회귀를 못 막는다.
#   ★카운트 줄을 재므로 `assert_case`(마커 1+1) 대신 커스텀 `_why` 를 쓴다.
run_fixture <<'EOF'
### BL-001

**우선순위:** P3
**상태:** ⏳ **대기 (트리거 미도래)** — 실자금 cutover 전.

---

### BL-002

**우선순위:** P3
**상태:** ⬜ Open — 지금 착수 가능.

---
EOF
_why=""
[ "$RC" -eq 0 ] || _why="${_why}종료코드=$RC(기대 0) "
printf '%s' "$OUT" | grep -qE '^  DEFERRED +1$' || _why="${_why}★'DEFERRED 1' 이 아니다(어휘 미신설/오분류) "
printf '%s' "$OUT" | grep -qE '^  ACTIVE +1$' || _why="${_why}★'ACTIVE 1' 이 아니다(DEFERRED 가 ACTIVE 로 샜다) "
report "⑥ DEFERRED 가 ACTIVE 와 따로 세어진다" "$_why"

# ── ⑦ 음성 대조 — 새 어휘가 **모든 것을 삼키지 않는다** ────────────────────────────
#   ⑥ 만 있으면 `verdict_of` 가 무조건 DEFERRED 를 반환해도 통과한다. 판별력이 0인 가드는
#   가드가 아니다 — ② 가 중복 검사에 대해 하는 일을 여기서 어휘에 대해 한다.
run_fixture <<'EOF'
### BL-001

**우선순위:** P3
**상태:** ⬜ Open — 지금 착수 가능.

---

### BL-002

**우선순위:** P3
**상태:** ✅ **Resolved** (fixture)

---
EOF
_why=""
[ "$RC" -eq 0 ] || _why="${_why}종료코드=$RC(기대 0) "
printf '%s' "$OUT" | grep -qE '^  DEFERRED +0$' || _why="${_why}★'DEFERRED 0' 이 아니다(어휘가 무관한 항목을 삼킨다) "
printf '%s' "$OUT" | grep -qE '^  ACTIVE +1$' || _why="${_why}'ACTIVE 1' 이 아니다 "
report "⑦ 음성 대조 — DEFERRED 가 남을 삼키지 않는다" "$_why"

# ── ⑧ DEFERRED 는 3면에서 **ACTIVE 와 같은 「미완」 쪽**이다 ────────────────────────
#   인덱스 표 행에 ✅ 가 있으면 불일치. 이걸 안 걸면 새 어휘가 crosscheck 를 **끄는** 통로가 된다
#   (지금은 ⏳ 가 UNKNOWN 이라 `if (v == "UNKNOWN") continue` 로 조용히 빠져나간다).
run_fixture <<'EOF'
## P3

| ID                  | 제목        |
| ------------------- | ----------- |
| [BL-001](#bl-001)   | ✅ fixture  |

### BL-001

**우선순위:** P3
**상태:** ⏳ **대기 (트리거 미도래)** — Beta 배포 후.

---
EOF
#   ★`▶ 불일치` 를 마커로 쓰면 **항상 통과한다** — 그 블록 머리는 "없음" 일 때도 찍힌다
#     (이 파일 59-61 이 경고한 그 함정에 이 케이스가 실제로 한 번 빠졌다). 본문 문장을 재라.
_why=""
[ "$RC" -eq 1 ] || _why="${_why}종료코드=$RC(기대 1) "
printf '%s' "$OUT" | grep -q '섹션은 DEFERRED' || _why="${_why}★불일치 본문에 '섹션은 DEFERRED' 없음(crosscheck 가 새 어휘를 건너뛴다) "
printf '%s' "$OUT" | grep -qE '^  UNKNOWN +0$' || _why="${_why}★UNKNOWN 이 0 이 아니다(어휘 미해석으로 exit 1 이 난 것뿐이다) "
printf '%s' "$OUT" | grep -q '▶ 중복' && _why="${_why}★'▶ 중복' 이 잘못 발화 "
report "⑧ DEFERRED + 표 행 ✅ → 불일치 exit 1" "$_why"

# ── ⑨ 트리거 정합 — `트리거 판정: 미도래` 인데 상태줄이 ACTIVE (BL-725, 2026-08-15) ──────
#   감사기는 상태줄만 SSOT 로 읽으므로, 본문에 「트리거도 미도래」를 적어 놓고 리드인만
#   `⬜ Open` 인 섹션이 **조용히 ACTIVE 로 세졌다**. ⓪ 표가 그걸 후보로 올리고 열어 보면 할 일이 없다.
run_fixture <<'EOF'
### BL-001

**우선순위:** P3
**상태:** ⬜ Open — 미착수.
**트리거 판정:** 미도래 — 동승 조건. 단독 착수 시 값이 0이다

---
EOF
_why=""
[ "$RC" -eq 1 ] || _why="${_why}종료코드=$RC(기대 1) "
printf '%s' "$OUT" | grep -q '트리거는 미도래인데 상태줄이 ACTIVE' || _why="${_why}★트리거 정합 축이 발화하지 않았다 "
printf '%s' "$OUT" | grep -q '▶ 중복' && _why="${_why}★'▶ 중복' 이 잘못 발화 "
report "⑨ 트리거 미도래 + 상태줄 Open → exit 1" "$_why"

# ── ⑩ 음성 대조 — 트리거 축이 **모든 것을 삼키지 않는다** ──────────────────────────
#   두 축을 한 fixture 에서 동시에 잰다:
#   ⒜ 정합(미도래 + ⏳ 대기)은 통과해야 한다 — 안 그러면 원장 164 섹션이 전부 red 다.
#   ⒝ ★**취소선 친 미도래는 미도래가 아니다** — 이 레포에서 `~~` 는 철회 표기다([BL-547] 이 그 판:
#      `**트리거 판정:** ~~미도래 …~~` + `⬜ Open` 이 정합이다). 이걸 삼키면 **도래한 항목이
#      DEFERRED 로 몰려 원장이 조용히 얼어붙는다.**
run_fixture <<'EOF'
### BL-001

**우선순위:** P3
**상태:** ⏳ **대기 (트리거 미도래)** — 동승 조건.
**트리거 판정:** 미도래 — 동승 조건

---

### BL-002

**우선순위:** P3
**상태:** ⬜ Open — 지금 착수 가능.
**트리거 판정:** ~~미도래 — 외생 조건~~ 2026-08-11 에 도래했다

---
EOF
_why=""
[ "$RC" -eq 0 ] || _why="${_why}종료코드=$RC(기대 0) "
printf '%s' "$OUT" | grep -q '▶ 트리거 정합' && _why="${_why}★트리거 축이 정합/철회 항목을 잘못 잡았다 "
printf '%s' "$OUT" | grep -qE '^  ACTIVE +1$' || _why="${_why}'ACTIVE 1' 이 아니다(취소선 항목이 DEFERRED 로 삼켜졌다) "
printf '%s' "$OUT" | grep -qE '^  DEFERRED +1$' || _why="${_why}'DEFERRED 1' 이 아니다 "
report "⑩ 음성 대조 — 정합·취소선을 삼키지 않는다" "$_why"

# ── ⑪ 중복 트리거 판정 줄 = 이 축의 우회 경로 (2026-08-15 codex P1) ────────────────
#   판정은 **첫 줄**로 하므로, 뒤에 `미도래` 를 한 줄 더 적으면 ⑨ 가 통째로 무력해진다.
#   상태줄(③)과 같은 계약으로 SSOT 를 하나로 강제한다.
run_fixture <<'EOF'
### BL-001

**우선순위:** P3
**상태:** ⬜ Open — 미착수.
**트리거 판정:** 도래 — 지금 착수 가능
**트리거 판정:** 미도래 — 동승 조건

---
EOF
_why=""
[ "$RC" -eq 1 ] || _why="${_why}종료코드=$RC(기대 1) — 둘째 줄이 조용히 무시됐다 "
printf '%s' "$OUT" | grep -q '▶ 중복 트리거 판정 줄' || _why="${_why}★중복 트리거줄 축이 발화하지 않았다 "
report "⑪ 중복 트리거 판정 줄 → exit 1" "$_why"

echo
printf '══ 통과 %d / 실패 %d ══\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0

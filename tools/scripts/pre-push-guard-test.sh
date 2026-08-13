#!/usr/bin/env bash
# pre-push ref 가드 하네스 — BL-554 · BL-555. 전건 통과 = 종료 코드 0.
#
# 왜 필요한가
#   `.husky/pre-push` 는 **메인 워크트리에서만** 판정 분기를 탄다(git_dir == git_common_dir).
#   워커 워크트리에서 훅을 그대로 실행하면 else 가지로 빠져 **판정 로직이 아예 안 돈다** —
#   그래서 "고쳤다" 를 증명할 수 없다. 여기서는 훅에 `--qb-selftest` 를 3 번째 인자로 줘서
#   (a) 그 분기를 강제로 타게 하고 (b) ref 가드 직후 멈추게 한다.
#
# ★주 시험은 **훅 스크립트를 실제로 실행**하고 stdin 을 파이프한다.
#   순수 함수만 시험하면 호출부를 다시 `git symbolic-ref HEAD` 기준으로 되돌리는 변이를 못 잡는다 —
#   함수는 그대로라 green 이다. 그래서 케이스마다 **종료 코드 + 출력 마커**를 함께 단언한다:
#     ref 경로  → `ref 판정` 을 찍는다
#     폴백 경로 → `폴백` 을 찍는다
#   판정 주체가 뒤바뀌면 마커가 어긋나 red 다. 이 단언은 **현재 브랜치 이름과 무관**하다.
#
# ★task 원문의 삭제 케이스는 "현재 브랜치 = main" 이다. 하네스는 브랜치를 바꾸지 않는다(그럴 권한이
#   없고, 그러면 그 자체가 부작용이다). 대신 위 마커 단언이 그 자리를 메운다 — 폴백으로 빠지는 순간
#   red 이므로, 현재 브랜치가 무엇이든 "삭제를 현재 브랜치로 판정하는 회귀" 를 잡는다.
#
# 사용법: tools/scripts/pre-push-guard-test.sh

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
HOOK="$ROOT/.husky/pre-push"
LIB="$ROOT/tools/scripts/lib/pre-push-ref-guard.sh"
[ -f "$HOOK" ] || { echo "✗ 훅이 없다: $HOOK" >&2; exit 1; }
[ -f "$LIB" ]  || { echo "✗ 판정 lib 이 없다: $LIB" >&2; exit 1; }

Z40="0000000000000000000000000000000000000000"
S1="1111111111111111111111111111111111111111"
S2="2222222222222222222222222222222222222222"

PASS=0; FAIL=0
OUT=""; RC=0

run_hook() {  # run_hook <bypass 0|1> <stdin 문자열>   → $OUT / $RC
  OUT="$(printf '%s' "$2" | QB_PRE_PUSH_BYPASS="$1" \
    sh "$HOOK" origin "https://example.invalid/qb.git" --qb-selftest 2>&1)"
  RC=$?
}

run_hook_no_stdin() {  # stdin 자체가 없는 경로 (③-c)
  OUT="$(QB_PRE_PUSH_BYPASS="$1" \
    sh "$HOOK" origin "https://example.invalid/qb.git" --qb-selftest </dev/null 2>&1)"
  RC=$?
}

report() {  # report <label> <why(빈 문자열이면 통과)>
  if [ -n "$2" ]; then
    FAIL=$((FAIL + 1))
    printf '  ✗ %-52s %s\n' "$1" "$2"
    printf '%s\n' "$OUT" | sed 's/^/        | /'
  else
    PASS=$((PASS + 1))
    printf '  ✓ %-52s\n' "$1"
  fi
}

assert_hook() {  # assert_hook <label> <allow|deny> <ref|fallback> <bypass> <stdin>
  run_hook "$4" "$5"
  local why=""
  if [ "$2" = "allow" ]; then
    [ "$RC" -eq 0 ] || why="${why}종료코드=$RC(허용 기대) "
  else
    [ "$RC" -ne 0 ] || why="${why}종료코드=0(차단 기대) "
  fi
  if [ "$3" = "ref" ]; then
    printf '%s' "$OUT" | grep -q 'ref 판정' || why="${why}'ref 판정' 마커 없음 "
    if printf '%s' "$OUT" | grep -q '폴백'; then why="${why}★폴백 경로로 빠졌다(현재 브랜치 판정) "; fi
  else
    printf '%s' "$OUT" | grep -q '폴백' || why="${why}'폴백' 마커 없음 "
  fi
  report "$1" "$why"
}

echo "══ pre-push ref 가드 하네스  (훅 실제 실행 + stdin 파이프) ══"
echo "  현재 브랜치: $(git -C "$ROOT" symbolic-ref --short HEAD 2>/dev/null || echo unknown)"
echo

# ── 훅 실행 케이스 (⑤-b · ⑤-c′) ───────────────────────────────────────────────
assert_hook "① main 갱신" \
  deny ref 0 "refs/heads/main $S1 refs/heads/main $S2"

assert_hook "①' main 갱신 + BYPASS=1 (bypass 불가)" \
  deny ref 1 "refs/heads/main $S1 refs/heads/main $S2"

assert_hook "② stage/foo 갱신 (BL-555)" \
  allow ref 0 "refs/heads/stage/foo $S1 refs/heads/stage/foo $S2"

assert_hook "③ feat/foo 갱신 (기존 동작 불변)" \
  allow ref 0 "refs/heads/feat/foo $S1 refs/heads/feat/foo $S2"

assert_hook "④ stage/foo 삭제 (BL-554 본체)" \
  allow ref 0 "(delete) $Z40 refs/heads/stage/foo $S2"

assert_hook "⑤ main 삭제" \
  deny ref 0 "(delete) $Z40 refs/heads/main $S2"

assert_hook "⑥ 임의 wip-xyz 갱신, bypass 없음" \
  deny ref 0 "refs/heads/wip-xyz $S1 refs/heads/wip-xyz $S2"

assert_hook "⑦ 임의 wip-xyz 갱신, BYPASS=1 (기존 동작 불변)" \
  allow ref 1 "refs/heads/wip-xyz $S1 refs/heads/wip-xyz $S2"

assert_hook "⑧ feat/foo → main 교차 refspec + BYPASS=1" \
  deny ref 1 "refs/heads/feat/foo $S1 refs/heads/main $S2"

assert_hook "⑨ 다중 라인 (stage/x 갱신 + main 갱신)" \
  deny ref 0 "refs/heads/stage/x $S1 refs/heads/stage/x $S2
refs/heads/main $S1 refs/heads/main $S2"

# R1-④ 태그 — 릴리스 태깅이 조용히 막히던 회귀. 정책 근거는 lib 의 qb_ref_is_tag_ref 주석.
assert_hook "⑨-a 태그 갱신 (git push origin v1.2.3)" \
  allow ref 0 "refs/tags/v1.2.3 $S1 refs/tags/v1.2.3 $Z40"

assert_hook "⑨-b 태그 삭제 (git push origin --delete v1.2.3)" \
  allow ref 0 "(delete) $Z40 refs/tags/v1.2.3 $S2"

# 한쪽만 태그면 태그 규칙을 주지 않는다 — 교차 refspec 으로 규칙을 골라 타지 못하게.
assert_hook "⑨-c 브랜치 → 태그 교차 refspec, bypass 없음" \
  deny ref 0 "refs/heads/feat/foo $S1 refs/tags/v9 $Z40"

# stdin 없음 → 폴백. fail-open 이 아닌지(= 통과 도장을 찍지 않는지)까지 본다.
run_hook_no_stdin 0
_why=""
printf '%s' "$OUT" | grep -q '폴백' || _why="${_why}'폴백' 마커 없음 "
printf '%s' "$OUT" | grep -q 'ref 판정' && _why="${_why}ref 경로로 갔다 "
_br="$(git -C "$ROOT" symbolic-ref --short HEAD 2>/dev/null || echo unknown)"
case "$_br" in
  stage/*|feat/*|fix/*|chore/*|docs/*|test/*|refactor/*|hotfix/*)
    # 화이트리스트 브랜치에서 돌리면 폴백이 허용하는 것이 정상이다.
    [ "$RC" -eq 0 ] || _why="${_why}종료코드=$RC (화이트리스트 브랜치 $_br 는 폴백에서 허용 기대) " ;;
  *)
    [ "$RC" -ne 0 ] || _why="${_why}종료코드=0 (비화이트리스트 $_br 는 폴백에서 차단 기대 = fail-open 금지) " ;;
esac
report "⑩ stdin 없음 → 현재 브랜치 폴백 ($_br)" "$_why"

# fd 0 이 **닫힌** 채 호출되는 경로. `cat` 이 에러로 끝나지 않고 무한 대기한다(실측 2 분 hang) —
# 훅이 매달리는 것 자체가 사고이므로 fail-closed 로 끊는지 본다.
if command -v timeout >/dev/null 2>&1; then
  OUT="$(timeout 15 sh "$HOOK" origin "https://example.invalid/qb.git" --qb-selftest 0<&- 2>&1)"; RC=$?
  _why=""
  [ "$RC" -eq 1 ] || _why="${_why}종료코드=$RC (1 기대 — 124 면 여전히 hang 이다) "
  printf '%s' "$OUT" | grep -q 'fd 0' || _why="${_why}fd 0 진단 메시지 없음 "
  report "⑪ fd 0 닫힘 → hang 없이 fail-closed" "$_why"
else
  echo "  – ⑪ fd 0 닫힘 케이스 건너뜀 (timeout 커맨드 없음 — hang 을 안전하게 잴 수 없다)"
fi

# 판정 규칙 파일이 없으면 통과시키지 않는지 (fail-closed). 임시 레포에서 훅만 떼어 돌린다.
_tmp="$(mktemp -d)"
git init -q "$_tmp" 2>/dev/null
mkdir -p "$_tmp/.husky"
cp "$HOOK" "$_tmp/.husky/pre-push"
OUT="$(cd "$_tmp" && printf 'refs/heads/feat/x %s refs/heads/feat/x %s\n' "$S1" "$S2" \
  | sh .husky/pre-push origin "https://example.invalid/qb.git" --qb-selftest 2>&1)"; RC=$?
_why=""
[ "$RC" -ne 0 ] || _why="${_why}종료코드=0 (판정 규칙 없이 통과했다 = fail-open) "
printf '%s' "$OUT" | grep -q '판정 규칙 파일이 없다' || _why="${_why}진단 메시지 없음 "
report "⑫ 판정 lib 부재 → fail-closed" "$_why"
rm -rf "$_tmp"

# ── 보조: 순수 함수 단독 (⑤-a) ────────────────────────────────────────────────
# ★보조다. 이것만으로는 호출부 회귀를 못 잡는다 (위 마커 단언이 그 몫이다).
# shellcheck source=tools/scripts/lib/pre-push-ref-guard.sh
. "$LIB"

assert_verdict() {  # assert_verdict <기대> <local_ref> <local_sha> <remote_ref> <remote_sha> [bypass]
  local want="$1"; shift
  local got; got="$(qb_push_ref_verdict "$1" "$2" "$3" "$4" "${5:-0}")"
  OUT="qb_push_ref_verdict $1 ${2:0:8}.. $3 ${4:0:8}.. ${5:-0} → $got"
  local why=""
  [ "$got" = "$want" ] || why="기대=$want 실측=$got"
  report "순수: $1 → $3 (bypass=${5:-0}) = $want" "$why"
}

echo
assert_verdict deny-main       "refs/heads/main" "$S1" "refs/heads/main" "$S2" 1
assert_verdict deny-main       "refs/heads/feat/foo" "$S1" "refs/heads/main" "$S2" 1
assert_verdict allow-delete    "(delete)" "$Z40" "refs/heads/stage/foo" "$S2" 0
assert_verdict allow-whitelist "refs/heads/stage/foo" "$S1" "refs/heads/stage/foo" "$S2" 0
# 교차 refspec — 화이트리스트 local 로 임의 원격 ref 를 만들 수 없다 (codex G1 P1).
assert_verdict deny-arbitrary  "refs/heads/feat/foo" "$S1" "refs/heads/wip-x" "$S2" 0
# R1-④ 태그 정책 — 갱신·삭제 허용, 교차 refspec 은 태그 규칙을 안 준다.
assert_verdict allow-tag        "refs/tags/v1" "$S1" "refs/tags/v1" "$Z40" 0
assert_verdict allow-tag-delete "(delete)" "$Z40" "refs/tags/v1" "$S2" 0
assert_verdict deny-arbitrary   "refs/heads/feat/foo" "$S1" "refs/tags/v1" "$Z40" 0
# 태그 규칙이 main 보호를 앞지르지 않는지 — refs/tags 가 아닌 main 은 그대로 차단.
assert_verdict deny-main        "refs/tags/v1" "$S1" "refs/heads/main" "$S2" 1
# 짧은 0 sha 를 삭제로 인정하지 않는다 = fail-closed (codex G1 P2).
assert_verdict deny-arbitrary  "refs/heads/wip" "0" "refs/heads/stage/foo" "$S2" 0

echo
echo "══════════════════════════════════════════"
printf '  통과 %d · 실패 %d\n' "$PASS" "$FAIL"
echo "══════════════════════════════════════════"
[ "$FAIL" -eq 0 ] || exit 1
echo "✓ 전건 통과"

#!/usr/bin/env bash
# final-gates 모드 디스패치 판별력 하네스 — 전건 통과 = 종료 코드 0.
#
# 무엇을 재는가 — **어느 모드가 어느 게이트를 도는가**, 그 하나다.
#   `final-gates.sh` 는 전량 1회가 15~20분이라 하네스가 실물을 돌릴 수 없다. 그래서
#   `--dry-run`(아무 게이트도 실행하지 않고 계획만 표로 낸다)을 판정 표면으로 쓴다.
#   dry-run 이 없었으면 이 계약은 **검사할 방법이 없었다** — 그래서 플래그가 먼저 생겼다.
#
# ★★정직한 한계 (이 하네스가 **안** 재는 것 — 다음 사람이 이 줄을 믿고 넘어가지 마라):
#   ⑴ 유예 원장 파일(`deferred.txt`)의 기록·해제는 **실제 통과 실행**에서만 일어나므로 여기서
#      안 잰다. 2026-08-14 에 손으로 1회 확인했다(pre-pr 이 쓰고 deferred-only 가 지운다).
#   ⑵ 각 게이트의 **내용**(pytest 가 무엇을 도는가)은 이 파일의 대상이 아니다. 여기서 재는 것은
#      「돌기로 되어 있는가」까지다.
#   ⑶ dry-run 은 더러운 트리에서도 돈다(아무것도 실행하지 않으므로 BL-549 의 거짓 그린이
#      성립하지 않는다). 그 예외 자체를 케이스 ⑦ 이 고정한다.
#
# ★모드가 갈리는 지점은 `mode_runs()` 하나다. 변이 M1~M3 이 그 함수와 `DEFERRABLE` 목록을
#   각각 무력화해 **케이스가 실제로 그것을 보고 있는지** 증명한다.

set -uo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
GATES="$ROOT/tools/scripts/final-gates.sh"
TMP="$(mktemp -d)"
# ★변이 사본은 **레포 안**(`tools/scripts/`)에 둬야 한다. `final-gates.sh` 는
#   `ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"` 로 자기 위치에서 레포 루트를 구하므로,
#   `$TMP` 에 복사하면 ROOT 가 엉뚱한 곳을 가리켜 **git status 에서 죽는다**.
#   그러면 변이가 무엇이든 케이스가 전부 같은 이유로 red 가 되고 — 초판이 정확히 그랬다 —
#   「변이 3종 전건 판별」이라는 **거짓 보고**가 나온다. 그것을 잡은 것은 음성 대조 N1 이다.
MUTDIR="$ROOT/tools/scripts"
trap 'rm -rf "$TMP"; rm -f "$MUTDIR"/.fg-mutant-*.sh' EXIT

FAIL=0
RED_IDS=""
TARGET="$GATES"   # 변이 실행 시 사본으로 바뀐다

echo "══ final-gates 모드 하네스 ══"
echo "  대상: ${GATES#$ROOT/}"
echo

# 계획 표에서 특정 마크의 줄 수를 센다. 마크 = plan / DEFER / skip
plan_count() { # plan_count <mark> <mode-args...>
  local mark="$1"; shift
  bash "$TARGET" --run harness-probe --dry-run "$@" 2>&1 |
    grep -cE "^  ${mark} " || true
}

# 계획 표에서 특정 게이트가 어떤 마크를 받았는지
# ★**결과표 줄만** 본다. 진행 출력에도 같은 라벨이 `▶ BE pytest` 로 먼저 나오므로, 그것까지
#   훑으면 마크 자리에 `▶` 가 잡힌다 — 하네스 초판이 정확히 그래서 ⑤⑥ 이 red 였다.
mark_of() { # mark_of <gate-label> <mode-args...>
  local label="$1"; shift
  bash "$TARGET" --run harness-probe --dry-run "$@" 2>&1 |
    grep -E "^  (plan|DEFER|skip|PASS|FAIL) " |
    awk -v l="$label" 'index($0, l) {print $1; exit}'
}

report() { # report <번호> <라벨> <why(빈 문자열이면 통과)>
  if [ -n "$3" ]; then
    FAIL=$((FAIL + 1)); RED_IDS="${RED_IDS}$1"
    printf "  ✗ %s %s\n        | %s\n" "$1" "$2" "$3"
  else
    printf "  ✓ %s %s\n" "$1" "$2"
  fi
}

run_suite() { # 케이스 8건
  local why full_plan pre_plan pre_defer def_plan def_skip m

  # ① full 모드는 아무것도 유예하지 않는다
  why=""
  full_plan="$(plan_count plan)"
  [ "$(plan_count DEFER)" = "0" ] || why="full 모드가 유예했다 ($(plan_count DEFER)건)"
  [ "${full_plan:-0}" -ge 20 ] || why="${why}${why:+ · }full 계획이 ${full_plan}건뿐이다 (≥20 기대)"
  report "①" "full — 유예 0 · 계획 ${full_plan}건" "$why"

  # ② --pre-pr 은 유예한다
  why=""
  pre_plan="$(plan_count plan --pre-pr)"; pre_defer="$(plan_count DEFER --pre-pr)"
  [ "${pre_defer:-0}" -gt 0 ] || why="--pre-pr 이 아무것도 유예하지 않았다"
  [ "${pre_plan:-0}" -lt "${full_plan:-0}" ] || why="${why}${why:+ · }--pre-pr 계획이 full 보다 적지 않다 ($pre_plan vs $full_plan)"
  report "②" "--pre-pr — 유예 ${pre_defer}건 · 계획 ${pre_plan}건" "$why"

  # ③ --deferred-only 는 유예분만 돈다
  why=""
  def_plan="$(plan_count plan --deferred-only)"; def_skip="$(plan_count skip --deferred-only)"
  [ "${def_plan:-0}" = "${pre_defer:-x}" ] || why="deferred-only 계획($def_plan) ≠ pre-pr 유예($pre_defer)"
  [ "${def_skip:-0}" -gt "${def_plan:-0}" ] || why="${why}${why:+ · }deferred-only 가 건너뛴 것이 도는 것보다 적다"
  report "③" "--deferred-only — 계획 ${def_plan}건 = pre-pr 유예분" "$why"

  # ④ ★분할이 상보적이다 — 두 모드를 합치면 full 이 된다 (어느 쪽에도 안 드는 게이트가 없다)
  why=""
  [ $(( ${pre_plan:-0} + ${def_plan:-0} )) = "${full_plan:-0}" ] ||
    why="pre-pr($pre_plan) + deferred-only($def_plan) ≠ full($full_plan) — 사라지거나 겹친 게이트가 있다"
  report "④" "분할 상보성 pre-pr + deferred-only == full" "$why"

  # ⑤ 무거운 게이트는 --pre-pr 에서 유예된다 (대표 2종)
  why=""
  for m in "BE pytest" "e2e authed"; do
    [ "$(mark_of "$m" --pre-pr)" = "DEFER" ] || why="${why}${why:+ · }'$m' 가 --pre-pr 에서 유예되지 않았다"
  done
  report "⑤" "BE pytest · e2e authed 는 --pre-pr 에서 DEFER" "$why"

  # ⑥ 싼 게이트는 --pre-pr 에서도 돈다 (대표 2종)
  why=""
  for m in "BE ruff" "FE build"; do
    [ "$(mark_of "$m" --pre-pr)" = "plan" ] || why="${why}${why:+ · }'$m' 가 --pre-pr 에서 안 돈다"
  done
  report "⑥" "BE ruff · FE build 는 --pre-pr 에서도 돈다" "$why"

  # ⑦ dry-run 은 아무 게이트도 실행하지 않는다 (더러운 트리에서도 계획을 낸다)
  why=""
  local out; out="$(bash "$TARGET" --run harness-probe --dry-run 2>&1)"
  case "$out" in *"→ exit="*) why="dry-run 인데 게이트가 실제로 돌았다 (exit= 줄이 있다)" ;; esac
  case "$out" in *"아무 게이트도 돌지 않았다"*) : ;; *) why="${why}${why:+ · }dry-run 종결 문구가 없다" ;; esac
  report "⑦" "--dry-run — 실행 0 · 계획만" "$why"

  # ⑧ 모드는 상호 배타 · 미상 플래그는 거부
  why=""
  bash "$TARGET" --run harness-probe --pre-pr --deferred-only >/dev/null 2>&1 && why="두 모드를 함께 받았다"
  bash "$TARGET" --run harness-probe --no-such-flag >/dev/null 2>&1 && why="${why}${why:+ · }미상 플래그를 받았다"
  report "⑧" "모드 배타 · 미상 플래그 거부" "$why"
}

run_suite
echo
echo "  케이스: $((8 - FAIL))/8 통과, ${FAIL} 실패"

# ── 변이 — 케이스가 실제로 모드 디스패치를 보고 있는지 증명한다 ────────────────
if [ "${1:-}" = "--mutants" ]; then
  echo
  echo "── 변이 M1~M3 (사본 주입 · 케이스 8건 전량 재실행) ──"
  BASE_RED="$RED_IDS"
  MUT_FAIL=0

  mutate() { # mutate <id> <old> <new> <기대 red 부분집합>
    local id="$1" old="$2" new="$3" expect="$4"
    python3 - "$GATES" "$MUTDIR/.fg-mutant-$id.sh" "$old" "$new" <<'PY'
import sys
src, dst, old, new = sys.argv[1:5]
s = open(src, encoding="utf-8").read()
if old not in s:
    sys.stderr.write("✗ 변이 앵커를 못 찾았다: %r\n" % old)
    sys.exit(9)
open(dst, "w", encoding="utf-8").write(s.replace(old, new, 1))
PY
    if [ $? -ne 0 ]; then
      printf "  ✗ %s → 앵커 소실 (하네스가 낡았다)\n" "$id"; MUT_FAIL=$((MUT_FAIL + 1)); return
    fi
    TARGET="$MUTDIR/.fg-mutant-$id.sh"; FAIL=0; RED_IDS=""
    run_suite >/dev/null 2>&1
    TARGET="$GATES"
    if [ -z "$RED_IDS" ]; then
      printf "  ✗ %s → red 0건 (변이가 잡히지 않았다 = 케이스가 이 축을 안 본다)\n" "$id"
      MUT_FAIL=$((MUT_FAIL + 1))
    else
      printf "  ✓ %s → red [%s] (기대 %s 포함)\n" "$id" "$RED_IDS" "$expect"
      case "$RED_IDS" in *"$expect"*) : ;; *)
        printf "        | 기대 %s 가 red 집합에 없다\n" "$expect"; MUT_FAIL=$((MUT_FAIL + 1)) ;;
      esac
    fi
  }

  # M1 — mode_runs 가 언제나 「돈다」 ⇒ 유예가 사라진다
  mutate M1 '    pre-pr)        is_deferrable "$1" && return 1 || return 0 ;;' \
             '    pre-pr)        return 0 ;;' "②"
  # M2 — deferred-only 가 전부 돈다 ⇒ 분할이 깨진다
  mutate M2 '    deferred-only) is_deferrable "$1" && return 0 || return 1 ;;' \
             '    deferred-only) return 0 ;;' "③"
  # M3 — 유예 목록이 비면 --pre-pr 이 아무것도 안 미룬다
  mutate M3 'DEFERRABLE="BE pytest|e2e chromium' 'DEFERRABLE="__none__|e2e chromium' "⑤"

  # ★음성 대조 — 주석만 바꾼 사본은 red 0건이어야 한다 (변이 엔진 자체가 red 를 만들지 않는다)
  echo
  mutate_neutral() {
    sed 's/^# final-gates 모드 디스패치 판별력.*/# (음성 대조 주석)/' "$GATES" > "$MUTDIR/.fg-mutant-N1.sh"
    TARGET="$MUTDIR/.fg-mutant-N1.sh"; FAIL=0; RED_IDS=""
    run_suite >/dev/null 2>&1
    TARGET="$GATES"
    if [ -n "$RED_IDS" ]; then
      printf "  ✗ N1 → red [%s] (등가 사본인데 red 가 났다)\n" "$RED_IDS"; MUT_FAIL=$((MUT_FAIL + 1))
    else
      printf "  ✓ N1 → red 0건 (등가 확인)\n"
    fi
  }
  mutate_neutral

  echo
  if [ "$MUT_FAIL" -gt 0 ]; then
    echo "✗ 변이 ${MUT_FAIL}건 미판별 — 케이스가 모드 디스패치를 못 보고 있다"; exit 1
  fi
  echo "✓ 변이 3종 + 음성 대조 1종 전건 판별"
  FAIL=0; RED_IDS="$BASE_RED"
  [ -n "$BASE_RED" ] && FAIL=1
fi

echo
if [ "$FAIL" -gt 0 ]; then echo "✗ 실패 [$RED_IDS]"; exit 1; fi
echo "✓ 전건 통과"

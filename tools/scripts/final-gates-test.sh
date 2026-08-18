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
# ★M4·M5 는 모드 축이 아니라 **신호의 required 술어**를 지킨다([BL-739], 2026-08-15) — 케이스 ⑩
#   이 자기 변이 없이 들어오지 않게 함께 신설했다.
# ★M6 은 하네스 전용 영역 주입 훅을 지켜 ⑩의 합성 음성·양성 대조를 환경 독립으로 만든다([BL-780]).

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
# ★케이스 ⑩ 이 `apps/api/src` 에 탐침 파일을 잠깐 만든다 — 죽어도 남지 않게 여기서 지운다.
PROBE_SRC="$ROOT/apps/api/src/__fg_harness_probe__.py"
trap 'rm -rf "$TMP"; rm -f "$MUTDIR"/.fg-mutant-*.sh "$PROBE_SRC"' EXIT

FAIL=0
RED_IDS=""
# ★케이스 수는 **센다**. 종전에는 종결 줄이 `10/10` 을 하드코딩했는데 `report` 호출은 이미
#   11건이라 인쇄가 낡아 있었다(2026-08-18 발견). rc 는 `FAIL`/`RED_IDS` 가 정하므로 판정은
#   틀리지 않았지만, 사람이 읽는 수가 거짓이면 케이스가 하나 사라져도 눈치채지 못한다.
CASES=0
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

# 계획 표에서 그 게이트의 **사유 문자열**을 꺼낸다 (마크 열은 버린다).
# ★신호 게이트의 required 는 dry-run 사유에만 드러난다 — 그 노출이 [BL-739] 수리의 일부다.
signal_note() { # signal_note <label 조각> <mode-args...>
  local label="$1"; shift
  bash "$TARGET" --run harness-probe --dry-run "$@" 2>&1 |
    grep -E "^  (plan|DEFER|skip|PASS|FAIL) " |
    awk -v l="$label" 'index($0, l) { sub(/^ +[A-Za-z]+ +/, ""); print; exit }'
}

# 영역을 합성으로 주입해 '화면 검증' 행의 사유를 읽는다 ([BL-780]).
screen_note_fake() { QB_FG_FAKE_CHANGED="$1" signal_note '화면 검증'; }

report() { # report <번호> <라벨> <why(빈 문자열이면 통과)>
  CASES=$((CASES + 1))
  if [ -n "$3" ]; then
    FAIL=$((FAIL + 1)); RED_IDS="${RED_IDS}$1"
    printf "  ✗ %s %s\n        | %s\n" "$1" "$2" "$3"
  else
    printf "  ✓ %s %s\n" "$1" "$2"
  fi
}

run_suite() { # 케이스 10건
  local why full_plan pre_plan pre_defer def_plan def_skip m

  # ① full 모드는 아무것도 유예하지 않는다
  # ★하한은 **계획 수가 아니라 게이트 행 수**로 잰다 (2026-08-14 · [BL-723]).
  #   종전 `full_plan >= 20` 은 영역 판정이 넓어질수록 줄어드는 양이라 **환경 의존**이었다 —
  #   앱 코드 diff 0 인 브랜치에서 정확히 20 이 나와 한 칸 남았다. 재려던 것은 「게이트 목록이
  #   통째로 사라지지 않았나」이고, 그건 plan+skip 합계가 답한다(⑥ 과 같은 병이다).
  why=""
  full_plan="$(plan_count plan)"
  local full_rows=$(( full_plan + $(plan_count skip) ))
  [ "$(plan_count DEFER)" = "0" ] || why="full 모드가 유예했다 ($(plan_count DEFER)건)"
  [ "${full_rows:-0}" -ge 20 ] || why="${why}${why:+ · }full 게이트 행이 ${full_rows}건뿐이다 (≥20 기대)"
  report "①" "full — 유예 0 · 계획 ${full_plan}건 / 전체 행 ${full_rows}건" "$why"

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

  # ⑤ 무거운 게이트는 --pre-pr 에서 유예된다.
  # ★대표를 **영역 판정 밖의 유예 대상**으로 바꿨다 (2026-08-14 · [BL-723]). 종전 대표
  #   `BE pytest`·`e2e authed` 는 이제 영역 게이트라 앱 코드 diff 0 인 트리에서 DEFER 가 아니라
  #   **skip** 이다 — ⑥ 이 죽어 있던 것과 **정확히 같은 병**이고, 이번엔 옮겨 심지 않는다.
  why=""
  for m in "CI fresh DB alembic" "/codex 적대 리뷰"; do
    [ "$(mark_of "$m" --pre-pr)" = "DEFER" ] || why="${why}${why:+ · }'$m' 가 --pre-pr 에서 유예되지 않았다"
  done
  # 영역 게이트인 유예 대상은 **조건부**로 잰다 — 영역이 살아 있을 때(full=plan)만 DEFER 여야 한다.
  for m in "BE pytest" "e2e authed"; do
    if [ "$(mark_of "$m")" = "plan" ]; then
      [ "$(mark_of "$m" --pre-pr)" = "DEFER" ] ||
        why="${why}${why:+ · }'$m' 가 full=plan 인데 --pre-pr 에서 유예되지 않았다"
    fi
  done
  report "⑤" "무거운 게이트는 --pre-pr 에서 DEFER (영역 게이트는 영역이 살아 있을 때)" "$why"

  # ⑥ 싼 게이트는 --pre-pr 에서도 돈다.
  # ★★대표를 **영역 판정 밖의 게이트**로 바꿨다(2026-08-14). 종전 판본은 `BE ruff`·`FE build` 가
  #   `--pre-pr` 에서 `plan` 이기를 요구했는데, 그 둘은 **영역 게이트**라 BE/FE diff 가 0 인 트리에서
  #   모드와 무관하게 `skip` 이다 ⇒ docs·tools 만 고친 브랜치에서 **상시 red**, `mise run gate-harnesses`
  #   가 통째로 빨강이었다. 재려던 것(「모드가 싼 게이트를 유예하지 않는다」)과 재고 있던 것
  #   (「영역이 이 게이트를 골랐다」)이 뭉쳐 있었다 — 검사기 표면 ≠ 실패 표면(§8.6).
  # ★그리고 그 둘로는 **변이도 안 잡힌다**: `run_gate` 앞에서 영역이 먼저 `skip_gate` 로 빠지므로
  #   `DEFERRABLE` 에 `BE ruff` 를 넣어도 마크가 안 갈린다(실측 — 첫 수리판이 이 변이를 통과했다).
  #   그래서 대표는 **항상 계획되는** `BL 감사`·`문서 감사` 다. 여기서는 변이가 실제로 red 를 낸다.
  why=""
  for m in "BL 감사" "문서 감사"; do
    [ "$(mark_of "$m" --pre-pr)" = "plan" ] || why="${why}${why:+ · }'$m' 가 --pre-pr 에서 안 돈다"
  done
  # 영역 게이트는 **모드가 손대지 않는다**만 잰다 — diff 가 있는 트리에서만 `plan` 이 정상이다.
  for m in "BE ruff" "FE build"; do
    pre_mark="$(mark_of "$m" --pre-pr)"; full_mark="$(mark_of "$m")"
    [ "$pre_mark" = "$full_mark" ] ||
      why="${why}${why:+ · }'$m' 가 full=$full_mark 인데 --pre-pr 에서 $pre_mark 다"
  done
  report "⑥" "싼 게이트는 --pre-pr 에서도 돈다 (영역 게이트는 full 과 같은 마크)" "$why"

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

  # ⑨ ★비싼 게이트도 **영역 판정에 걸려 있다** ([BL-723]).
  # 왜 있나 — 2026-08-14 실측: 앱 코드 diff 가 0 인 회차에서 `BE pytest` **357초**,
  #   `e2e authed` **268초**, `e2e design-canon` **42초**가 그냥 탔다. 같은 회차에 CI 는
  #   `backend`·`e2e` 잡을 전부 skip 했다 — **로컬이 CI 보다 더 돌면서 잴 것은 없었다.**
  #   싼 형제(`BE ruff`·`e2e chromium`)는 이미 걸려 있었으므로 비대칭이 결함이다.
  # ★★단언을 **환경 독립**으로 짠다 — 「skip 이어야 한다」로 쓰면 diff 가 있는 브랜치에서
  #   상시 red 다(⑥ 이 정확히 그 병으로 죽어 있었다). 대신 **형제와 같은 마크**를 요구한다:
  #   diff 가 있으면 둘 다 plan, 없으면 둘 다 skip. 어느 트리에서도 참이다.
  local be_ruff be_pytest e2e_chr e2e_canon e2e_auth
  why=""
  be_ruff="$(mark_of "BE ruff")";        be_pytest="$(mark_of "BE pytest")"
  e2e_chr="$(mark_of "e2e chromium")";   e2e_canon="$(mark_of "e2e design-canon")"
  e2e_auth="$(mark_of "e2e authed")"
  [ "$be_pytest" = "$be_ruff" ] ||
    why="'BE pytest'($be_pytest) 가 'BE ruff'($be_ruff) 와 다르다 — 같은 has_be 여야 한다"
  [ "$e2e_canon" = "$e2e_chr" ] ||
    why="${why}${why:+ · }'e2e design-canon'($e2e_canon) 가 'e2e chromium'($e2e_chr) 와 다르다 — 같은 has_fe 여야 한다"
  # authed = has_fe **또는** has_be. 둘 다 죽었으면(=형제 둘 다 skip) authed 도 skip 이어야 한다.
  # ★그 반대는 요구하지 않는다 — BE 만 바뀐 트리에서 chromium 은 skip 인데 authed 는 돌아야 한다.
  if [ "$e2e_chr" = "skip" ] && [ "$be_ruff" = "skip" ]; then
    [ "$e2e_auth" = "skip" ] ||
      why="${why}${why:+ · }FE·BE 둘 다 diff 0 인데 'e2e authed' 가 $e2e_auth 다"
  fi
  report "⑨" "비싼 게이트도 영역 판정에 걸린다 (pytest~ruff · canon~chromium · authed=fe|be)" "$why"

  # ⑩ [BL-739] `screen.ok` 의 required 술어 = `apps/web/` ∪ `apps/api/src/`
  #    합성 음성·BE 축 양성·실물 양성을 함께 대조한다([BL-780]).
  local s_fake_clean s_fake_api_src s_dirty
  why=""
  s_fake_clean="$(screen_note_fake 'docs/status.md')"
  case "$s_fake_clean" in
    *"필수 아님"*) ;;
    "") why="합성 음성 대조 사유를 못 읽었다 [$s_fake_clean]" ;;
    *) why="합성 음성 대조: apps/web·apps/api/src diff 0 인데 필수다 [$s_fake_clean]" ;;
  esac
  s_fake_api_src="$(screen_note_fake 'apps/api/src/probe.py')"
  case "$s_fake_api_src" in
    *"필수 아님"*) why="${why}${why:+ · }합성 양성 대조(BE 축): apps/api/src 가 바뀌었는데 필수가 아니다 [$s_fake_api_src]" ;;
    *"· 필수"*) ;;
    "") why="${why}${why:+ · }합성 양성 대조(BE 축) 사유를 못 읽었다 [$s_fake_api_src]" ;;
    *) why="${why}${why:+ · }합성 양성 대조(BE 축)의 필수 사유를 못 읽었다 [$s_fake_api_src]" ;;
  esac
  : > "$PROBE_SRC"
  s_dirty="$(signal_note '화면 검증' --allow-dirty)"
  rm -f "$PROBE_SRC"
  case "$s_dirty" in
    *"필수 아님"*) why="${why}${why:+ · }실물 양성 대조: apps/api/src 가 바뀌었는데 필수가 아니다 [$s_dirty]" ;;
    *"· 필수"*) ;;
    "") why="${why}${why:+ · }실물 양성 대조 사유를 못 읽었다 [$s_dirty]" ;;
    *) why="${why}${why:+ · }실물 양성 대조의 필수 사유를 못 읽었다 [$s_dirty]" ;;
  esac
  report "⑩" "screen.ok required = apps/web ∪ apps/api/src ([BL-739]) · 합성 음성+양성 ([BL-780])" "$why"

  # ⑪ [BL-797] 「화면 증거 팩」 배선이 실재하고 FE 영역 판정에 걸린다.
  #    ★이 검사가 없으면 그 블록을 통째로 지워도 ①의 「행 ≥20」이 통과한다 —
  #    codex 적대 리뷰가 그것을 지적했고 실제로 하네스에 라벨이 0회 등장했다(2026-08-17).
  # ★★단언을 **환경 독립**으로 짠다 — 바로 위 ⑨ 의 주석이 경고한 그 함정이다.
  #   「skip 이어야 한다」로 쓰면 `BASE` 가 빈 트리(shallow clone 한 CI 러너 — `merge-base
  #   origin/main HEAD` 실패)에서 fail-safe 가 이겨 상시 red 다. 이 검사의 초판이 정확히
  #   그래서 CI 에서만 죽었다(2026-08-17 실측). 대신 **같은 `has_fe` 분기를 쓰는 형제**
  #   (`FE build`)와 마크가 같기를 요구한다 — 어느 트리에서도 참이고 배선이 사라지면 red 다.
  local ev_fe ev_nofe ev_full sib_nofe
  why=""
  ev_full="$(mark_of '화면 증거 팩')"
  [ -n "$ev_full" ] || why="full 계획에 「화면 증거 팩」 행이 없다 — 배선이 사라졌다"
  ev_fe="$(QB_FG_FAKE_CHANGED='apps/web/src/app/page.tsx' mark_of '화면 증거 팩')"
  [ "$ev_fe" = "plan" ] || why="${why}${why:+ · }FE diff 가 있는데 계획되지 않았다 [$ev_fe]"
  ev_nofe="$(QB_FG_FAKE_CHANGED='docs/status.md' mark_of '화면 증거 팩')"
  sib_nofe="$(QB_FG_FAKE_CHANGED='docs/status.md' mark_of 'FE build')"
  [ "$ev_nofe" = "$sib_nofe" ] ||
    why="${why}${why:+ · }FE diff 0 에서 '화면 증거 팩'($ev_nofe) 이 형제 'FE build'($sib_nofe) 와 다르다 — 같은 has_fe 분기여야 한다"
  # ★유예 집합에 들어가면 안 된다 — 유예되면 화면을 바꾼 PR 이 증거 없이 지나간다.
  local ev_pre
  ev_pre="$(QB_FG_FAKE_CHANGED='apps/web/src/app/page.tsx' mark_of '화면 증거 팩' --pre-pr)"
  [ "$ev_pre" != "DEFER" ] || why="${why}${why:+ · }--pre-pr 이 화면 증거 팩을 유예했다 [$ev_pre]"
  report "⑪" "화면 증거 팩 — 배선 실재 · has_fe 양성/음성 · --pre-pr 유예 금지 ([BL-797])" "$why"

  # ⑫ [BL-797] authed 화면 증거 레그 — 형제 ⑪ 과 **정반대의 성질 둘**을 고정한다.
  #    ⓐ 영역 술어가 `has_fe` 가 아니라 `has_fe ∪ has_be` 다 (authed 화면은 BE 응답에도 흔들린다)
  #    ⓑ **유예 대상이다** — ⑪ 은 「유예되면 안 된다」이고 여기는 「유예돼야 한다」. 두 케이스가
  #       서로의 반증이라, 한쪽 성질을 다른 쪽에 복사하는 실수가 반드시 red 를 낸다.
  #    ★단언은 ⑪ 과 같은 이유로 **형제 대조**다 — `-z "$BASE"` 인 shallow clone 에서도 참이어야 한다.
  local av_full av_be av_nofe sib_be sib_nofe_a av_pre
  why=""
  av_full="$(mark_of '화면 증거 팩 (authed)')"
  [ -n "$av_full" ] || why="full 계획에 「화면 증거 팩 (authed)」 행이 없다 — 배선이 사라졌다"
  # ⓐ-1 BE 만 고친 diff — 형제 `e2e authed` 와 같아야 한다(둘 다 has_be 를 본다).
  av_be="$(QB_FG_FAKE_CHANGED='apps/api/src/main.py' mark_of '화면 증거 팩 (authed)')"
  sib_be="$(QB_FG_FAKE_CHANGED='apps/api/src/main.py' mark_of 'e2e authed')"
  [ "$av_be" = "$sib_be" ] ||
    why="${why}${why:+ · }BE diff 에서 authed 화면 증거($av_be) 가 형제 'e2e authed'($sib_be) 와 다르다 — 같은 영역 술어여야 한다"
  # ⓐ-2 어느 영역도 아닌 diff — 역시 형제와 같아야 한다.
  av_nofe="$(QB_FG_FAKE_CHANGED='docs/status.md' mark_of '화면 증거 팩 (authed)')"
  sib_nofe_a="$(QB_FG_FAKE_CHANGED='docs/status.md' mark_of 'e2e authed')"
  [ "$av_nofe" = "$sib_nofe_a" ] ||
    why="${why}${why:+ · }diff 0 에서 authed 화면 증거($av_nofe) 가 형제 'e2e authed'($sib_nofe_a) 와 다르다"
  # ⓑ `--pre-pr` 은 **유예해야** 한다. BE 와 로그인 세션을 요구하므로 중간 검사에서 돌 수 없다.
  av_pre="$(QB_FG_FAKE_CHANGED='apps/web/src/app/page.tsx' mark_of '화면 증거 팩 (authed)' --pre-pr)"
  [ "$av_pre" = "DEFER" ] ||
    why="${why}${why:+ · }--pre-pr 이 authed 화면 증거를 유예하지 않았다 [$av_pre] — 서버 없는 중간 검사에서 죽는다"
  report "⑫" "화면 증거 팩 (authed) — 배선 실재 · has_fe∪has_be 형제 대조 · --pre-pr 유예 필수 ([BL-797])" "$why"
}

run_suite
echo
echo "  케이스: $((CASES - FAIL))/${CASES} 통과, ${FAIL} 실패"

# ── 변이 — 케이스가 실제로 모드 디스패치를 보고 있는지 증명한다 ────────────────
if [ "${1:-}" = "--mutants" ]; then
  echo
  echo "── 변이 (사본 주입 · 케이스 전량 재실행) ──"
  BASE_RED="$RED_IDS"
  MUT_FAIL=0

  # ★변이 종수도 **센다** — 위 케이스 계수와 같은 이유다(하드코딩 「6종」이 M7 추가로 낡았다).
  MUTANTS=0
  mutate() { # mutate <id> <old> <new> <기대 red 부분집합>
    MUTANTS=$((MUTANTS + 1))
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
  # M3 — 유예 목록에서 대표를 빼면 --pre-pr 이 그것을 안 미룬다.
  # ★앵커를 `BE pytest` → `CI fresh DB alembic` 으로 옮겼다 ([BL-723]) — `BE pytest` 는 이제
  #   영역 게이트라 앱 코드 diff 0 인 트리에서 **DEFERRABLE 에서 빼도 마크가 안 갈린다**
  #   (영역이 먼저 skip 한다). 그 앵커로는 변이가 보이지 않는다.
  mutate M3 '|CI fresh DB alembic|' '|__none__|' "⑤"

  # ★M4·M5 — ⑩ 을 지키는 영구 변이 ([BL-739]). 이것이 없으면 ⑩ 은 **자기 변이가 없는 케이스**다
  #   (BL-714 회차가 ㉖ 에 M12 를 신설한 것과 같은 이유).
  #   M4 = 술어를 리터럴 1 로 되돌린다(= 수리 전 상태). ⑩ 의 **음성 대조 절**이 잡아야 한다.
  mutate M4 '} && screen_req=1' '} ; screen_req=1' "⑩"
  #   M5 = `apps/api/src` 축을 죽인다(= `$has_fe` 단독으로 바꾼 것과 같다). ⑩ 의 **둘째 절**이 잡는다.
  mutate M5 '[ "${src_n:-0}" -gt 0 ] && has_api_src=1' '[ "${src_n:-0}" -gt 99999 ] && has_api_src=1' "⑩"
  #   M6 = 하네스 전용 주입 훅을 죽인다 ([BL-780]). ⑩ 의 절 1(합성 음성)과 절 2(합성 양성)는
  #        **서로 반대의 답**을 요구하므로, 훅이 죽어 둘이 같은 실제 diff 를 보면 어느 트리에서든
  #        반드시 한쪽이 red 다 — 이 변이는 환경 독립이다.
  mutate M6 'CHANGED="$QB_FG_FAKE_CHANGED"' ': # 훅 무력화' "⑩"

  # ★M7 — ⑫ 를 지키는 영구 변이 ([BL-797]). authed 레그를 유예 집합에서 빼면 `--pre-pr` 이
  #   그것을 **실행하려 들고**, 서버가 없는 중간 검사에서 죽는다. ⑫ 의 절 ⓑ 가 잡아야 한다.
  mutate M7 '|화면 증거 팩 (authed)"' '|__none__"' "⑫"

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
  echo "✓ 변이 ${MUTANTS}종 + 음성 대조 1종 전건 판별"
  FAIL=0; RED_IDS="$BASE_RED"
  [ -n "$BASE_RED" ] && FAIL=1
fi

echo
if [ "$FAIL" -gt 0 ]; then echo "✗ 실패 [$RED_IDS]"; exit 1; fi
echo "✓ 전건 통과"

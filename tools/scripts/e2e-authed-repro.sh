#!/usr/bin/env bash
# [BL-784] `e2e authed` 비결정성 관측기 — 게이트 실행을 **그 앞선 것들까지 포함해** 재현한다.
#
# 왜 있나
#   `e2e authed` 는 단독 실행에서는 항상 green 이고 게이트 실행에서만 red 였다. 그러면 차이는
#   테스트가 아니라 **게이트가 그 앞에 하는 일**에 있다. 그런데 그 「앞에 하는 일」은 한 가지가
#   아니다 — `final-gates.sh` 의 영역 판정이 브랜치마다 다른 집합을 켠다. 그래서 모양이 둘이다.
#
#   QB_REPRO_SHAPE=be-branch  (기본) — has_be=1 · has_fe=0. ★**[BL-784] 가 실제로 관측된 모양이다.**
#       BE pytest (§2)  →  pnpm e2e:authed (§4 leg 3)
#       ★`FE vitest`·`FE build`·`e2e chromium`·`e2e design-canon` 은 **전부 skip 된다** — 그 넷의
#         술어는 `has_fe` 뿐인데 `e2e authed` 만 `has_fe ∪ has_be` 다(`final-gates.sh:378`).
#
#   QB_REPRO_SHAPE=fe-branch — has_fe=1. `apps/web` 을 건드리는 회차의 모양이다.
#       pnpm build (§3) → pnpm e2e (leg 1) → pnpm e2e:design-canon (leg 2) → pnpm e2e:authed (leg 3)
#       ★build 는 `next dev` 가 :3100+N 에서 살아 있는 채로 같은 `apps/web` 에서 돈다.
#
#   QB_REPRO_SHAPE=standalone — `pnpm e2e:authed` 하나만. 앞선 것이 **하나도** 없는 대조군이다.
#       [BL-784] 가 「단독 실행은 항상 green」이라 적은 그 조건이고, 표를 채우려면 이것도 재야 한다.
#
#   QB_REPRO_LOAD=<N> — authed 레그가 **도는 동안** 형제 레인을 흉내 내는 부하 N 개를 붙인다.
#       [BL-784] 가 관측된 밤은 워크트리 레인 3개가 동시에 게이트를 돌리고 있었다. 순서만
#       재현해서는 그 조건이 안 나온다. 부하 워커는 `vitest run --maxWorkers=2` 반복이다 —
#       CPU 를 먹되 `.next/` 도 앱 DB 도 건드리지 않아 **관측 대상을 바꾸지 않는다.**
#       ★이것은 재현이 아니라 **합성**이다. 보고할 때 그렇게 적어라.
#       ★★**`--maxWorkers` 를 빼지 마라.** 2026-08-17 에 `pnpm test`(워커 = 코어 수) 를 2개
#         루프로 돌렸더니 **load average 가 217** 까지 갔다. 형제 레인 2개는 그런 부하를 만들지
#         않는다 — 그 조건에서 나온 실패는 원인을 지목하는 게 아니라 새 원인을 만든 것이다.
#         상한은 4 로 막아 뒀다.
#
# 사용법
#   QB_REPRO_SHAPE=be-branch tools/scripts/e2e-authed-repro.sh <라벨> [반복횟수]
#
#   아티팩트: apps/web/test-results/<라벨>-<i>/<project>/  (trace.zip · results.json)
#   요약    : apps/web/test-results/<라벨>-summary.txt
#
# ★서버는 짝으로 미리 띄워라 — `mise run be-isolated` + `mise run fe-isolated`.
#   FE 만 띄우면 playwright 가 자기 webServer 를 올리는데 그 프로세스는 `BETTER_AUTH_URL` 을
#   못 받아 로그인이 403 `INVALID_ORIGIN` 으로 죽는다.
set -uo pipefail

LABEL="${1:-}"
ITERATIONS="${2:-3}"
SHAPE="${QB_REPRO_SHAPE:-be-branch}"
[ -n "$LABEL" ] || { echo "사용법: $0 <라벨> [반복횟수]" >&2; exit 1; }
case "$LABEL" in *[!A-Za-z0-9._-]*) echo "라벨은 영숫자·점·밑줄·하이픈만" >&2; exit 1 ;; esac
case "$ITERATIONS" in ''|*[!0-9]*) echo "반복횟수는 정수여야 한다" >&2; exit 1 ;; esac
case "$SHAPE" in be-branch|fe-branch|standalone) : ;; *) echo "QB_REPRO_SHAPE 는 be-branch · fe-branch · standalone 중 하나" >&2; exit 1 ;; esac
LOAD="${QB_REPRO_LOAD:-0}"
case "$LOAD" in ''|*[!0-9]*) echo "QB_REPRO_LOAD 는 정수여야 한다" >&2; exit 1 ;; esac
[ "$LOAD" -le 4 ] || { echo "QB_REPRO_LOAD 상한은 4 다 (2026-08-17: 무제한 부하가 load 217 을 냈다)" >&2; exit 1; }

ROOT="$(cd "$(dirname "$0")/../.." && pwd -P)"
SLOT=0
[ -f "$ROOT/.worktree-slot" ] && SLOT="$(sed -n 's/^QB_SLOT[[:space:]]*=[[:space:]]*//p' "$ROOT/.worktree-slot" | tr -d ' ')"
: "${SLOT:=0}"
FE_PORT=$((3100 + SLOT))
BASE_URL="http://localhost:$FE_PORT"
WEB="$ROOT/apps/web"
OUT="$WEB/test-results"
SUMMARY="$OUT/$LABEL-summary.txt"
mkdir -p "$OUT"

# ★정체성 프로브 — `final-gates.sh` 가 e2e 앞에 하는 것과 같은 검사다. 남의 앱을 재고
#   「전건 통과」를 내는 사고 이력이 있다.
title="$(curl -s --max-time 30 "$BASE_URL/" | sed -n 's/.*<title>\([^<]*\)<\/title>.*/\1/p' | head -1)"
case "$title" in
  *QuantBridge*) : ;;
  *) echo "✗ $BASE_URL 가 QuantBridge 가 아니다 (got: ${title:-없음}). 서버를 띄우고 다시 돌려라." >&2; exit 1 ;;
esac

{
  echo "══ e2e authed 재현 — label=$LABEL iterations=$ITERATIONS slot=$SLOT base=$BASE_URL"
  echo "   시작: $(date '+%Y-%m-%d %H:%M:%S')  shape=$SHAPE"
} | tee "$SUMMARY"

leg() {  # leg <회차디렉터리라벨> <레그이름> <pnpm 스크립트...>
  local run_label="$1" leg_name="$2"; shift 2
  local log="$OUT/$run_label-$leg_name.log"
  local t0=$SECONDS
  # ★파이프로 감싸지 않는다 — rc 가 tail 의 것으로 바뀐다(이 레포에서 다섯 번 밟았다).
  ( cd "$WEB" && PW_ARTIFACT_RUN="$run_label" PLAYWRIGHT_BASE_URL="$BASE_URL" mise exec -- pnpm "$@" ) > "$log" 2>&1
  local rc=$?
  printf '  %-14s rc=%-3d %4ds  %s\n' "$leg_name" "$rc" "$((SECONDS-t0))" "$log" | tee -a "$SUMMARY"
  return $rc
}

LOAD_PIDS=()
start_load() {
  [ "$LOAD" -gt 0 ] || return 0
  local n=1
  while [ "$n" -le "$LOAD" ]; do
    ( cd "$WEB" && while :; do mise exec -- pnpm exec vitest run --maxWorkers=2; done ) \
      > "$OUT/$1-load$n.log" 2>&1 &
    LOAD_PIDS+=("$!")
    n=$((n + 1))
  done
  printf '  %-14s %d 개 기동 (합성 부하)\n' "load" "$LOAD" | tee -a "$SUMMARY"
}
stop_load() {
  [ "${#LOAD_PIDS[@]}" -gt 0 ] || return 0
  for pid in "${LOAD_PIDS[@]}"; do
    # 서브셸이 죽어도 그 자식 vitest 는 남는다 — 프로세스 그룹째 끊는다.
    kill -- "-$pid" 2>/dev/null || kill "$pid" 2>/dev/null
  done
  wait "${LOAD_PIDS[@]}" 2>/dev/null
  LOAD_PIDS=()
}
trap 'stop_load' EXIT INT TERM
set -m   # 부하 워커를 각자 프로세스 그룹으로 — 위 `kill -- -PID` 가 성립하려면 필요하다

FAILED_ITERATIONS=0
i=1
while [ "$i" -le "$ITERATIONS" ]; do
  RUN_LABEL="$LABEL-$i"
  printf '\n▶ 회차 %d/%d  (%s)\n' "$i" "$ITERATIONS" "$(date '+%H:%M:%S')" | tee -a "$SUMMARY"

  if [ "$SHAPE" = "be-branch" ]; then
    # ★`.env.local` 을 **통째** 소싱한다. `DATABASE_URL` 만 주입하면 세션 픽스처의 `drop_all` 이
    #   개발 DB 를 겨눈다(2026-07-25 에 실제로 전소했다).
    t0=$SECONDS
    ( cd "$ROOT/apps/api"; set -a; . ./.env.local; set +a; mise exec -- uv run pytest -q ) \
      > "$OUT/$RUN_LABEL-pytest.log" 2>&1
    pytest_rc=$?
    printf '  %-14s rc=%-3d %4ds  %s\n' "BE pytest" "$pytest_rc" "$((SECONDS-t0))" \
      "$OUT/$RUN_LABEL-pytest.log" | tee -a "$SUMMARY"
  elif [ "$SHAPE" = "fe-branch" ]; then
    leg "$RUN_LABEL" "build" build
    leg "$RUN_LABEL" "chromium" e2e
    leg "$RUN_LABEL" "design-canon" e2e:design-canon
  fi

  start_load "$RUN_LABEL"
  printf '  %-14s %s\n' "loadavg(전)" "$(uptime | sed 's/.*load averages*: //')" | tee -a "$SUMMARY"
  leg "$RUN_LABEL" "authed" e2e:authed
  authed_rc=$?
  printf '  %-14s %s\n' "loadavg(후)" "$(uptime | sed 's/.*load averages*: //')" | tee -a "$SUMMARY"
  stop_load
  [ "$authed_rc" -eq 0 ] || FAILED_ITERATIONS=$((FAILED_ITERATIONS + 1))

  i=$((i + 1))
done

{
  echo
  echo "══ 결과: authed 레그 실패 $FAILED_ITERATIONS / $ITERATIONS 회차"
  echo "   종료: $(date '+%Y-%m-%d %H:%M:%S')"
  echo "   trace 열기: cd apps/web && pnpm exec playwright show-trace test-results/<회차>/chromium-authed/<테스트>/trace.zip"
} | tee -a "$SUMMARY"

exit 0

#!/usr/bin/env bash
#
# Prometheus multiprocess mmap 파일을 **모든 writer 가 멈춘 콜드 스타트에서만** 지운다.
# 종전에는 Makefile 의 `metrics-wipe` 타깃 레시피였고, 그때 compose 파일 집합은
# 타깃별 변수(`up-isolated: METRICS_COMPOSE_FILES := ...`)로 갈렸다. mise 태스크에는
# 그 기능이 없으므로 **compose 인자를 그대로 받는다** — 호출자가 어느 스택인지 정한다.
#
#   tools/scripts/metrics-wipe.sh --project-directory . -f infra/compose/docker-compose.yml
#
# ★실패가 아니라 건너뛴다 — `up*` 은 이미 떠 있는 스택을 재조정할 때도 쓰는 멱등 커맨드다.
#   wipe 는 전제조건이 아니라 위생 단계이므로, 살아 있는 writer 가 있으면 조용히가 아니라
#   시끄럽게 알리고 넘어간다(지우면 그 writer 가 고아 inode 에 쓰게 되어 지표가 무음 손실된다).
#
# ★가드를 여기 안에 둔다. 호출자(mise task)도 자기 첫 줄에서 같은 가드를 부르지만, 이
#   스크립트가 단독 호출될 수 있으므로 여기서도 판정한다 — 워크트리에서 `docker compose ps` 는
#   **디렉터리 이름에서 유도된 다른 compose 프로젝트**를 보는 바람에 writer 를 0개로 세고
#   (실측: 워크트리 0 / 메인 4 / 실제 구동 4), exit 0 이라 fail-closed 분기도 안 타고
#   곧장 삭제 분기로 간다.

set -uo pipefail

_here="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$_here" || exit 1

"$_here/tools/scripts/assert-main-checkout.sh" metrics-wipe || exit 1

# metrics-prepare 상당 — 디렉터리가 없으면 find 가 실패한다.
mkdir -p apps/api/.metrics
chmod 0777 apps/api/.metrics

WRITERS="backend-worker backend-ws-stream backend-optimizer-heavy backend-beat"

# shellcheck disable=SC2086
writers="$(docker compose "$@" ps -q $WRITERS)"
status=$?

if [ "$status" -ne 0 ]; then
  echo "metrics-wipe: SKIPPED — compose ps failed; preserving metric files (fail-closed)"
elif [ -n "$writers" ]; then
  echo "metrics-wipe: SKIPPED — metric writers running"
else
  find apps/api/.metrics -maxdepth 1 -type f -name '*.db' -delete
  echo "metrics-wipe: WIPED — no metric writers running"
fi

#!/usr/bin/env bash
#
# 서버 배포 — 이미지 태그 하나로 워커 4개·FE·호스트 API 를 갈아 끼운다 (ADR-043, 2026-09-10)
#
# 왜 있나
#   종전 배포는 런북 §3.3 의 40줄 복붙이었고(down → pin → db 만 up → migrate → up → API 재시작), 그 안의
#   회수 한 줄은 깨진 채 열흘을 갔다 — 결과를 아무도 안 봤기 때문이다. 이미지는 CI 가 만든다
#   (`.github/workflows/release.yml`). 이 스크립트는 그것을 **받아서 끼우고, 결과를 텔레그램에 적는다.**
#   소크의 `.soak/src` pin 은 이미지 태그(`sha-<7>`)가 대신한다 — 창·게이트·감시 타이머는 없다.
#
# 사용:
#   tools/scripts/deploy.sh <sha>             # 배포 (release.yml 이 올린 sha-<7> 태그)
#   tools/scripts/deploy.sh --dry-run <sha>   # 판정만 — 무실격·DDL 대조까지 하고 아무것도 안 바꾼다
#   tools/scripts/deploy.sh --status          # 지금 도는 태그 · DB revision · 24h 실격 · 체크아웃 신선도
#   tools/scripts/deploy.sh --migrate <sha>   # ★사람 전용 — 백업 → 이미지 안에서 alembic upgrade head → 재확인
#
# 종료 코드: 0 = 배포 완료 / 1 = 실패(중간에 멈춤 — 텔레그램에 단계가 적힌다) /
#           2 = **막힘**(24h 실격 ≥1 · DDL 필요) — 아무것도 안 바꿨다. 자동 배포(release.yml)는 여기서 멈추고
#               사람이 판단한다. 이것이 「서버 DDL 은 매번 명시 승인」 규칙의 집행 지점이다.
#
# 순서 (각 단계가 실패하면 그 자리에서 멈춘다 — 앞 단계는 되돌리지 않는다)
#   ① 체크아웃 갱신 (git pull --ff-only origin main — compose·스크립트만. 코드는 이미지에 있다)
#   ② 24h 무실격  — `trading.live_signal_sessions.deactivated_reason` 이 자동 사망 8종이면 막힘.
#                   어휘 정본 = `src/trading/models.py:SessionDeactivationReason` (테스트가 대조)
#   ③ DDL 대조    — 이미지의 `alembic heads` ≠ DB `alembic_version` 이면 막힘 (`--migrate` 는 사람이)
#   ④ pull        — BE 4서비스 + FE
#   ⑤ 롤링 교체   — beat → optimizer-heavy → worker → ws-stream 순으로 하나씩 `up -d --no-deps`.
#                   Celery 워커는 수평 확장 안전(acks_late · prefetch 1)이고 ws-stream 은 Redis lease 가
#                   단일성을 지키므로 한 서비스씩 갈아도 매매가 안 끊긴다(재부팅 실측 2026-09-03).
#                   ★교체 중 수십 초 동안 **구·신 워커가 서로 다른 서비스에서 겹친다**(신 ws-stream 이 발행한
#                   태스크를 구 worker 가 받을 수 있다). 태스크 시그니처를 바꿀 때 kwarg 기본값 호환을 지켜라 —
#                   `src/tasks/trading.py` 의 주석이 그 규칙이다.
#   ⑥ FE up
#   ⑦ 호스트 API  — uv sync → import probe(재시작 **전에** 잰다 — 살아 있는 API 를 죽이고 알면 늦다)
#                   → systemctl restart → /health
#   ⑧ 회수        — docker-reclaim.sh --confirm (실패해도 배포 실패는 아니다 — 경고만)
#   ⑨ 텔레그램 요약
#
# env (전부 `.env.example` 에 있다):
#   QB_DB_CONTAINER          psql 을 대는 컨테이너. 기본 quantbridge-db
#   QB_NOTIFY_ENV_FILE       `.env.local` 경로 — 텔레그램 크레덴셜 + import probe 의 환경. 기본 apps/api/.env.local
#   QB_DEPLOY_API_PYTHON     호스트 API venv 의 python. 기본 apps/api/.venv/bin/python (★테스트 seam)
#   QB_DEPLOY_NOTIFY_CMD     주입 seam — 하네스가 실제 텔레그램을 쏘지 않게 하는 유일한 경로
#   QB_DEPLOY_FORCE          1 = ② 를 건너뛴다. **사람이 알면서 쓸 때만** (rc 2 를 본 뒤)
#   QB_DEPLOY_ROOT           체크아웃 루트. 기본 = 이 스크립트의 레포 (★테스트 seam — .env·compose 경로가 여기서 풀린다)
#
# 테스트 seam: docker·git·uv·systemctl·curl 은 PATH 로 찾는다 — `apps/api/tests/scripts/test_deploy.py` 가
#   가짜 바이너리로 ②③ 막힘 · ⑤ 순서 · 실패 비은폐 · --dry-run 무부작용을 잰다.

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
ROOT="${QB_DEPLOY_ROOT:-$(cd "${SCRIPT_DIR}/../.." && pwd -P)}"

DB_CONTAINER="${QB_DB_CONTAINER:-quantbridge-db}"
ENV_FILE="${QB_NOTIFY_ENV_FILE:-${ROOT}/apps/api/.env.local}"
API_PYTHON="${QB_DEPLOY_API_PYTHON:-${ROOT}/apps/api/.venv/bin/python}"
FORCE="${QB_DEPLOY_FORCE:-}"

IMAGE_BACKEND="ghcr.io/woosung-dev/quantbridge-backend"
API_UNIT="quantbridge-api.service"
API_HEALTH="http://127.0.0.1:8100/health"

COMPOSE=(--project-directory "${ROOT}" -f "${ROOT}/infra/compose/docker-compose.yml" -f "${ROOT}/infra/compose/docker-compose.server.yml")
COMPOSE_FE=(--project-directory "${ROOT}" -f "${ROOT}/infra/compose/docker-compose.frontend.yml" -p quantbridge-fe)
# 롤링 순서. 매매와 먼 것부터 — beat(스케줄) → optimizer → 백테스트 워커 → ws-stream(매매 스트림).
ROLL_SERVICES=(backend-beat backend-optimizer-heavy backend-worker backend-ws-stream)
# (연관 배열을 안 쓴다 — 맥 기본 bash 3.2 에서 테스트가 돌아야 한다)
_container_of() { case "$1" in
  backend-beat) echo quantbridge-beat ;;
  backend-optimizer-heavy) echo quantbridge-optimizer-heavy ;;
  backend-worker) echo quantbridge-worker ;;
  backend-ws-stream) echo quantbridge-ws-stream ;;
  *) return 1 ;;
esac; }

# ★자동 사망 8종 — `src/trading/models.py:SessionDeactivationReason` 중 「엔진이 스스로 무너졌다」인 것.
#   행정 사유(user_stopped · account_deleted)는 실격이 아니다. 어긋나면 test_deploy.py 가 잡는다.
AUTO_DEATH_REASONS="'coverage_unrunnable','degraded_unconsented','equity_baseline_missing','equity_exhausted','run_live_error','runtime_divergence','gap_resync_position_mismatch','position_divergence'"

die() { echo "✗ $1" >&2; exit "${2:-1}"; }

# ── 알림 ────────────────────────────────────────────────────────────────────────
NOTIFY_LIB="${QB_NOTIFY_LIB:-${SCRIPT_DIR}/lib/notify-telegram.sh}"
[ -f "${NOTIFY_LIB}" ] || die "알림 라이브러리가 없다: ${NOTIFY_LIB}"
# shellcheck source=tools/scripts/lib/notify-telegram.sh
. "${NOTIFY_LIB}"
_notify() { # 실패해도 배포를 멈추지 않는다 — 알림은 부수 채널이다
  QB_NOTIFY_CMD="${QB_DEPLOY_NOTIFY_CMD:-}" QB_NOTIFY_ENV_FILE="${ENV_FILE}" QB_NOTIFY_TIMEOUT=15 \
    qb_notify_telegram "$1" || echo "⚠ 텔레그램 전송 실패 (배포는 계속)" >&2
}

# ── 판독 ────────────────────────────────────────────────────────────────────────
_tag_of() { printf 'sha-%s\n' "$(printf '%s' "$1" | cut -c1-7)"; }

_sql() { docker exec "${DB_CONTAINER}" psql -U quantbridge -d quantbridge -Atc "$1" 2> /dev/null; }

_auto_deaths_24h() {
  _sql "SELECT count(*) FROM trading.live_signal_sessions WHERE deactivated_at >= now() - interval '24 hours' AND deactivated_reason IN (${AUTO_DEATH_REASONS});"
}

_db_revision() { _sql "SELECT version_num FROM alembic_version;"; }

_image_head() { # 이미지 안의 alembic head. 오프라인·DB 없이 — heads 는 스크립트 디렉터리만 읽는다.
  docker run --rm --network none --entrypoint "" \
    -e DATABASE_URL=postgresql+asyncpg://x:x@localhost:1/x \
    "${IMAGE_BACKEND}:$1" alembic heads 2> /dev/null | awk 'NR==1{print $1}'
}

_running_tag() { # <container> → 지금 도는 이미지 ref
  docker inspect -f '{{.Config.Image}}' "$1" 2> /dev/null
}

_set_env_tag() { # _set_env_tag <KEY> <value> — 루트 .env 의 줄을 바꾸거나 없으면 붙인다
  local key="$1" val="$2" f="${ROOT}/.env"
  touch "${f}"
  if grep -q "^${key}=" "${f}"; then
    sed -i.bak "s|^${key}=.*|${key}=${val}|" "${f}" && rm -f "${f}.bak"
  else
    printf '%s=%s\n' "${key}" "${val}" >> "${f}"
  fi
}

# ── 판정 (②③) — dry-run 과 실배포가 공유한다 ──────────────────────────────────
_gate() { # _gate <tag> → 0 통과 / 2 막힘
  local tag="$1" deaths cur head
  deaths="$(_auto_deaths_24h)"
  [ -n "${deaths}" ] || die "24h 실격 수를 못 읽었다 (${DB_CONTAINER}) — 판정 불가를 「이상 없음」으로 접지 않는다" 1
  if [ "${deaths}" != "0" ] && [ "${FORCE}" != "1" ]; then
    echo "■ 막힘: 지난 24h 자동 사망 ${deaths}건 — 새 코드를 얹기 전에 원인을 봐라 (알면서 넘기려면 QB_DEPLOY_FORCE=1)" >&2
    _notify "⛔ deploy ${tag} 막힘 — 24h 자동 사망 ${deaths}건. 사람이 판단한다."
    return 2
  fi
  echo "  ② 24h 자동 사망: ${deaths}건 ✓"
  cur="$(_db_revision)"
  [ -n "${cur}" ] || die "DB 의 alembic_version 을 못 읽었다 (${DB_CONTAINER})" 1
  head="$(_image_head "${tag}")"
  [ -n "${head}" ] || die "이미지 ${IMAGE_BACKEND}:${tag} 의 alembic head 를 못 읽었다 — pull 됐나, 태그가 맞나" 1
  if [ "${cur}" != "${head}" ]; then
    echo "■ 막힘: DDL 필요 — DB ${cur} ≠ 이미지 head ${head}. 사람이 \`deploy.sh --migrate ${tag}\` 를 친다." >&2
    _notify "⛔ deploy ${tag} 막힘 — DDL 필요 (DB ${cur} → ${head}). deploy.sh --migrate 는 사람이."
    return 2
  fi
  echo "  ③ 스키마: DB ${cur} = 이미지 head ✓"
  return 0
}

_assert_main() {
  local br
  br="$(git -C "${ROOT}" branch --show-current 2> /dev/null)"
  [ "${br}" = main ] || die "체크아웃이 main 이 아니다 (${br:-detached}) — 서버 배포는 main 체크아웃에서만" 1
}

_wait_running() { # _wait_running <container> — 최대 60초
  local c="$1" i=0 st
  while [ "${i}" -lt 30 ]; do
    st="$(docker inspect -f '{{.State.Status}}' "${c}" 2> /dev/null)"
    [ "${st}" = running ] && return 0
    sleep 2; i=$((i + 1))
  done
  return 1
}

# ── 배포 ────────────────────────────────────────────────────────────────────────
_deploy() { # _deploy <sha> <dry|run>
  local sha="$1" mode="$2" tag svc c
  tag="$(_tag_of "${sha}")"
  echo "■ deploy ${tag} (${mode})"
  _assert_main

  if [ "${mode}" = run ]; then
    echo "  ① git pull --ff-only origin main"
    git -C "${ROOT}" pull -q --ff-only origin main || die "git pull 실패 — 추적 변경이 있거나 fast-forward 가 아니다" 1
  fi

  # 이미지가 없으면 head 를 못 읽는다 — 판정 전에 BE 이미지를 당긴다 (pull 자체는 부작용이 아니다: 디스크뿐)
  docker pull -q "${IMAGE_BACKEND}:${tag}" > /dev/null || die "이미지 pull 실패: ${IMAGE_BACKEND}:${tag} — release.yml 이 올렸나, GHCR 패키지가 public 인가" 1
  _gate "${tag}"; local g=$?
  [ "${g}" -eq 0 ] || return "${g}"

  if [ "${mode}" = dry ]; then
    echo "■ dry-run 끝 — 통과했다. 실배포는 인자 없이 <sha> 만."
    return 0
  fi

  _set_env_tag QB_BACKEND_TAG "${tag}"
  _set_env_tag QB_FRONTEND_TAG "${tag}"

  echo "  ④ pull"
  docker compose "${COMPOSE[@]}" pull -q "${ROLL_SERVICES[@]}" || { _notify "🔴 deploy ${tag} 실패 ④ BE pull"; die "BE pull 실패" 1; }
  docker compose "${COMPOSE_FE[@]}" pull -q || { _notify "🔴 deploy ${tag} 실패 ④ FE pull"; die "FE pull 실패" 1; }

  echo "  ⑤ 롤링 교체"
  for svc in "${ROLL_SERVICES[@]}"; do
    c="$(_container_of "${svc}")"
    docker compose "${COMPOSE[@]}" up -d --no-deps --no-build "${svc}" \
      || { _notify "🔴 deploy ${tag} 실패 ⑤ ${svc} up"; die "${svc} up 실패" 1; }
    _wait_running "${c}" || { _notify "🔴 deploy ${tag} 실패 ⑤ ${c} 가 60초 안에 running 이 아니다"; die "${c} 기동 실패 — docker logs ${c}" 1; }
    echo "     ✓ ${svc} → $(_running_tag "${c}")"
  done

  echo "  ⑥ FE up"
  docker compose "${COMPOSE_FE[@]}" up -d --no-build || { _notify "🔴 deploy ${tag} 실패 ⑥ FE up"; die "FE up 실패" 1; }

  echo "  ⑦ 호스트 API"
  (cd "${ROOT}/apps/api" && uv sync -q) || { _notify "🔴 deploy ${tag} 실패 ⑦ uv sync"; die "uv sync 실패" 1; }
  [ -f "${ENV_FILE}" ] || die "env 파일이 없다: ${ENV_FILE}" 1
  # shellcheck disable=SC1090
  (cd "${ROOT}/apps/api" && set -a && . "${ENV_FILE}" && set +a \
    && PYTHONPATH=. "${API_PYTHON}" -c "import src.main; src.main.create_app()") \
    || { _notify "🔴 deploy ${tag} 실패 ⑦ import probe — API 를 재시작하지 않았다(옛 API 가 살아 있다)"; die "import probe 실패 — 재시작 안 함" 1; }
  systemctl --user restart "${API_UNIT}" || { _notify "🔴 deploy ${tag} 실패 ⑦ systemctl restart"; die "API 재시작 실패" 1; }
  sleep 8
  curl -fsS --max-time 10 "${API_HEALTH}" > /dev/null || { _notify "🔴 deploy ${tag} 실패 ⑦ /health"; die "/health 실패 — journalctl --user -u ${API_UNIT}" 1; }
  echo "     ✓ /health"

  echo "  ⑧ 회수"
  bash "${SCRIPT_DIR}/docker-reclaim.sh" --confirm > /dev/null 2>&1 || echo "  ⚠ docker-reclaim 실패 — 배포와 무관, 따로 봐라" >&2

  _notify "✅ deploy ${tag} 완료 — 워커 4 · FE · API 교체, DB $(_db_revision)"
  echo "■ deploy ${tag} 완료"
  return 0
}

# ── --migrate (사람 전용) ───────────────────────────────────────────────────────
_migrate() {
  local sha="$1" tag cur head after brc
  tag="$(_tag_of "${sha}")"
  _assert_main
  cur="$(_db_revision)"; [ -n "${cur}" ] || die "DB 의 alembic_version 을 못 읽었다" 1
  head="$(_image_head "${tag}")"; [ -n "${head}" ] || die "이미지 head 를 못 읽었다 (${tag})" 1
  echo "■ migrate ${tag}: DB ${cur} → 이미지 head ${head}"
  [ "${cur}" != "${head}" ] || { echo "✓ 이미 head 다 — 할 일이 없다."; return 0; }
  echo "  백업 먼저 (db-backup.sh run)"
  bash "${SCRIPT_DIR}/db-backup.sh" run; brc=$?
  # rc 3 = 로컬 덤프는 정상, 원격 사본만 실패 — DDL 앞 안전판으로는 충분하다
  case "${brc}" in 0 | 3) ;; *) die "백업 실패 (rc=${brc}) — DDL 을 넣지 않는다" 1 ;; esac
  echo "  alembic upgrade head (advisory lock · 이미지 안 · compose 네트워크)"
  docker compose "${COMPOSE[@]}" run --rm --no-deps --entrypoint "" backend-worker \
    python -m src.scripts.run_alembic_with_lock --lock-key "${ALEMBIC_ADVISORY_LOCK_KEY:-1903723824}" --timeout "${ALEMBIC_LOCK_TIMEOUT_S:-30}" \
    || die "alembic upgrade 실패" 1
  after="$(_db_revision)"
  [ "${after}" = "${head}" ] || die "적용 후에도 DB 가 ${after:-없음} 다 (기대 ${head})" 1
  _notify "🛠 migrate ${tag}: ${cur} → ${after} (사람이 승인)"
  echo "✓ ${cur} → ${after}"
}

# ── --status ────────────────────────────────────────────────────────────────────
_status() {
  local svc c
  echo "■ 도는 이미지"
  for svc in "${ROLL_SERVICES[@]}"; do
    c="$(_container_of "${svc}")"
    printf '  %-26s %s\n' "${c}" "$(_running_tag "${c}" || echo '(없음)')"
  done
  printf '  %-26s %s\n' quantbridge-frontend "$(_running_tag quantbridge-frontend || echo '(없음)')"
  echo "■ DB revision: $(_db_revision || echo '?')"
  echo "■ 24h 자동 사망: $(_auto_deaths_24h || echo '?')건"
  echo "■ 체크아웃: $(git -C "${ROOT}" rev-parse --short HEAD 2> /dev/null) (branch $(git -C "${ROOT}" branch --show-current 2> /dev/null))"
}

# ── 진입 ────────────────────────────────────────────────────────────────────────
case "${1:-}" in
  -h | --help | "") sed -n '2,45p' "$0"; exit 0 ;;
  --status) _status ;;
  --dry-run) [ -n "${2:-}" ] || die "--dry-run <sha>" 1; _deploy "$2" dry ;;
  --migrate) [ -n "${2:-}" ] || die "--migrate <sha>" 1; _migrate "$2" ;;
  --*) die "알 수 없는 인자: $1 (--help)" 1 ;;
  *) _deploy "$1" run ;;
esac

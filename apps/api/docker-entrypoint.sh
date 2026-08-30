#!/bin/sh
# QuantBridge Backend — docker entrypoint (Sprint 30 ε B6).
#
# **Scope: prod / container 전용** (Cloud Run, docker-compose 안 backend service).
# host 개발 (`mise run be` / `mise run be-isolated`) 은 본 entrypoint 를 거치지 않음 —
# uvicorn 직접 실행. 따라서 host 개발 환경의 alembic 자동 적용은
# 루트 `Makefile` 의 `migrate` / `migrate-isolated` 타깃이 책임 (Sprint 32 BL-168).
#
# 역할:
# 1. PostgreSQL advisory lock 으로 동시 migration 방어 (다중 인스턴스 cold start 시 race 차단).
# 2. lock 획득 → `alembic upgrade head` → release.
# 3. role (api/worker/beat/ws-stream/optimizer-heavy) 분기 후 해당 프로세스 실행.
#
# advisory lock key: 0x71_62_67_30 = 'qbg0' (QuantBridge ε hash) — 임의의 큰 64-bit 정수.
# 동일 DB 안 다른 service 와 충돌 회피 위해 32-bit 영역 안에 안전한 namespace 선정.
#
# 사용 (container 안):
#   docker run --rm quantbridge-backend            # default = api (alembic + uvicorn)
#   docker run --rm quantbridge-backend api        # 명시적 api
#   docker run --rm quantbridge-backend worker     # celery worker (default queue, alembic skip)
#   docker run --rm quantbridge-backend ws-stream  # celery ws_stream queue worker (alembic skip)
#   docker run --rm quantbridge-backend optimizer-heavy  # celery optimizer_heavy queue worker (alembic skip)
#   docker run --rm quantbridge-backend beat       # celery beat (alembic skip)
#   docker run --rm quantbridge-backend migrate    # alembic upgrade head 만 (지원 X — api 와 동일 lock 충돌 회피)
#
# host 개발 시:
#   mise run migrate-isolated     # 격리 DB (5433) alembic upgrade head
#   mise run migrate              # 기본 DB (5432) alembic upgrade head
#   mise run dev-isolated         # up + migrate + be + fe (자동 통합)

set -e

ROLE="${1:-api}"

ALEMBIC_LOCK_KEY="${ALEMBIC_ADVISORY_LOCK_KEY:-1903723824}"  # 0x71626730 = 'qbg0'
ALEMBIC_LOCK_TIMEOUT_S="${ALEMBIC_LOCK_TIMEOUT_S:-30}"

# DATABASE_URL 은 런타임 inject (Cloud Run Secret Manager / docker-compose ENV).
# prod/container 에서 미주입 시 alembic 이 alembic.ini 의 dev url 로 silent fallback →
# 잘못된 DB 로 migration/연결되는 사고를 막기 위해 DB 의존 role 은 아래에서 fail-fast.

run_alembic_with_lock() {
    # PostgreSQL session-level advisory lock 으로 다중 인스턴스 동시 migration 차단.
    # alembic 자체도 alembic_version 테이블에 row-level lock 을 걸지만,
    # session 시작 전 race window 가 존재하여 advisory lock 으로 보강.
    #
    # python 안에서 asyncpg/psycopg 로 lock 획득 후 alembic upgrade head 실행.
    # max ${ALEMBIC_LOCK_TIMEOUT_S}s 대기. 미획득 시 exit 1.

    echo "[entrypoint] alembic upgrade head (advisory lock key=${ALEMBIC_LOCK_KEY}, timeout=${ALEMBIC_LOCK_TIMEOUT_S}s)"

    python -m src.scripts.run_alembic_with_lock \
        --lock-key "${ALEMBIC_LOCK_KEY}" \
        --timeout "${ALEMBIC_LOCK_TIMEOUT_S}" \
        || {
            echo "[entrypoint] alembic upgrade FAILED (lock or migration error)" >&2
            exit 1
        }

    echo "[entrypoint] alembic upgrade head OK"
}

# DB 의존 role 은 DATABASE_URL 미주입 시 fail-fast (silent alembic.ini dev-url fallback 차단).
# 임의 명령 passthrough(*) 은 제외 (debug shell 등).
case "$ROLE" in
    api|worker|beat|ws-stream|optimizer-heavy|migrate)
        if [ -z "${DATABASE_URL:-}" ]; then
            echo "[entrypoint] FATAL: DATABASE_URL not set — Secret Manager/ENV 주입 확인 (role=$ROLE)" >&2
            exit 1
        fi
        ;;
esac

# ★★★**이 아래 role 분기는 compose 경로에서 하나도 돌지 않는다** (2026-08-30 실측).
#   compose 는 `command: celery -A src.tasks.celery_app worker …` 를 주므로 `$1` = "celery" 이고,
#   여기서 매칭되는 것은 **맨 아래 `*)` passthrough** 뿐이다(`exec "$@"`).
#   `api)` 도 안 돈다 — 서버 API 는 컨테이너가 아니라 호스트 `quantbridge-api.service`
#   (`apps/api/.venv/bin/uvicorn`)이고, compose 에 api 서비스 자체가 없다.
#   ⇒ **여기를 고쳐도 배포에 아무 영향이 없다.** 실제로 2026-08-30 에 이 파일의 `uv run` 을
#     고친 변경이 서버에는 no-op 이었다(효과를 낸 것은 compose 의 `command` 쪽이었다).
#   살려 두는 이유는 Dockerfile 머리말의 Cloud Run 타깃 계약이다. 그 계약을 버릴 때 함께 지워라.
#   ★워커 동작을 바꾸려면 `infra/compose/docker-compose*.yml` 의 `command` 를 고쳐라.
case "$ROLE" in
    api)
        # 컨테이너 API는 worker와 같은 metrics volume을 mount하고 두 multiprocess env를 주입해야 worker 지표를 수집한다.
        run_alembic_with_lock
        echo "[entrypoint] starting uvicorn on port=${PORT:-8080}"
        # ★[BL-347] `--no-server-header` 는 **이중화**다 — `SecurityHeadersMiddleware` 가
        #   이미 `server` 헤더를 지운다(`common/security_headers.py`). 미들웨어를 못 타는
        #   응답 경로(핸드셰이크 거부·프로토콜 오류 등)까지 덮으려고 서버 쪽에서도 끈다.
        #   ★gunicorn 이 아니다 — 이 레포에 gunicorn 은 0건이고 `--server_header False`
        #   라는 플래그는 존재하지 않는다(2026-08-16 실측, 원장 BL-347 본문 정정).
        exec uvicorn src.main:app --no-server-header --host 0.0.0.0 --port "${PORT:-8080}"
        ;;
    worker)
        # Celery worker — migration 미수행 (api 인스턴스가 책임).
        echo "[entrypoint] starting celery worker (prefork, concurrency=${CELERY_CONCURRENCY:-4})"
        exec celery -A src.tasks worker \
            --loglevel=info \
            --concurrency="${CELERY_CONCURRENCY:-4}" \
            --pool=prefork
        ;;
    ws-stream)
        # Sprint 12 — Bybit Private WebSocket stream worker (ws_stream queue 전용).
        # docker-compose backend-ws-stream 미러 (BL-012: prefork 복귀). alembic skip.
        echo "[entrypoint] starting celery ws-stream worker (queue=ws_stream, prefork, concurrency=${WS_STREAM_CONCURRENCY:-2})"
        exec celery -A src.tasks worker -Q ws_stream \
            --loglevel=info \
            --concurrency="${WS_STREAM_CONCURRENCY:-2}" \
            --pool=prefork
        ;;
    optimizer-heavy)
        # Sprint 57 BL-237 — Optimizer heavy queue dedicated worker (CPU/메모리 집중).
        # docker-compose backend-optimizer-heavy 미러. alembic skip.
        echo "[entrypoint] starting celery optimizer-heavy worker (queue=optimizer_heavy, prefork, concurrency=${OPTIMIZER_HEAVY_CONCURRENCY:-1})"
        exec celery -A src.tasks worker -Q optimizer_heavy \
            --loglevel=info \
            --concurrency="${OPTIMIZER_HEAVY_CONCURRENCY:-1}" \
            --pool=prefork
        ;;
    beat)
        echo "[entrypoint] starting celery beat"
        exec celery -A src.tasks beat --loglevel=info
        ;;
    migrate)
        run_alembic_with_lock
        ;;
    *)
        # 임의 명령 passthrough (debug 용)
        exec "$@"
        ;;
esac

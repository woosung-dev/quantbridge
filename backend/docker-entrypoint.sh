#!/bin/sh
# QuantBridge Backend — docker entrypoint (Sprint 30 ε B6).
#
# **Scope: prod / container 전용** (Cloud Run, docker-compose 안 backend service).
# host 개발 (`make be` / `make be-isolated`) 은 본 entrypoint 를 거치지 않음 —
# uvicorn 직접 실행. 따라서 host 개발 환경의 alembic 자동 적용은
# 루트 `Makefile` 의 `migrate` / `migrate-isolated` 타깃이 책임 (Sprint 32 BL-168).
#
# 역할:
# 1. PostgreSQL advisory lock 으로 동시 migration 방어 (다중 인스턴스 cold start 시 race 차단).
# 2. lock 획득 → `alembic upgrade head` → release.
# 3. role (api/worker/beat) 분기 후 해당 프로세스 실행.
#
# advisory lock key: 0x71_62_67_30 = 'qbg0' (QuantBridge ε hash) — 임의의 큰 64-bit 정수.
# 동일 DB 안 다른 service 와 충돌 회피 위해 32-bit 영역 안에 안전한 namespace 선정.
#
# 사용 (container 안):
#   docker run --rm quantbridge-backend            # default = api (alembic + uvicorn)
#   docker run --rm quantbridge-backend api        # 명시적 api
#   docker run --rm quantbridge-backend worker     # celery worker (alembic skip)
#   docker run --rm quantbridge-backend beat       # celery beat (alembic skip)
#   docker run --rm quantbridge-backend migrate    # alembic upgrade head 만 (지원 X — api 와 동일 lock 충돌 회피)
#
# host 개발 시:
#   make migrate-isolated     # 격리 DB (5433) alembic upgrade head
#   make migrate              # 기본 DB (5432) alembic upgrade head
#   make dev-isolated         # up + migrate + be + fe (자동 통합)

set -e

ROLE="${1:-api}"

ALEMBIC_LOCK_KEY="${ALEMBIC_ADVISORY_LOCK_KEY:-1903723824}"  # 0x71626730 = 'qbg0'
ALEMBIC_LOCK_TIMEOUT_S="${ALEMBIC_LOCK_TIMEOUT_S:-30}"

# DATABASE_URL 은 런타임 inject. 미지정 시 alembic 이 alembic.ini 의 sqlalchemy.url 사용.
# Cloud Run / docker-compose 는 ENV 로 주입 (Sprint 31 Secret Manager).

run_alembic_with_lock() {
    # PostgreSQL session-level advisory lock 으로 다중 인스턴스 동시 migration 차단.
    # alembic 자체도 alembic_version 테이블에 row-level lock 을 걸지만,
    # session 시작 전 race window 가 존재하여 advisory lock 으로 보강.
    #
    # python 안에서 asyncpg/psycopg 로 lock 획득 후 alembic upgrade head 실행.
    # max ${ALEMBIC_LOCK_TIMEOUT_S}s 대기. 미획득 시 exit 1.

    echo "[entrypoint] alembic upgrade head (advisory lock key=${ALEMBIC_LOCK_KEY}, timeout=${ALEMBIC_LOCK_TIMEOUT_S}s)"

    uv run python -m src.scripts.run_alembic_with_lock \
        --lock-key "${ALEMBIC_LOCK_KEY}" \
        --timeout "${ALEMBIC_LOCK_TIMEOUT_S}" \
        || {
            echo "[entrypoint] alembic upgrade FAILED (lock or migration error)" >&2
            exit 1
        }

    echo "[entrypoint] alembic upgrade head OK"
}

case "$ROLE" in
    api)
        run_alembic_with_lock
        echo "[entrypoint] starting uvicorn on port=${PORT:-8080}"
        exec uv run uvicorn src.main:app --host 0.0.0.0 --port "${PORT:-8080}"
        ;;
    worker)
        # Celery worker — migration 미수행 (api 인스턴스가 책임).
        echo "[entrypoint] starting celery worker (prefork, concurrency=${CELERY_CONCURRENCY:-4})"
        exec uv run celery -A src.tasks worker \
            --loglevel=info \
            --concurrency="${CELERY_CONCURRENCY:-4}" \
            --pool=prefork
        ;;
    beat)
        echo "[entrypoint] starting celery beat"
        exec uv run celery -A src.tasks beat --loglevel=info
        ;;
    migrate)
        run_alembic_with_lock
        ;;
    *)
        # 임의 명령 passthrough (debug 용)
        exec "$@"
        ;;
esac

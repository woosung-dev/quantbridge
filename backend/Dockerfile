# QuantBridge Backend — multi-stage uv 이미지 (Cloud Run target).
# Sprint 30 ε (B1): builder 단계로 dependency 캐시 + runner 단계로 슬림화.
#
# 역할 (api/worker/beat):
# - api: docker-entrypoint.sh 가 alembic upgrade head (advisory lock) → uvicorn
# - worker/beat: docker-compose 에서 command override.
#
# Cloud Run 표준 ENV PORT=8080 (default). docker-compose 는 8000 으로 inline override.

# ───────────────────────────────────────────────────────────
# Stage 1 — builder: uv sync (dev 제외) + dependency layer 캐시
# ───────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /app

# uv 설치 (공식 이미지에서 binary copy)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 1. 의존성 먼저 설치 (Docker 레이어 캐시 활용 — pyproject/uv.lock 변경 시만 재빌드)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 2. 코드 복사 + 프로젝트 설치 (editable 아님 — copy install)
COPY . .
RUN uv sync --frozen --no-dev


# ───────────────────────────────────────────────────────────
# Stage 2 — runner: slim runtime + 비root user + Cloud Run port
# ───────────────────────────────────────────────────────────
FROM python:3.12-slim AS runner

WORKDIR /app

# uv 는 entrypoint 에서 alembic 호출 시 사용
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# 비root user (CSO-2)
RUN useradd -m -u 1000 appuser

# builder 에서 빌드된 venv + 코드 복사
COPY --from=builder --chown=appuser:appuser /app /app

# entrypoint 실행 권한 보장 (host umask 영향 무시)
RUN chmod +x /app/docker-entrypoint.sh

USER appuser

# Cloud Run 은 ENV PORT 를 inject. 미지정 시 8080 default.
EXPOSE 8080

# B6 — entrypoint 가 alembic upgrade head (advisory lock) → uvicorn 실행.
# docker-compose worker/beat 는 command 로 override (entrypoint bypass 위해 --entrypoint "" 또는 직접 CMD 갈음).
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["api"]

# QuantBridge Backend — uv 기반 단일 이미지 (api/worker/beat 공용).
# docker-compose에서 command override로 역할 구분.
FROM python:3.12-slim

WORKDIR /app

# uv 설치 (공식 이미지에서 binary copy)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 1. 의존성 먼저 설치 (Docker 레이어 캐시 활용)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 2. 코드 복사 + 프로젝트 설치
COPY . .
RUN uv sync --frozen --no-dev

# 비-root 실행 (CSO-2)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# 기본 명령 — docker-compose에서 worker/beat/api로 override
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

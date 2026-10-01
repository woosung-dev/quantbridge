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
COPY --from=ghcr.io/astral-sh/uv:0.10.4 /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# 의존성만 설치한다 (Docker 레이어 캐시 활용 — pyproject/uv.lock 변경 시만 재빌드).
# ★빌더는 코드를 받지 않는다 (2026-10-02). 종전의 `COPY . .` + 두 번째 `uv sync --frozen --no-dev` 는
#   `[tool.uv] package = false`(pyproject.toml) 라 venv 에 아무것도 더하지 않았고, 코드만 빌더 `/app` 에
#   섞어 러너의 레이어를 키웠다. 코드는 러너가 빌드 컨텍스트에서 직접 받는다.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project


# ───────────────────────────────────────────────────────────
# Stage 2 — runner: slim runtime + 비root user + Cloud Run port
# ───────────────────────────────────────────────────────────
FROM python:3.12-slim AS runner

WORKDIR /app

# ★러너에는 uv 가 없다 (2026-10-02). 마지막 사용처 `run_alembic_with_lock` 의 `uv run` 이 매 마이그레이션마다
#   dev 그룹을 PyPI 에서 받고 있었다. 도구는 `PATH=/app/.venv/bin` 의 맨 이름으로 부른다 —
#   `uv run` 이 다시 들어오면 조용한 재설치가 아니라 `uv: not found` 로 즉시 드러난다.

ENV UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080

# 비root user (CSO-2)
RUN useradd -m -u 1000 appuser

# ★레이어를 둘로 나눈다 (2026-10-02). 종전 `COPY --from=builder /app /app` 한 줄은 venv 와 코드를 **한 레이어**로
#   묶어서 코드 한 줄만 바뀌어도 그 레이어(운영 `sha-2f0ac34` 의 `docker history` 실측 420MB)가 통째로 새로 생겼다 —
#   서버는 배포마다 그만큼 받고(압축 ~141MB), 3세대 보존분과 GHCR 에 버전마다 쌓였다.
#   분리 후 코드만 바뀐 빌드의 새 레이어 ≈ 4.7MB(깨끗한 체크아웃 · 로컬 arm64 실측, venv 레이어 416MB 는 재사용).
# ① 의존성 레이어 — pyproject.toml·uv.lock 이 같고 빌드 캐시가 살아 있으면 직전 이미지와 같은 레이어다
COPY --from=builder --chown=appuser:appuser /app/.venv /app/.venv
# ② 코드 레이어 — 배포마다 바뀌는 것은 이것뿐이다 (tests·docs·.venv 는 .dockerignore 가 뺀다)
COPY --chown=appuser:appuser . /app

# entrypoint 실행 권한 보장 (host umask 영향 무시)
RUN chmod +x /app/docker-entrypoint.sh

# beat schedule 볼륨(/data) 소유권 seed — named volume 은 첫 생성 시 이미지 마운트
# 포인트의 내용·소유권을 복사한다. 이 디렉토리가 이미지에 없으면 볼륨이 root 소유로
# 초기화되어 appuser beat 가 /data/celerybeat-schedule 쓰기 실패 (Sprint 4→tier-c 만성
# 재발). 기존 root-소유 볼륨은 1회 재생성 필요.
RUN mkdir -p /data /metrics && chown appuser:appuser /data /metrics

USER appuser

# Cloud Run 은 ENV PORT 를 inject. 미지정 시 8080 default.
EXPOSE 8080

# B6 — entrypoint 가 alembic upgrade head (advisory lock) → uvicorn 실행.
# docker-compose worker/beat 는 command 로 override (entrypoint bypass 위해 --entrypoint "" 또는 직접 CMD 갈음).
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["api"]

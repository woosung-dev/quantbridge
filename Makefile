# QuantBridge — 로컬 개발 명령 wrapper
#
# 두 모드 지원 — .env.local 변형 없이 명령으로 분기:
#   기본:   3000 / 8000 / 5432 / 6379  (다른 작업 없을 때)
#   격리:   3100 / 8100 / 5433 / 6380  (다른 웹앱과 병렬 실행 시)
#
# 사용 예:
#   make up && make be          # 한 터미널에서 인프라 + 백엔드
#   make fe                     # 다른 터미널에서 프론트
#   make up-isolated && make be-isolated && (다른 터미널) make fe-isolated

.DEFAULT_GOAL := help
.PHONY: help up down logs be fe \
        up-isolated down-isolated logs-isolated be-isolated fe-isolated \
        test be-test fe-test lint typecheck

ISOLATED_COMPOSE := -f docker-compose.yml -f docker-compose.isolated.yml

# === Help ===

help:
	@echo "QuantBridge dev commands"
	@echo ""
	@echo "  기본 포트 (3000 / 8000 / 5432 / 6379)"
	@echo "    make up           # docker compose up -d (db + redis + workers)"
	@echo "    make down         # docker compose down"
	@echo "    make logs         # docker compose logs -f"
	@echo "    make be           # backend uvicorn (port 8000)"
	@echo "    make fe           # frontend Next.js (port 3000)"
	@echo ""
	@echo "  격리 포트 (3100 / 8100 / 5433 / 6380) — 다른 웹앱과 병렬"
	@echo "    make up-isolated"
	@echo "    make down-isolated"
	@echo "    make logs-isolated"
	@echo "    make be-isolated  # backend uvicorn (port 8100)"
	@echo "    make fe-isolated  # frontend Next.js (port 3100)"
	@echo ""
	@echo "  품질"
	@echo "    make test         # backend pytest + frontend vitest"
	@echo "    make lint         # ruff + eslint"
	@echo "    make typecheck    # mypy + tsc"

# === 기본 모드 (3000 / 8000 / 5432 / 6379) ===

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

be:
	cd backend && uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

fe:
	cd frontend && pnpm dev

# === 격리 모드 (3100 / 8100 / 5433 / 6380) ===

up-isolated:
	docker compose $(ISOLATED_COMPOSE) up -d

down-isolated:
	docker compose $(ISOLATED_COMPOSE) down

logs-isolated:
	docker compose $(ISOLATED_COMPOSE) logs -f

# 환경변수는 process env > dotenv 우선순위 (pydantic-settings).
# .env.local 의 기본값(5432/6379/3000/8000)을 inline 으로 override.
be-isolated:
	cd backend && \
	  DATABASE_URL=postgresql+asyncpg://quantbridge:password@localhost:5433/quantbridge \
	  REDIS_URL=redis://localhost:6380/0 \
	  CELERY_BROKER_URL=redis://localhost:6380/1 \
	  CELERY_RESULT_BACKEND=redis://localhost:6380/2 \
	  REDIS_LOCK_URL=redis://localhost:6380/3 \
	  FRONTEND_URL=http://localhost:3100 \
	  WAITLIST_INVITE_BASE_URL=http://localhost:3100/invite \
	  uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8100

fe-isolated:
	cd frontend && \
	  NEXT_PUBLIC_API_URL=http://localhost:8100 \
	  NEXT_PUBLIC_WS_URL=ws://localhost:8100 \
	  PORT=3100 \
	  pnpm dev

# === 품질 ===

test: be-test fe-test

be-test:
	cd backend && uv run pytest -v

fe-test:
	cd frontend && pnpm test

lint:
	cd backend && uv run ruff check .
	cd frontend && pnpm lint

typecheck:
	cd backend && uv run mypy src/
	cd frontend && pnpm tsc --noEmit

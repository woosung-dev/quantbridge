# QuantBridge — 로컬 개발 명령 wrapper
#
# 두 모드 지원 — .env.local 변형 없이 명령으로 분기:
#   기본:   3000 / 8000 / 5432 / 6379  (다른 작업 없을 때)
#   격리:   3100 / 8100 / 5433 / 6380  (다른 웹앱과 병렬 실행 시)
#
# 사용 예:
#   make dev                    # 한 줄에 up + be + fe 동시 실행 (Ctrl+C 로 양쪽 종료)
#   make dev-isolated           # 격리 포트로 동일
#
#   # 또는 분리 실행:
#   make up && make be          # 한 터미널에서 인프라 + 백엔드
#   make fe                     # 다른 터미널에서 프론트

.DEFAULT_GOAL := help
.PHONY: help dev up down logs be fe \
        dev-isolated up-isolated up-isolated-build down-isolated logs-isolated be-isolated fe-isolated \
        test be-test fe-test fe-e2e fe-e2e-authed lint typecheck

ISOLATED_COMPOSE := -f docker-compose.yml -f docker-compose.isolated.yml

# === Help ===

help:
	@echo "QuantBridge dev commands"
	@echo ""
	@echo "  기본 포트 (3000 / 8000 / 5432 / 6379)"
	@echo "    make dev          # up + be + fe 동시 (한 줄, Ctrl+C 로 양쪽 종료)"
	@echo "    make up           # docker compose up -d (db + redis + workers)"
	@echo "    make down         # docker compose down"
	@echo "    make logs         # docker compose logs -f"
	@echo "    make be           # backend uvicorn (port 8000)"
	@echo "    make fe           # frontend Next.js (port 3000)"
	@echo ""
	@echo "  격리 포트 (3100 / 8100 / 5433 / 6380) — 다른 웹앱과 병렬"
	@echo "    make dev-isolated # up + be + fe 동시 (한 줄)"
	@echo "    make up-isolated"
	@echo "    make up-isolated-build  # up-isolated + --build (코드 변경 후 image 재빌드)"
	@echo "    make down-isolated"
	@echo "    make logs-isolated"
	@echo "    make be-isolated  # backend uvicorn (port 8100)"
	@echo "    make fe-isolated  # frontend Next.js (port 3100)"
	@echo ""
	@echo "  품질"
	@echo "    make test           # backend pytest + frontend vitest"
	@echo "    make fe-e2e         # frontend Playwright (smoke only, no Clerk)"
	@echo "    make fe-e2e-authed  # frontend Playwright (Clerk authed, requires .env.local)"
	@echo "    make lint           # ruff + eslint"
	@echo "    make typecheck      # mypy + tsc"

# === 기본 모드 (3000 / 8000 / 5432 / 6379) ===

# `dev` — up + be + fe 동시. trap 으로 Ctrl+C 시 양쪽 자식 프로세스 종료.
# be / fe 는 둘 다 long-running foreground (uvicorn --reload, pnpm dev) 라
# `&&` chain 으로는 동시 실행 불가 → `&` + `wait` + `trap 'kill 0'` 패턴.
# 두 프로세스 stdout/stderr 가 한 터미널에 섞여 출력됨 (분리 원하면 make be / make fe 별도 터미널).
dev: up
	@echo "▶ make be + make fe 동시 실행 (Ctrl+C 로 양쪽 종료)"
	@trap 'kill 0' INT TERM; \
	  $(MAKE) -s be & \
	  $(MAKE) -s fe & \
	  wait

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

dev-isolated: up-isolated
	@echo "▶ make be-isolated + make fe-isolated 동시 실행 (Ctrl+C 로 양쪽 종료)"
	@trap 'kill 0' INT TERM; \
	  $(MAKE) -s be-isolated & \
	  $(MAKE) -s fe-isolated & \
	  wait

up-isolated:
	docker compose $(ISOLATED_COMPOSE) up -d

# Sprint 23 BL-101 — 코드 변경 후 image 재빌드 + 부팅. daily flow 영향 0.
# 기본 up-isolated 는 빠른 부팅 유지 (image cache 사용).
up-isolated-build:
	docker compose $(ISOLATED_COMPOSE) up -d --build

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

# Sprint 25 — Playwright E2E 분기:
#   fe-e2e          smoke.spec.ts 만 (chromium project, public routes, Clerk 불요)
#   fe-e2e-authed   chromium-authed (trading-ui + dogfood-flow). Clerk dev keys + storageState 필수.
#                    NODE_ENV=production 차단. global.setup.ts 가 매 실행 시 storageState 갱신.
fe-e2e:
	cd frontend && pnpm e2e

fe-e2e-authed:
	cd frontend && pnpm e2e:authed

lint:
	cd backend && uv run ruff check .
	cd frontend && pnpm lint

typecheck:
	cd backend && uv run mypy src/
	cd frontend && pnpm tsc --noEmit

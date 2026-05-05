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
        migrate migrate-isolated wait-db-isolated \
        test be-test fe-test fe-e2e fe-e2e-authed lint typecheck

ISOLATED_COMPOSE := -f docker-compose.yml -f docker-compose.isolated.yml

# 격리 모드 DB URL (host 5433 / container 내부 5432) — be-isolated / migrate-isolated 공통.
# .env.local 변형 없이 inline override 패턴 (process env > pydantic-settings dotenv 우선순위).
ISOLATED_DATABASE_URL := postgresql+asyncpg://quantbridge:password@localhost:5433/quantbridge

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
	@echo "    make dev-isolated      # up + migrate + be + fe 동시 (한 줄, alembic 자동 적용)"
	@echo "    make up-isolated       # docker compose up (db + redis + workers, migrate 미포함)"
	@echo "    make up-isolated-build # up-isolated + --build (코드 변경 후 image 재빌드)"
	@echo "    make migrate-isolated  # alembic upgrade head (격리 DB 5433) — Sprint 32 BL-168"
	@echo "    make down-isolated"
	@echo "    make logs-isolated"
	@echo "    make be-isolated       # migrate-isolated 선행 + backend uvicorn (port 8100)"
	@echo "    make fe-isolated       # frontend Next.js (port 3100)"
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

# Sprint 32 BL-168 — dev-isolated 가 migrate-isolated 선행 의무.
# host be-isolated 는 docker-entrypoint.sh 를 안 타기 때문에 (uvicorn 직접 실행)
# alembic upgrade 를 root Makefile 에서 명시 통합. fresh `make dev-isolated` 첫 부팅
# 시 backtests.config 같은 신규 컬럼이 schema drift 없이 반영됨.
dev-isolated: up-isolated migrate-isolated
	@echo "▶ make be-isolated + make fe-isolated 동시 실행 (Ctrl+C 로 양쪽 종료)"
	@trap 'kill 0' INT TERM; \
	  $(MAKE) -s be-isolated QB_MIGRATE_DONE=1 & \
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

# Sprint 32 BL-168 — DB healthy 대기 (up-isolated 직후 migrate 가 race 안 타도록).
# `quantbridge-db` container_name 고정 (docker-compose.yml 안 명시) → `docker exec` 로
# 직접 pg_isready 호출. compose project 이름과 무관 (worktree 격리 시 robust).
# 30s 까지 1s 간격 폴링. 미달성 시 exit 1.
wait-db-isolated:
	@echo "▶ wait db (5433) healthy …"
	@for i in $$(seq 1 30); do \
	  if docker exec quantbridge-db pg_isready -U quantbridge -d quantbridge >/dev/null 2>&1; then \
	    echo "  db ready ($${i}s)"; exit 0; \
	  fi; \
	  sleep 1; \
	done; \
	echo "  db NOT ready after 30s" >&2; exit 1

# Sprint 32 BL-168 — 격리 DB 5433 에 alembic upgrade head 적용.
# host uvicorn 이 docker-entrypoint.sh 안 타는 점을 보강. process env override 로
# .env.local 의 5432 default 를 5433 으로 변경. up-isolated 후 db healthy 대기.
migrate-isolated: wait-db-isolated
	@echo "▶ alembic upgrade head (격리 DB 5433)"
	cd backend && \
	  DATABASE_URL=$(ISOLATED_DATABASE_URL) \
	  uv run alembic upgrade head

# 기본 모드 마이그레이션 — host 5432.
migrate:
	cd backend && uv run alembic upgrade head

# 환경변수는 process env > dotenv 우선순위 (pydantic-settings).
# .env.local 의 기본값(5432/6379/3000/8000)을 inline 으로 override.
#
# Sprint 32 BL-168 — be-isolated 가 migrate-isolated 선행 의무.
# `make be-isolated` 단독 실행 시도 fresh start 호환 (db healthy + alembic 자동).
# QB_MIGRATE_DONE=1 sentinel — `dev-isolated` 가 이미 migrate-isolated 수행한 경우
# sub-make 호출에서 중복 실행 회피 (GNU make 는 target 캐시를 sub-process 와 공유 안 함).
ifndef QB_MIGRATE_DONE
be-isolated: migrate-isolated
endif
be-isolated:
	cd backend && \
	  DATABASE_URL=$(ISOLATED_DATABASE_URL) \
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

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
        dev-isolated up-isolated up-isolated-build up-isolated-watch down-isolated logs-isolated be-isolated fe-isolated \
        migrate migrate-isolated wait-db-isolated seed \
        test be-test fe-test fe-e2e fe-e2e-authed lint typecheck metrics-prepare metrics-wipe

ISOLATED_COMPOSE := -f docker-compose.yml -f docker-compose.isolated.yml
METRICS_COMPOSE_FILES :=
METRICS_WRITER_SERVICES := backend-worker backend-ws-stream backend-optimizer-heavy backend-beat

# 워크트리 병렬 슬롯 — scripts/worktree-bootstrap.sh 가 워크트리 루트에 `.worktree-slot` 을 쓴다.
# 파일이 없으면(= 메인 체크아웃) 슬롯 0 이고, 그때 포트는 기존 값 3100/8100 과 정확히 같다.
# 컨테이너(5433/6380)는 슬롯과 무관하게 공유한다 — container_name 이 고정이라 스택은 1벌뿐이다.
-include .worktree-slot
QB_SLOT ?= 0
QB_MAIN_ROOT ?= (메인 체크아웃)
QB_FE_PORT := $(shell expr 3100 + $(QB_SLOT))
QB_BE_PORT := $(shell expr 8100 + $(QB_SLOT))

# 공유 자원을 변형하는 타깃은 메인 체크아웃(슬롯 0)에서만 돈다.
#
# 왜 문서가 아니라 코드로 막는가 — `docs/reference/worktree-parallel.md` 와 부트스트랩 요약이
# "하면 안 된다" 고 적어만 두던 것들이다. 사람은 읽지만 **에이전트는 읽지 않고 실행한다.**
# 워크트리에서 이 중 하나가 돌면 다른 워크트리와 메인이 함께 깨지고, 깨진 쪽은 원인을
# 알 수 없는 빨간불을 받는다(누가 언제 무엇을 드롭했는지 흔적이 남지 않는다).
#
#   up/down 계열   → container_name 이 고정이라 스택은 1벌뿐이다. 남의 DB 를 죽인다.
#   migrate 계열   → 대상이 **공유 앱 DB** 다. 워크트리 브랜치의 마이그레이션을 전원이 뒤집어쓴다.
#   seed           → 공유 앱 DB 를 갈아엎는다.
define guard-main-only
@if [ "$(QB_SLOT)" != "0" ]; then \
  echo "✗ '$@' 은 메인 체크아웃 전용이다 (지금 슬롯 $(QB_SLOT))." >&2; \
  echo "  컨테이너와 앱 DB 는 슬롯과 무관하게 1벌 공유다 — 여기서 실행하면 다른 워크트리와 메인이 깨진다." >&2; \
  echo "  → 메인에서 실행해라: cd $(QB_MAIN_ROOT) && make $@" >&2; \
  echo "  (근거: docs/reference/worktree-parallel.md §2)" >&2; \
  exit 1; \
fi
endef

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
	@echo "  워크트리 병렬 — 현재 슬롯 $(QB_SLOT) (FE $(QB_FE_PORT) / BE $(QB_BE_PORT))"
	@echo "    scripts/herdr-fleet.sh          # herdr 2x2 함대 — 워크트리 3 + CONTROL 1 (메인에서)"
	@echo "    scripts/worktree-bootstrap.sh   # 새 워크트리를 실행 가능 상태로 (슬롯·테스트DB·env)"
	@echo "    docs/reference/worktree-parallel.md   # 무엇이 병렬 가능하고 무엇이 불가능한가"
	@echo "    * 슬롯 != 0 에서는 up/down/migrate/seed 계열이 거부된다 (공유 자원 보호)"
	@echo ""
	@echo "  품질"
	@echo "    make test           # backend pytest + frontend vitest"
	@echo "    make fe-e2e         # frontend Playwright (smoke only, no Clerk)"
	@echo "    make fe-e2e-authed  # frontend Playwright (Clerk authed, requires .env.local)"
	@echo "    make lint           # ruff + eslint"
	@echo "    make typecheck      # mypy + tsc"

# Prometheus mmap 파일은 모든 writer가 멈춘 콜드 스타트에서만 제거한다.
# 부분 재기동 타깃에는 metrics-wipe를 절대 붙이지 않는다.
metrics-prepare:
	mkdir -p backend/.metrics
	chmod 0777 backend/.metrics

# ★실패가 아니라 건너뛴다 — `up*` 은 이미 떠 있는 스택을 재조정할 때도 쓰는 멱등 커맨드다.
# wipe 는 전제조건이 아니라 위생 단계이므로, 살아 있는 writer 가 있으면 조용히가 아니라
# 시끄럽게 알리고 넘어간다(지우면 그 writer 가 고아 inode 에 쓰게 되어 지표가 무음 손실된다).
metrics-wipe: metrics-prepare
	@writers="$$(docker compose $(METRICS_COMPOSE_FILES) ps -q $(METRICS_WRITER_SERVICES))"; status=$$?; \
	if [ $$status -ne 0 ]; then \
		echo "metrics-wipe: SKIPPED — compose ps failed; preserving metric files (fail-closed)"; \
	elif [ -n "$$writers" ]; then \
		echo "metrics-wipe: SKIPPED — metric writers running"; \
	else \
		find backend/.metrics -maxdepth 1 -type f -name '*.db' -delete; \
		echo "metrics-wipe: WIPED — no metric writers running"; \
	fi

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

up: metrics-wipe
	$(guard-main-only)
	docker compose up -d

down:
	$(guard-main-only)
	docker compose down

logs:
	docker compose logs -f

be: metrics-prepare
	cd backend && \
	  PROMETHEUS_MULTIPROC_DIR=$(CURDIR)/backend/.metrics \
	  QB_METRICS_ROLE=api \
	  uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

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

up-isolated: METRICS_COMPOSE_FILES := $(ISOLATED_COMPOSE)
up-isolated: metrics-wipe
	$(guard-main-only)
	docker compose $(ISOLATED_COMPOSE) up -d

# Sprint 23 BL-101 — 코드 변경 후 image 재빌드 + 부팅. daily flow 영향 0.
# 기본 up-isolated 는 빠른 부팅 유지 (image cache 사용).
up-isolated-build: METRICS_COMPOSE_FILES := $(ISOLATED_COMPOSE)
up-isolated-build: metrics-wipe
	$(guard-main-only)
	docker compose $(ISOLATED_COMPOSE) up -d --build

# Sprint 38 BL-181 — 격리 모드 + worker auto-rebuild on src 변경.
# backend-worker / backend-ws-stream / backend-beat 3 서비스 한정으로
# `./backend/src` bind-mount + watchfiles wrapper 적용 (isolated.yml override).
# host src 변경 시 컨테이너 안 celery 가 자동 reload → 수동 rebuild 제거.
# 패키지 변경은 image rebuild 의무 (ADR docs/reference/infra/2026-05-06-bl-181-*).
up-isolated-watch: metrics-prepare
	$(guard-main-only)
	docker compose $(ISOLATED_COMPOSE) up -d --build backend-worker backend-ws-stream backend-beat

down-isolated:
	$(guard-main-only)
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
	$(guard-main-only)
	@echo "▶ alembic upgrade head (격리 DB 5433)"
	cd backend && \
	  DATABASE_URL=$(ISOLATED_DATABASE_URL) \
	  uv run alembic upgrade head

# 기본 모드 마이그레이션 — host 5432.
migrate:
	$(guard-main-only)
	cd backend && uv run alembic upgrade head

# dogfood 복원 시더 — 빈 DB 를 전 화면 사용 가능 상태로.
# 전략·백테스트를 실 서비스 계층 + 실 Celery 로 만든다(HTTP/auth 만 우회 —
# clerk SDK 가 azp 클레임을 필수로 요구해 헤드리스 HTTP 시딩이 구조적으로 불가).
# OHLCV 는 따로 안 심는다 — TimescaleProvider 가 cache-miss 시 Bybit 에서 받아
# ts.ohlcv 에 직접 쓰므로 첫 백테스트가 곧 시딩이다. 멱등.
#   make seed            전체
#   make seed ONLY=daily 하나만
seed:
	$(guard-main-only)
	cd backend && set -a; . ./.env.local; set +a; \
	  uv run python scripts/seed_dogfood.py --confirm $(if $(ONLY),--only $(ONLY),)

# 환경변수는 process env > dotenv 우선순위 (pydantic-settings).
# .env.local 의 기본값(5432/6379/3000/8000)을 inline 으로 override.
#
# Sprint 32 BL-168 — be-isolated 가 migrate-isolated 선행 의무.
# `make be-isolated` 단독 실행 시도 fresh start 호환 (db healthy + alembic 자동).
# QB_MIGRATE_DONE=1 sentinel — `dev-isolated` 가 이미 migrate-isolated 수행한 경우
# sub-make 호출에서 중복 실행 회피 (GNU make 는 target 캐시를 sub-process 와 공유 안 함).
#
# 워크트리(슬롯 ≠ 0)에서는 선행을 아예 걸지 않는다. 대상이 **공유 앱 DB** 라 워크트리
# 브랜치의 마이그레이션이 다른 워크트리와 메인에 걸리기 때문이다. 지금까지는 사람이
# `QB_MIGRATE_DONE=1` 을 매번 붙여서 피해야 했는데(문서 §5 의 ⚠️), 슬롯이 이미 그 정보를
# 갖고 있으므로 사람에게 의무를 지울 이유가 없다. 한 번 빠뜨리면 남이 깨진다.
# 마이그레이션을 실제로 적용해야 하는 작업이라면 메인 체크아웃에서 해라.
ifndef QB_MIGRATE_DONE
ifeq ($(QB_SLOT),0)
be-isolated: migrate-isolated
endif
endif
be-isolated: metrics-prepare
	cd backend && \
	  DATABASE_URL=$(ISOLATED_DATABASE_URL) \
	  REDIS_URL=redis://localhost:6380/0 \
	  CELERY_BROKER_URL=redis://localhost:6380/1 \
	  CELERY_RESULT_BACKEND=redis://localhost:6380/2 \
	  REDIS_LOCK_URL=redis://localhost:6380/3 \
	  FRONTEND_URL=http://localhost:$(QB_FE_PORT) \
	  WAITLIST_INVITE_BASE_URL=http://localhost:$(QB_FE_PORT)/invite \
	  PROMETHEUS_MULTIPROC_DIR=$(CURDIR)/backend/.metrics \
	  QB_METRICS_ROLE=api \
	  uv run uvicorn src.main:app --reload --host 0.0.0.0 --port $(QB_BE_PORT)

fe-isolated:
	cd frontend && \
	  NEXT_PUBLIC_API_URL=http://localhost:$(QB_BE_PORT) \
	  NEXT_PUBLIC_WS_URL=ws://localhost:$(QB_BE_PORT) \
	  PORT=$(QB_FE_PORT) \
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

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
.PHONY: help dev up down logs be fe gate-harnesses \
        dev-isolated up-isolated up-isolated-build up-isolated-watch down-isolated logs-isolated be-isolated fe-isolated \
        migrate migrate-isolated wait-db-isolated seed \
        db-snapshot db-restore \
        test be-test fe-test fe-e2e fe-e2e-authed lint typecheck docs-audit header-audit metrics-prepare metrics-wipe

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
# 왜 문서가 아니라 코드로 막는가 — `docs/reference/operations/worktree-parallel.md` 와 부트스트랩 요약이
# "하면 안 된다" 고 적어만 두던 것들이다. 사람은 읽지만 **에이전트는 읽지 않고 실행한다.**
# 워크트리에서 이 중 하나가 돌면 다른 워크트리와 메인이 함께 깨지고, 깨진 쪽은 원인을
# 알 수 없는 빨간불을 받는다(누가 언제 무엇을 드롭했는지 흔적이 남지 않는다).
#
#   up/down 계열   → container_name 이 고정이라 스택은 1벌뿐이다. 남의 DB 를 죽인다.
#   migrate 계열   → 대상이 **공유 앱 DB** 다. 워크트리 브랜치의 마이그레이션을 전원이 뒤집어쓴다.
#   seed           → 공유 앱 DB 를 갈아엎는다.
# ★가드는 **선행 타깃**이어야 한다. 레시피 첫 줄에 두면 선행 타깃이 이미 돌아간 뒤에 발동한다.
# 실측으로 걸린 두 사례:
#   - up-isolated 의 선행 metrics-wipe — 워크트리에서 `docker compose ps` 가 **디렉터리 이름에서
#     유도된 다른 compose 프로젝트**를 보는 바람에 writer 를 0개로 세고
#     (실측: 워크트리 0 / 메인 4 / 실제 구동 4), exit 0 이라 fail-closed 분기도 안 타고
#     곧장 삭제 분기로 간다.
#   - migrate-isolated 의 선행 wait-db-isolated — DB 를 30초 폴링한 뒤에야 가드가 뜬다. 스택이
#     내려가 있으면 "DB 가 죽었다" 로 오진하고 슬롯 가드 메시지는 영영 안 나온다.
# 선행 타깃은 (직렬 make 에서) 나열 순서대로 실행되므로 이걸 **맨 앞**에 둔다.
#
# 종료 코드는 셸에선 1 이지만 **`make` 는 2 로 감싼다.** 문서에 "exit 1" 이라고 쓰지 마라.
#
# ★판정 기준은 `$(QB_SLOT)` 이 **아니다.** make 는 명령행 변수(`make QB_SLOT=0 up`)를
#   `-include` 로 읽은 파일보다 우선하므로, 슬롯 변수로 판정하면 **인자 하나로 가드가 꺼진다.**
#   실측 — 슬롯 1 워크트리에서 `make QB_SLOT=0 _guard-main-only` 가 exit 0 으로 통과했다
#   (codex 리뷰 P1). 인자로 끌 수 있는 가드는 가드가 아니다.
#   그래서 **git 에게 묻는다**: 워크트리에서만 git-dir 과 git-common-dir 이 갈린다.
#   이건 어떤 make 변수로도 못 바꾼다.
#
# ★가드는 **선행 타깃과 레시피 첫 줄 양쪽**에 건다. 한쪽만으로는 각각 구멍이 있고, 둘이 서로의
#   구멍을 막는다:
#     - 선행 타깃만  → `make -o _guard-main-only seed` 로 선행을 "이미 최신" 취급시켜 건너뛸 수
#                      있다. 실측 — 그 명령이 워크트리에서 **exit 0** 으로 통과했고 dry-run 은
#                      `seed_dogfood.py --confirm` 이 **공유 앱 DB** 에 돌 것임을 보여줬다.
#     - 레시피만    → `up-isolated: metrics-wipe` 처럼 **선행의 부작용이 먼저** 실행된다.
#   그래서 둘 다 건다. 중복 실행 비용은 `git rev-parse` 두 번뿐이다.
# 가드 호출은 **문자열 리터럴**이다. `$(...)` 변수 참조를 쓰지 않는다 —
# 변수로 두면 `make 'qb-guard=@:' seed` 로 빈 명령으로 덮여 그대로 통과한다(실측).
.PHONY: _guard-main-only
_guard-main-only:
	@scripts/assert-main-checkout.sh "$(or $(MAKECMDGOALS),이 타깃)"

# 소크 고정본 스택 보호 — up-isolated 계열은 같은 container_name 을 덮어써 돌고 있는 소크를
# 끊는다. 같은 이유로 선행 타깃과 레시피 양쪽에 건다(위 §가드 설명과 동일한 논리).
# ★고정본 스택이 안 떠 있으면 이 가드는 **아무 일도 하지 않는다** — 기존 워크플로의 의미 불변.
.PHONY: _guard-no-pinned-soak
_guard-no-pinned-soak:
	@scripts/soak-stack.sh assert-not-pinned


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
	@echo "    docs/reference/operations/worktree-parallel.md   # 무엇이 병렬 가능하고 무엇이 불가능한가"
	@echo "    * 슬롯 != 0 에서는 up/down/migrate/seed 계열이 거부된다 (공유 자원 보호)"
	@echo ""
	@echo "  DB 백업 / 복원 (BL-451 — 파괴적 작업 전에 찍어라)"
	@echo "    make db-snapshot                    # 개발 DB → .backups/<db>-<ts>.dump"
	@echo "    make db-snapshot DB=quantbridge_test"
	@echo "    make db-restore FILE=... TO=<대상 DB>  # TO 는 기본값 없음 (안전장치)"
	@echo ""
	@echo "  품질"
	@echo "    make test           # backend pytest + frontend vitest"
	@echo "    make fe-e2e         # frontend Playwright (smoke only, no Clerk)"
	@echo "    make fe-e2e-authed  # frontend Playwright (Clerk authed, requires .env.local)"
	@echo "    make lint           # ruff + eslint"
	@echo "    make typecheck      # mypy + tsc"
	@echo "    make docs-audit     # 활성 문서 링크 + 폐기 경로 검사"
	@echo "    make header-audit   # 소스 첫 3줄 한국어 헤더 주석 검사 (BL-307)"

# Prometheus mmap 파일은 모든 writer가 멈춘 콜드 스타트에서만 제거한다.
# 부분 재기동 타깃에는 metrics-wipe를 절대 붙이지 않는다.
metrics-prepare:
	mkdir -p backend/.metrics
	chmod 0777 backend/.metrics

# ★실패가 아니라 건너뛴다 — `up*` 은 이미 떠 있는 스택을 재조정할 때도 쓰는 멱등 커맨드다.
# wipe 는 전제조건이 아니라 위생 단계이므로, 살아 있는 writer 가 있으면 조용히가 아니라
# 시끄럽게 알리고 넘어간다(지우면 그 writer 가 고아 inode 에 쓰게 되어 지표가 무음 손실된다).
metrics-wipe: metrics-prepare
	@scripts/assert-main-checkout.sh metrics-wipe || exit 1; \
	writers="$$(docker compose $(METRICS_COMPOSE_FILES) ps -q $(METRICS_WRITER_SERVICES))"; status=$$?; \
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

up: _guard-main-only metrics-wipe
	@scripts/assert-main-checkout.sh up || exit 1; \
	  docker compose up -d

down: _guard-main-only
	@scripts/assert-main-checkout.sh down || exit 1; \
	  docker compose down

logs:
	docker compose logs -f

be: metrics-prepare
	cd backend && \
	  PROMETHEUS_MULTIPROC_DIR=$(CURDIR)/backend/.metrics \
	  QB_METRICS_ROLE=api \
	  uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# ★[BL-650] — Turbopack 영속 캐시가 자라면 `next dev` 가 **요청 0건에서** CPU 를 태우고
#   낡은 CSS 를 재기동 너머로 계속 준다(음성 대조를 거짓 통과시킨다). 처방은 `rm -rf .next` 뿐이다.
#   ★★임계 1GB 는 **정책이 아니라 관측 장치**다. 근거는 두 점뿐이다 — 1.99GB 에서 417% CPU /
#   120초 타임아웃(2026-08-08 fe-canon-and-responsive), 593MB 에서 0.1% CPU / 0.61초
#   (2026-08-08 재측정). 그 사이 어디가 문턱인지는 **아직 아무도 모른다.** 이 줄이 하는 일은
#   경고를 남겨 다음 사람이 그 문턱을 실제로 재게 만드는 것이다. 숫자를 정본으로 인용하지 마라.
FE_CACHE_WARN_MB ?= 1024
fe:
	@sz=$$(du -sm frontend/.next 2>/dev/null | cut -f1); \
	if [ -n "$$sz" ] && [ "$$sz" -ge $(FE_CACHE_WARN_MB) ]; then \
	  echo "⚠ frontend/.next 가 $${sz}MB 다 (경고선 $(FE_CACHE_WARN_MB)MB) — [BL-650]"; \
	  echo "  dev 가 느리거나 CSS 변경이 안 먹으면 먼저: rm -rf frontend/.next"; \
	  echo "  ★이 경고선은 문턱의 실측치가 아니다. 태우기 시작하는 크기를 재면 백로그에 적어라."; \
	fi
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
up-isolated: _guard-main-only _guard-no-pinned-soak metrics-wipe
	@scripts/assert-main-checkout.sh up-isolated || exit 1; \
	  scripts/soak-stack.sh assert-not-pinned || exit 1; \
	  docker compose $(ISOLATED_COMPOSE) up -d

# Sprint 23 BL-101 — 코드 변경 후 image 재빌드 + 부팅. daily flow 영향 0.
# 기본 up-isolated 는 빠른 부팅 유지 (image cache 사용).
up-isolated-build: METRICS_COMPOSE_FILES := $(ISOLATED_COMPOSE)
up-isolated-build: _guard-main-only _guard-no-pinned-soak metrics-wipe
	@scripts/assert-main-checkout.sh up-isolated-build || exit 1; \
	  scripts/soak-stack.sh assert-not-pinned || exit 1; \
	  docker compose $(ISOLATED_COMPOSE) up -d --build

# Sprint 38 BL-181 — 격리 모드 + worker auto-rebuild on src 변경.
# backend-worker / backend-ws-stream / backend-beat 3 서비스 한정으로
# `./backend/src` bind-mount + watchfiles wrapper 적용 (isolated.yml override).
# host src 변경 시 컨테이너 안 celery 가 자동 reload → 수동 rebuild 제거.
# 패키지 변경은 image rebuild 의무 (ADR-019, docs/decisions/019-worker-auto-rebuild.md).
up-isolated-watch: _guard-main-only _guard-no-pinned-soak metrics-prepare
	@scripts/assert-main-checkout.sh up-isolated-watch || exit 1; \
	  scripts/soak-stack.sh assert-not-pinned || exit 1; \
	  docker compose $(ISOLATED_COMPOSE) up -d --build backend-worker backend-ws-stream backend-beat

down-isolated: _guard-main-only
	@scripts/assert-main-checkout.sh down-isolated || exit 1; \
	  docker compose $(ISOLATED_COMPOSE) down

# ── 소크 스택 (BL-003 게이트) ────────────────────────────────────────────────
# 워커가 작업 트리가 아니라 **고정된 커밋 스냅샷**(.soak/src)을 돌게 한다. 그래야
# `backend/src` 를 편집해도 돌고 있는 소크가 죽지 않는다. 정본 = scripts/soak-stack.sh.
# ★up-isolated 계열은 같은 container_name 을 덮어써 소크를 끊으므로 _guard-no-pinned-soak
#   를 단다. 고정본 스택이 안 떠 있으면 이 가드는 아무 일도 하지 않는다(기존 의미 불변).

soak-pin: _guard-main-only
	@scripts/assert-main-checkout.sh soak-pin || exit 1; \
	  scripts/soak-stack.sh pin $(COMMIT)

up-soak: _guard-main-only
	@scripts/assert-main-checkout.sh up-soak || exit 1; \
	  scripts/soak-stack.sh up

down-soak: _guard-main-only
	@scripts/assert-main-checkout.sh down-soak || exit 1; \
	  scripts/soak-stack.sh down

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
migrate-isolated: _guard-main-only wait-db-isolated
	@scripts/assert-main-checkout.sh migrate-isolated || exit 1; \
	  echo "▶ alembic upgrade head (격리 DB 5433)"
	@scripts/assert-main-checkout.sh migrate-isolated || exit 1; \
	  cd backend && \
	  DATABASE_URL=$(ISOLATED_DATABASE_URL) \
	  uv run alembic upgrade head

# 기본 모드 마이그레이션 — host 5432.
migrate: _guard-main-only
	@scripts/assert-main-checkout.sh migrate || exit 1; \
	  cd backend && uv run alembic upgrade head

# === DB 백업 / 복원 ([BL-451]) =============================================
#
# 2026-07-25 에 로컬 개발 DB 가 전소했다 — 주문 17행 · 암호화된 Bybit demo API 키 1 ·
# 전략 6종 Pine 소스 · 세션 4 · 이벤트 10. `.env.local` 에 평문 키가 없어 **API 키는 복구
# 불가**였고 사용자가 재등록해야 했다. 가드를 아무리 세워도 백업이 없으면 한 번의 사고가
# 되돌릴 수 없는 사고다.
#
# ★대상 DB 를 **인자로 명시**한다. 기본/격리 스택은 `container_name` 이 같아 "지금 뜬 것" 에
#   따라 대상이 갈리기 때문이다. 특히 `db-restore` 의 `TO=` 는 기본값이 없다 — 기본값을
#   개발 DB 로 두면 그 편의가 곧 이 항목이 막으려는 사고다.
#
#   make db-snapshot                            # 개발 DB(quantbridge) → .backups/<db>-<ts>.dump
#   make db-snapshot DB=quantbridge_test        # 다른 DB
#   make db-restore FILE=.backups/x.dump TO=quantbridge_restore_probe
BACKUP_DIR := .backups
DB_USER := quantbridge
DB ?= quantbridge

db-snapshot: _guard-main-only
	@scripts/assert-main-checkout.sh db-snapshot || exit 1; \
	  mkdir -p $(BACKUP_DIR); \
	  out="$(BACKUP_DIR)/$(DB)-$$(date -u +%Y%m%dT%H%M%SZ).dump"; \
	  echo "▶ pg_dump $(DB) → $$out"; \
	  if ! docker compose exec -T db pg_dump -U $(DB_USER) -d $(DB) -Fc > "$$out"; then \
	    rm -f "$$out"; echo "  ✗ pg_dump 실패 — 빈 파일을 남기지 않는다" >&2; exit 1; \
	  fi; \
	  size=$$(wc -c < "$$out" | tr -d ' '); \
	  if [ "$$size" -le 0 ]; then \
	    rm -f "$$out"; echo "  ✗ 덤프 크기가 0 이다" >&2; exit 1; \
	  fi; \
	  echo "  ✓ $$out ($$size bytes)"

db-restore: _guard-main-only
	@scripts/assert-main-checkout.sh db-restore || exit 1; \
	  test -n "$(FILE)" || { echo "FILE=<덤프 경로> 가 필요하다" >&2; exit 1; }; \
	  test -f "$(FILE)" || { echo "$(FILE) 가 없다" >&2; exit 1; }; \
	  test -n "$(TO)" || { echo "TO=<대상 DB> 가 필요하다 — 기본값을 두지 않는 것이 안전장치다" >&2; exit 1; }; \
	  echo "▶ pg_restore $(FILE) → $(TO)"; \
	  docker compose exec -T db pg_restore -U $(DB_USER) -d "$(TO)" --clean --if-exists < "$(FILE)"; \
	  echo "  ✓ 복원 완료 → $(TO)"

# dogfood 복원 시더 — 빈 DB 를 전 화면 사용 가능 상태로.
# 전략·백테스트를 실 서비스 계층 + 실 Celery 로 만든다(HTTP/auth 만 우회 —
# clerk SDK 가 azp 클레임을 필수로 요구해 헤드리스 HTTP 시딩이 구조적으로 불가).
# OHLCV 는 따로 안 심는다 — TimescaleProvider 가 cache-miss 시 Bybit 에서 받아
# ts.ohlcv 에 직접 쓰므로 첫 백테스트가 곧 시딩이다. 멱등.
#   make seed            전체
#   make seed ONLY=daily 하나만
seed: _guard-main-only
	@scripts/assert-main-checkout.sh seed || exit 1; \
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

docs-audit:
	scripts/docs-audit.sh

# 게이트 하네스 전량 — **게이트가 무엇을 재는지 재는** 검사기들. 합계 12.2초(2026-08-11 실측 ·
# `skip-ratchet-test` 2.9초 포함. 그쪽은 fixture 로 550 파일 트리를 케이스마다 복제한다).
# ★왜 별 타깃인가: CI 는 종전에 **하네스를 하나도 돌지 않았다**(7종 전부 CI=0). 게이트 본체만
#   돌면, 레포가 이미 깨끗하기 때문에 **판정 로직을 통째로 지워도 초록**이다 — BL-569 가
#   `bl-audit` 에서, BL-601 이 `fleet-dispatch` 에서 겪은 그 모양이고, 종전에는 그것을 잡는 유일한
#   자리가 회차 끝 로컬 `final-gates.sh` 1회였다. 즉 회귀를 **다음 회차 끝**까지 못 봤다.
# ★docker·네트워크·거래소 의존 0 — 전부 mktemp 트리 + PATH 앞단 가짜다. `soak-restart-test` 는
#   docker 를 언급하지만 **진짜 docker 를 부르지 않는다**(로그+exit 1 스텁을 PATH 앞단에 깔고
#   돌려 17/17 통과 · 스텁 호출 0회로 확인, 2026-08-11).
gate-harnesses:
	@rc=0; for h in bl-audit header-audit fleet-dispatch soak-restart soak-watch docs-audit pre-push-guard skip-ratchet; do \
	  printf '\n▶ %s-test\n' "$$h"; \
	  bash scripts/$$h-test.sh || rc=$$?; \
	done; \
	if [ "$$rc" != 0 ]; then echo; echo "✗ 하네스 실패 — 게이트가 판별력을 잃었다"; exit 1; fi; \
	echo; echo "✓ 게이트 하네스 8종 전건 통과"

header-audit:
	scripts/header-audit.sh

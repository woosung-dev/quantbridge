# QuantBridge — 로컬 개발 환경 셋업

> **목적:** 처음 클론한 개발자가 5분 내에 dev 서버 부팅.
> **SSOT:** 환경변수 정의는 [`.env.example`](../../../.env.example), 인프라는 [`docker-compose.yml`](../../../infra/compose/docker-compose.yml).

---

## 1. Prerequisites

★**버전의 SSOT 는 레포 루트 [`mise.toml`](../../../mise.toml) 하나다** ([ADR-036](../../decisions/036-tool-version-ssot-mise.md)).
아래 표에 숫자를 다시 적지 않는 이유가 그것이다 — 값을 알고 싶으면 그 파일을 열거나 `mise ls` 를 쳐라.

| 도구           | 버전          | 설치                                           |
| -------------- | ------------- | ---------------------------------------------- |
| mise           | 최신          | `brew install mise`                            |
| Node           | ← `mise.toml` | `mise install`                                 |
| Python         | ← `mise.toml` | `mise install`                                 |
| pnpm           | ← `mise.toml` | `mise install`                                 |
| uv             | ← `mise.toml` | `mise install`                                 |
| Docker Desktop | 최신          | https://www.docker.com/products/docker-desktop |
| Git            | 최신          | `brew install git`                             |

셸에 붙이기 (한 번만):

```bash
echo 'eval "$(mise activate zsh)"' >> ~/.zshrc && exec zsh
```

확인:

```bash
mise ls                 # 도구 · 실제 버전 · 출처 config 를 한 표로 — 이것이 정본 확인법
node --version
pnpm --version
uv --version
uv run python --version
docker compose version
```

> **시스템 python 불필요.** 위 4종은 mise 가 격리 설치하고, Python 의존성은 `uv` 가 관리한다.
> ★`mise` 없이 `uv` 만 도는 환경도 `pyproject.toml` 의 `requires-python` **상한**이 3.12 로 묶는다 —
> 상한이 없으면 uv 는 조건을 만족하는 **가장 높은** 것을 고른다(실측 2026-08-16: 3.13.12).
> 아래 모든 Python 명령은 `uv run` prefix 로 실행한다.

---

## 2. 클론 + 환경 설정

`.env.example`은 **3개로 분리** (Pattern 2 — 서비스별, turborepo/cal.com 표준). 각 파일이 해당 loader만 담당:

| 위치                    | Loader                                                         | 파일명                    |
| ----------------------- | -------------------------------------------------------------- | ------------------------- |
| `./.env.example`        | docker compose (`docker-compose.yml`의 `${VAR}` interpolation) | `.env` (NOT `.env.local`) |
| `apps/api/.env.example` | pydantic-settings (`cd apps/api && uv run uvicorn/celery`)     | `.env.local`              |
| `apps/web/.env.example` | Next.js (`cd apps/web && pnpm dev`)                            | `.env.local`              |

```bash
git clone <repo>
cd quant-bridge

# 3 파일 복사 (각 loader 관행에 맞춘 파일명)
cp .env.example .env                                  # docker compose (자동 로드: ./.env)
cp apps/api/.env.example apps/api/.env.local            # pydantic-settings
cp apps/web/.env.example apps/web/.env.local          # Next.js
```

> **왜 root만 `.env`?** docker compose는 `./env`만 자동 로드하고 `.env.local`은 매번 `--env-file .env.local` 플래그 필요. 표준 관행 준수가 plumbing 적음.
> **왜 apps/api/frontend는 `.env.local`?** pydantic-settings 및 Next.js 공식 관행. `.gitignore`에도 `.env.local` 패턴으로 이미 안전 처리됨.

### 2.1 필수로 채워야 할 키

**인증 (Better Auth 자체 호스팅 — [ADR-034](../../decisions/034-auth-self-host-better-auth.md)):**

★**브라우저로 나가는 값이 하나도 없다.** 구 Clerk 의 publishable key 처럼 `NEXT_PUBLIC_` 으로
번들에 인라인되는 인증 키는 이제 없다. 아래는 전부 **서버 전용**이다.

`apps/web/.env.local` (이 앱이 인증 서버 본체다):

```env
BETTER_AUTH_SECRET=          # 32자 이상. 생성: openssl rand -base64 32
BETTER_AUTH_URL=http://localhost:3000
BETTER_AUTH_DATABASE_URL=postgresql://quantbridge:password@localhost:5432/quantbridge
```

`apps/api/.env.local` (FastAPI 는 JWKS 로 검증만 한다):

```env
BETTER_AUTH_URL=http://localhost:3000   # ★FE 와 **같은 값**. 어긋나면 전건 401 이다
BETTER_AUTH_JWKS_URL=                   # 비우면 위 URL 에서 파생
```

`pnpm e2e:authed` 를 돌릴 거라면 `apps/web/.env.local` 에 `E2E_AUTH_EMAIL`·`E2E_AUTH_PASSWORD` 도
넣는다 — `e2e/global.setup.ts` 가 그 계정으로 **실제 `/sign-in` 폼**을 채운다.

**Sprint 6+ (거래소 API Key AES-256 암호화, 필수):**

`TRADING_ENCRYPTION_KEYS`는 Fernet 키. 최초 1회만 생성해서 영구 저장 (변경 시 기존 암호화된 API Key 복호화 불가):

```bash
cd apps/api
KEY=$(uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
# 3곳 모두에 추가 (docker compose: root / uvicorn: apps/api / 기타 검증 스크립트)
echo "TRADING_ENCRYPTION_KEYS=$KEY" >> .env.local
echo "TRADING_ENCRYPTION_KEYS=$KEY" >> ../../.env      # ★루트는 `.env` 다 — compose 가 `.env.local` 은 자동 로드하지 않는다
cd ../..
```

> **rotation 전략:** 콤마 구분으로 여러 키 허용 (`TRADING_ENCRYPTION_KEYS=new_key,old_key`). 첫 번째 키가 encrypt, 나머지는 decrypt 허용 — 무중단 키 교체.

> 상세 획득법은 [`clerk-setup.md`](./better-auth-setup.md). 모든 변수는 [`env-vars.md`](./env-vars.md) 카탈로그.

---

## 3. 인프라 기동 (DB + Redis)

```bash
make up   # = docker compose --project-directory . -f infra/compose/docker-compose.yml up -d

# healthy 확인 (compose 를 직접 부를 땐 반드시 위 플래그 2종을 함께 — 프로젝트명·볼륨이 루트 파생이다, ADR-029)
docker compose --project-directory . -f infra/compose/docker-compose.yml ps
# NAME                STATUS
# quantbridge-db      Up (healthy)
# quantbridge-redis   Up (healthy)
```

서비스 상세는 [`docker-compose-guide.md`](./docker-compose-guide.md).

---

## 4. Backend 셋업

```bash
cd apps/api

# 의존성 설치 (uv lock 기반)
uv sync

# DB 마이그레이션 적용
uv run alembic upgrade head        # 기본 모드 (5432) — 또는 root 에서 `make migrate`

# API 서버 (개발)
uv run uvicorn src.main:app --no-server-header --reload --host 0.0.0.0 --port 8000
```

> **Sprint 32 BL-168 — `make dev-isolated` 자동 통합.** 격리 모드 사용 시
> `make dev-isolated` 가 `up-isolated` → `migrate-isolated` → `be-isolated` (8100) +
> `fe-isolated` (3100) 를 순서대로 실행한다. fresh `make down-isolated` 후에도
> alembic schema drift 없이 첫 부팅에 신규 컬럼이 반영됨 (예: `backtests.config`).
> host uvicorn 은 `apps/api/docker-entrypoint.sh` 를 거치지 않으므로 root Makefile
> 이 alembic 적용을 책임. `docker-entrypoint.sh` 의 advisory lock 은 prod / container
> 전용 (Cloud Run multi-instance race 방어).

별도 터미널에서 Celery worker:

```bash
cd apps/api
uv run celery -A src.tasks worker --loglevel=info --concurrency=4 --pool=prefork
```

> Sprint 5 예정: docker-compose에 worker 서비스 통합.

### 4.1 Backend 검증

```bash
curl http://localhost:8000/health           # 200 {"status": "ok"}
curl http://localhost:8000/auth/me          # 401 (인증 필요)
curl http://localhost:8000/docs             # FastAPI Swagger UI
```

---

## 5. Frontend 셋업

별도 터미널:

```bash
cd apps/web
pnpm install
pnpm dev      # http://localhost:3000
```

### 5.1 Frontend 검증

- 브라우저: http://localhost:3000 → 홈 200
- `/sign-in` 로그인 동작 (`BETTER_AUTH_*` 3종 정상 등록 시)

---

## 6. 테스트 실행

### Backend

```bash
cd apps/api
uv run pytest -q              # 전체
uv run pytest tests/strategy  # 도메인별
uv run pytest -k "test_cancel" # 키워드
```

### Frontend

```bash
cd apps/web
pnpm test
```

### 린트/타입

```bash
# Backend
cd apps/api
uv run ruff check .
uv run mypy src/

# Frontend
cd apps/web
pnpm lint
pnpm tsc --noEmit
```

---

## 7. Smoke 체크리스트 (셋업 완료 검증)

| 항목                 | 명령                                                                        | 기대                                      |
| -------------------- | --------------------------------------------------------------------------- | ----------------------------------------- |
| DB healthy           | `docker compose ps`                                                         | `quantbridge-db Up (healthy)`             |
| Redis healthy        | `docker compose ps`                                                         | `quantbridge-redis Up (healthy)`          |
| API health           | `curl localhost:8000/health`                                                | 200                                       |
| API docs             | 브라우저 `localhost:8000/docs`                                              | Swagger UI                                |
| FE 홈                | 브라우저 `localhost:3000`                                                   | 200 (`BETTER_AUTH_*` 누락 시 부팅 실패)   |
| pytest               | `cd apps/api && uv run pytest -q`                                           | 모두 pass (Sprint 7a 기준 524)            |
| Migration round-trip | `cd apps/api && uv run alembic downgrade -1 && uv run alembic upgrade head` | 에러 없음                                 |
| FE tsc/lint          | `cd apps/web && pnpm tsc --noEmit && pnpm lint`                             | EXIT 0 (Sprint 7c 기준)                   |
| Sprint 7c E2E        | `/strategies` 접속 → 새 전략 생성 wizard → 편집 탭 3개                      | Monaco 5색 하이라이트 + 300ms 실시간 파싱 |

---

## 8. 자주 발생하는 문제

### 8.1 `.env.local`이 로드 안 됨

- 위치 확인: docker compose는 **root**, uvicorn은 **apps/api/**, Next.js는 **apps/web/**
- 심링크로 통일하려면: `ln -s ../.env.local apps/api/.env.local`

### 8.2 DB 연결 거부

- `docker compose ps` 로 healthy 확인
- `DATABASE_URL` 호스트가 `localhost`인지 확인 (compose 내부면 `db`)

### 8.3 Celery 워커가 task를 못 받음

- Redis URL 환경변수 확인 (`CELERY_BROKER_URL=redis://localhost:6379/1`)
- worker 로그에 `[tasks]` 등록 확인
- pool=prefork 명시 확인 (gevent/eventlet 비호환 — Sprint 4 D3)

### 8.4 ruff 통과 / CI 실패

- 로컬 `.ruff_cache` stale 가능성 — `rm -rf apps/api/.ruff_cache` 후 재실행 (Sprint 4 D1)

### 8.5 mypy `Pyright`와 결과 다름

- IDE Pyright는 uv venv 미연결로 false positive 가능 — `uv run mypy` 결과만 신뢰 (Sprint 4 D1)

### 8.6 `docker compose up` 시 `TRADING_ENCRYPTION_KEYS` missing 에러

- root `.env.local`에 `TRADING_ENCRYPTION_KEYS=<Fernet key>` 있는지 확인 (§2.1 Sprint 6+ 섹션 참조)
- `cp apps/api/.env.local .env.local` 로 빠르게 동기화 가능 (값은 동일해야 함)
- Fernet 키 자체는 `cd apps/api && uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` 로 생성

### 8.7 `python: command not found` (uv-only 환경)

- 시스템 python 없어도 됨 — 모든 python 명령은 `uv run python ...` 또는 `uv run --project backend python ...`
- cryptography / pandas 등 backend 의존성이 필요하면 `uv run` 앞에 붙이면 backend venv 자동 사용
- 일회성 실행은 `uvx --from cryptography python -c "..."` 도 가능

### 8.8 Frontend `.env.local` 미생성 시 로그인 페이지 에러

- `BETTER_AUTH_DATABASE_URL` 누락 시 Better Auth 가 인증 테이블에 붙지 못한다
- `apps/web/.env.local`에 최소 5줄:
  ```env
  BETTER_AUTH_SECRET=<openssl rand -base64 32>
  BETTER_AUTH_URL=http://localhost:3000
  BETTER_AUTH_DATABASE_URL=postgresql://quantbridge:password@localhost:5432/quantbridge
  NEXT_PUBLIC_API_URL=http://localhost:8000
  NEXT_PUBLIC_WS_URL=ws://localhost:8000
  ```

### 8.9 Monaco Editor 번들 로딩 실패 (Sprint 7c+)

- `/strategies/new` 또는 `/strategies/[id]/edit`에서 에디터 영역이 검은 박스로 남아있음
- `next/dynamic({ ssr: false })` 패턴이므로 브라우저만 로드. Next.js dev 로그에 `@monaco-editor/react` chunk 오류 있는지 확인
- `pnpm install` 재실행 + `.next/` 삭제 후 `pnpm dev` 재시작

---

## 9. 다음 단계

- 환경 변수 의미: [`env-vars.md`](./env-vars.md)
- 인증 셋업 상세: [`better-auth-setup.md`](./better-auth-setup.md)
- Compose 운영: [`docker-compose-guide.md`](./docker-compose-guide.md)
- CI/CD: [`ci-cd.md`](./ci-cd.md)
- 개발 방법론: [`development-methodology.md`](./workflows/development-methodology.md)
- Sprint 진행 상태: [`status.md`](../../status.md)

---

## 변경 이력

- **2026-04-16** — 초안 작성 (Sprint 5 Stage A)
- **2026-04-17** — Sprint 7c 반영: Python 3.12+/uv-only 명시, TRADING_ENCRYPTION_KEYS 생성 섹션(§2.1 Sprint 6+), 테스트 수 368→524, FE tsc/lint smoke, §8.6~8.9 트러블슈팅 4건 추가
- **2026-04-17** — `.env.example` Pattern 2(service별 분리)로 재구성 — root `.env` (compose), `apps/api/.env.local` (uvicorn), `apps/web/.env.local` (Next.js). 3 파일로 분리. turborepo/cal.com 표준 준수

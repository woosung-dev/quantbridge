# QuantBridge — 로컬 개발 환경 셋업

> **목적:** 처음 클론한 개발자가 5분 내에 dev 서버 부팅.
> **SSOT:** 환경변수 정의는 [`../../.env.example`](../../.env.example), 인프라는 [`../../docker-compose.yml`](../../docker-compose.yml).

---

## 1. Prerequisites

| 도구 | 버전 | 설치 |
|------|------|------|
| Python | 3.12+ | `brew install python@3.12` 또는 `uv python install 3.12` |
| uv | 최신 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Node | 22+ | `brew install node` 또는 nvm |
| pnpm | 최신 | `npm install -g pnpm` 또는 `corepack enable` |
| Docker Desktop | 최신 | https://www.docker.com/products/docker-desktop |
| Git | 최신 | `brew install git` |

확인:
```bash
uv --version                              # uv가 python 3.12+ 자동 관리
uv run --project backend python --version # 3.12+
node --version                            # 22+
pnpm --version
docker --version
docker compose version
```

> **시스템 python 불필요.** `uv`가 프로젝트별 Python + 의존성 격리 관리. 아래 모든 Python 명령은 `uv run` prefix로 실행.

---

## 2. 클론 + 환경 설정

`.env.example`은 **3개로 분리** (Pattern 2 — 서비스별, turborepo/cal.com 표준). 각 파일이 해당 loader만 담당:

| 위치 | Loader | 파일명 |
|------|--------|-------|
| `./.env.example` | docker compose (`docker-compose.yml`의 `${VAR}` interpolation) | `.env` (NOT `.env.local`) |
| `backend/.env.example` | pydantic-settings (`cd backend && uv run uvicorn/celery`) | `.env.local` |
| `frontend/.env.example` | Next.js (`cd frontend && pnpm dev`) | `.env.local` |

```bash
git clone <repo>
cd quant-bridge

# 3 파일 복사 (각 loader 관행에 맞춘 파일명)
cp .env.example .env                                  # docker compose (자동 로드: ./.env)
cp backend/.env.example backend/.env.local            # pydantic-settings
cp frontend/.env.example frontend/.env.local          # Next.js
```

> **왜 root만 `.env`?** docker compose는 `./env`만 자동 로드하고 `.env.local`은 매번 `--env-file .env.local` 플래그 필요. 표준 관행 준수가 plumbing 적음.
> **왜 backend/frontend는 `.env.local`?** pydantic-settings 및 Next.js 공식 관행. `.gitignore`에도 `.env.local` 패턴으로 이미 안전 처리됨.

### 2.1 필수로 채워야 할 키

**Sprint 3+ (Clerk 인증):**

```env
CLERK_SECRET_KEY=sk_test_...                  # Clerk Dashboard → API Keys → Secret keys
CLERK_PUBLISHABLE_KEY=pk_test_...             # Clerk Dashboard → API Keys → Publishable keys
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_... # 동일 값 (Next.js 노출용)
# CLERK_WEBHOOK_SECRET은 Sprint 7 배포까지 placeholder OK
```

**Sprint 6+ (거래소 API Key AES-256 암호화, 필수):**

`TRADING_ENCRYPTION_KEYS`는 Fernet 키. 최초 1회만 생성해서 영구 저장 (변경 시 기존 암호화된 API Key 복호화 불가):

```bash
cd backend
KEY=$(uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
# 3곳 모두에 추가 (docker compose: root / uvicorn: backend / 기타 검증 스크립트)
echo "TRADING_ENCRYPTION_KEYS=$KEY" >> .env.local
echo "TRADING_ENCRYPTION_KEYS=$KEY" >> ../.env.local
cd ..
```

> **rotation 전략:** 콤마 구분으로 여러 키 허용 (`TRADING_ENCRYPTION_KEYS=new_key,old_key`). 첫 번째 키가 encrypt, 나머지는 decrypt 허용 — 무중단 키 교체.

> 상세 획득법은 [`clerk-setup.md`](./clerk-setup.md). 모든 변수는 [`env-vars.md`](./env-vars.md) 카탈로그.

---

## 3. 인프라 기동 (DB + Redis)

```bash
docker compose up -d

# healthy 확인
docker compose ps
# NAME                STATUS
# quantbridge-db      Up (healthy)
# quantbridge-redis   Up (healthy)
```

서비스 상세는 [`../06_devops/docker-compose-guide.md`](../06_devops/docker-compose-guide.md).

---

## 4. Backend 셋업

```bash
cd backend

# 의존성 설치 (uv lock 기반)
uv sync

# DB 마이그레이션 적용
uv run alembic upgrade head

# API 서버 (개발)
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

별도 터미널에서 Celery worker:
```bash
cd backend
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
cd frontend
pnpm install
pnpm dev      # http://localhost:3000
```

### 5.1 Frontend 검증

- 브라우저: http://localhost:3000 → 홈 200
- Clerk 로그인 동작 (Clerk 키 정상 등록 시)

---

## 6. 테스트 실행

### Backend
```bash
cd backend
uv run pytest -q              # 전체
uv run pytest tests/strategy  # 도메인별
uv run pytest -k "test_cancel" # 키워드
```

### Frontend
```bash
cd frontend
pnpm test
```

### 린트/타입
```bash
# Backend
cd backend
uv run ruff check .
uv run mypy src/

# Frontend
cd frontend
pnpm lint
pnpm tsc --noEmit
```

---

## 7. Smoke 체크리스트 (셋업 완료 검증)

| 항목 | 명령 | 기대 |
|------|------|------|
| DB healthy | `docker compose ps` | `quantbridge-db Up (healthy)` |
| Redis healthy | `docker compose ps` | `quantbridge-redis Up (healthy)` |
| API health | `curl localhost:8000/health` | 200 |
| API docs | 브라우저 `localhost:8000/docs` | Swagger UI |
| FE 홈 | 브라우저 `localhost:3000` | 200 (Clerk 키 누락 시 401 페이지 가능) |
| pytest | `cd backend && uv run pytest -q` | 모두 pass (Sprint 7a 기준 524) |
| Migration round-trip | `cd backend && uv run alembic downgrade -1 && uv run alembic upgrade head` | 에러 없음 |
| FE tsc/lint | `cd frontend && pnpm tsc --noEmit && pnpm lint` | EXIT 0 (Sprint 7c 기준) |
| Sprint 7c E2E | `/strategies` 접속 → 새 전략 생성 wizard → 편집 탭 3개 | Monaco 5색 하이라이트 + 300ms 실시간 파싱 |

---

## 8. 자주 발생하는 문제

### 8.1 `.env.local`이 로드 안 됨
- 위치 확인: docker compose는 **root**, uvicorn은 **backend/**, Next.js는 **frontend/**
- 심링크로 통일하려면: `ln -s ../.env.local backend/.env.local`

### 8.2 DB 연결 거부
- `docker compose ps` 로 healthy 확인
- `DATABASE_URL` 호스트가 `localhost`인지 확인 (compose 내부면 `db`)

### 8.3 Celery 워커가 task를 못 받음
- Redis URL 환경변수 확인 (`CELERY_BROKER_URL=redis://localhost:6379/1`)
- worker 로그에 `[tasks]` 등록 확인
- pool=prefork 명시 확인 (gevent/eventlet 비호환 — Sprint 4 D3)

### 8.4 ruff 통과 / CI 실패
- 로컬 `.ruff_cache` stale 가능성 — `rm -rf backend/.ruff_cache` 후 재실행 (Sprint 4 D1)

### 8.5 mypy `Pyright`와 결과 다름
- IDE Pyright는 uv venv 미연결로 false positive 가능 — `uv run mypy` 결과만 신뢰 (Sprint 4 D1)

### 8.6 `docker compose up` 시 `TRADING_ENCRYPTION_KEYS` missing 에러
- root `.env.local`에 `TRADING_ENCRYPTION_KEYS=<Fernet key>` 있는지 확인 (§2.1 Sprint 6+ 섹션 참조)
- `cp backend/.env.local .env.local` 로 빠르게 동기화 가능 (값은 동일해야 함)
- Fernet 키 자체는 `cd backend && uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` 로 생성

### 8.7 `python: command not found` (uv-only 환경)
- 시스템 python 없어도 됨 — 모든 python 명령은 `uv run python ...` 또는 `uv run --project backend python ...`
- cryptography / pandas 등 backend 의존성이 필요하면 `uv run` 앞에 붙이면 backend venv 자동 사용
- 일회성 실행은 `uvx --from cryptography python -c "..."` 도 가능

### 8.8 Frontend `.env.local` 미생성 시 로그인 페이지 에러
- `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` 누락 시 Clerk가 "Missing publishable key" 에러
- `frontend/.env.local`에 최소 3줄:
  ```env
  NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
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
- Clerk 셋업 상세: [`clerk-setup.md`](./clerk-setup.md)
- Compose 운영: [`../06_devops/docker-compose-guide.md`](../06_devops/docker-compose-guide.md)
- CI/CD: [`../06_devops/ci-cd.md`](../06_devops/ci-cd.md)
- 개발 방법론: [`../guides/development-methodology.md`](../guides/development-methodology.md)
- Sprint 진행 상태: [`../TODO.md`](../TODO.md)

---

## 변경 이력

- **2026-04-16** — 초안 작성 (Sprint 5 Stage A)
- **2026-04-17** — Sprint 7c 반영: Python 3.12+/uv-only 명시, TRADING_ENCRYPTION_KEYS 생성 섹션(§2.1 Sprint 6+), 테스트 수 368→524, FE tsc/lint smoke, §8.6~8.9 트러블슈팅 4건 추가
- **2026-04-17** — `.env.example` Pattern 2(service별 분리)로 재구성 — root `.env` (compose), `backend/.env.local` (uvicorn), `frontend/.env.local` (Next.js). 3 파일로 분리. turborepo/cal.com 표준 준수

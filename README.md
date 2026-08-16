# QuantBridge

> **TradingView Pine Script 전략 → 백테스트 → 스트레스 테스트 → 데모/라이브 트레이딩 파이프라인.**
> Pine Script를 정직하게 파싱(미지원 함수 한 개라도 포함되면 전체 Unsupported 반환)하고, CCXT 기반으로 주요 거래소에 자동 주문을 집행한다. AES-256 API Key 암호화 + Kill Switch로 리스크 경계를 명시적으로 관리.

---

## Tech Stack

| 레이어        | 기술                                                                                                                                                |
| ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------- |
| Frontend      | Next.js 16 App Router · TypeScript Strict · Tailwind CSS v4 · shadcn/ui v4 (Base UI) · Monaco Editor · React Query · Zustand · Zod v4 · Better Auth |
| Backend       | FastAPI · SQLModel 2.0 · Celery + Redis · PostgreSQL + TimescaleDB · Alembic · Pydantic v2 · CCXT (async)                                           |
| Parser        | 커스텀 Pine v4/v5 토크나이저·인터프리터 (`exec`/`eval` 금지 — ADR 003)                                                                              |
| Backtest      | `pine_v2` 자체 AST 인터프리터 (bar-by-bar SSOT, ADR-011). 지표도 `pine_v2/stdlib.py` 가 pandas/numpy 로 직접 계산                                   |
| 패키지 매니저 | `uv` (backend) · `pnpm` (frontend)                                                                                                                  |
| 인증          | Better Auth 자체 호스팅 (Next 앱이 인증 서버 · FastAPI 는 JWKS 검증) — [ADR-034](docs/decisions/034-auth-self-host-better-auth.md)                  |

---

## Quick Start (로컬 개발)

### 1. Prerequisites

```bash
# macOS 기준
brew install node python@3.12 docker git
npm install -g pnpm
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 2. Clone + 환경 변수

`.env.example`은 서비스별로 분리됨 (loader 관행에 맞춤). root는 docker compose가 자동 로드하는 `.env`, apps/api/frontend는 각 loader 관행인 `.env.local`.

```bash
git clone <repo-url> quant-bridge
cd quant-bridge

# Root (docker compose) — 파일명 주의: .env (NOT .env.local)
cp .env.example .env

# Backend (pydantic-settings가 .env.local 읽음)
cp apps/api/.env.example apps/api/.env.local

# Frontend (Next.js가 .env.local 읽음)
cp apps/web/.env.example apps/web/.env.local
```

필수 실값 교체 (각 파일 `[필수 …]` 마킹된 키):

- `apps/api/.env.local` + `.env`: `TRADING_ENCRYPTION_KEYS` ([생성 방법](#3-trading_encryption_keys-생성-sprint-6)) · `BETTER_AUTH_URL`
- `apps/web/.env.local`: `BETTER_AUTH_SECRET` (`openssl rand -base64 32`) · `BETTER_AUTH_URL` · `BETTER_AUTH_DATABASE_URL`

> **왜 3파일?** docker compose는 `./env`만 자동 로드, backend pydantic-settings는 `apps/api/.env.local` → `apps/api/.env` 순서로 로드, Next.js는 `apps/web/.env.local` 로드. 파일 하나에 몰면 "이 변수가 어디서 쓰이나?" 추론 필요 + loader 간 약속이 drift됨. 서비스별 분리가 turborepo/cal.com/Vercel 공식 예제 표준.

### 3. `TRADING_ENCRYPTION_KEYS` 생성 (Sprint 6+)

거래소 API Key AES-256 암호화용 Fernet 키. **최초 1회만 생성**, 변경 시 기존 암호화된 API Key 복호화 불가:

```bash
cd apps/api
KEY=$(uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
echo "TRADING_ENCRYPTION_KEYS=$KEY" >> .env.local      # uvicorn/celery (로컬)
echo "TRADING_ENCRYPTION_KEYS=$KEY" >> ../../.env      # docker compose 컨테이너 (레포 루트)
cd ../..
```

두 파일 값이 **반드시 동일**해야 compose 워커와 로컬 uvicorn이 같은 키로 복호화 일관 유지.

### 4. 인프라 + 서버

```bash
# Postgres + Redis + TimescaleDB (background)
docker compose up -d db redis

# Backend (마이그레이션 + API 서버 + Celery worker — 각 별도 터미널)
cd apps/api
uv sync                              # 의존성 설치
uv run alembic upgrade head          # DB 스키마
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
uv run celery -A src.tasks worker --loglevel=info --concurrency=4 --pool=prefork

# Frontend (별도 터미널)
cd apps/web
pnpm install
pnpm dev                             # http://localhost:3000
```

### 5. Smoke 검증

```bash
curl http://localhost:8000/health                   # 200 {"status":"ok"}
open http://localhost:8000/docs                     # Swagger UI
open http://localhost:3000                          # FE 홈 → 로그인
cd apps/api && uv run pytest -q                      # ~1831 tests pass (2026-05 기준)
```

상세 셋업·환경변수·트러블슈팅은 **[`docs/reference/operations/local-setup.md`](docs/reference/operations/local-setup.md)** 참조.

---

## Documentation

| 위치                                                                                    | 용도                                                                 |
| --------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| [`AGENTS.md`](AGENTS.md)                                                                | 개발 원칙·스택 규칙·새 세션의 읽기 순서 (LLM/에이전트 + 개발자 공용) |
| [`DESIGN.md`](DESIGN.md)                                                                | Stage 2 디자인 시스템 — 색상·타이포·간격 토큰 SSOT                   |
| [`docs/README.md`](docs/README.md)                                                      | 현행 문서 지도 — 상태·로드맵·백로그·정본의 진입점                    |
| [`docs/status.md`](docs/status.md)                                                      | 활성 또는 다음 스프린트의 실행 계약                                  |
| [`apps/api/AGENTS.md`](apps/api/AGENTS.md) · [`apps/web/AGENTS.md`](apps/web/AGENTS.md) | 스택별 강제 규칙 (FastAPI 3-Layer · React Hooks 안전 등 — ADR-027)   |

---

## Sprint 진행 요약 (2026-04-17 기준 — ⚠ Sprint 7c 에서 고정, 이력 스냅샷)

> **현행 sprint 상태·이력은 [`docs/status.md`](docs/status.md) + [`docs/dev-log/INDEX.md`](docs/dev-log/INDEX.md) SSOT** (현재 Sprint 60+, Beta 진입). 아래 표는 Sprint 1-7c 초기 이력만.

| Sprint      | 내용                                                                                           | 상태                        |
| ----------- | ---------------------------------------------------------------------------------------------- | --------------------------- |
| 1~4         | Pine Parser MVP · 구 vectorbt Engine(철거됨) · Strategy CRUD API · Celery + Backtest REST      | ✅ 완료                     |
| 5 Stage A/B | DateTime tz-aware · TimescaleDB · CCXT + TimescaleProvider · docker-compose worker/beat        | ✅ 완료 (PR #6/#7)          |
| 6           | Trading 데모 MVP — webhook 자동 집행 · Kill Switch · AES-256 API Key 암호화                    | ✅ 완료 (PR #9)             |
| 7a          | Bybit Futures + Cross Margin — leverage · margin_mode · leverage cap                           | ✅ 완료 (PR #10, 524 tests) |
| 7c          | FE 따라잡기 — Strategy CRUD UI (목록 · 3-step wizard · 편집 3탭 · delete 409 archive fallback) | ✅ 완료 (본 README와 함께)  |
| 7b          | Trading Sessions + OKX 멀티 거래소                                                             | 🔜 다음                     |
| 8+          | Binance mainnet 실거래 · Kill Switch `capital_base` 동적 바인딩                                | 예정                        |

상세: [`AGENTS.md`](AGENTS.md) "현재 작업" 섹션.

---

## License

Private (개인 프로젝트).

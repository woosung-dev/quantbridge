# QuantBridge

> **TradingView Pine Script 전략 → 백테스트 → 스트레스 테스트 → 데모/라이브 트레이딩 파이프라인.**
> Pine Script를 정직하게 파싱(미지원 함수 한 개라도 포함되면 전체 Unsupported 반환)하고, CCXT 기반으로 주요 거래소에 자동 주문을 집행한다. AES-256 API Key 암호화 + Kill Switch로 리스크 경계를 명시적으로 관리.

---

## Tech Stack

| 레이어 | 기술 |
|-------|------|
| Frontend | Next.js 16 App Router · TypeScript Strict · Tailwind CSS v4 · shadcn/ui v4 (Base UI) · Monaco Editor · React Query · Zustand · Zod v4 · Clerk |
| Backend | FastAPI · SQLModel 2.0 · Celery + Redis · PostgreSQL + TimescaleDB · Alembic · Pydantic v2 · CCXT (async) |
| Parser | 커스텀 Pine v4/v5 토크나이저·인터프리터 (`exec`/`eval` 금지 — ADR 003) |
| Backtest | vectorbt 기반 벡터화 엔진 |
| 패키지 매니저 | `uv` (backend) · `pnpm` (frontend) |
| 인증 | Clerk (Frontend + Backend JWT 검증) |

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

`.env.example`은 서비스별로 분리됨 (loader 관행에 맞춤). root는 docker compose가 자동 로드하는 `.env`, backend/frontend는 각 loader 관행인 `.env.local`.

```bash
git clone <repo-url> quant-bridge
cd quant-bridge

# Root (docker compose) — 파일명 주의: .env (NOT .env.local)
cp .env.example .env

# Backend (pydantic-settings가 .env.local 읽음)
cp backend/.env.example backend/.env.local

# Frontend (Next.js가 .env.local 읽음)
cp frontend/.env.example frontend/.env.local
```

필수 실값 교체 (각 파일 `[필수 …]` 마킹된 키):
- `backend/.env.local` + `.env`: `CLERK_SECRET_KEY` (Clerk Dashboard → API Keys → Secret keys), `TRADING_ENCRYPTION_KEYS` ([생성 방법](#3-trading_encryption_keys-생성-sprint-6))
- `frontend/.env.local`: `NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY` (Clerk Dashboard → Publishable keys)

> **왜 3파일?** docker compose는 `./env`만 자동 로드, backend pydantic-settings는 `backend/.env.local` → `backend/.env` 순서로 로드, Next.js는 `frontend/.env.local` 로드. 파일 하나에 몰면 "이 변수가 어디서 쓰이나?" 추론 필요 + loader 간 약속이 drift됨. 서비스별 분리가 turborepo/cal.com/Vercel 공식 예제 표준.

### 3. `TRADING_ENCRYPTION_KEYS` 생성 (Sprint 6+)

거래소 API Key AES-256 암호화용 Fernet 키. **최초 1회만 생성**, 변경 시 기존 암호화된 API Key 복호화 불가:

```bash
cd backend
KEY=$(uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
echo "TRADING_ENCRYPTION_KEYS=$KEY" >> .env.local      # uvicorn/celery (로컬)
echo "TRADING_ENCRYPTION_KEYS=$KEY" >> ../.env         # docker compose 컨테이너
cd ..
```

두 파일 값이 **반드시 동일**해야 compose 워커와 로컬 uvicorn이 같은 키로 복호화 일관 유지.

### 4. 인프라 + 서버

```bash
# Postgres + Redis + TimescaleDB (background)
docker compose up -d db redis

# Backend (마이그레이션 + API 서버 + Celery worker — 각 별도 터미널)
cd backend
uv sync                              # 의존성 설치
uv run alembic upgrade head          # DB 스키마
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
uv run celery -A src.tasks worker --loglevel=info --concurrency=4 --pool=prefork

# Frontend (별도 터미널)
cd frontend
pnpm install
pnpm dev                             # http://localhost:3000
```

### 5. Smoke 검증

```bash
curl http://localhost:8000/health                   # 200 {"status":"ok"}
open http://localhost:8000/docs                     # Swagger UI
open http://localhost:3000                          # FE 홈 → Clerk 로그인
cd backend && uv run pytest -q                      # 524 tests pass (Sprint 7a 기준)
```

상세 셋업·환경변수·트러블슈팅은 **[`docs/05_env/local-setup.md`](docs/05_env/local-setup.md)** 참조.

---

## Documentation

| 위치 | 용도 |
|------|------|
| [`AGENTS.md`](AGENTS.md) | 개발 원칙·스택 규칙·현재 작업 상태 (LLM/에이전트 + 개발자 공용) |
| [`DESIGN.md`](DESIGN.md) | Stage 2 디자인 시스템 — 색상·타이포·간격 토큰 SSOT |
| [`QUANTBRIDGE_PRD.md`](QUANTBRIDGE_PRD.md) | 제품 요구사항 |
| [`docs/`](docs/) | 설계 산출물 (00_project ~ 07_infra) · ADR (`dev-log/`) · 로컬 셋업 (`05_env/`) · 프로토타입 (`prototypes/`) |
| [`docs/TODO.md`](docs/TODO.md) | Sprint 진행 상태 + 백로그 |
| [`docs/superpowers/plans/`](docs/superpowers/plans/) | superpowers:writing-plans 산출물 (Sprint별 implementation plan) |
| [`.ai/rules/`](.ai/rules/) | 스택별 강제 규칙 (backend.md, frontend.md, typescript.md 등) |

---

## Sprint 진행 요약 (2026-04-17 기준)

| Sprint | 내용 | 상태 |
|--------|------|------|
| 1~4 | Pine Parser MVP · vectorbt Engine · Strategy CRUD API · Celery + Backtest REST | ✅ 완료 |
| 5 Stage A/B | DateTime tz-aware · TimescaleDB · CCXT + TimescaleProvider · docker-compose worker/beat | ✅ 완료 (PR #6/#7) |
| 6 | Trading 데모 MVP — webhook 자동 집행 · Kill Switch · AES-256 API Key 암호화 | ✅ 완료 (PR #9) |
| 7a | Bybit Futures + Cross Margin — leverage · margin_mode · leverage cap | ✅ 완료 (PR #10, 524 tests) |
| 7c | FE 따라잡기 — Strategy CRUD UI (목록 · 3-step wizard · 편집 3탭 · delete 409 archive fallback) | ✅ 완료 (본 README와 함께) |
| 7b | Trading Sessions + OKX 멀티 거래소 | 🔜 다음 |
| 8+ | Binance mainnet 실거래 · Kill Switch `capital_base` 동적 바인딩 | 예정 |

상세: [`AGENTS.md`](AGENTS.md) "현재 작업" 섹션.

---

## License

Private (개인 프로젝트).

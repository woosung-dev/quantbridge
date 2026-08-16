# QuantBridge — Backend

> 위치: `apps/api/` (구 `backend/` — 2026-08-13 [ADR-029](../../docs/decisions/029-monorepo-standard-layout.md) 재배치)

FastAPI + SQLModel + Celery. 100% 비동기. 3-Layer(Router/Service/Repository) 도메인 모듈러.

## 준비

```bash
uv sync
cp .env.example .env.local      # backend 전용 env (pydantic-settings 자동 로드)
```

> `.env.example`은 **서비스별 분리**. backend는 `apps/api/.env.example` 사용. docker compose는 루트 `./.env`, Next.js는 `apps/web/.env.local` — 전체 구조는 [루트 README](../../README.md#2-clone--환경-변수) + [local-setup.md](../../docs/reference/operations/local-setup.md#2-클론--환경-설정) 참조.

## 실행

```bash
uv run uvicorn src.main:app --no-server-header --reload --host 0.0.0.0 --port 8000
```

## 개발 도구

```bash
uv run ruff check .        # 린트
uv run ruff format .       # 포맷
uv run mypy src            # 타입 체크
uv run pytest              # 테스트
```

## 마이그레이션

```bash
uv run alembic revision --autogenerate -m "message"
uv run alembic upgrade head
```

## 디렉토리

- `src/core/` — `config.py` 하나. 전 도메인의 `Settings`(pydantic-settings)
- `src/common/` — 도메인을 모르는 기술 기반. DB 세션·예외 베이스·Redis·redlock·metrics·rate limit·로깅·알림 발송(Slack/Telegram)
- `src/{strategy,backtest,stress_test,optimizer,trading,waitlist}/` — 도메인별 3-Layer (router/service/repository/schemas/models)
- `src/market_data/` — 공개 REST 없는 **내부 전용 subdomain**. OHLCV provider(CCXT·Timescale·fixture)를 위 도메인들에 공급한다
- `src/auth/` — 사용자 원장 + 탈퇴. **JWT 검증기는 `src/realtime/auth.py`** 다 (Better Auth JWKS — [ADR-034](../../docs/decisions/034-auth-self-host-better-auth.md))
- `src/realtime/` · `src/health/` · `src/tasks/`(Celery entrypoint) · `src/scripts/`(운영 helper) — 3-Layer 비적용. 예외 근거는 `AGENTS.md` §3

> `exchange/` 는 없다 — [ADR-018](../../docs/decisions/018-sprint12-ws-supervisor-and-exchange-stub-removal.md) 로 `trading/` 에 통합됐다.

## 규칙

자세한 아키텍처 규칙은 저장소 루트의 `apps/api/AGENTS.md` 참조.

- **AsyncSession은 Repository만 보유.** Service는 Repository 주입 → 트랜잭션 경계 담당.
- **`.dict()` 금지** → `.model_dump()`. **`session.exec()` 금지** → `await session.execute(...)`.
- Pine 트랜스파일에서 **`exec()`/`eval()` 절대 금지** (ADR-003).

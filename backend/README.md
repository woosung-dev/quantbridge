# QuantBridge — Backend

FastAPI + SQLModel + Celery. 100% 비동기. 3-Layer(Router/Service/Repository) 도메인 모듈러.

## 준비

```bash
uv sync
cp ../.env.example .env.local   # 루트 .env.example 기준
```

## 실행

```bash
uv run uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
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

- `src/core/` — config (pydantic-settings)
- `src/common/` — database, exceptions, pagination
- `src/auth/` — Clerk JWT 검증
- `src/{strategy,backtest,stress_test,optimizer,trading,exchange,market_data}/` — 도메인별 3-Layer

## 규칙

자세한 아키텍처 규칙은 저장소 루트의 `.ai/rules/backend.md` 참조.

- **AsyncSession은 Repository만 보유.** Service는 Repository 주입 → 트랜잭션 경계 담당.
- **`.dict()` 금지** → `.model_dump()`. **`session.exec()` 금지** → `await session.execute(...)`.
- Pine 트랜스파일에서 **`exec()`/`eval()` 절대 금지** (ADR-003).

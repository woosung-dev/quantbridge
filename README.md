# QuantBridge

[![CI](https://github.com/woosung-dev/quantbridge/actions/workflows/ci.yml/badge.svg)](https://github.com/woosung-dev/quantbridge/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Next.js](https://img.shields.io/badge/next.js-16-black)
![License](https://img.shields.io/badge/license-private-lightgrey)

> **TradingView Pine Script 전략 → 백테스트 → 스트레스 테스트 → 최적화 → 데모/라이브 트레이딩을 한 파이프라인으로.**
> Pine Script 를 트랜스파일 없이 AST 로 해석·실행(`pine_v2` 인터프리터)하고, 미지원 함수가 하나라도 있으면
> 전체 Unsupported 로 정직하게 거절하며, CCXT 로 거래소 주문을 집행한다. AES-256 API Key 암호화 + Kill Switch.

## Highlights

- **`pine_v2` 자체 인터프리터** — 백테스트·라이브 신호의 단일 진실. `exec`/`eval` 금지, bar-by-bar 이벤트 루프 (ADR-003/011)
- **Trust Layer** — pine_v2 결과의 3-Layer parity 를 CI 가 회귀 검증 (ADR-020)
- **라이브 안전 경계** — Kill Switch 리스크 게이트 · 조건부 체결 권한은 주문 원장 (ADR-025) · 현재 Bybit demo 전용
- **검증 문화** — BE 4,199 / FE 1,084 테스트 (2026-08-06 실측) · `scripts/` 게이트 체인(bl-audit · docs-audit · soak-gate)

## Quick Start

```bash
brew install node python@3.12 docker git && npm i -g pnpm
curl -LsSf https://astral.sh/uv/install.sh | sh

git clone https://github.com/woosung-dev/quantbridge.git quant-bridge && cd quant-bridge
cp .env.example .env                             # docker compose 용
cp backend/.env.example backend/.env.local       # pydantic-settings 용
cp frontend/.env.example frontend/.env.local     # Next.js 용
# [필수] 키 채우기: CLERK_SECRET_KEY · NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY · TRADING_ENCRYPTION_KEYS(아래)

make dev          # db+redis 기동 → BE 8000 · FE 3000 (상세 타깃: make help)
```

`TRADING_ENCRYPTION_KEYS`(거래소 API Key 암호화용 Fernet, **최초 1회만** — 변경 시 기존 키 복호화 불가):

```bash
cd backend && KEY=$(uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())") \
  && echo "TRADING_ENCRYPTION_KEYS=$KEY" >> .env.local && echo "TRADING_ENCRYPTION_KEYS=$KEY" >> ../.env && cd ..
# 두 파일 값이 동일해야 compose 워커와 로컬 uvicorn 이 같은 키로 복호화한다
```

Smoke: `curl localhost:8000/health` → 200 · `open localhost:3000` → Clerk 로그인.
상세 셋업·트러블슈팅 = [`docs/reference/operations/local-setup.md`](docs/reference/operations/local-setup.md) ·
검증 게이트 = [`docs/reference/operations/gates-and-traps.md`](docs/reference/operations/gates-and-traps.md).

## Architecture at a Glance

FastAPI + SQLModel/SQLAlchemy 2.0 + Celery(prefork) + PostgreSQL/TimescaleDB + Redis 백엔드에
Next.js 16(App Router) + React Query + Zustand + shadcn/ui v4 프론트. 핵심 도메인 6종 =
Strategy(`pine_v2`) / Backtest / Stress Test / Optimizer / Trading / Market Data.

- 시스템 조립: [`docs/reference/architecture/system-architecture.md`](docs/reference/architecture/system-architecture.md)
- 데이터 흐름: [`docs/reference/architecture/data-flow.md`](docs/reference/architecture/data-flow.md)
- Pine 실행: [`docs/reference/architecture/pine-execution-architecture.md`](docs/reference/architecture/pine-execution-architecture.md)
- 패키지 매니저 `uv`(backend) · `pnpm`(frontend) · 인증 Clerk(FE + BE JWT)

## Documentation

| 문서                                                             | 역할                                                                    |
| ---------------------------------------------------------------- | ----------------------------------------------------------------------- |
| [`CONTEXT.md`](CONTEXT.md)                                       | **도메인 헌법** — 용어/관계 SSOT. 도메인 작업 전 필독                   |
| [`AGENTS.md`](AGENTS.md)                                         | 에이전트/개발자 오리엔테이션 — 읽기 순서·Golden Rules·커맨드            |
| [`docs/README.md`](docs/README.md)                               | 문서 지도 — 상태 3종·reference·decisions·lessons 진입점                 |
| [`docs/status.md`](docs/status.md)                               | 활성/다음 스프린트의 실행 계약                                          |
| [`docs/decisions/`](docs/decisions/)                             | ADR 26편 — 왜 이 선택인가 (SSOT 원칙 = ADR-026)                         |
| [`DESIGN.md`](DESIGN.md)                                         | 디자인 시스템 — 색상·타이포·간격 토큰 SSOT                              |
| `.claude/rules/`                                                 | 스택 규칙 (backend/frontend/nextjs-shared — `paths` 매칭 시 자동 로드)  |

## License

Private (개인 프로젝트).

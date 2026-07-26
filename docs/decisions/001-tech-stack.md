# ADR-001: 기술 스택 결정

> **상태:** 확정
> **일자:** 2026-04-13
> **작성자:** QuantBridge 팀

---

## 컨텍스트

QuantBridge는 TradingView Pine Script 전략을 백테스트·데모·라이브 트레이딩으로 연결하는 퀀트 플랫폼이다.
초기 PRD 작성 후, `.ai/` 코딩 규칙(ai-rules)과의 정합성 분석을 수행하여 기술 스택을 확정했다.

## 결정

### Frontend

| 항목 | 결정 | 근거 |
|------|------|------|
| Framework | **Next.js 16** (App Router) | .ai/ spec 표준. params/searchParams Promise 패턴, proxy.ts 사용 |
| Language | **TypeScript Strict** | `any` 금지, 명시적 API 타입 |
| Styling | **Tailwind CSS v4 + shadcn/ui v4** | .ai/ spec 표준. @base-ui/react 기반 |
| State (Server) | **React Query v5** (TanStack Query) | Query Key Factory 패턴, 서버 상태 전담 |
| State (Client) | **Zustand** (최소화) | 글로벌 UI 상태만 (sidebar, theme). 도메인 상태는 React Query |
| Form | **react-hook-form + Zod v4** | 스키마 퍼스트 검증, `import from "zod/v4"` |
| Auth | **Clerk** | proxy.ts 미들웨어, useAuth()/useUser() 클라이언트 훅 |
| Charts | **TradingView Lightweight Charts v4** | 트레이딩 차트 업계 표준 |
| Editor | **Monaco Editor** | Pine Script 편집기, 구문 강조 |
| 3D Viz | **Plotly.js** | 파라미터 서피스 시각화 |
| Package Manager | **pnpm** | .ai/ spec 표준 |
| Deploy | **Vercel** (MVP) | .ai/ spec 표준, Next.js 최적화 |

### Backend

| 항목 | 결정 | 근거 |
|------|------|------|
| Framework | **FastAPI** (100% async) | 고성능 Python 웹 프레임워크 |
| ORM | **SQLModel** + SQLAlchemy 2.0 (asyncpg) | .ai/ spec 표준. `await session.execute()` 패턴 |
| Validation | **Pydantic V2** + pydantic-settings | `.model_dump()`, `@model_validator`, `ConfigDict` |
| Auth | **Clerk JWT 검증** | `clerk-sdk-python`으로 토큰 검증만 수행 |
| Task Queue | **Celery + Redis** | 장시간 백테스트/최적화 필수. BackgroundTasks로는 부족 |
| Architecture | **Router/Service/Repository 3-Layer** | .ai/ spec 표준. Router 10줄 이내, DB접근은 Repository만 |
| Package Manager | **uv** | .ai/ spec 표준 |
| Deploy | **Docker** (MVP), Cloud Run (추후) | Celery 워커 포함 |

### Database

| 항목 | 결정 | 근거 |
|------|------|------|
| Main DB | **PostgreSQL 15+** | 사용자, 전략, 설정 데이터 |
| Time Series | **TimescaleDB** | OHLCV, 펀딩레이트 hypertable |
| Cache/Broker | **Redis** | 세션 캐시, Celery 메시지 브로커 |
| ID 전략 | **cuid2 / nanoid** | auto-increment 금지 (.ai/ spec) |
| Timestamps | **createdAt + updatedAt** | 모든 테이블 필수 (.ai/ spec) |
| Hosting | **추후 결정** | Self-hosted vs Neon — TimescaleDB 요구사항 검토 후 |

### Backtest Engine

| 항목 | 결정 | 근거 |
|------|------|------|
| Core | **vectorbt** | numpy 기반 벡터화 백테스트, 고속 |
| Alternative | **backtrader** | 복잡한 전략 로직 지원 |
| Optimization | **Optuna** | 베이지안 최적화 |
| Indicators | **pandas-ta, TA-Lib** | 기술적 지표 라이브러리 |

### Exchange Integration

| 항목 | 결정 | 근거 |
|------|------|------|
| Library | **CCXT / CCXT Pro** | 107개 거래소 통합, WebSocket 지원 |
| Primary | **Bybit** (Demo + Live) | 데모 API 지원 |
| Secondary | **Binance** (Testnet + Live) | 거래량 최대 |
| API Key 보안 | **AES-256 암호화** (Fernet) | 평문 저장 금지 |

## 거부한 대안

| 대안 | 거부 이유 |
|------|----------|
| Custom JWT (python-jose) | Clerk가 인증 위임으로 구현 비용 절감. 거래소 키는 별도 암호화 |
| Drizzle ORM (Frontend) | FE+BE 분리 구조에서 불필요. React Query로 API 호출 전용 |
| SQLAlchemy 직접 사용 | SQLModel이 Pydantic 통합으로 코드 간결화 |
| Neon Serverless | TimescaleDB hypertable 필요, Celery Redis 연동 — self-hosted가 유리 |
| Kubernetes (초기) | MVP에 과도. Docker Compose로 시작 |

## 결과

- PRD 전체 기술 스택 섹션 업데이트 필요
- DB 스키마에서 users.hashed_password 제거, id를 Clerk user_id 포맷으로 변경
- Auth 관련 API 엔드포인트 (register/login/refresh) Clerk으로 대체
- .env.example에서 JWT 관련 변수 제거, Clerk 변수 추가

# QuantBridge — 퀀트 트레이딩 백테스트 & 실행 플랫폼

## 프로젝트 정의

QuantBridge는 TradingView Pine Script 전략을 가져와서, 과거 데이터 기반 백테스팅 → 스트레스 테스트 → 거래소 데모 트레이딩 → 실거래 전환까지 하나의 파이프라인으로 연결하는 웹 기반 퀀트 트레이딩 플랫폼이다.

### 핵심 가치

- TradingView 커뮤니티의 수만 개 공개 전략을 "가져와서 바로 테스트"할 수 있는 진입 편의성
- TV 내장 백테스터가 제공하지 못하는 멀티심볼, 리얼리스틱 슬리피지, Monte Carlo, Walk-Forward 등 고급 검증
- Bybit Demo Trading API를 활용한 실시간 데모 트레이딩으로 백테스트 결과와 실제 시장 괴리 측정
- 검증 완료된 전략을 실거래로 원클릭 전환 (동일 코드, URL만 교체)

### 타겟 사용자

- TradingView에서 Pine Script 전략을 사용하는 크립토 트레이더
- 전략을 만들었지만 고급 백테스트 도구가 없어 검증이 부족한 개인 퀀트
- Bybit/Binance 등에서 선물 트레이딩을 하며 자동화를 원하는 트레이더

---

## 기술 스택

### 프론트엔드
- **프레임워크**: Next.js 16+ (App Router, TypeScript Strict)
- **차트**: TradingView Lightweight Charts v4 (`lightweight-charts` npm)
- **코드 에디터**: Monaco Editor (`@monaco-editor/react`)
- **UI 컴포넌트**: shadcn/ui v4 + Tailwind CSS v4
- **상태관리**: React Query v5 (서버 상태) + Zustand (글로벌 UI만, 최소화)
- **폼 검증**: react-hook-form + Zod v4 (`import { z } from "zod/v4"`)
- **데이터 시각화**: Recharts (리포트 차트), Plotly.js (3D 서피스)
- **실시간 통신**: Socket.IO client
- **HTTP 클라이언트**: React Query v5 (TanStack Query) — fetch 기반
- **인증**: Clerk (`@clerk/nextjs`) — proxy.ts 미들웨어, useAuth()/useUser()
- **패키지 매니저**: pnpm

### 백엔드
- **프레임워크**: FastAPI (Python 3.11+, 100% async)
- **ORM**: SQLModel + SQLAlchemy 2.0 (asyncpg) + Alembic (마이그레이션)
- **검증**: Pydantic V2 + pydantic-settings (`.model_dump()`, `ConfigDict`)
- **인증**: Clerk JWT 검증 (`clerk-sdk-python`) — 토큰 검증만, 자체 발급 없음
- **작업 큐**: Celery + Redis
- **웹소켓**: FastAPI WebSocket + Socket.IO (python-socketio)
- **API 문서**: 자동 생성 (FastAPI Swagger/ReDoc)
- **아키텍처**: Router/Service/Repository 3-Layer (`.ai/rules/backend.md` 참조)
- **패키지 매니저**: uv

### 백테스트 엔진
- **핵심**: vectorbt (벡터화 백테스팅, numpy 기반 초고속)
- **보조**: backtrader (복잡한 전략 로직용)
- **최적화**: Optuna (베이지안 최적화)
- **통계**: scipy, statsmodels (Monte Carlo, Walk-Forward)
- **인디케이터**: pandas-ta, TA-Lib

### 거래소 연동
- **통합 라이브러리**: CCXT (107개 거래소 지원)
- **주요 타겟**: Bybit (Demo + Live), Binance (Testnet + Live), OKX
- **실시간 데이터**: CCXT Pro (WebSocket)

### 데이터베이스
- **메인 DB**: PostgreSQL 15+ (사용자, 전략, 설정)
- **시계열 DB**: TimescaleDB (OHLCV, 체결 데이터)
- **캐시**: Redis (세션, 작업 큐, 실시간 데이터)

### 인프라
- **컨테이너**: Docker + Docker Compose (개발), Kubernetes (프로덕션)
- **리버스 프록시**: Nginx
- **모니터링**: Prometheus + Grafana

---

## 디렉토리 구조

> Frontend: FSD Lite (Feature-Sliced Design), Backend: 도메인별 3-Layer (Router/Service/Repository)
> 상세 규칙: `.ai/rules/frontend.md`, `.ai/rules/backend.md` 참조

```
quantbridge/
├── docker-compose.yml
├── .env.example
├── AGENTS.md
├── QUANTBRIDGE_PRD.md
├── docs/                            # 프로젝트 문서 (.ai/rules/global.md 참조)
│
├── frontend/                        # Next.js 16 (pnpm)
│   ├── package.json
│   ├── next.config.ts
│   ├── tsconfig.json
│   ├── src/
│   │   ├── app/                     # View Layer (라우팅만, 로직 금지)
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   ├── error.tsx            # 글로벌 에러 바운더리
│   │   │   ├── loading.tsx          # 글로벌 로딩
│   │   │   ├── not-found.tsx
│   │   │   ├── (auth)/              # Clerk 인증 (로그인/가입은 Clerk UI)
│   │   │   ├── strategies/
│   │   │   ├── templates/
│   │   │   └── settings/
│   │   ├── components/
│   │   │   ├── ui/                  # shadcn/ui v4 (수정 금지, 래핑만)
│   │   │   └── layout/              # Sidebar, Header
│   │   ├── features/                # 비즈니스 레이어 (FSD Lite)
│   │   │   ├── strategy/            # 전략 CRUD + Pine Editor
│   │   │   │   ├── components/      # PineScriptEditor, StrategyParser
│   │   │   │   ├── api.ts           # API 호출 + Query Key Factory
│   │   │   │   ├── hooks.ts         # React Query + 비즈니스 로직
│   │   │   │   ├── schemas.ts       # Zod v4 검증
│   │   │   │   └── types.ts
│   │   │   ├── backtest/            # 백테스트 설정/결과/리포트
│   │   │   │   ├── components/      # BacktestConfig, Report, TradeTable, MetricsCards
│   │   │   │   ├── api.ts
│   │   │   │   ├── hooks.ts
│   │   │   │   └── schemas.ts
│   │   │   ├── stress-test/         # Monte Carlo, Walk-Forward, 파라미터
│   │   │   ├── trading/             # 데모/라이브 트레이딩
│   │   │   │   ├── components/      # DemoPanel, LivePanel, PositionTable, KillSwitch
│   │   │   │   ├── api.ts
│   │   │   │   ├── hooks.ts
│   │   │   │   └── store.ts         # 실시간 포지션/PnL (Zustand)
│   │   │   ├── exchange/            # 거래소 계정 관리
│   │   │   ├── market-data/         # 차트, OHLCV
│   │   │   │   └── components/      # TradingChart, EquityCurve, DrawdownChart 등
│   │   │   └── charts/              # 공용 차트 (MonteCarloChart, ParameterSurface 등)
│   │   ├── hooks/                   # 범용 훅 (useWebSocket 등)
│   │   ├── lib/                     # API 클라이언트, 유틸리티
│   │   ├── store/                   # 글로벌 Zustand (sidebar, theme만)
│   │   └── types/                   # 글로벌 타입
│   └── Dockerfile
│
├── backend/                         # FastAPI (uv)
│   ├── pyproject.toml               # uv 의존성 관리
│   ├── alembic.ini
│   ├── alembic/                     # DB 마이그레이션
│   ├── src/
│   │   ├── main.py                  # FastAPI 앱 엔트리포인트
│   │   ├── auth/                    # Clerk JWT 검증
│   │   │   └── dependencies.py      # get_current_user (Clerk 토큰 → user_id)
│   │   ├── common/                  # 공통 모듈
│   │   │   ├── database.py          # AsyncSession, engine
│   │   │   ├── exceptions.py        # 커스텀 예외
│   │   │   └── pagination.py        # 페이지네이션 유틸
│   │   ├── core/
│   │   │   └── config.py            # Pydantic V2 BaseSettings (ConfigDict)
│   │   │
│   │   ├── strategy/                # 도메인: 전략 CRUD
│   │   │   ├── router.py            # HTTP만, 10줄 이내 — DB접근 금지
│   │   │   ├── service.py           # 비즈니스 로직 — AsyncSession 금지
│   │   │   ├── repository.py        # DB 쿼리만 — 유일한 DB 접근점
│   │   │   ├── schemas.py           # Pydantic V2 스키마
│   │   │   ├── models.py            # SQLModel 모델
│   │   │   └── dependencies.py      # Depends() 조립
│   │   │
│   │   ├── backtest/                # 도메인: 백테스트 (동일 3-Layer 구조)
│   │   ├── stress_test/             # 도메인: 스트레스 테스트
│   │   ├── optimizer/               # 도메인: 최적화
│   │   ├── trading/                 # 도메인: 데모/라이브 트레이딩
│   │   ├── exchange/                # 도메인: 거래소 계정
│   │   ├── market_data/             # 도메인: 시장 데이터
│   │   │
│   │   ├── engine/                  # 핵심 엔진 (비즈니스 로직, HTTP 무관)
│   │   │   ├── pine_parser/         # Pine Script 파서 (lexer, parser, transpiler)
│   │   │   ├── backtest_engine/     # vectorbt 기반 백테스트 실행
│   │   │   ├── stress_test_engine/  # Monte Carlo, Walk-Forward
│   │   │   ├── optimizer_engine/    # Grid, Bayesian, Genetic
│   │   │   ├── trading_engine/      # CCXT executor, strategy runner, risk manager
│   │   │   └── data_engine/         # OHLCV collector, manager
│   │   │
│   │   ├── tasks/                   # Celery 비동기 태스크
│   │   │   ├── celery_app.py
│   │   │   ├── backtest_tasks.py
│   │   │   ├── stress_test_tasks.py
│   │   │   ├── data_tasks.py
│   │   │   └── optimize_tasks.py
│   │   │
│   │   └── utils/
│   │       ├── security.py          # AES-256 API Key 암호화 (Clerk 인증과 분리)
│   │       └── exchange_utils.py    # 거래소 유틸리티
│   │
│   ├── tests/
│   └── Dockerfile
│
├── data/                            # Docker volume 마운트
│
└── scripts/
    ├── init_db.py
    ├── seed_templates.py
    └── collect_data.py
```

---

## 데이터베이스 스키마

### users 테이블
```sql
-- Clerk 인증 연동: id는 Clerk user_id, 비밀번호 필드 없음
CREATE TABLE users (
    id VARCHAR(255) PRIMARY KEY,              -- Clerk user_id (e.g., "user_2abc...")
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE,             -- Clerk에서 동기화, nullable
    is_active BOOLEAN DEFAULT true,
    is_premium BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### strategies 테이블
```sql
CREATE TABLE strategies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    pine_script TEXT NOT NULL,                    -- 원본 Pine Script 코드
    python_code TEXT,                             -- 변환된 Python 코드
    parsed_params JSONB DEFAULT '{}',             -- 파싱된 파라미터 목록
    parsed_indicators JSONB DEFAULT '[]',         -- 사용된 인디케이터 목록
    parsed_entry_conditions JSONB DEFAULT '{}',   -- 진입 조건
    parsed_exit_conditions JSONB DEFAULT '{}',    -- 청산 조건
    version INTEGER DEFAULT 1,
    is_template BOOLEAN DEFAULT false,            -- 템플릿 여부
    source_url VARCHAR(500),                      -- TV 커뮤니티 원본 URL
    status VARCHAR(50) DEFAULT 'draft',           -- draft, backtested, demo, live
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### backtests 테이블
```sql
CREATE TABLE backtests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID REFERENCES strategies(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    -- 백테스트 설정
    config JSONB NOT NULL,
    /*
    config 예시:
    {
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "exchange": "bybit",
        "timeframe": "1h",
        "start_date": "2024-01-01",
        "end_date": "2025-12-31",
        "initial_capital": 10000,
        "leverage": 1,
        "commission_rate": 0.0006,
        "slippage_pct": 0.0005,
        "include_funding": true,
        "params_override": {"rsi_period": 14, "rsi_overbought": 70}
    }
    */
    
    -- 실행 상태
    status VARCHAR(50) DEFAULT 'pending',  -- pending, running, completed, failed
    progress FLOAT DEFAULT 0,              -- 0.0 ~ 1.0
    error_message TEXT,
    
    -- 결과 (completed 시 채워짐)
    results JSONB,
    /*
    results 예시:
    {
        "total_return_pct": 45.2,
        "annual_return_pct": 22.1,
        "sharpe_ratio": 1.85,
        "sortino_ratio": 2.31,
        "calmar_ratio": 1.42,
        "max_drawdown_pct": -15.6,
        "max_drawdown_duration_days": 23,
        "win_rate_pct": 58.3,
        "profit_factor": 1.72,
        "total_trades": 342,
        "avg_trade_pct": 0.13,
        "best_trade_pct": 8.4,
        "worst_trade_pct": -3.2,
        "avg_holding_hours": 18.5,
        "consecutive_wins_max": 12,
        "consecutive_losses_max": 7,
        "long_trades": 180,
        "short_trades": 162,
        "long_win_rate_pct": 61.1,
        "short_win_rate_pct": 55.2,
        "monthly_returns": {"2024-01": 3.2, "2024-02": -1.1, ...},
        "equity_curve": [[timestamp, equity], ...],
        "drawdown_curve": [[timestamp, drawdown_pct], ...],
        "trades": [
            {
                "entry_time": "2024-01-15T08:00:00Z",
                "exit_time": "2024-01-15T14:00:00Z",
                "symbol": "BTCUSDT",
                "side": "long",
                "entry_price": 42500.0,
                "exit_price": 43200.0,
                "quantity": 0.1,
                "pnl": 70.0,
                "pnl_pct": 1.65,
                "commission": 5.14,
                "slippage": 2.13
            }, ...
        ]
    }
    */
    
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### stress_tests 테이블
```sql
CREATE TABLE stress_tests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    backtest_id UUID REFERENCES backtests(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    test_type VARCHAR(50) NOT NULL,   -- monte_carlo, walk_forward, parameter_stability
    config JSONB NOT NULL,
    /*
    Monte Carlo config 예시:
    {
        "num_simulations": 1000,
        "shuffle_trades": true,
        "randomize_slippage": true,
        "slippage_range": [0.0001, 0.001],
        "confidence_level": 0.95
    }
    
    Walk-Forward config 예시:
    {
        "in_sample_months": 6,
        "out_of_sample_months": 2,
        "step_months": 2,
        "min_oos_ratio": 0.5
    }
    
    Parameter Stability config 예시:
    {
        "param_ranges": {
            "rsi_period": [7, 21, 1],
            "rsi_overbought": [65, 80, 1]
        }
    }
    */
    
    status VARCHAR(50) DEFAULT 'pending',
    progress FLOAT DEFAULT 0,
    results JSONB,
    /*
    Monte Carlo results 예시:
    {
        "simulations": 1000,
        "median_return_pct": 42.1,
        "p5_return_pct": 12.3,
        "p95_return_pct": 78.5,
        "median_max_drawdown_pct": -18.2,
        "p95_max_drawdown_pct": -32.1,
        "ruin_probability_pct": 2.3,
        "equity_bands": {
            "p5": [[ts, val], ...],
            "p25": [[ts, val], ...],
            "p50": [[ts, val], ...],
            "p75": [[ts, val], ...],
            "p95": [[ts, val], ...]
        }
    }
    
    Walk-Forward results 예시:
    {
        "periods": [
            {
                "is_start": "2024-01-01",
                "is_end": "2024-06-30",
                "oos_start": "2024-07-01",
                "oos_end": "2024-08-31",
                "is_return_pct": 25.3,
                "oos_return_pct": 8.1,
                "oos_is_ratio": 0.32,
                "is_sharpe": 2.1,
                "oos_sharpe": 1.4
            }, ...
        ],
        "avg_oos_is_ratio": 0.45,
        "pass": true,
        "combined_oos_return_pct": 34.2,
        "combined_oos_sharpe": 1.52
    }
    */
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
```

### exchange_accounts 테이블
```sql
CREATE TABLE exchange_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    exchange VARCHAR(50) NOT NULL,       -- bybit, binance, okx
    label VARCHAR(100) NOT NULL,         -- 사용자가 지정한 이름
    api_key_encrypted TEXT NOT NULL,      -- AES-256 암호화된 API Key
    api_secret_encrypted TEXT NOT NULL,   -- AES-256 암호화된 API Secret
    is_demo BOOLEAN DEFAULT true,        -- 데모 계정 여부
    is_active BOOLEAN DEFAULT true,
    permissions JSONB DEFAULT '[]',      -- ["read", "trade"] 등
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(user_id, exchange, label)
);
```

### trading_sessions 테이블
```sql
CREATE TABLE trading_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    strategy_id UUID REFERENCES strategies(id) ON DELETE CASCADE,
    exchange_account_id UUID REFERENCES exchange_accounts(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    
    mode VARCHAR(20) NOT NULL,           -- demo, live
    status VARCHAR(50) DEFAULT 'stopped', -- stopped, running, paused, error
    
    -- 트레이딩 설정
    config JSONB NOT NULL,
    /*
    {
        "symbol": "BTCUSDT",
        "timeframe": "1h",
        "leverage": 3,
        "position_size_pct": 10,
        "max_positions": 1,
        "risk_config": {
            "daily_loss_limit_pct": 5,
            "max_drawdown_pct": 15,
            "stop_loss_pct": 2,
            "take_profit_pct": 6,
            "kill_switch_enabled": true
        }
    }
    */
    
    -- 실시간 성과
    current_pnl DECIMAL(20, 8) DEFAULT 0,
    current_pnl_pct FLOAT DEFAULT 0,
    total_trades INTEGER DEFAULT 0,
    win_trades INTEGER DEFAULT 0,
    
    -- 백테스트와의 비교용
    reference_backtest_id UUID REFERENCES backtests(id),
    
    started_at TIMESTAMPTZ,
    stopped_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### live_trades 테이블
```sql
CREATE TABLE live_trades (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES trading_sessions(id) ON DELETE CASCADE,
    
    symbol VARCHAR(50) NOT NULL,
    side VARCHAR(10) NOT NULL,           -- long, short
    
    entry_time TIMESTAMPTZ NOT NULL,
    exit_time TIMESTAMPTZ,
    
    entry_price DECIMAL(20, 8) NOT NULL,
    exit_price DECIMAL(20, 8),
    
    quantity DECIMAL(20, 8) NOT NULL,
    leverage INTEGER DEFAULT 1,
    
    -- 실제 체결 정보
    entry_order_id VARCHAR(100),         -- 거래소 주문 ID
    exit_order_id VARCHAR(100),
    actual_slippage DECIMAL(20, 8),      -- 실측 슬리피지
    commission DECIMAL(20, 8),
    funding_fee DECIMAL(20, 8),
    
    pnl DECIMAL(20, 8),
    pnl_pct FLOAT,
    
    status VARCHAR(20) DEFAULT 'open',   -- open, closed, cancelled
    close_reason VARCHAR(50),            -- signal, stop_loss, take_profit, kill_switch
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### OHLCV 시계열 테이블 (TimescaleDB)
```sql
CREATE TABLE ohlcv (
    time TIMESTAMPTZ NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    timeframe VARCHAR(10) NOT NULL,      -- 1m, 5m, 15m, 1h, 4h, 1d
    open DECIMAL(20, 8) NOT NULL,
    high DECIMAL(20, 8) NOT NULL,
    low DECIMAL(20, 8) NOT NULL,
    close DECIMAL(20, 8) NOT NULL,
    volume DECIMAL(20, 8) NOT NULL,
    
    PRIMARY KEY (time, exchange, symbol, timeframe)
);

-- TimescaleDB 하이퍼테이블 변환
SELECT create_hypertable('ohlcv', 'time');

-- 인덱스
CREATE INDEX idx_ohlcv_lookup ON ohlcv (exchange, symbol, timeframe, time DESC);
```

### funding_rates 테이블
```sql
CREATE TABLE funding_rates (
    time TIMESTAMPTZ NOT NULL,
    exchange VARCHAR(50) NOT NULL,
    symbol VARCHAR(50) NOT NULL,
    funding_rate DECIMAL(20, 10) NOT NULL,
    
    PRIMARY KEY (time, exchange, symbol)
);

SELECT create_hypertable('funding_rates', 'time');
```

---

## API 엔드포인트

### 인증 (Auth) — Clerk 기반
```
# 회원가입/로그인/토큰 갱신은 Clerk가 처리 (별도 엔드포인트 불필요)
GET    /api/v1/auth/me                # Clerk 토큰 검증 → 현재 사용자 정보
POST   /api/v1/auth/webhook           # Clerk Webhook → 사용자 생성/업데이트 동기화
```

### 전략 (Strategies)
```
GET    /api/v1/strategies              # 내 전략 목록
POST   /api/v1/strategies              # 새 전략 생성 (Pine Script 업로드)
GET    /api/v1/strategies/:id          # 전략 상세 조회
PUT    /api/v1/strategies/:id          # 전략 수정
DELETE /api/v1/strategies/:id          # 전략 삭제

POST   /api/v1/strategies/parse        # Pine Script 파싱만 수행 (미리보기용)
POST   /api/v1/strategies/import-url   # TV 커뮤니티 URL로 가져오기
```

### 전략 템플릿 (Templates)
```
GET    /api/v1/templates               # 템플릿 목록
GET    /api/v1/templates/:id           # 템플릿 상세
POST   /api/v1/templates/:id/use       # 템플릿으로 내 전략 생성
```

### 백테스트 (Backtests)
```
POST   /api/v1/backtests               # 백테스트 실행 요청
GET    /api/v1/backtests               # 내 백테스트 목록
GET    /api/v1/backtests/:id           # 백테스트 결과 조회
GET    /api/v1/backtests/:id/trades    # 개별 거래 내역 (페이지네이션)
DELETE /api/v1/backtests/:id           # 백테스트 결과 삭제

GET    /api/v1/backtests/:id/progress  # 백테스트 진행률 (polling용, WS 대안)
```

### 스트레스 테스트 (Stress Tests)
```
POST   /api/v1/stress-tests/monte-carlo        # Monte Carlo 시뮬레이션 실행
POST   /api/v1/stress-tests/walk-forward       # Walk-Forward 분석 실행
POST   /api/v1/stress-tests/parameter-stability # 파라미터 안정성 분석 실행

GET    /api/v1/stress-tests/:id                # 결과 조회
```

### 최적화 (Optimization)
```
POST   /api/v1/optimize/grid           # 그리드 서치 실행
POST   /api/v1/optimize/bayesian       # 베이지안 최적화 실행
GET    /api/v1/optimize/:id            # 최적화 결과 조회
```

### 거래소 계정 (Exchange Accounts)
```
GET    /api/v1/exchanges/accounts      # 등록된 거래소 계정 목록
POST   /api/v1/exchanges/accounts      # 거래소 API Key 등록
DELETE /api/v1/exchanges/accounts/:id  # 거래소 계정 삭제
POST   /api/v1/exchanges/accounts/:id/test  # API Key 유효성 테스트

GET    /api/v1/exchanges/accounts/:id/balance  # 잔고 조회 (데모/라이브)
```

### 트레이딩 (Trading Sessions)
```
POST   /api/v1/trading/sessions               # 트레이딩 세션 생성
GET    /api/v1/trading/sessions               # 내 세션 목록
GET    /api/v1/trading/sessions/:id           # 세션 상세

POST   /api/v1/trading/sessions/:id/start     # 트레이딩 시작
POST   /api/v1/trading/sessions/:id/stop      # 트레이딩 중지
POST   /api/v1/trading/sessions/:id/kill      # 긴급 전체 청산 (Kill Switch)

GET    /api/v1/trading/sessions/:id/trades    # 세션 거래 내역
GET    /api/v1/trading/sessions/:id/performance  # 성과 요약
GET    /api/v1/trading/sessions/:id/comparison   # 백테스트 vs 실제 비교 데이터
```

### 시장 데이터 (Market Data)
```
GET    /api/v1/market/symbols          # 지원 심볼 목록 (거래소별)
GET    /api/v1/market/ohlcv            # OHLCV 데이터 조회
GET    /api/v1/market/funding-rates    # 펀딩비 데이터 조회
```

### WebSocket 이벤트
```
# 클라이언트 → 서버
ws://api/ws
  - subscribe_backtest_progress(backtest_id)     # 백테스트 진행률 구독
  - subscribe_trading_session(session_id)        # 트레이딩 세션 실시간 데이터 구독
  - subscribe_market_data(exchange, symbol, tf)  # 실시간 시장 데이터 구독

# 서버 → 클라이언트
  - backtest_progress(backtest_id, progress, status)
  - backtest_completed(backtest_id, results_summary)
  - trade_opened(session_id, trade_data)
  - trade_closed(session_id, trade_data)
  - position_updated(session_id, position_data)
  - pnl_updated(session_id, pnl_data)
  - risk_alert(session_id, alert_type, message)
  - market_data(exchange, symbol, ohlcv)
  - kill_switch_triggered(session_id, reason)
```

---

## 기능 상세 명세

### 기능 1: Pine Script 파서 + Python 변환

#### 개요
사용자가 입력한 Pine Script 코드를 파싱하여 메타데이터를 추출하고, 백테스트 가능한 Python 코드로 변환한다.

#### Pine Script 인디케이터 → Python 매핑 (MVP 지원 목록)

```python
# indicator_map.py
INDICATOR_MAP = {
    # 이동평균
    "ta.sma": "pandas_ta.sma",
    "ta.ema": "pandas_ta.ema",
    "ta.wma": "pandas_ta.wma",
    "ta.vwma": "pandas_ta.vwma",
    
    # 오실레이터
    "ta.rsi": "pandas_ta.rsi",
    "ta.stoch": "pandas_ta.stoch",
    "ta.cci": "pandas_ta.cci",
    "ta.mfi": "pandas_ta.mfi",
    "ta.willr": "pandas_ta.willr",
    
    # 트렌드
    "ta.macd": "pandas_ta.macd",
    "ta.adx": "pandas_ta.adx",
    "ta.supertrend": "pandas_ta.supertrend",
    
    # 변동성
    "ta.bb": "pandas_ta.bbands",
    "ta.atr": "pandas_ta.atr",
    "ta.kc": "pandas_ta.kc",
    
    # 시그널 함수
    "ta.crossover": "custom_crossover",     # a > b and a[-1] <= b[-1]
    "ta.crossunder": "custom_crossunder",   # a < b and a[-1] >= b[-1]
    "ta.cross": "custom_cross",             # crossover or crossunder
    
    # 가격 데이터
    "close": "df['close']",
    "open": "df['open']",
    "high": "df['high']",
    "low": "df['low']",
    "volume": "df['volume']",
    "hl2": "(df['high'] + df['low']) / 2",
    "hlc3": "(df['high'] + df['low'] + df['close']) / 3",
    "ohlc4": "(df['open'] + df['high'] + df['low'] + df['close']) / 4",
}
```

#### 파싱 결과 예시

입력 Pine Script:
```pine
//@version=5
strategy("RSI Strategy", overlay=true)
rsiLength = input.int(14, "RSI Length")
overbought = input.int(70, "Overbought")
oversold = input.int(30, "Oversold")

rsiValue = ta.rsi(close, rsiLength)

if (ta.crossover(rsiValue, oversold))
    strategy.entry("Long", strategy.long)
if (ta.crossunder(rsiValue, overbought))
    strategy.close("Long")
```

파싱 결과:
```json
{
    "name": "RSI Strategy",
    "version": 5,
    "overlay": true,
    "parameters": [
        {"name": "rsiLength", "type": "int", "default": 14, "label": "RSI Length"},
        {"name": "overbought", "type": "int", "default": 70, "label": "Overbought"},
        {"name": "oversold", "type": "int", "default": 30, "label": "Oversold"}
    ],
    "indicators": ["ta.rsi"],
    "entry_conditions": {
        "long": "ta.crossover(rsiValue, oversold)",
        "short": null
    },
    "exit_conditions": {
        "long": "ta.crossunder(rsiValue, overbought)",
        "short": null
    }
}
```

변환된 Python 코드:
```python
import pandas as pd
import pandas_ta as ta
import numpy as np

def run_strategy(df: pd.DataFrame, params: dict) -> pd.DataFrame:
    """
    RSI Strategy - 변환된 Python 코드
    """
    rsi_length = params.get("rsiLength", 14)
    overbought = params.get("overbought", 70)
    oversold = params.get("oversold", 30)
    
    # 인디케이터 계산
    df["rsi"] = ta.rsi(df["close"], length=rsi_length)
    
    # 시그널 생성
    df["long_entry"] = (df["rsi"] > oversold) & (df["rsi"].shift(1) <= oversold)
    df["long_exit"] = (df["rsi"] < overbought) & (df["rsi"].shift(1) >= overbought)
    
    # 포지션 계산
    df["signal"] = 0
    df.loc[df["long_entry"], "signal"] = 1
    df.loc[df["long_exit"], "signal"] = -1
    
    return df
```

#### 구현 우선순위
1단계(MVP): 정규식 기반 간이 파서 — input 파라미터, 기본 인디케이터, strategy.entry/close 추출
2단계: AST 기반 정식 파서 — 조건문, 변수, 함수 호출 등 전체 구문 분석
3단계: 복잡한 Pine Script 지원 — 멀티 타임프레임, 커스텀 함수, security() 등

---

### 기능 2: 히스토리컬 백테스트 엔진

#### 핵심 로직 (vectorbt 기반)

```python
# engine.py 핵심 로직 개요
import vectorbt as vbt
import pandas as pd
import numpy as np

class BacktestEngine:
    def __init__(self, config: dict):
        self.config = config
        self.initial_capital = config["initial_capital"]
        self.commission = config["commission_rate"]
        self.slippage = config["slippage_pct"]
        
    def run(self, df: pd.DataFrame, strategy_func, params: dict) -> dict:
        """단일 심볼 백테스트 실행"""
        
        # 1. 전략 실행 → 시그널 생성
        signals_df = strategy_func(df.copy(), params)
        
        # 2. 진입/청산 시그널 추출
        entries = signals_df["long_entry"].values
        exits = signals_df["long_exit"].values
        
        # 3. vectorbt 포트폴리오 시뮬레이션
        portfolio = vbt.Portfolio.from_signals(
            close=df["close"],
            entries=entries,
            exits=exits,
            init_cash=self.initial_capital,
            fees=self.commission,
            slippage=self.slippage,
            freq="1h"  # config["timeframe"]에서 변환
        )
        
        # 4. 성과 지표 계산
        metrics = self._calculate_metrics(portfolio)
        
        # 5. 거래 내역 추출
        trades = self._extract_trades(portfolio)
        
        return {
            "metrics": metrics,
            "trades": trades,
            "equity_curve": portfolio.value().tolist(),
            "drawdown_curve": portfolio.drawdown().tolist()
        }
    
    def run_multi_symbol(self, symbols: list, strategy_func, params: dict) -> dict:
        """멀티 심볼 병렬 백테스트"""
        results = {}
        for symbol in symbols:
            df = self._load_data(symbol)
            results[symbol] = self.run(df, strategy_func, params)
        return results
    
    def _calculate_metrics(self, portfolio) -> dict:
        """종합 성과 지표 계산"""
        stats = portfolio.stats()
        returns = portfolio.returns()
        
        return {
            "total_return_pct": float(stats["Total Return [%]"]),
            "annual_return_pct": float(stats.get("Annualized Return [%]", 0)),
            "sharpe_ratio": float(stats.get("Sharpe Ratio", 0)),
            "sortino_ratio": float(self._sortino(returns)),
            "calmar_ratio": float(self._calmar(returns, portfolio)),
            "max_drawdown_pct": float(stats["Max Drawdown [%]"]),
            "win_rate_pct": float(stats.get("Win Rate [%]", 0)),
            "profit_factor": float(stats.get("Profit Factor", 0)),
            "total_trades": int(stats.get("Total Trades", 0)),
            "avg_trade_pct": float(stats.get("Avg Winning Trade [%]", 0)),
            "best_trade_pct": float(stats.get("Best Trade [%]", 0)),
            "worst_trade_pct": float(stats.get("Worst Trade [%]", 0)),
        }
```

#### 리얼리스틱 시뮬레이션 상세

```python
# realistic.py — 현실적 조건 반영 모듈

class RealisticSimulator:
    """TV 백테스터가 반영하지 않는 현실적 조건들"""
    
    def apply_dynamic_slippage(self, order_size: float, orderbook_depth: dict) -> float:
        """주문량 대비 호가창 깊이를 고려한 동적 슬리피지"""
        # 큰 주문일수록 불리한 가격에 체결됨
        pass
    
    def apply_funding_fee(self, position: dict, funding_rates: pd.Series) -> float:
        """무기한 선물 8시간 펀딩비 반영"""
        # 포지션 보유 중 발생하는 펀딩비 차감/지급
        pass
    
    def apply_exchange_fees(self, trade: dict, fee_tier: str = "default") -> dict:
        """거래소별 실제 수수료 체계 반영"""
        FEE_TABLE = {
            "bybit": {"maker": 0.0001, "taker": 0.0006},
            "binance": {"maker": 0.0002, "taker": 0.0004},
            "okx": {"maker": 0.0002, "taker": 0.0005},
        }
        pass
    
    def apply_market_hours(self, df: pd.DataFrame) -> pd.DataFrame:
        """크립토는 24/7이지만, 주식의 경우 장중/장외 구분"""
        pass
```

---

### 기능 3: 스트레스 테스트

#### Monte Carlo 시뮬레이션

```python
# monte_carlo.py

class MonteCarloSimulator:
    def __init__(self, num_simulations: int = 1000, confidence: float = 0.95):
        self.num_simulations = num_simulations
        self.confidence = confidence
    
    def run(self, trade_returns: np.ndarray) -> dict:
        """
        거래 수익률 배열을 입력받아 Monte Carlo 시뮬레이션 실행
        
        시뮬레이션 방법:
        1. trade_returns의 순서를 무작위로 섞어 새로운 equity curve 생성
        2. 이를 num_simulations번 반복
        3. 각 시뮬레이션의 최종 수익률, MDD 등을 수집
        4. 분위수별 통계 산출
        """
        all_final_returns = []
        all_max_drawdowns = []
        all_equity_curves = []
        
        for _ in range(self.num_simulations):
            shuffled = np.random.permutation(trade_returns)
            equity = np.cumprod(1 + shuffled) 
            
            # MDD 계산
            peak = np.maximum.accumulate(equity)
            drawdown = (equity - peak) / peak
            
            all_final_returns.append(equity[-1] - 1)
            all_max_drawdowns.append(drawdown.min())
            all_equity_curves.append(equity.tolist())
        
        return {
            "simulations": self.num_simulations,
            "median_return_pct": float(np.median(all_final_returns) * 100),
            "p5_return_pct": float(np.percentile(all_final_returns, 5) * 100),
            "p95_return_pct": float(np.percentile(all_final_returns, 95) * 100),
            "median_max_drawdown_pct": float(np.median(all_max_drawdowns) * 100),
            "p95_max_drawdown_pct": float(np.percentile(all_max_drawdowns, 5) * 100),
            "ruin_probability_pct": float(np.mean(np.array(all_final_returns) < -0.5) * 100),
            "equity_bands": self._calculate_bands(all_equity_curves)
        }
```

#### Walk-Forward Analysis

```python
# walk_forward.py

class WalkForwardAnalyzer:
    def __init__(self, is_months: int = 6, oos_months: int = 2, step_months: int = 2):
        self.is_months = is_months
        self.oos_months = oos_months
        self.step_months = step_months
    
    def run(self, df: pd.DataFrame, strategy_func, param_ranges: dict) -> dict:
        """
        1. 데이터를 IS(학습)/OOS(검증) 구간으로 롤링 분할
        2. 각 IS 구간에서 파라미터 최적화
        3. 최적 파라미터를 OOS 구간에 적용하여 성과 측정
        4. OOS 성과 / IS 성과 비율로 과적합 여부 판단
        """
        periods = self._generate_periods(df)
        results = []
        
        for period in periods:
            # IS 구간에서 최적화
            is_data = df[period["is_start"]:period["is_end"]]
            best_params, is_metrics = self._optimize_in_sample(
                is_data, strategy_func, param_ranges
            )
            
            # OOS 구간에서 검증
            oos_data = df[period["oos_start"]:period["oos_end"]]
            oos_metrics = self._evaluate_out_of_sample(
                oos_data, strategy_func, best_params
            )
            
            results.append({
                **period,
                "best_params": best_params,
                "is_return_pct": is_metrics["return_pct"],
                "oos_return_pct": oos_metrics["return_pct"],
                "oos_is_ratio": oos_metrics["return_pct"] / max(is_metrics["return_pct"], 0.01),
                "is_sharpe": is_metrics["sharpe"],
                "oos_sharpe": oos_metrics["sharpe"],
            })
        
        avg_ratio = np.mean([r["oos_is_ratio"] for r in results])
        
        return {
            "periods": results,
            "avg_oos_is_ratio": float(avg_ratio),
            "pass": avg_ratio >= 0.5,  # OOS가 IS의 50% 이상이면 통과
        }
```

---

### 기능 4: 데모 트레이딩 (Bybit Demo API 연동)

#### 거래소 실행기 (CCXT 기반)

```python
# executor.py

import ccxt
from typing import Literal

class ExchangeExecutor:
    """CCXT 기반 거래소 주문 실행기. 데모/라이브 동일 인터페이스."""
    
    DEMO_URLS = {
        "bybit": {
            "rest": "https://api-demo.bybit.com",
            "ws": "wss://stream-demo.bybit.com"
        },
        "binance": {
            "rest": "https://testnet.binancefuture.com",
        }
    }
    
    def __init__(self, exchange_name: str, api_key: str, api_secret: str, 
                 mode: Literal["demo", "live"] = "demo"):
        
        exchange_class = getattr(ccxt, exchange_name)
        config = {
            "apiKey": api_key,
            "secret": api_secret,
            "enableRateLimit": True,
            "options": {"defaultType": "swap"},  # USDT 무기한 선물
        }
        
        # 데모 모드면 URL 오버라이드
        if mode == "demo" and exchange_name in self.DEMO_URLS:
            config["urls"] = {"api": self.DEMO_URLS[exchange_name]}
        
        self.exchange = exchange_class(config)
        self.mode = mode
    
    async def get_balance(self) -> dict:
        """잔고 조회"""
        return await self.exchange.fetch_balance()
    
    async def place_market_order(self, symbol: str, side: str, amount: float) -> dict:
        """시장가 주문"""
        order = await self.exchange.create_order(
            symbol=symbol, type="market", side=side, amount=amount
        )
        return order
    
    async def place_limit_order(self, symbol: str, side: str, amount: float, price: float) -> dict:
        """지정가 주문"""
        order = await self.exchange.create_order(
            symbol=symbol, type="limit", side=side, amount=amount, price=price
        )
        return order
    
    async def set_leverage(self, symbol: str, leverage: int):
        """레버리지 설정"""
        await self.exchange.set_leverage(leverage, symbol)
    
    async def get_positions(self) -> list:
        """현재 포지션 조회"""
        return await self.exchange.fetch_positions()
    
    async def close_all_positions(self, symbol: str = None):
        """전체 포지션 청산 (Kill Switch)"""
        positions = await self.get_positions()
        for pos in positions:
            if pos["contracts"] > 0:
                if symbol and pos["symbol"] != symbol:
                    continue
                side = "sell" if pos["side"] == "long" else "buy"
                await self.place_market_order(pos["symbol"], side, pos["contracts"])
```

#### 실시간 전략 실행 루프

```python
# strategy_runner.py

class StrategyRunner:
    """실시간으로 전략을 실행하고 시그널에 따라 주문을 전송하는 메인 루프"""
    
    def __init__(self, executor: ExchangeExecutor, strategy_func, params: dict,
                 risk_manager: RiskManager, config: dict):
        self.executor = executor
        self.strategy_func = strategy_func
        self.params = params
        self.risk_manager = risk_manager
        self.config = config
        self.running = False
        self.current_position = None
    
    async def start(self):
        """전략 실행 시작"""
        self.running = True
        symbol = self.config["symbol"]
        timeframe = self.config["timeframe"]
        
        await self.executor.set_leverage(symbol, self.config["leverage"])
        
        while self.running:
            try:
                # 1. 최신 OHLCV 데이터 가져오기
                ohlcv = await self.executor.exchange.fetch_ohlcv(
                    symbol, timeframe, limit=500
                )
                df = self._ohlcv_to_dataframe(ohlcv)
                
                # 2. 전략 실행 → 현재 시그널 판단
                signals_df = self.strategy_func(df, self.params)
                current_signal = self._get_current_signal(signals_df)
                
                # 3. 리스크 체크
                if not self.risk_manager.check(current_signal, self.current_position):
                    continue
                
                # 4. 시그널에 따라 주문 실행
                if current_signal == "long_entry" and self.current_position is None:
                    await self._open_position("buy", symbol)
                elif current_signal == "long_exit" and self.current_position == "long":
                    await self._close_position(symbol)
                elif current_signal == "short_entry" and self.current_position is None:
                    await self._open_position("sell", symbol)
                elif current_signal == "short_exit" and self.current_position == "short":
                    await self._close_position(symbol)
                
                # 5. 다음 봉까지 대기
                await self._wait_for_next_bar(timeframe)
                
            except Exception as e:
                # 에러 로깅 + 알림
                await self._handle_error(e)
    
    async def stop(self):
        """전략 실행 중지 (포지션 유지)"""
        self.running = False
    
    async def kill(self):
        """긴급 중지 + 모든 포지션 청산"""
        self.running = False
        await self.executor.close_all_positions(self.config["symbol"])
```

#### 리스크 매니저

```python
# risk_manager.py

class RiskManager:
    """트레이딩 리스크 관리"""
    
    def __init__(self, config: dict):
        self.daily_loss_limit_pct = config["daily_loss_limit_pct"]
        self.max_drawdown_pct = config["max_drawdown_pct"]
        self.stop_loss_pct = config.get("stop_loss_pct")
        self.take_profit_pct = config.get("take_profit_pct")
        self.kill_switch_enabled = config.get("kill_switch_enabled", True)
        
        self.daily_pnl = 0
        self.peak_equity = 0
        self.current_equity = 0
    
    def check(self, signal: str, current_position: str) -> bool:
        """주문 전 리스크 체크. False 반환 시 주문 차단"""
        
        # 일일 손실 한도 체크
        if self.daily_pnl <= -(self.daily_loss_limit_pct):
            self._trigger_alert("DAILY_LOSS_LIMIT", 
                f"일일 손실 한도 {self.daily_loss_limit_pct}% 도달. 금일 트레이딩 중단.")
            return False
        
        # 최대 낙폭 체크
        current_dd = (self.current_equity - self.peak_equity) / self.peak_equity * 100
        if current_dd <= -(self.max_drawdown_pct):
            self._trigger_alert("MAX_DRAWDOWN",
                f"최대 낙폭 {self.max_drawdown_pct}% 도달. Kill Switch 발동.")
            return False
        
        return True
    
    def calculate_position_size(self, equity: float, risk_per_trade_pct: float,
                                 stop_loss_distance_pct: float) -> float:
        """포지션 사이즈 계산 (리스크 기반)"""
        risk_amount = equity * (risk_per_trade_pct / 100)
        position_size = risk_amount / (stop_loss_distance_pct / 100)
        return position_size
```

---

### 기능 5: 백테스트 vs 데모 괴리 분석

#### 개요
이 기능은 히스토리컬 백테스트의 예상 성과와 데모 트레이딩의 실제 성과를 실시간으로 비교하여, 전략의 실전 적합성을 평가한다. 다른 서비스에 없는 핵심 차별점이다.

#### 비교 항목
```python
# performance.py

class PerformanceComparator:
    """백테스트 예상 vs 실제 데모 성과 비교"""
    
    def compare(self, backtest_trades: list, live_trades: list) -> dict:
        return {
            # 슬리피지 분석
            "avg_slippage_expected": self._avg_slippage(backtest_trades),
            "avg_slippage_actual": self._avg_slippage(live_trades),
            "slippage_deviation": ...,  # 예상 대비 실제 편차
            
            # 체결 분석
            "avg_fill_time_ms": ...,    # 평균 체결 시간
            "partial_fill_rate": ...,   # 부분 체결 비율
            
            # 수익률 비교
            "backtest_return_pct": ...,
            "demo_return_pct": ...,
            "tracking_error": ...,       # 추적 오차
            
            # 시그널 일치율
            "signal_match_rate": ...,    # 백테스트 시그널과 실제 진입 시점 일치율
            
            # 경고
            "alerts": [
                {"type": "SLIPPAGE_HIGH", "message": "실측 슬리피지가 예상의 3.2배입니다."},
                {"type": "TRACKING_ERROR_HIGH", "message": "추적 오차가 5% 이상입니다."},
            ]
        }
```

---

## 전략 템플릿 시드 데이터

MVP에 포함할 사전 구축 전략 템플릿:

### 1. RSI 역추세 전략
```pine
//@version=5
strategy("RSI Mean Reversion", overlay=true)
length = input.int(14, "RSI Period")
oversold = input.int(30, "Oversold Level")
overbought = input.int(70, "Overbought Level")

rsi = ta.rsi(close, length)

if ta.crossover(rsi, oversold)
    strategy.entry("Long", strategy.long)
if ta.crossunder(rsi, overbought)
    strategy.close("Long")
```

### 2. 이동평균 크로스오버
```pine
//@version=5
strategy("MA Crossover", overlay=true)
fastLen = input.int(9, "Fast MA")
slowLen = input.int(21, "Slow MA")

fast = ta.ema(close, fastLen)
slow = ta.ema(close, slowLen)

if ta.crossover(fast, slow)
    strategy.entry("Long", strategy.long)
if ta.crossunder(fast, slow)
    strategy.close("Long")
```

### 3. 볼린저 밴드 브레이크아웃
```pine
//@version=5
strategy("BB Breakout", overlay=true)
length = input.int(20, "BB Length")
mult = input.float(2.0, "BB Multiplier")

[middle, upper, lower] = ta.bb(close, length, mult)

if ta.crossover(close, upper)
    strategy.entry("Long", strategy.long)
if ta.crossunder(close, lower)
    strategy.close("Long")
```

### 4. MACD 시그널 전략
```pine
//@version=5
strategy("MACD Signal", overlay=false)
fastLen = input.int(12, "Fast")
slowLen = input.int(26, "Slow")
sigLen = input.int(9, "Signal")

[macdLine, signalLine, hist] = ta.macd(close, fastLen, slowLen, sigLen)

if ta.crossover(macdLine, signalLine)
    strategy.entry("Long", strategy.long)
if ta.crossunder(macdLine, signalLine)
    strategy.close("Long")
```

### 5. 슈퍼트렌드 전략
```pine
//@version=5
strategy("Supertrend Strategy", overlay=true)
atrPeriod = input.int(10, "ATR Period")
factor = input.float(3.0, "Factor")

[supertrend, direction] = ta.supertrend(factor, atrPeriod)

if direction < 0
    strategy.entry("Long", strategy.long)
if direction > 0
    strategy.close("Long")
```

---

## 환경 변수 (.env.example)

```env
# === 앱 설정 ===
APP_NAME=QuantBridge
APP_ENV=development          # development | staging | production
DEBUG=true
SECRET_KEY=your-secret-key-change-in-production

# === Clerk 인증 ===
CLERK_SECRET_KEY=sk_test_...
CLERK_PUBLISHABLE_KEY=pk_test_...
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_test_...
CLERK_WEBHOOK_SECRET=whsec_...         # Clerk Webhook 검증용

# === 데이터베이스 ===
DATABASE_URL=postgresql+asyncpg://quantbridge:password@db:5432/quantbridge
TIMESCALE_URL=postgresql+asyncpg://quantbridge:password@timescaledb:5432/quantbridge_ts

# === Redis ===
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# === 암호화 (거래소 API Key 저장용) ===
ENCRYPTION_KEY=your-aes-256-encryption-key

# === CORS ===
FRONTEND_URL=http://localhost:3000

# === 거래소 기본 설정 ===
DEFAULT_EXCHANGE=bybit
```

---

## Docker Compose (개발 환경)

```yaml
version: "3.8"

services:
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
      - NEXT_PUBLIC_WS_URL=ws://localhost:8000
    volumes:
      - ./frontend/src:/app/src
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: .env
    volumes:
      - ./backend/app:/app/app
      - ./data:/app/data
    depends_on:
      - db
      - timescaledb
      - redis
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  celery_worker:
    build: ./backend
    env_file: .env
    volumes:
      - ./backend/app:/app/app
      - ./data:/app/data
    depends_on:
      - redis
      - db
    command: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4

  celery_beat:
    build: ./backend
    env_file: .env
    depends_on:
      - redis
    command: celery -A app.tasks.celery_app beat --loglevel=info

  db:
    image: postgres:15
    environment:
      POSTGRES_USER: quantbridge
      POSTGRES_PASSWORD: password
      POSTGRES_DB: quantbridge
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  timescaledb:
    image: timescale/timescaledb:latest-pg15
    environment:
      POSTGRES_USER: quantbridge
      POSTGRES_PASSWORD: password
      POSTGRES_DB: quantbridge_ts
    ports:
      - "5433:5432"
    volumes:
      - timescale_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
  timescale_data:
```

---

## 구현 순서 (Phase별 상세)

### Phase 1: 프로젝트 초기화 + 기본 백테스트 (주 1~4)

**주 1: 프로젝트 셋업**
- [ ] Next.js 16 + TypeScript Strict + Tailwind v4 + shadcn/ui v4 프론트엔드 초기화 (pnpm)
- [ ] FastAPI + SQLModel + Alembic 백엔드 초기화 (uv, 100% async)
- [ ] Docker Compose 개발 환경 구성 (healthcheck 포함)
- [ ] PostgreSQL + TimescaleDB + Redis 컨테이너 설정
- [ ] DB 마이그레이션 (users, strategies 테이블 — cuid2 ID, createdAt/updatedAt)
- [ ] Clerk 인증 연동 (Frontend proxy.ts + Backend JWT 검증 + Webhook 동기화)

**주 2: Pine Script 파서 + 데이터 파이프라인**
- [ ] Pine Script 간이 파서 구현 (정규식 기반)
  - input 파라미터 추출
  - 인디케이터 사용 감지
  - strategy.entry / strategy.close 추출
- [ ] Pine → Python 기본 변환기 (인디케이터 매핑 테이블)
- [ ] CCXT 기반 Bybit OHLCV 데이터 수집기 구현
- [ ] TimescaleDB에 OHLCV 저장 + 조회 API
- [ ] 전략 CRUD API (생성, 조회, 수정, 삭제)

**주 3: 백테스트 엔진 코어**
- [ ] vectorbt 기반 백테스트 엔진 구현
- [ ] 단일 심볼 백테스트 실행
- [ ] 성과 지표 계산 모듈 (샤프, MDD, 승률, PF 등)
- [ ] 거래 내역 추출
- [ ] Celery 비동기 태스크로 백테스트 실행
- [ ] 백테스트 진행률 WebSocket 전송

**주 4: 프론트엔드 기본 UI**
- [ ] 대시보드 레이아웃 (사이드바, 헤더)
- [ ] Pine Script 에디터 페이지 (Monaco Editor)
- [ ] 파싱 결과 미리보기 패널
- [ ] 백테스트 설정 폼 (심볼, 기간, 자본금, 수수료 등)
- [ ] 백테스트 결과 리포트 페이지
  - 핵심 지표 카드
  - Equity Curve 차트 (TradingView Lightweight Charts)
  - 드로우다운 차트
  - 거래 내역 테이블

### Phase 2: 고급 백테스트 + 최적화 (주 5~8)

**주 5: 멀티심볼 + 리얼리스틱 시뮬레이션**
- [ ] 멀티심볼 병렬 백테스트 (Celery 워커 활용)
- [ ] 심볼별 결과 비교 히트맵 UI
- [ ] 리얼리스틱 슬리피지 모델
- [ ] 거래소별 수수료 체계 반영
- [ ] 펀딩비 데이터 수집 + 반영
- [ ] 멀티 타임프레임 비교 테스트

**주 6: 스트레스 테스트**
- [ ] Monte Carlo 시뮬레이션 구현 (거래 순서 셔플, 슬리피지 랜덤)
- [ ] Monte Carlo 결과 시각화 (Equity Curve 밴드, 분위수)
- [ ] Walk-Forward Analysis 구현
- [ ] Walk-Forward 결과 시각화 (IS vs OOS 비교 차트)
- [ ] 파라미터 안정성 분석 (3D 서피스 차트)
- [ ] 스트레스 테스트 리포트 종합 페이지

**주 7: 파라미터 최적화**
- [ ] 그리드 서치 최적화 구현
- [ ] Optuna 기반 베이지안 최적화 구현
- [ ] 최적화 결과 시각화 (파라미터 히트맵, 수렴 그래프)
- [ ] 과적합 경고 시스템 (파라미터 절벽 감지)

**주 8: 전략 템플릿 + 폴리시**
- [ ] 사전 구축 전략 템플릿 5개 등록
- [ ] 템플릿 목록/상세 페이지 UI
- [ ] 템플릿에서 내 전략으로 복사 기능
- [ ] 월간 수익률 히트맵 차트
- [ ] 시간대별 성과 분석 차트
- [ ] 전체 UI 폴리시 + 반응형 대응

### Phase 3: 데모 트레이딩 (주 9~12)

**주 9: 거래소 연동 기반**
- [ ] 거래소 API Key 등록/관리 API + UI
- [ ] API Key AES-256 암호화 저장
- [ ] CCXT 기반 ExchangeExecutor 구현
- [ ] Bybit Demo API 연결 테스트
- [ ] 잔고 조회, 주문, 포지션 조회 기본 기능
- [ ] API Key 유효성 테스트 엔드포인트

**주 10: 실시간 전략 실행 엔진**
- [ ] StrategyRunner 실시간 루프 구현
- [ ] 실시간 시장 데이터 수신 (CCXT WebSocket)
- [ ] 시그널 판단 → 주문 전송 파이프라인
- [ ] RiskManager 구현 (일일 손실 한도, MDD 한도)
- [ ] Kill Switch 긴급 청산 기능
- [ ] 트레이딩 세션 상태 관리 (start/stop/kill)

**주 11: 데모 트레이딩 UI**
- [ ] 데모 트레이딩 모니터링 페이지
- [ ] 실시간 차트 + 진입/청산 마커
- [ ] 현재 포지션 / 미체결 주문 테이블
- [ ] 실시간 PnL 트래커
- [ ] 거래 로그 (체결가, 슬리피지, 수수료)
- [ ] Kill Switch 버튼 (확인 다이얼로그 포함)

**주 12: 백테스트 vs 데모 비교**
- [ ] PerformanceComparator 구현
- [ ] 백테스트 예상 vs 데모 실제 비교 차트
- [ ] 슬리피지 실측 분석
- [ ] 추적 오차 계산
- [ ] 괴리 경고 알림 시스템
- [ ] Binance Testnet 추가 연동

### Phase 4: 라이브 트레이딩 + 확장 (주 13~16)

**주 13: 라이브 전환**
- [ ] 라이브 모드 ExchangeExecutor (URL 전환)
- [ ] 라이브 전환 확인 프로세스 (체크리스트 + 경고)
- [ ] 라이브 트레이딩 콘솔 UI
- [ ] 점진적 스케일업 설정 (1주차 최소 → 점진 증가)

**주 14: 리스크 관리 강화**
- [ ] 고급 포지션 사이징 (리스크 기반, Kelly Criterion)
- [ ] 이상 감지 (백테스트 대비 2σ 이상 괴리 시 알림)
- [ ] 일일/주간 리포트 자동 생성
- [ ] 텔레그램/디스코드 알림 연동

**주 15: 추가 거래소 + 데이터**
- [ ] OKX Demo Trading 연동
- [ ] Bitget Demo 연동
- [ ] 데이터 자동 수집 스케줄러 (Celery Beat)
- [ ] 더 많은 심볼 데이터 수집

**주 16: 최종 폴리시**
- [ ] 전체 UI/UX 리뷰 + 개선
- [ ] 에러 핸들링 + 로깅 강화
- [ ] 성능 최적화 (쿼리, 캐싱)
- [ ] 문서화 (API 문서, 사용 가이드)
- [ ] 배포 파이프라인 (Docker 이미지, CI/CD)

---

## UI 디자인 가이드라인

### 색상 팔레트
- **배경**: 다크 테마 기본 (`#0f1117` 메인, `#1a1d29` 카드/패널)
- **텍스트**: `#e1e4e8` (기본), `#8b949e` (보조)
- **수익/상승**: `#26a69a` (초록)
- **손실/하락**: `#ef5350` (빨강)
- **액센트**: `#5b8def` (파란색, 버튼/링크)
- **경고**: `#ffb74d` (주황)
- **보더**: `#30363d`

### 레이아웃
- 좌측 사이드바 (접을 수 있음): 네비게이션
- 상단 헤더: 사용자 정보, 알림, 설정
- 메인 콘텐츠: 풀 너비 활용, 카드 기반 레이아웃
- TradingView 차트는 가능한 넓게 (최소 높이 400px)

### 폰트
- 코드: JetBrains Mono 또는 Fira Code
- UI: Inter

### 차트 스타일
- TradingView Lightweight Charts 다크 테마
- 캔들: 상승 `#26a69a`, 하락 `#ef5350`
- 그리드: `#1e222d`
- 크로스헤어: `#758696`

---

## 주의사항 및 제약

### 보안
- 거래소 API Key는 반드시 AES-256으로 암호화 저장. 평문 저장 절대 금지.
- JWT 토큰 만료 시간 적절히 설정 (기본 24시간)
- API Rate Limiting 적용 (백테스트 요청 등)
- CORS 설정 프론트엔드 도메인만 허용

### 성능
- 백테스트는 반드시 Celery 비동기 태스크로 실행. 절대 API 요청 내에서 동기 실행하지 않음.
- OHLCV 데이터는 TimescaleDB에서 직접 조회. 매번 거래소 API 호출하지 않음.
- 멀티심볼 백테스트 시 Celery 워커 풀 활용한 병렬 처리.
- 대용량 백테스트 결과(거래 내역 등)는 페이지네이션 필수.

### 데이터
- 거래소 API Rate Limit 준수 (CCXT enableRateLimit: true)
- OHLCV 데이터 수집 시 누락 구간 감지 + 재수집 로직 필요
- 데이터 품질 검증 (이상치, 갭 등) 백테스트 전 수행

### Pine Script 파서 한계
- MVP에서는 모든 Pine Script를 100% 변환할 수 없음을 사용자에게 안내
- 지원하지 않는 함수/구문 발견 시 명확한 에러 메시지 제공
- security() (멀티 타임프레임), request.financial() 등은 Phase 2 이후 지원

### 거래소 관련
- Bybit Demo Trading과 Testnet은 다른 환경. Demo는 메인넷 기반 시뮬레이션, Testnet은 별도 플랫폼.
- Demo API의 WebSocket은 private stream만 지원. public data는 메인넷 WebSocket 사용.
- 한국 사용자의 경우 특정 거래소 접근 제한 가능성 있음 (IP 기반)

---

## 성공 기준 (KPI)

### MVP 런칭 시점 기준
- Pine Script 파싱 성공률: 주요 전략 패턴 80% 이상
- 백테스트 실행 시간: 단일 심볼 1년 1시간봉 기준 10초 이내
- 데모 트레이딩 주문 체결 지연: 2초 이내
- 백테스트 결과 정확성: vectorbt 직접 실행 결과와 99% 이상 일치

### 사용자 관점
- 전략 임포트부터 첫 백테스트 결과까지 5분 이내
- 백테스트에서 데모 트레이딩 전환까지 3클릭 이내
- 데모에서 라이브 전환까지 2클릭 이내 (확인 포함)

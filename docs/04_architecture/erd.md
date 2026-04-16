# QuantBridge — ERD (Entity Relationship Diagram)

> **기준:** Sprint 4 완료 시점 SQLModel 실제 코드 기반 (2026-04-16).
> **SSOT:** 각 도메인 `backend/src/<domain>/models.py`. 본 문서와 코드 충돌 시 코드 우선.
> **DB:** PostgreSQL 15+ (메인) + TimescaleDB 확장 (시계열) + Redis (캐시/Celery)

---

## 엔티티 관계도

```mermaid
erDiagram
    users ||--o{ strategies : "owns (CASCADE)"
    users ||--o{ backtests : "runs (CASCADE)"
    strategies ||--o{ backtests : "tested by (RESTRICT)"
    backtests ||--o{ backtest_trades : "contains (CASCADE)"

    users ||--o{ exchange_accounts : "owns"
    users ||--o{ stress_tests : "runs"
    users ||--o{ trading_sessions : "runs"
    strategies ||--o{ trading_sessions : "executed by"
    backtests ||--o{ stress_tests : "analyzed by"
    backtests ||--o| trading_sessions : "referenced by"
    exchange_accounts ||--o{ trading_sessions : "used by"
    trading_sessions ||--o{ live_trades : "contains"

    users {
        uuid id PK "uuid4"
        varchar clerk_user_id UK "Clerk user_id (max 64)"
        varchar email "nullable (max 320)"
        varchar username "nullable (max 64)"
        boolean is_active "default true, indexed"
        datetime created_at "server_default NOW()"
        datetime updated_at "onupdate NOW()"
    }

    strategies {
        uuid id PK "uuid4"
        uuid user_id FK "→ users.id CASCADE, indexed"
        varchar name "max 120, NOT NULL"
        varchar description "nullable (max 2000)"
        text pine_source "NOT NULL"
        enum pine_version "PineVersion: v4 | v5"
        enum parse_status "ParseStatus: ok | unsupported | error, indexed"
        jsonb parse_errors "nullable"
        varchar timeframe "nullable (max 16)"
        varchar symbol "nullable (max 32)"
        jsonb tags "default []"
        boolean is_archived "default false, indexed"
        datetime created_at "server_default NOW()"
        datetime updated_at "onupdate NOW()"
    }

    backtests {
        uuid id PK "uuid4"
        uuid user_id FK "→ users.id CASCADE, indexed"
        uuid strategy_id FK "→ strategies.id RESTRICT, indexed"
        varchar symbol "max 32, NOT NULL"
        varchar timeframe "max 8, NOT NULL"
        datetime period_start "NOT NULL"
        datetime period_end "NOT NULL"
        decimal initial_capital "DECIMAL(20,8), NOT NULL"
        enum status "BacktestStatus (6값), indexed"
        varchar celery_task_id "nullable (max 64)"
        jsonb metrics "nullable (completed 시)"
        jsonb equity_curve "nullable (completed 시)"
        text error "nullable (failed 시)"
        datetime created_at "NOT NULL"
        datetime started_at "nullable"
        datetime completed_at "nullable"
    }

    backtest_trades {
        uuid id PK "uuid4"
        uuid backtest_id FK "→ backtests.id CASCADE, indexed"
        integer trade_index "NOT NULL"
        enum direction "TradeDirection: long | short"
        enum status "TradeStatus: open | closed"
        datetime entry_time "NOT NULL"
        datetime exit_time "nullable"
        decimal entry_price "DECIMAL(20,8)"
        decimal exit_price "nullable, DECIMAL(20,8)"
        decimal size "DECIMAL(20,8)"
        decimal pnl "DECIMAL(20,8)"
        decimal return_pct "DECIMAL(12,6)"
        decimal fees "DECIMAL(20,8), default 0"
    }

    stress_tests {
        uuid id PK "uuid4 (미구현)"
        uuid backtest_id FK "→ backtests.id"
        uuid user_id FK "→ users.id"
        varchar test_type "monte_carlo | walk_forward | param_stability"
        jsonb config "시뮬레이션 설정"
        varchar status ""
        float progress ""
        jsonb results ""
        datetime created_at ""
        datetime updated_at ""
        datetime completed_at ""
    }

    exchange_accounts {
        uuid id PK "uuid4 (미구현)"
        uuid user_id FK "→ users.id"
        varchar exchange "bybit | binance | okx"
        varchar label ""
        text api_key_encrypted "AES-256"
        text api_secret_encrypted "AES-256"
        boolean is_demo ""
        boolean is_active ""
        jsonb permissions ""
        datetime created_at ""
        datetime updated_at ""
    }

    trading_sessions {
        uuid id PK "uuid4 (미구현)"
        uuid strategy_id FK "→ strategies.id"
        uuid exchange_account_id FK "→ exchange_accounts.id"
        uuid user_id FK "→ users.id"
        varchar mode "demo | live"
        varchar status ""
        jsonb config "심볼/레버리지/리스크"
        decimal current_pnl "DECIMAL(20,8)"
        decimal current_pnl_pct "DECIMAL(12,6)"
        integer total_trades ""
        integer win_trades ""
        uuid reference_backtest_id FK "→ backtests.id, nullable"
        datetime started_at ""
        datetime stopped_at ""
        datetime created_at ""
        datetime updated_at ""
    }

    live_trades {
        uuid id PK "uuid4 (미구현)"
        uuid session_id FK "→ trading_sessions.id"
        varchar symbol ""
        varchar side "buy | sell"
        datetime entry_time ""
        datetime exit_time ""
        decimal entry_price "DECIMAL(20,8)"
        decimal exit_price "DECIMAL(20,8)"
        decimal quantity "DECIMAL(20,8)"
        integer leverage ""
        varchar entry_order_id "거래소 주문 ID"
        varchar exit_order_id "거래소 주문 ID"
        decimal actual_slippage "DECIMAL(20,8)"
        decimal commission "DECIMAL(20,8)"
        decimal funding_fee "DECIMAL(20,8)"
        decimal pnl "DECIMAL(20,8)"
        decimal pnl_pct "DECIMAL(12,6)"
        varchar status "open | closed"
        varchar close_reason ""
        datetime created_at ""
        datetime updated_at ""
    }
```

---

## Enum 정의 (구현됨)

| Enum | 값 | 코드 위치 |
|------|----|-----------|
| `BacktestStatus` | `queued` · `running` · `cancelling` (transient) · `completed` · `failed` · `cancelled` | `backtest/models.py` |
| `ParseStatus` | `ok` · `unsupported` · `error` | `strategy/models.py` |
| `PineVersion` | `v4` · `v5` | `strategy/models.py` |
| `TradeDirection` | `long` · `short` | `backtest/models.py` |
| `TradeStatus` | `open` · `closed` | `backtest/models.py` |

---

## FK 정책 (구현됨)

| 부모 → 자식 | ondelete | 이유 |
|-------------|----------|------|
| `users` → `strategies` | CASCADE | 사용자 탈퇴 시 전략 일괄 삭제 |
| `users` → `backtests` | CASCADE | 동일 |
| `strategies` → `backtests` | **RESTRICT** | 백테스트가 참조 중이면 전략 삭제 금지 → 409 |
| `backtests` → `backtest_trades` | CASCADE | 백테스트 삭제 시 trades 동시 삭제 + ORM cascade all,delete-orphan |

미구현 도메인의 FK 정책은 구현 sprint에서 확정 (PRD 기준 계획만 존재).

---

## 인덱스 (구현됨)

| 테이블 | 인덱스 | 컬럼 |
|--------|--------|------|
| `users` | PK | `id` |
| `users` | UNIQUE | `clerk_user_id` |
| `users` | index | `is_active` |
| `strategies` | PK | `id` |
| `strategies` | index | `user_id` |
| `strategies` | index | `parse_status` |
| `strategies` | index | `is_archived` |
| `strategies` | composite | `(user_id, is_archived, updated_at)` — `ix_strategies_owner_active_updated` |
| `backtests` | PK | `id` |
| `backtests` | index | `user_id` |
| `backtests` | index | `strategy_id` |
| `backtests` | index | `status` — `ix_backtests_status` |
| `backtests` | composite | `(user_id, created_at)` — `ix_backtests_user_created` |
| `backtest_trades` | PK | `id` |
| `backtest_trades` | index | `backtest_id` |
| `backtest_trades` | composite | `(backtest_id, trade_index)` — `ix_backtest_trades_backtest_idx` |

---

## 구현 상태

| 테이블 | SQLModel | Alembic Migration | Sprint |
|--------|----------|--------------------|----|
| `users` | ✅ `auth/models.py` | ✅ | 3 |
| `strategies` | ✅ `strategy/models.py` | ✅ | 3 |
| `backtests` | ✅ `backtest/models.py` | ✅ | 4 |
| `backtest_trades` | ✅ `backtest/models.py` | ✅ | 4 |
| `stress_tests` | ❌ 빈 파일 | ❌ | Sprint 6+ |
| `exchange_accounts` | ❌ 빈 파일 | ❌ | Sprint 7+ |
| `trading_sessions` | ❌ 빈 파일 | ❌ | Sprint 7+ |
| `live_trades` | ❌ 빈 파일 | ❌ | Sprint 7+ |
| `ts.ohlcv` (hypertable) | ✅ `market_data/models.py` | ✅ M2 | 5 |
| `funding_rates` (hypertable) | ❌ 빈 파일 | ❌ | Sprint 6+ |

> 미구현 도메인의 스키마는 PRD 설계 기준. 구현 sprint에서 SQLModel과 재정합 필수.

---

## JSONB 데이터 구조 (구현됨)

| 테이블 | 필드 | 내용 | 직렬화 규칙 |
|--------|------|------|-------------|
| `strategies` | `parse_errors` | 미지원 함수 목록 `[{"call": "request.security", ...}]` | — |
| `strategies` | `tags` | 분류 태그 `["trend", "momentum"]` | — |
| `backtests` | `metrics` | `{total_return: "0.12", sharpe: "1.5", max_drawdown: "0.08", num_trades: 42, ...}` | Decimal → str, `num_trades`는 int (cardinality 필드) |
| `backtests` | `equity_curve` | `[{"t": "2024-01-01T00:00:00Z", "v": "10120.50"}, ...]` | Decimal → str, datetime → ISO 8601 Z |

> 직렬화: `backtest/serializers.py` (`metrics_to_jsonb`, `equity_curve_to_jsonb`).

---

## PRD 대비 실제 변경사항

| 항목 | PRD/Phase 0 ERD | 실제 구현 (Sprint 4) | 이유 |
|------|-----------------|---------------------|------|
| `users.id` | `VARCHAR(255)` Clerk user_id를 PK로 | `UUID` PK + `clerk_user_id` 별도 컬럼 | 내부 PK와 외부 ID 분리 (더 나은 설계) |
| `users.hashed_password` | 존재 | **삭제** | Clerk가 인증 담당 |
| `users.is_premium` | 존재 | **삭제** | Sprint 3 미구현, 추후 추가 가능 |
| `users.email/username` | UNIQUE | nullable, UNIQUE 미설정 | Clerk 동기화 시 없을 수 있음 |
| 모든 엔티티 ID | `VARCHAR` (cuid2) | **`UUID`** (uuid4) | 구현 시 UUID로 통일 |
| `strategies.pine_script` | 존재 | `pine_source` | 컬럼명 변경 |
| `strategies.parsed_result` (JSONB) | 존재 | **삭제** (parse_errors + parse_status로 대체) | 파서 결과 구조 변경 |
| `strategies.version` (int) | 존재 | **삭제** | 불필요 판단 |
| `strategies.status` | `varchar` | `parse_status` enum (ok/unsupported/error) | 명확한 enum + 이름 변경 |
| `backtests.config` (JSONB) | 단일 JSONB | 개별 컬럼 5개로 정규화 | 타입 안전성 + 쿼리 가능 |
| `backtests.results` (JSONB) | 단일 JSONB | `metrics` + `equity_curve` 2개 JSONB로 분리 | 용도 분리 |
| `backtests.progress` | float | **삭제** | 불필요 판단 (status로 충분) |
| `backtests.updated_at` | 존재 | **삭제** | created_at + started_at + completed_at로 충분 |
| `backtest_trades` | **없음** | Sprint 4에서 추가 (12 컬럼) | 개별 거래 기록 필요 |
| 금융 수치 | `FLOAT` 혼용 | `DECIMAL(20, 8)` 통일 | 정밀도 보장 (float 금지) |
| 수익률/비율 | 미정 | `DECIMAL(12, 6)` | 10,000% 여유 |

---

## TimescaleDB 테이블 (시계열)

### ts.ohlcv (hypertable, ✅ Sprint 5 M2 활성)
```sql
-- 마이그레이션 파일: backend/alembic/versions/20260416_1458_create_ohlcv_hypertable.py
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE SCHEMA IF NOT EXISTS ts;

CREATE TABLE ts.ohlcv (
    time TIMESTAMPTZ NOT NULL,                  -- AwareDateTime (ADR-005)
    symbol VARCHAR(32) NOT NULL,                -- CCXT unified format ("BTC/USDT")
    timeframe VARCHAR(8) NOT NULL,              -- Literal["1m","5m","15m","1h","4h","1d"]
    exchange VARCHAR(32) NOT NULL,              -- "bybit", "binance", ...
    open NUMERIC(18, 8) NOT NULL,               -- Decimal-first 정책 (float 금지)
    high NUMERIC(18, 8) NOT NULL,
    low NUMERIC(18, 8) NOT NULL,
    close NUMERIC(18, 8) NOT NULL,
    volume NUMERIC(18, 8) NOT NULL,
    PRIMARY KEY (time, symbol, timeframe)       -- partition key(time) 포함 필수
);
SELECT create_hypertable(
    'ts.ohlcv', 'time',
    chunk_time_interval => INTERVAL '7 days',
    if_not_exists => TRUE
);
-- 보조 인덱스: 최신 캔들 조회 reverse scan (Postgres ASC 인덱스 양방향 가능)
CREATE INDEX ix_ohlcv_symbol_tf_time_desc ON ts.ohlcv (symbol, timeframe, time);
```

**운영 정책:**
- Repository: `OHLCVRepository` (`backend/src/market_data/repository.py`)
  - `insert_bulk` — `ON CONFLICT (time, symbol, timeframe) DO NOTHING` (idempotent)
  - `find_gaps` — `generate_series` + `EXCEPT` + ROW_NUMBER island grouping
  - `acquire_fetch_lock` — `pg_advisory_xact_lock(hashtext(symbol:tf:start:end))` (동시 fetch race 방지)
- Provider: `TimescaleProvider` cache → CCXT fallback fetch + advisory lock + insert (자세한 flow는 [`data-flow.md`](./data-flow.md) §OHLCV cache)

### funding_rates (hypertable, ⏳ Sprint 6+ 계획)
```sql
CREATE TABLE ts.funding_rates (
    time TIMESTAMPTZ NOT NULL,
    exchange VARCHAR(32) NOT NULL,
    symbol VARCHAR(32) NOT NULL,
    funding_rate NUMERIC(20, 10) NOT NULL,
    PRIMARY KEY (time, exchange, symbol)
);
SELECT create_hypertable('ts.funding_rates', 'time', chunk_time_interval => INTERVAL '7 days');
```

> 마이그레이션 자체가 `CREATE EXTENSION` + `CREATE SCHEMA`까지 책임 — `docker/db/init/01-timescaledb.sql`이 누락된 환경(test/fresh)에서도 단독 동작 보장.

---

## Datetime 정책

- Sprint 5 S3-05 이전 (현재): naive UTC (`datetime.now(UTC).replace(tzinfo=None)`) + ISO 8601 Z 수동 포맷
- Sprint 5 S3-05 이후 (예정): `DateTime(timezone=True)` (TIMESTAMPTZ) + `datetime.now(UTC)` + `.isoformat()`
- 상세: `docs/TODO.md` §S3-05

---

## 변경 이력

- **2026-04-13** — Phase 0 초안 (PRD 기반)
- **2026-04-16** — Sprint 4 완료 기준 전면 갱신 (Sprint 5 Stage A)
  - ID 체계 cuid2 → UUID 반영
  - users.id 구조 변경 (UUID PK + clerk_user_id 분리) 반영
  - strategies 컬럼 대폭 변경 반영
  - backtests config/results 정규화 반영
  - backtest_trades 테이블 추가
  - Enum/FK/Index 상세 추가
  - PRD 대비 변경사항 표 갱신

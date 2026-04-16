# QuantBridge — 엔티티 카탈로그 (ENT-###)

> **목적:** 도메인 엔티티의 책임·핵심 필드·상태·코드 위치 인덱스.
> **SSOT:** 컬럼 정의는 [`04_architecture/erd.md`](../04_architecture/erd.md), 실 SQLModel은 `backend/src/<domain>/models.py`.
> **Note:** 미구현 도메인의 엔티티는 PRD/ERD 기준 **계획 명세** — 실제 활성 sprint에서 ERD와 재정합.

---

## ENT-001 — User

- **도메인:** auth
- **코드:** `backend/src/auth/models.py` (`class User`)
- **테이블:** `users`
- **책임:** Clerk 동기화된 사용자 계정. 모든 도메인의 권한 단위.
- **PK:** Clerk `user_id` (VARCHAR) — auto-increment 금지
- **주요 필드:**
  - `id: str` (Clerk user_id)
  - `email: str` (unique)
  - `username: str | None` (Clerk 동기화 누락 가능)
  - `is_active: bool`, `is_premium: bool`
  - `created_at`, `updated_at`
- **불변량:** id 변경 불가. Clerk Webhook으로 lifecycle 동기화.
- **API:** `GET /auth/me`, Webhook `POST /webhooks/clerk`

---

## ENT-002 — Strategy

- **도메인:** strategy
- **코드:** `backend/src/strategy/models.py` (`class Strategy`)
- **테이블:** `strategies`
- **책임:** Pine Script 코드 + 파싱 결과 + 트랜스파일된 Python 코드의 진실.
- **PK:** UUID
- **주요 필드:**
  - `id: UUID`, `user_id: str FK`
  - `name: str`, `description: str | None`
  - `pine_version: PineVersion` (V4 / V5)
  - `raw_source: str` (Pine 코드 원본)
  - `parsed_result: JSONB` (인디케이터·진입/청산 조건·트랜스파일된 Python)
  - `parse_status: ParseStatus` (PENDING / SUPPORTED / UNSUPPORTED)
  - `version: int`, `is_archived: bool`
  - `created_at`, `updated_at`
- **상태 머신:** `parse_status` (단순), `is_archived` (soft delete) — [`state-machines.md`](./state-machines.md)
- **불변량:**
  - `parse_status=UNSUPPORTED`이면 백테스트 불가
  - 백테스트가 참조 중이면 hard delete 금지 (FK RESTRICT → 409)
- **API:** §전략 (CRUD 6 + parse preview 1)

---

## ENT-003 — Backtest

- **도메인:** backtest
- **코드:** `backend/src/backtest/models.py` (`class Backtest`)
- **테이블:** `backtests`
- **책임:** vectorbt 실행 결과. 입력 파라미터(불변) + 진행 상태 + 결과(JSONB).
- **PK:** UUID
- **주요 필드:**
  - `id: UUID`, `user_id FK`, `strategy_id FK` (RESTRICT)
  - 입력 (불변): `symbol`, `timeframe`, `period_start`, `period_end`, `initial_capital: Decimal`, `fees`, `slippage`
  - 상태: `status: BacktestStatus` (QUEUED → RUNNING → COMPLETED/FAILED, 또는 CANCELLING transient → CANCELLED)
  - 진행: `progress: float` (0~1), `started_at`, `completed_at`
  - 결과: `metrics: JSONB` (sharpe, MDD, total_return, num_trades 등), `equity_curve: JSONB`
  - 에러: `error_reason: str | None`, `error_traceback: str | None`
  - Cancel: `cancellation_requested_at: datetime | None`
- **상태 머신:** [`state-machines.md`](./state-machines.md) §Backtest 6-state
- **불변량:**
  - `metrics` 저장은 Decimal → str 변환 필수
  - `equity_curve` timestamp는 ISO 8601 Z 포맷
  - 완료 write와 trade insert는 단일 트랜잭션 (atomicity)
  - `BacktestStatus` 전이 검증은 Service의 3-guard
- **API:** §백테스트 (submit/list/detail/cancel/delete/trades/progress 7개)

---

## ENT-004 — BacktestTrade

- **도메인:** backtest
- **코드:** `backend/src/backtest/models.py` (`class BacktestTrade`)
- **테이블:** `backtest_trades`
- **책임:** 백테스트 시뮬레이션의 개별 거래 기록.
- **PK:** UUID
- **주요 필드:**
  - `id: UUID`, `backtest_id FK` (CASCADE)
  - `direction: TradeDirection` (LONG/SHORT)
  - `status: TradeStatus` (OPEN/CLOSED)
  - `entry_time`, `entry_price: Decimal`, `entry_bar_index: int`
  - `exit_time`, `exit_price: Decimal`, `exit_bar_index: int`
  - `quantity: Decimal`, `pnl: Decimal`, `pnl_pct: Decimal`
  - `fees: Decimal` (진입+청산 합산 — Decimal-first)
  - `close_reason: str | None` (signal/sl/tp/timeout 등)
- **불변량:**
  - 부모 Backtest 삭제 시 CASCADE 정리
  - PnL 계산은 Decimal-first (`Decimal(str(exit)) - Decimal(str(entry))` 후 합산)
- **API:** `GET /backtests/:id/trades` (페이지네이션)

---

## ENT-005 — StressTest *(미구현, Sprint 6+)*

- **도메인:** stress_test
- **코드:** `backend/src/stress_test/models.py` (스캐폴딩)
- **테이블:** `stress_tests` (계획)
- **책임:** Backtest 결과 위에서 Monte Carlo / Walk-Forward / 파라미터 안정성 분석.
- **계획 필드:** `backtest_id FK` (CASCADE), `test_type`, `config: JSONB`, `status`, `progress`, `results: JSONB` (CI 95%, 파산 확률 등)
- **API:** §스트레스 테스트 (PRD §API 참조)

---

## ENT-006 — Optimization *(미구현, Sprint 6+)*

- **도메인:** optimizer
- **코드:** `backend/src/optimizer/models.py` (스캐폴딩)
- **책임:** 파라미터 grid/Bayesian/genetic 탐색 결과.
- **계획 필드:** `strategy_id FK`, `method` (GRID/BAYES/GENETIC), `param_space: JSONB`, `best_params: JSONB`, `trials: JSONB`
- **API:** §최적화

---

## ENT-007 — TradingSession *(미구현, Sprint 7+)*

- **도메인:** trading
- **코드:** `backend/src/trading/models.py` (스캐폴딩)
- **테이블:** `trading_sessions` (계획)
- **책임:** 데모/라이브 트레이딩 세션 lifecycle + 누적 PnL.
- **계획 필드:**
  - `strategy_id FK`, `exchange_account_id FK`, `user_id FK`
  - `mode: SessionMode` (DEMO/LIVE)
  - `status: SessionStatus` (PENDING/RUNNING/STOPPED/KILLED)
  - `config: JSONB` (심볼/레버리지/리스크 한도/Kill Switch 임계)
  - `current_pnl: Decimal`, `total_trades`, `win_trades`
  - `reference_backtest_id FK | None` (검증 비교용)
  - `started_at`, `stopped_at`
- **상태 머신:** [`state-machines.md`](./state-machines.md) §TradingSession (계획)

---

## ENT-008 — LiveTrade *(미구현, Sprint 7+)*

- **도메인:** trading
- **코드:** `backend/src/trading/models.py` (스캐폴딩)
- **책임:** 실거래 또는 데모 거래의 개별 체결 기록.
- **계획 필드:**
  - `session_id FK` (CASCADE 검토 필요 — 세션 종료 시 보존 정책 미정)
  - `symbol`, `side`, `entry_time`, `exit_time`
  - `entry_price`, `exit_price`, `quantity`, `leverage`
  - `entry_order_id`, `exit_order_id` (거래소 주문 ID)
  - `actual_slippage`, `commission`, `funding_fee`, `pnl`
  - `status` (OPEN/CLOSED), `close_reason`

---

## ENT-009 — ExchangeAccount *(미구현, Sprint 7+)*

- **도메인:** exchange
- **코드:** `backend/src/exchange/models.py` (스캐폴딩)
- **테이블:** `exchange_accounts` (계획)
- **책임:** 사용자별 거래소 API Key 보관 + 권한 메타.
- **계획 필드:**
  - `user_id FK`, `exchange` (BYBIT/BINANCE/OKX), `label`
  - `api_key_encrypted: TEXT` (AES-256), `api_secret_encrypted: TEXT` (AES-256)
  - `is_demo: bool`, `is_active: bool`, `permissions: JSONB`
- **불변량:**
  - 평문 키 절대 DB 미저장
  - API 응답에서 `api_key_masked="****abcd"` 형태로만 노출
  - 활성 TradingSession이 참조 중이면 삭제 금지 (FK RESTRICT)

---

## ENT-010 — OHLCV *(Sprint 5 도입)*

- **도메인:** market_data
- **코드:** `backend/src/market_data/models.py` (스캐폴딩, Sprint 5에서 활성)
- **테이블:** `ohlcv` (TimescaleDB hypertable)
- **책임:** 거래소별 시계열 가격 데이터.
- **계획 필드 (ERD §TimescaleDB):**
  - `time: TIMESTAMPTZ`, `exchange`, `symbol`, `timeframe`
  - `open`, `high`, `low`, `close`, `volume` (모두 `DECIMAL(20, 8)`)
  - PK: `(time, exchange, symbol, timeframe)`
- **하이퍼테이블 설정:** `create_hypertable('ohlcv', 'time')` + `chunk_time_interval` 1주 [가정]
- **불변량:**
  - 동일 PK 중복 시 idempotent (UPSERT 정책 — Sprint 5 결정)
  - Alembic migration과 별도 초기화 (`scripts/init_db.py` 또는 별도 migration step)

---

## ENT-011 — FundingRate *(미구현, Sprint 6+)*

- **도메인:** market_data
- **테이블:** `funding_rates` (TimescaleDB hypertable, 계획)
- **책임:** Perpetual Futures funding rate 시계열.
- **계획 필드:** `time`, `exchange`, `symbol`, `funding_rate: DECIMAL(20, 10)` — PK `(time, exchange, symbol)`

---

## 공통 패턴

### ID 정책
- 사용자(`User.id`)는 Clerk user_id (VARCHAR)
- 그 외 모든 엔티티는 UUID (또는 cuid2 — ERD 참조). auto-increment 금지.

### Timestamp 정책
- 모든 테이블에 `created_at`, `updated_at` 필수 (.ai/ spec)
- Sprint 5 S3-05까지 naive UTC (Z 접미사 수동), 이후 tz-aware

### Decimal 정책
- 금융 수치 컬럼: `DECIMAL(20, 8)`
- 코드에서는 `Decimal` 타입. 합산은 Decimal-first.

### JSONB 직렬화 정책
- Decimal → str (`metrics_to_jsonb`, `equity_curve_to_jsonb` — `backend/src/backtest/serializers.py`)
- naive UTC datetime → ISO 8601 Z 수동 포맷

---

## 변경 이력

- **2026-04-16** — 초안 작성 (Sprint 5 Stage A, ERD/PRD/SQLModel 교차 참조)

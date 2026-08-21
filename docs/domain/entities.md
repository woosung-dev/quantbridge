# QuantBridge — 엔티티 카탈로그 (ENT-###)

> **목적:** 도메인 엔티티의 책임·핵심 필드·상태·코드 위치 인덱스.
> **SSOT:** 컬럼 정의는 [`erd.md`](./erd.md), 실 SQLModel은 `apps/api/src/<domain>/models.py`.
> 정확한 컬럼은 코드 `models.py`와 `erd.md`가 정본이다. `ENT-007`·`ENT-008`은 초기 계획에만 있던 결번이며, 라이브 거래 lifecycle은 `live_signal_sessions` + `orders` + `live_signal_events`가 표현한다.

---

## ENT-001 — User

- **도메인:** auth
- **코드:** `apps/api/src/auth/models.py` (`class User`)
- **테이블:** `users`
- **책임:** 인증 subject 에 대응하는 사용자 계정. 모든 도메인의 권한 단위.
- **PK:** `id: UUID` (`uuid4`). 인증 공급자의 subject 는 별도 `auth_subject` (UK, VARCHAR max 64) — 내부 PK ↔ 외부 ID 분리. ★이 분리 덕에 2026-08-17 Clerk → Better Auth 전환이 **이 컬럼 하나**로 끝났다(ADR-034).
- **주요 필드:**
  - `id: UUID` (PK), `auth_subject: str` (UK)
  - `email: str | None` (nullable, max 320 — JWT payload 에 없을 수 있다)
  - `username: str | None` (nullable, max 64)
  - `is_active: bool` (`DELETE /auth/me` → soft delete). (`is_premium` 삭제됨)
  - `created_at`, `updated_at`
- **불변량:** id 변경 불가. 행은 첫 인증 요청에서 생긴다(JIT — 웹훅 없음, ADR-034).
- **API:** `GET /auth/me` · `DELETE /auth/me`(탈퇴 — 돈을 멈춘다)

---

## ENT-002 — Strategy

- **도메인:** strategy
- **코드:** `apps/api/src/strategy/models.py` (`class Strategy`)
- **테이블:** `strategies`
- **책임:** Pine Script 원본 + 파싱 결과 + Live Signal 설정의 진실. (트랜스파일 아님 — `pine_v2` AST 인터프리터, ADR-003)
- **PK:** UUID
- **주요 필드:**
  - `id: UUID`, `user_id: UUID FK` (→ users.id CASCADE)
  - `name: str`, `description: str | None`
  - `pine_source: str` (Pine 코드 원본), `pine_version: PineVersion` (`v4` / `v5`)
  - `parse_status: ParseStatus` (`ok` / `unsupported` / `error` — 파서는 `ok`/`error` 만 set, `unsupported` 는 예약값)
  - `parse_errors: JSONB | None`
  - `timeframe / symbol: str | None`, `tags: JSONB`, `trading_sessions: JSONB` (Sprint 7d session gate)
  - `settings: JSONB | None` (Sprint 26 Live Signal params — leverage/margin_mode/position_size_pct)
  - `is_archived: bool`
  - `created_at`, `updated_at`
- **상태 머신:** `parse_status` + `is_archived` — [`state-machines.md`](./state-machines.md)
- **불변량:**
  - 미지원 함수 포함 시 백테스트 제출 거부 — `parse_status` 가 아니라 **backtest 시점 coverage analyzer** 가 판정 (ADR-003 all-or-nothing)
  - 백테스트가 참조 중이면 hard delete 금지 (FK RESTRICT → 409)
- **API:** §전략 (CRUD 6 + parse preview 1)

---

## ENT-003 — Backtest

- **도메인:** backtest
- **코드:** `apps/api/src/backtest/models.py` (`class Backtest`)
- **테이블:** `backtests`
- **책임:** `pine_v2` 인터프리터(SSOT) 백테스트 실행 결과. 입력 파라미터(불변) + 상태 + 결과(JSONB). (vectorbt 는 ADR-011 로 강등된 뒤 2026-08-06 의존성 제거)
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
- **코드:** `apps/api/src/backtest/models.py` (`class BacktestTrade`)
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

## ENT-005 — StressTest

- **도메인:** stress_test
- **코드:** `apps/api/src/stress_test/models.py`
- **테이블:** `stress_tests`
- **책임:** Backtest 결과 위에서 Monte Carlo / Walk-Forward / 파라미터 안정성 분석.
- **핵심 필드:** `backtest_id`, `kind`, `params`, `status`, `result`, `error`.
- **상태:** [`state-machines.md`](./state-machines.md) §StressTest

---

## ENT-006 — Optimization

- **도메인:** optimizer
- **코드:** `apps/api/src/optimizer/models.py`
- **테이블:** `optimization_runs`
- **책임:** 파라미터 grid/Bayesian/genetic 탐색 결과.
- **핵심 필드:** `backtest_id`, `kind`, `param_space`, `status`, `result`, `error_message`.
- **상태:** [`state-machines.md`](./state-machines.md) §Optimization

---

## Retired IDs — ENT-007 / ENT-008

`TradingSession`과 `LiveTrade`는 초기 계획에서만 쓰인 이름이다. 실제 테이블·모델은 생성되지 않았으며, ID 재사용 금지 원칙에 따라 결번으로 보존한다. 자동매매 lifecycle은 `LiveSignalSession` + `Order` + `LiveSignalEvent`가 표현한다.

> **Order exit 필드 (Wave 1/2/3 + STEP B, 코드/erd.md SSOT):** `orders` 테이블이 라이브 손익보호 프리미티브 보유 — `reduce_only` / `trigger_price` / `trigger_by` / `take_profit` / `stop_loss` / `trigger_direction` / `oco_group_id` / `trailing_stop`. ★ **불변식: `Order.trailing_stop` = 영속된 트레일링 _의도_ 일 뿐, entry `create_order` 에 절대 주입 안 함** (ccxt 가 trailingStop 을 trading-stop 엔드포인트로 라우팅 → entry 깨짐). 체결 후 `place_trailing_stop` task 가 읽어 `set_trading_stop` 으로 포지션에 부착. 상세 = `docs/dev-log/2026-06-26-trailing-live-placement.md`.

---

## ENT-009 — ExchangeAccount _(구현됨 Sprint 6 — `exchange_accounts`, AES-256 암호화; 코드/erd.md SSOT)_

- **도메인:** trading (구 `exchange` 도메인 통합 — ADR-018, `apps/api/src/exchange/` 부재)
- **코드:** `apps/api/src/trading/models.py` (`class ExchangeAccount`)
- **테이블:** `exchange_accounts`
- **책임:** 사용자별 거래소 API Key 보관 + 권한 메타.
- **핵심 필드:** `user_id`, `exchange`, `mode`, 암호화된 API key/secret/passphrase, `label`, 거래소 UID/권한 메타.
- **불변량:**
  - 평문 키 절대 DB 미저장
  - API 응답에서 `api_key_masked="****abcd"` 형태로만 노출
  - 참조 중인 주문·세션과의 정확한 FK 정책은 `erd.md`와 모델이 정본

---

## ENT-010 — OHLCV _(Sprint 5 M2 ✅ 활성)_

- **도메인:** market_data
- **코드:** `apps/api/src/market_data/models.py`, `repository.py`, `providers/timescale.py`
- **테이블:** `ts.ohlcv` (TimescaleDB hypertable, `ts` schema 격리)
- **책임:** 거래소별 시계열 가격 데이터. Backtest의 OHLCV 캐시 + CCXT fallback fetch.
- **필드 (실제):**
  - `time: TIMESTAMPTZ` (AwareDateTime), `symbol: VARCHAR(32)`, `timeframe: VARCHAR(8)`, `exchange: VARCHAR(32)`
  - `open`, `high`, `low`, `close`, `volume`: 모두 `NUMERIC(18, 8)` (Decimal-first 정책)
  - PK: `(time, symbol, timeframe)` — TimescaleDB가 partition key(`time`) 포함 요구
  - 보조 인덱스: `ix_ohlcv_symbol_tf_time_desc(symbol, timeframe, time)` — 최신 캔들 조회 reverse scan
- **하이퍼테이블 설정:** `create_hypertable('ts.ohlcv', 'time', chunk_time_interval => INTERVAL '7 days')`
- **불변량:**
  - 동일 PK 중복 insert는 `ON CONFLICT DO NOTHING`으로 idempotent (Repository 정책)
  - Alembic migration이 schema/extension까지 책임 (test/fresh DB 단독 동작 보장)
  - 동시 fetch race는 `pg_advisory_xact_lock(hashtext(symbol:tf:start:end))`로 직렬화

---

## ENT-011 — FundingRate

- **도메인:** trading (시장 데이터 수집 계약)
- **코드:** `apps/api/src/trading/models.py` (`class FundingRate`)
- **테이블:** `trading.funding_rates` (일반 테이블)
- **책임:** Perpetual Futures funding rate 시계열.
- **핵심 필드:** `funding_timestamp`, `exchange`, `symbol`, `funding_rate: Decimal`.

---

## 공통 패턴

### ID 정책

- 사용자(`User.id`)는 UUID PK (`uuid4`); 인증 subject 는 별도 `auth_subject` 컬럼(UK, VARCHAR max 64). 내부 PK ↔ 외부 ID 분리 (erd.md §변경사항, Sprint 4 · 이름은 ADR-034 에서 공급자 중립으로).
- 그 외 모든 엔티티도 UUID (`uuid4`). auto-increment 금지.

### Timestamp 정책

- 모든 테이블에 `created_at`, `updated_at` 필수 (`apps/api/AGENTS.md` 규칙)
- Sprint 5 S3-05까지 naive UTC (Z 접미사 수동), 이후 tz-aware

### Decimal 정책

- 금융 수치 컬럼: `DECIMAL(20, 8)`
- 코드에서는 `Decimal` 타입. 합산은 Decimal-first.

### JSONB 직렬화 정책

- Decimal → str (`metrics_to_jsonb`, `equity_curve_to_jsonb` — `apps/api/src/backtest/serializers.py`)
- naive UTC datetime → ISO 8601 Z 수동 포맷

---

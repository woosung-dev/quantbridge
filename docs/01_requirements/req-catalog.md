# QuantBridge — REQ-### 카탈로그

> **목적:** 도메인별 요구사항 ID 카탈로그 + Given/When/Then 시나리오.
> **상위 문서:** [`requirements-overview.md`](./requirements-overview.md)
> **SSOT:** API 계약은 [`03_api/endpoints.md`](../03_api/endpoints.md), 도메인 규칙은 [`02_domain/`](../02_domain/), 비즈니스 규칙은 [`QUANTBRIDGE_PRD.md`](../../QUANTBRIDGE_PRD.md).

## 우선순위

- **P0:** MVP 필수 (Phase 1 차단)
- **P1:** Phase 2~3 차단 (스트레스/데모 트레이딩)
- **P2:** Phase 4+ 또는 Nice-to-have

## 구현 sprint 표기

- ✅ — 완료 (sprint 번호 표기)
- 🔄 — 진행 중
- ⏳ — 예정 (예상 sprint)

---

## REQ-AUTH-* — 인증

| ID | 설명 | 우선순위 | 의존 API | 구현 |
|----|------|----------|----------|------|
| REQ-AUTH-01 | Clerk 세션 기반 사용자 인증 | P0 | Clerk SDK | ✅ Sprint 3 |
| REQ-AUTH-02 | Clerk JWT 백엔드 검증 | P0 | `auth/clerk.py` JWKS | ✅ Sprint 3 |
| REQ-AUTH-03 | Clerk Webhook (user.created/updated/deleted) Svix 서명 검증 | P0 | `POST /webhooks/clerk` | ✅ Sprint 3 |
| REQ-AUTH-04 | 현재 사용자 정보 조회 (`GET /auth/me`) | P0 | `auth/router.py` | ✅ Sprint 3 |
| REQ-AUTH-05 | API Key 기반 외부 호출 (M2M) | P2 | (미구현) | ⏳ Sprint 9+ |

**시나리오 (REQ-AUTH-02):**
- Given: 사용자가 Clerk 로그인 완료, 유효한 JWT 보유
- When: 보호된 API 호출 (`GET /strategies` 등)
- Then: JWT 서명·만료·issuer 검증 통과 → user 컨텍스트 주입, 200 응답
- And: 검증 실패 시 401 + `code="auth.invalid_token"`

---

## REQ-STR-* — 전략 (Strategy)

| ID | 설명 | 우선순위 | 의존 API | 구현 |
|----|------|----------|----------|------|
| REQ-STR-01 | 전략 CRUD (Create/Read/Update/Delete/List) | P0 | `strategies/router.py` 6 endpoints | ✅ Sprint 3 |
| REQ-STR-02 | Pine Script 코드 보관 (raw_source) | P0 | `Strategy.raw_source` | ✅ Sprint 3 |
| REQ-STR-03 | Pine v4/v5 파싱 (Regex 기반 MVP) | P0 | `strategy/parser/` | ✅ Sprint 1 |
| REQ-STR-04 | Pine → Python 인터프리터 (no exec/eval) | P0 | `strategy/interpreter/` | ✅ Sprint 1 |
| REQ-STR-05 | 미지원 함수 즉시 "Unsupported" 응답 | P0 | `POST /strategies/parse` | ✅ Sprint 3 |
| REQ-STR-06 | 백테스트가 참조 중인 전략 삭제 시 409 (FK RESTRICT) | P0 | `DELETE /strategies/:id` | ✅ Sprint 4 |
| REQ-STR-07 | 전략 archive (soft delete) | P1 | `Strategy.is_archived` | ⏳ FE Sprint 5+ UX |
| REQ-STR-08 | Pine 파서 커버리지 ≥80% (상위 50개 전략) | P0 | `tests/strategy/parser/` | 🔄 진행 중 |
| REQ-STR-09 | 전략 템플릿 시드 (RSI / EMA / BB / MACD / SuperTrend) | P1 | `templates/router.py` | ⏳ Sprint 6+ |

**시나리오 (REQ-STR-05):**
- Given: 사용자가 미지원 함수 (`request.security` 등)를 포함한 Pine 코드 제출
- When: `POST /strategies/parse` 호출
- Then: `parse_outcome.status="unsupported"`, `unsupported_calls`에 함수 목록 반환
- And: 부분 실행 결과 반환 금지 (전체 reject)

**시나리오 (REQ-STR-06):**
- Given: Strategy `S1`에 연결된 Backtest `B1` 존재
- When: `DELETE /strategies/S1` 호출
- Then: 409 + `code="strategy.has_backtests"` 응답
- And: DB rollback 후 `S1` 유지

---

## REQ-BT-* — 백테스트 (Backtest)

| ID | 설명 | 우선순위 | 의존 API | 구현 |
|----|------|----------|----------|------|
| REQ-BT-01 | 백테스트 비동기 제출 (Celery) | P0 | `POST /backtests` | ✅ Sprint 4 |
| REQ-BT-02 | vectorbt 기반 엔진 (단일 심볼, OHLCV 입력) | P0 | `backtest/engine/` | ✅ Sprint 2 |
| REQ-BT-03 | 진행 상태 조회 (PENDING→QUEUED→RUNNING→COMPLETED/FAILED) | P0 | `GET /backtests/:id/progress` | ✅ Sprint 4 |
| REQ-BT-04 | 백테스트 취소 (3-guard pattern) | P0 | `POST /backtests/:id/cancel` | ✅ Sprint 4 |
| REQ-BT-05 | trades 목록 조회 (페이지네이션) | P0 | `GET /backtests/:id/trades` | ✅ Sprint 4 |
| REQ-BT-06 | metrics + equity_curve 결과 조회 | P0 | `GET /backtests/:id` | ✅ Sprint 4 |
| REQ-BT-07 | OHLCV 입력: FixtureProvider (합성/스냅샷) | P0 | `OHLCVProvider` Protocol | ✅ Sprint 4 |
| REQ-BT-08 | OHLCV 입력: TimescaleProvider (실 데이터) | P0 | (Sprint 5) | ⏳ Sprint 5 |
| REQ-BT-09 | 백테스트 결과 정확도 ≥99% (vectorbt 직접 실행 대비) | P0 | `tests/backtest/snapshot/` | ✅ Sprint 2 |
| REQ-BT-10 | Decimal-first 금융 연산 (수수료/PnL 합산) | P0 | `extract_trades()` | ✅ Sprint 4 |
| REQ-BT-11 | Stale `running` 자동 reclaim (worker crash) | P0 | startup hook + beat | ✅ startup (Sprint 4), 🔄 beat (Sprint 5) |
| REQ-BT-12 | Idempotency-Key 지원 (`POST /backtests`) | P1 | (미구현) | ⏳ Sprint 6+ |
| REQ-BT-13 | 단일 심볼 1Y/1H 백테스트 < 10초 | P0 | engine 성능 | 🔄 측정 필요 (Sprint 5 실데이터 후) |

**시나리오 (REQ-BT-04):**
- Given: Backtest `B1`이 RUNNING 상태
- When: `POST /backtests/B1/cancel` 호출
- Then: 202 + `cancellation_requested=true` 응답, status=CANCELLING로 전이
- And: 워커가 다음 guard 지점 도달 시 CANCELLED로 종결
- Edge: PENDING/QUEUED 상태에서도 즉시 CANCELLED 처리 가능

**시나리오 (REQ-BT-11):**
- Given: 워커 crash로 B1이 RUNNING 상태로 stale (10분 이상)
- When: 새 워커가 startup hook 또는 beat task로 reclaim
- Then: started_at(또는 created_at) 기준으로 stale 판정 → status=FAILED + reason="stale_reclaimed"

---

## REQ-MD-* — 시장 데이터 (Market Data)

| ID | 설명 | 우선순위 | 의존 API | 구현 |
|----|------|----------|----------|------|
| REQ-MD-01 | OHLCV 시계열 저장 (TimescaleDB hypertable) | P0 | `ohlcv` table | ⏳ Sprint 5 |
| REQ-MD-02 | CCXT를 통한 거래소 OHLCV 수집 (Binance/Bybit) | P0 | `CCXTProvider` | ⏳ Sprint 5 |
| REQ-MD-03 | OHLCV 조회 API | P0 | `GET /market-data/ohlcv` | ⏳ Sprint 5 |
| REQ-MD-04 | OHLCV 동기화 트리거 (비동기) | P0 | `POST /market-data/sync` | ⏳ Sprint 5 |
| REQ-MD-05 | Funding Rate 수집 (Perpetual Futures) | P1 | `funding_rates` table | ⏳ Sprint 6+ |
| REQ-MD-06 | 실시간 가격 스트림 (WebSocket) | P1 | `WS /market-data` | ⏳ Sprint 7+ |

**시나리오 (REQ-MD-02):**
- Given: 사용자가 BTCUSDT 1h 1년 OHLCV 동기화 요청
- When: `POST /market-data/sync` 호출
- Then: Celery task 디스패치, 202 응답
- And: CCXT rate limit 준수 (에러 시 백오프 재시도)
- And: 결과 hypertable에 적재 (`(symbol, timeframe, timestamp)` PK)

---

## REQ-ST-* — 스트레스 테스트 (Stress Test)

| ID | 설명 | 우선순위 | 의존 API | 구현 |
|----|------|----------|----------|------|
| REQ-ST-01 | Monte Carlo 시뮬레이션 (trade permutation) | P1 | `stress_tests/engine/monte_carlo.py` | ⏳ Sprint 6+ |
| REQ-ST-02 | Walk-Forward 분석 (in/out-sample 분할) | P1 | `stress_tests/engine/walk_forward.py` | ⏳ Sprint 6+ |
| REQ-ST-03 | 파라미터 안정성 분석 (sensitivity heatmap) | P1 | (Optimizer 결합) | ⏳ Sprint 6+ |
| REQ-ST-04 | 결과 리포트 (95% CI, 분포 그래프) | P1 | `GET /stress-tests/:id` | ⏳ Sprint 6+ |
| REQ-ST-05 | 비동기 실행 (Celery, Backtest와 dispatcher 공용) | P1 | `TaskDispatcher` 재사용 | ⏳ Sprint 6+ |

---

## REQ-OPT-* — 파라미터 최적화 (Optimizer)

| ID | 설명 | 우선순위 | 구현 |
|----|------|----------|------|
| REQ-OPT-01 | Grid Search | P1 | ⏳ Sprint 6+ |
| REQ-OPT-02 | Bayesian (Optuna) | P1 | ⏳ Sprint 6+ |
| REQ-OPT-03 | Genetic Algorithm | P2 | ⏳ Sprint 7+ |
| REQ-OPT-04 | 최적화 결과 ↔ Stress Test 자동 연동 | P1 | ⏳ Sprint 6+ |
| REQ-OPT-05 | 진행 상태 조회 + 취소 | P1 | ⏳ Sprint 6+ |

---

## REQ-EX-* — 거래소 계정 (Exchange Account)

| ID | 설명 | 우선순위 | 구현 |
|----|------|----------|------|
| REQ-EX-01 | 거래소 API Key 등록 (AES-256 암호화 저장) | P1 | ⏳ Sprint 7+ |
| REQ-EX-02 | API Key 검증 (CCXT `fetch_balance` 핑) | P1 | ⏳ Sprint 7+ |
| REQ-EX-03 | 데모/실거래 키 분리 (`is_testnet` 플래그) | P1 | ⏳ Sprint 7+ |
| REQ-EX-04 | API Key 회전·삭제 | P1 | ⏳ Sprint 7+ |
| REQ-EX-05 | 거래소별 권한 검증 (read-only / trade) | P2 | ⏳ Sprint 8+ |

**시나리오 (REQ-EX-01):**
- Given: 사용자가 Bybit testnet API Key 입력
- When: `POST /exchange-accounts` 호출
- Then: 평문 키 절대 DB 미저장 → AES-256으로 암호화 후 저장
- And: 응답에서 `api_key_masked="****abcd"` 형태로만 노출

---

## REQ-TRD-* — 트레이딩 (Trading Session)

| ID | 설명 | 우선순위 | 구현 |
|----|------|----------|------|
| REQ-TRD-01 | 데모 트레이딩 세션 시작 (Bybit testnet) | P1 | ⏳ Sprint 7+ |
| REQ-TRD-02 | 라이브 트레이딩 세션 시작 (확인 step + 클릭 ≤2) | P1 | ⏳ Sprint 8+ |
| REQ-TRD-03 | Risk Manager: 일일 최대 손실 한도 | P0 | ⏳ Sprint 7+ |
| REQ-TRD-04 | Kill Switch (즉시 모든 포지션 청산) | P0 | ⏳ Sprint 7+ |
| REQ-TRD-05 | 포지션 사이즈 가드 (ATR 기반) | P1 | ⏳ Sprint 7+ |
| REQ-TRD-06 | 데모 결과 vs 백테스트 괴리 분석 | P1 | ⏳ Sprint 7+ |
| REQ-TRD-07 | 라이브 거래 내역 기록 (`live_trades`) | P0 | ⏳ Sprint 7+ |
| REQ-TRD-08 | 데모 주문 체결 레이턴시 < 2초 | P1 | ⏳ Sprint 7+ 측정 |
| REQ-TRD-09 | 멀티 거래소 동시 운용 (Phase 4) | P2 | ⏳ Sprint 9+ |

---

## REQ-INFRA-* — 인프라/운영

| ID | 설명 | 우선순위 | 구현 |
|----|------|----------|------|
| REQ-INFRA-01 | Docker Compose dev 환경 (DB + Redis) | P0 | ✅ Phase 0 |
| REQ-INFRA-02 | Celery worker compose 통합 | P1 | ⏳ Sprint 5 |
| REQ-INFRA-03 | Beat scheduler (stale reclaim, market_data sync) | P1 | ⏳ Sprint 5 |
| REQ-INFRA-04 | Alembic migration round-trip CI gate | P0 | ✅ Sprint 3 |
| REQ-INFRA-05 | Pre-commit hooks (ruff/eslint/prettier) | P0 | ✅ Phase 0 |
| REQ-INFRA-06 | CI: changes-aware (frontend/backend 분리) | P0 | ✅ Phase 0 |
| REQ-INFRA-07 | 프로덕션 배포 (TBD) | P1 | ⏳ Sprint 8+ (`07_infra/deployment-plan.md`) |
| REQ-INFRA-08 | 관측성 (logs/metrics/traces) | P1 | ⏳ Sprint 7+ (`07_infra/observability-plan.md`) |

---

## REQ-NF-* — 비기능 요구사항

| ID | 카테고리 | 설명 | 우선순위 |
|----|----------|------|----------|
| REQ-NF-01 | 보안 | 환경 변수/시크릿 코드 하드코딩 금지 | P0 |
| REQ-NF-02 | 보안 | 거래소 API Key AES-256 암호화 | P0 |
| REQ-NF-03 | 보안 | Pine 실행 `exec()`/`eval()` 금지 | P0 |
| REQ-NF-04 | 정확성 | 금융 숫자 `Decimal` 사용 (`float` 금지) | P0 |
| REQ-NF-05 | 성능 | 백테스트 단일 1Y/1H < 10초 | P0 |
| REQ-NF-06 | 성능 | API 핸들러는 백테스트/최적화 직접 실행 금지 (Celery 비동기) | P0 |
| REQ-NF-07 | 가용성 | Worker crash 시 stale running 자동 reclaim | P0 |
| REQ-NF-08 | 정합성 | Strategy → Backtest FK RESTRICT (cascade 금지) | P0 |
| REQ-NF-09 | UX | 실시간 데이터 WebSocket + Zustand (React Query 분리) | P1 |
| REQ-NF-10 | 운영 | Alembic 모든 변경 round-trip 검증 | P0 |
| REQ-NF-11 | 운영 | Migration rollback `alembic downgrade -1` 동작 보장 | P0 |
| REQ-NF-12 | 가용성 | Idempotency-Key 멱등성 (Sprint 6+) | P1 |

---

## 매핑 — REQ ↔ API ↔ Sprint

| REQ 그룹 | API 섹션 (`endpoints.md`) | Backend 모듈 | Sprint |
|----------|----------------------------|--------------|--------|
| AUTH | §인증 | `src/auth/` | 3 |
| STR | §전략 | `src/strategy/` | 1, 3 |
| BT | §백테스트 | `src/backtest/` | 2, 4 |
| MD | §시장 데이터 | `src/market_data/` | 5 (예정) |
| ST | §스트레스 테스트 | `src/stress_test/` | 6+ |
| OPT | §최적화 | `src/optimizer/` | 6+ |
| TRD | §트레이딩 | `src/trading/` | 7+ |
| EX | §거래소 계정 | `src/exchange/` | 7+ |

---

## 변경 이력

- **2026-04-16** — 초안 작성 (Sprint 5 Stage A, PRD/endpoints.md 교차 참조)

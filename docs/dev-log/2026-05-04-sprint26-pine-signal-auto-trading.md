# Sprint 26 — Pine Signal Auto-Trading (Live Session daily flow)

> **목표**: TradingView Webhook 의존을 제거하고, Pine 전략을 사용자가 등록한 Bybit Demo
> 계정에서 1m/5m/15m/1h Beat 주기로 자동 평가 → outbox dispatcher → OrderService.execute
> 까지 daily flow 구축. dogfood-first indie SaaS 가치 (자기가 돈 내고 쓰고 싶은 것) 의
> 본격 시작.

---

## 활성 브랜치

`stage/h2-sprint26-signal` (cascade base: `9978d33`)

## 산출물 (3 commits 누적)

### Phase A — DB schema + register API (commit `d33a0b4`, 2026-05-04)

- `Strategy.settings` JSONB + StrategySettings (extra=forbid) + PUT /strategies/{id}/settings
- LiveSignalSession (partial unique is_active=true) / LiveSignalState (1:1 CASCADE) /
  LiveSignalEvent (UNIQUE 5-tuple — codex G.0 P2 #5 sequence_no idempotency) + 2 enum
- Alembic 20260504_0001_add_live_signal — upgrade + downgrade -1 + re-upgrade idempotent
- LiveSignalSessionRepository (try_claim_bar rowcount + list_active_due CASE) +
  LiveSignalEventRepository (insert_pending_events ON CONFLICT DO NOTHING)
- LiveSignalSessionService (Bybit Demo 강제 + 5건 quota + StrategySettings validate) +
  5 신규 exceptions
- 5 endpoints: POST/GET/DELETE /live-sessions + /state + /events
- LESSON-019 commit-spy 10 PASS + Backend 기존 회귀 0건

### Phase B — eval + dispatch task + tests (Task #9~#11, 본 sprint cascade)

- **B.3 (Task #9)** — `CCXTProvider.fetch_ohlcv` `limit_bars` 옵션 (codex P1 #6 fix):
  `since=now-(limit_bars+2)*tf`, mock-exchange clock-skew + 진행 중 bar 1개 buffer +
  기존 closed-bar filter 재사용. 호출자 default `None` → 무영향.
  6 tests PASS.
- **B.4-B.7 (Task #10)** — `tasks/live_signal.py` 신규 (~520 LOC):
  - `evaluate_live_signals_task` (Beat 60s, expires=50) → `_async_evaluate_all` →
    `list_active_due` → 각 session 별 `_async_evaluate_session`.
  - **P1 #4 fix** — RedisLock `ttl_ms=60_000` + `_heartbeat_extend` (20s 마다 token CAS PEXPIRE).
  - **P1 #6 fix** — `CCXTProvider.fetch_ohlcv(limit_bars=300)` closed-bar.
  - **P2 #3** — `try_claim_bar` winner-only (rowcount==1) + claim_lost 시 session.rollback.
  - **P1 #3 fix** — transactional outbox: events INSERT + state upsert + claim UPDATE +
    LESSON-019 commit 단일 트랜잭션. 신규 INSERT 된 event 만 dispatch task `apply_async` enqueue.
  - `dispatch_live_signal_event_task` (max_retries=3, delay=15s) — sessions_port=
    `_StrategySessionsAdapter` 의무 주입 (**P1 #5 fix** — bypass 차단). idempotency_key
    = `live:{session_id}:{bar_time}:{sequence_no}:{action}:{trade_id}` (**P2 #5**).
  - KillSwitchActive / NotionalExceeded / LeverageCapExceeded / TradingSessionClosed →
    `mark_failed` + commit + raise (deterministic reject — entry retry skip). 일시 장애 →
    `self.retry(exc=exc)` (max 3).
- **B.8 (Task #11)** — Phase B tests (~22 cases):
  - `test_live_signal_eval_task.py` — beat schedule + task name + RedisLock contention +
    session_inactive + invalid_settings + non_demo + no_new_bar + claim_lost + 정상 success
    (LESSON-019 commit-spy + dispatch enqueue) + 빈 due list.
  - `test_live_signal_dispatch_task.py` — missing event + already terminal + session_inactive
    - 정상 dispatch (sessions_port DI 검증 + idempotency_key sequence_no 검증) +
      KillSwitchActive → mark_failed + raise (LESSON-019 commit-spy) + helper unit.
  - **모든 inner 함수 직접 await** — `run_in_worker_loop` 우회 (pytest-asyncio loop
    이미 실행 중). `create_worker_engine_and_sm` monkeypatch 로 in-memory mock 주입.
- 신규 5 metrics:
  - `qb_live_signal_evaluated_total` Counter labels=[interval, outcome]
  - `qb_live_signal_dispatch_total` Counter labels=[action, outcome]
  - `qb_live_signal_skipped_total` Counter labels=[reason]
  - `qb_live_signal_eval_duration_seconds` Histogram labels=[interval]
  - `qb_live_signal_outbox_pending_gauge` Gauge

### Phase C — Frontend Live Sessions (Task #12+#13)

- `frontend/src/features/live-sessions/` 신규 모듈 (10 파일, ~640 LOC):
  - `schemas.ts` (Zod v4) / `types.ts` / `query-keys.ts` (userId-first identity) /
    `api.ts` / `utils.ts` (pure helpers `computeLiveSessionStateRefetchInterval` +
    `buildPnlSeries`) / `hooks.ts` (LESSON-004 H-2 module-level queryFn factories) /
    `components/{form,list,detail}.tsx` / `index.ts` (barrel) /
    `__tests__/utils.test.ts` (Vitest 6/6 PASS).
  - LESSON-004 H-1 의무 — useEffect dep array primitive only / react-hooks/\* disable
    0건 / @tanstack/query/exhaustive-deps disable 0건.
  - `MAX_LIVE_SESSIONS_PER_USER=5` / refetch active 5s / idle 30s.
- `frontend/src/app/(dashboard)/trading/_components/trading-tabs.tsx` 신규 — Client
  Component, `useSearchParams("tab")` + `router.replace()` URL sync (Sprint 13
  TabWebhook 패턴). `<TabsList>`: Orders / Live Sessions.
- `frontend/src/app/(dashboard)/trading/page.tsx` — `<TradingTabs />` + Suspense wrapper.
- `frontend/playwright.config.ts:47` — `chromium-authed.testMatch` 에 `live-session-flow`
  추가. `e2e/fixtures/api-mock.ts` — `API_ROUTES.liveSessions` 추가.
- `e2e/live-session-flow.spec.ts` 신규 — 3 시나리오 (serial mode):
  1. 빈 상태 (`live-session-empty` testId 노출 + Bybit Demo notice)
  2. submit enabled (Bybit Demo + 0건 active)
  3. submit disabled (5건 quota 도달)

### dogfood UX

- amber notice "Bybit Demo 한정 — 가상 자금만 사용. 실제 자금 손실 없음." (BL-003 mainnet
  runbook 완료 전까지)
- 5건 quota 도달 → submit disabled + tooltip 안내
- form-level 422 inline error (StrategySettingsRequired / InvalidStrategySettings /
  AccountModeNotAllowed / LiveSessionQuotaExceeded)
- Stop confirm dialog: "이 session 의 자동 trading 이 중단됩니다. 미체결 주문은 유지됩니다."

---

## 검증 결과

| 항목                              | 결과                                                                                                |
| --------------------------------- | --------------------------------------------------------------------------------------------------- |
| Backend ruff                      | All checks passed                                                                                   |
| Backend mypy                      | Success: no issues found                                                                            |
| Backend new tests                 | 22 PASS (eval 11 + dispatch 11) + 6 PASS (limit_bars)                                               |
| Backend 회귀 (test_ccxt_provider) | 5/5 PASS (test_timescale_provider 4 ERROR 는 main HEAD 도 동일 — DB conn 환경 문제, 본 sprint 무관) |
| Frontend tsc --noEmit             | 0 errors                                                                                            |
| Frontend pnpm lint                | 0 errors                                                                                            |
| Frontend Vitest                   | 257/257 PASS (이전 251 + 6 신규 utils.test.ts)                                                      |
| Frontend E2E                      | 3 시나리오 작성 (라이브 검증은 사용자 dogfood 단계)                                                 |
| codex G.0 surgery                 | Phase A 완료, Phase B 의 P1 #3/#4/#5/#6 모두 본 sprint 코드 반영                                    |
| codex G.2 challenge               | 11 vector 검증, P1 1건 즉시 fix → P1 0건 도달 (Phase D pre-flight 통과)                             |

---

## codex G.0 P1 / P2 surgery 적용 현황

| Vector                                | 상태             | 적용 위치                                                          |
| ------------------------------------- | ---------------- | ------------------------------------------------------------------ |
| P1 #1 hydrate 부족                    | ✅ Phase A       | Option B (warmup replay) — `run_live = run_historical wrapper`     |
| P1 #2 same-bar entry+close            | ✅ Phase A       | TradeEvent log + sequence_no idempotency                           |
| P1 #3 orphan order                    | ✅ Phase B.4     | transactional outbox (LiveSignalEvent table 분리 + commit 단일 tx) |
| P1 #4 RedisLock 5s 부족               | ✅ Phase B.4     | `ttl_ms=60_000` + `_heartbeat_extend` 20s 주기                     |
| P1 #5 sessions_port DI 누락           | ✅ Phase B.4     | `_StrategySessionsAdapter(session)` 의무 주입 + dispatch test 검증 |
| P1 #6 CCXT closed-bar                 | ✅ Phase B.3     | `since=now-(limit_bars+2)*tf` + 기존 closed-bar filter 재사용      |
| P2 #1 ExchangeName.bybit              | ✅ Phase A       | enum 'bybit' (not 'bybit_futures' string)                          |
| P2 #2 partial unique is_active=true   | ✅ Phase A       | Alembic index `uq_live_sessions_active_unique`                     |
| P2 #3 try_claim_bar rowcount          | ✅ Phase A + B.4 | rowcount==1 winner + claim_lost 시 rollback                        |
| P2 #4 StrategySettings.model_validate | ✅ Phase A + B.4 | read path 가 ValidationError catch → InvalidStrategySettings 422   |
| P2 #5 sequence_no idempotency         | ✅ Phase A + B.4 | UNIQUE 5-tuple + idempotency_key 형식 검증 unit test               |

---

## codex G.2 결과 + P1 fix

**Verdict (high reasoning, 11 vector, 1 iter)**:

- **P1 (production blocker, 1건)** — vector 10: dispatch task max_retries 소진 후 event 영구 stuck.
  - **즉시 fix 적용**:
    1. `dispatch_live_signal_event_task` 가 `self.request.retries >= max_retries` 시
       `_async_mark_event_failed(event_id, error="max_retries_exhausted")` 호출 +
       `qb_live_signal_dispatch_total{outcome=max_retries_exhausted}` inc.
    2. 신규 Beat task `live_signal.dispatch_pending` (5분 fire) — `list_pending(limit=50)`
       을 주기적 re-enqueue 하여 broker 일시 장애로 유실된 event 회수. 중복 fire 는
       dispatch task 의 `if event.status != pending: skipped` 가드 로 차단.
    3. 신규 2 cases test (eval_task.py) — task 등록 + Beat schedule entry 검증.
- **P2 (harden 필요, 2건)** — Sprint 27+ BL 후보 등록:
  - vector 8: partial unique index `is_active=true` 의 deactivate 후 재INSERT real-DB
    integration test (BL-119 후보).
  - vector 3: `INSERT ... ON CONFLICT DO NOTHING RETURNING *` 로 신규 INSERT 만 atomic
    반환 — 현재 list_by_session pre/post diff 는 정상 race 에서는 try_claim_bar 로
    막지만 수동 DB mutation 시 중복 dispatch enqueue 여지 남음 (BL-120 후보).
- **P3 (pass, 8건)** — vector 1/2/4/5/6/7/9/11 모두 현재 코드로 충분히 방어. nice-to-have
  로 real-DB concurrent test / heartbeat extend false 시 누수 없음 test 등 (BL-121 후보).

P1 0건 도달 → Phase D 진입 가능.

---

## 다음 단계 (Phase D)

1. ~~codex G.2 challenge~~ ✅ 완료 (P1 0건).
2. **사용자 직접 라이브 검증** (Phase D — 사용자 작업):
   - `make up-isolated-build` → API 기동
   - PUT `/api/v1/strategies/{id}/settings` (leverage=2, margin_mode=cross, position_size_pct=10)
   - POST `/api/v1/live-sessions` (Bybit Demo + 1m interval)
   - 60-90s 후 Prometheus query: `qb_live_signal_evaluated_total >= 1`
   - Bybit Demo 대시보드 캡처 — order reflects (사용자 evidence)
   - DevTools Performance 1분 — CPU < 30% (LESSON-004)
3. **PR 생성** (사용자 명시 승인 후): `git push origin stage/h2-sprint26-signal` →
   `gh pr create --title "H2 Sprint 26 — Pine Signal Auto-Trading (Live Session daily flow)"`.
4. **dogfood Day 3-7 재정의** — 기존 webhook 기반 → Live Session 기반.

---

## LESSON 후보

- **LESSON-026 (잠정)** — Python `import a.b.c as d` 가 `__init__.py` 의 `from a.b.c
import x` re-export 와 충돌 시 변수로 평가됨 (Celery 인스턴스가 module 자리 차지).
  Test 에서 `sys.modules["a.b.c"]` 로 우회. (test_live_signal_eval_task.py 발견)
- **LESSON-027 (잠정)** — Sprint 18 `_WORKER_LOOP` 패턴은 task 내부 로직 mock 시
  `run_in_worker_loop` 호출하지 않고 `_async_xxx` 직접 await — pytest-asyncio loop
  와 호환. 본 sprint 의 22 cases 모두 이 방식.

---

## 미해결 BL (사용자 라이브 검증 후 정식 등록)

- **BL-116 (예약)** — Bybit Demo dogfood Day 3-7 자동 평가 시나리오 7 (Live Session
  기반) 추가. `backend/tests/integration/test_auto_dogfood.py` 확장.
- **BL-117 (예약)** — `qb_pending_alerts > 50` 시 Slack/Grafana alert wire-up
  (Sprint 19 BL-081 운영 임계값 명시화).
- **BL-118 (예약)** — Live Session E2E 6 시나리오 확장 (현재 3건). PnL chart datapoint
  - Stop confirm dialog interaction + create form submit 성공 path.
- **BL-119 (예약, codex G.2 P2 vector 8)** — partial unique index `is_active=true` 의
  deactivate 후 재INSERT real-DB integration test. migration drift / DB predicate 차이
  방어.
- **BL-120 (예약, codex G.2 P2 vector 3)** — `INSERT ... ON CONFLICT DO NOTHING
RETURNING *` 로 신규 INSERT 만 atomic 반환. 현재 list_by_session pre/post diff 의
  race window 차단.
- **BL-121 (예약, codex G.2 P3 nice-to-have)** — real-DB concurrent test /
  heartbeat extend false 시 task 종료 + 누수 없음 test / direct DB mutation
  integration test 등.

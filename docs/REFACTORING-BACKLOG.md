# QuantBridge — Refactoring Backlog

> **deferred 작업 백로그.** active sprint 작업은 [`TODO.md`](./TODO.md), 정합성 검증은 [`04_architecture/architecture-conformance.md`](./04_architecture/architecture-conformance.md).
>
> 본 문서는 **"특정 시점 또는 조건 도래 시 trigger 되는 작업"** 의 SSOT. CLAUDE.md "현재 작업" 섹션 / dev-log 회고 / TODO.md 의 "Sprint N 이관" 자연어 표현은 모두 본 문서의 BL-XXX ID 로 cross-link.
>
> **신규 sprint 진입 시 본 문서 review 의무** — 각 BL 의 trigger 가 도래했는지 확인 후 active TODO 로 승격할지 결정.

**작성일:** 2026-04-30
**최종 갱신:** 2026-05-04 (Sprint 29 종료 — dual metric ALL PASS + codex G2 P0 fix)

**Sprint 29 종료 BL 변경:**

- ✅ **BL-096 partial Resolved** — heikinashi (a) ADR + security graceful + timeframe.period degraded gate (commit `5a72283`)
- 신규 0건 (P0=0, P1=0)
- BL-003 / BL-005 P0 deferred 유지 (trigger 미도래)
- BL-022 / BL-037 / BL-142 deferred 유지 (Sprint 30+)
- codex G2 P1 4건 (occurrence-based unsupported_calls / 422 응답 schema / workaround 정확도 / e2e 실제 vectorbt) → Sprint 30+ Beta sprint 또는 hotfix 묶음

**총 항목:** 50 BL — P0 5 (BL-001~005) / P1 17 (BL-010~026) / P2 14 (BL-030~043) / P3 8 (BL-050~057) / Beta 오픈 milestone 6 (BL-070~075) + Sprint 28+ 신규 BL (BL-141/140b/004 ✅ Resolved, BL-142~146 deferred / partial)

**Sprint 29 BL 매핑** (plan v2 §2, [`~/.claude/plans/quantbridge-sprint-29-sunny-origami.md`](../../.claude/plans/quantbridge-sprint-29-sunny-origami.md)):

- **진입 시점 P0 잔여 = 2건**: BL-003 (Bybit mainnet runbook, deferred — Pine pain 우선) + BL-005 (실자본 1-2주 dogfood, deferred — Pine 통과율 5/6 우선). BL-001/002 ✅ Sprint 15 Resolved + BL-004 ✅ Sprint 28 Resolved.
- **Pine 관련 BL Sprint 29 처리:**
  - **BL-022** golden expectations 재생성 → Sprint 30+ deferred (본 sprint scope 외)
  - **BL-037** Coverage Analyzer regex → AST visitor → 본 sprint deferred (Slice B 자연 연계, regex 정밀화 X)
  - **BL-096 partial** UtBot×2 잔존 (heikinashi/security) → **Slice A 안 ADR 결정 의무**. Trust Layer 정합 문제라 단순 supported 추가 incorrect
  - **BL-142** ts.ohlcv daily refresh → Sprint 30+ deferred 유지
  - **BL-146** 메타-방법론 4종 영구 규칙 승격 → Sprint 29 second validation (LESSON-037 baseline 재측정 preflight first validation 도 본 sprint 안)
- **Beta BL deferred 명시 (2026-05-05 office-hours session 정정):** BL-070~075 (도메인+DNS / Backend prod / Resend / 캠페인 / 인터뷰 / H2 게이트) **전부 Sprint 36+ deferred (BL-005 본격 1-2주 mainnet 통과 후 별도 trigger)**. office-hours session 의 P3 fictitious gate detection = "Day 7 ≥7 → Beta 본격" 은 BL-005 자체 skip 하는 fake gate. 정정 후 trigger = "Sprint 35 Day 7 4중 AND gate 통과 → Sprint 36 BL-003 mainnet runbook + BL-005 본격 → 통과 → Beta 본격 (BL-070~075)".

---

## 분류 차원

### Priority

| 라벨   | 의미                                               | 예시                                                      |
| ------ | -------------------------------------------------- | --------------------------------------------------------- |
| **P0** | dogfood-blocker / H1 종료 gate                     | submitted watchdog, mainnet runbook, 본인 1~2주 dogfood   |
| **P1** | risk-mitigation / 알려진 broken bug 패턴 재발 위험 | commit-spy 도메인 확장, Redis lease, Auth circuit breaker |
| **P2** | hardening / nice-to-have 가 아닌 "건강도" 작업     | cardinality allowlist, dogfood 통합 dashboard             |
| **P3** | nice-to-have / 컨벤션 정합 / 미래 path             | zod import 정정, Path γ/δ                                 |

### Trigger 유형

- **time-based** — Sprint N+ / Q2 / H2 말 등 시점 명시
- **event-based** — "after dogfood week 1", "Beta 5명 onboarding 후" 등 외부 사건
- **dependency-based** — 다른 BL 또는 외부 자원 (예: Bybit mainnet API key) 후
- **on-demand** — 특정 PR / sprint 안에서 발견 시 즉시

### Category

| #   | 카테고리                           | 항목 수              |
| --- | ---------------------------------- | -------------------- |
| 1   | 트랜잭션 / Order / 도메인          | 4                    |
| 2   | WebSocket / Celery / 비동기        | 7                    |
| 3   | 보안 / 시크릿 / 인증               | 4                    |
| 4   | Trust Layer / Mutation / Pine      | 5                    |
| 5   | Frontend UX / 안정성               | 8                    |
| 6   | Observability / Alert              | 4                    |
| 7   | Test infra / Golden / Fixture      | 4                    |
| 8   | Tooling / CI / Infra               | 4                    |
| 9   | Docs / 정합성                      | 4                    |
| 10  | Beta 오픈 / 인프라 (sub-task 묶음) | (3 BL + 18 sub-task) |

---

## P0 — Dogfood / H1 종료 blocker

| ID                | 제목                                                 | Trigger                      | Est                    | 출처             |
| ----------------- | ---------------------------------------------------- | ---------------------------- | ---------------------- | ---------------- |
| [BL-001](#bl-001) | submitted 영구 고착 watchdog                         | Sprint 15 진입 즉시          | M (3-4h)               | dogfood-day3 §5  |
| [BL-002](#bl-002) | Day 2 stuck pending order 분석 + 정리                | Sprint 15 진입 (BL-001 직후) | S (2h)                 | dogfood-day3 §3  |
| [BL-003](#bl-003) | Bybit mainnet 진입 runbook + smoke 스크립트          | H1 Stealth 종료 직전         | M (4-5h)               | TODO.md L646~651 |
| [BL-004](#bl-004) | KillSwitch `capital_base` 동적 바인딩 + leverage cap | H1 Stealth Step 3            | M (4-5h)               | TODO.md L658     |
| [BL-005](#bl-005) | 본인 실자본 1~2주 dogfood 운영                       | H1 종료 확정 조건            | L (≥ 14d, 사용자 수동) | TODO.md L652     |

### BL-001

**Status:** ✅ Resolved (2026-05-01, Sprint 15 stage/h2-sprint15)
**Title:** submitted 영구 고착 watchdog (silent data corruption 위험)
**Category:** 트랜잭션 / Order
**Priority:** P0 — silent data corruption 위험 (PnL / Kill Switch / dogfood report 가 거래소 현실과 다름)
**Trigger:** Sprint 15 진입 즉시
**Est:** M (3-4h)
**출처:** [`docs/dev-log/2026-04-27-dogfood-day3.md`](dev-log/2026-04-27-dogfood-day3.md) §5 (codex G.2 P1 #1, session `019dca46-ff2b-7a63-bce5-b45f8ed45442`)
**해결:** [`docs/dev-log/2026-05-01-sprint15-watchdog.md`](dev-log/2026-05-01-sprint15-watchdog.md) — Phase A.1 provider.fetch_order interface + Phase A.2 fetch_order_status_task Celery (retry 3회 backoff 15s→30s→60s + Redis throttle 1h alert) + Phase A.3 scan_stuck_orders beat 5min. codex G.0 P1 #1+#2+#3 + G.2 P1 #1+#2 모두 반영.

**원인 / 영향:** Sprint 14 Phase C fix 후 `receipt.status="submitted"` 분기는 `attach_exchange_order_id` 만 호출. terminal 전이는 WS event / reconciler 책임. 그러나 `tasks/websocket_task.py:208-250 reconcile_ws_streams` 는 stream 재시작만 하고 orphan submitted Order 전이 안 함. WS event 유실 / OKX (private WS 미보유) / Bybit 응답 손상 시 DB 영원히 submitted 고착.

**권장 접근:**

1. `provider.fetch_order(creds, exchange_order_id)` interface (Bybit / OKX / Fixture) — CCXT `fetch_order(id, symbol)`
2. `fetch_order_status_task` Celery — terminal 이면 transition. 미체결이면 backoff (15s → 30s → 60s) retry
3. `_async_execute` submitted 분기에서 `fetch_order_status_task.apply_async(countdown=15)` enqueue
4. `tasks/orphan_submitted_scanner` 별도 Celery beat (5분, 30분 이상 submitted → Slack alert + Sentry warn)

**의존성:** ADR-018 WS supervisor (완료) · BL-002 (Day 2 stuck pending 분석은 별도 root cause 가능성)

---

### BL-002

**Status:** ✅ Resolved (2026-05-01, Sprint 15 stage/h2-sprint15)
**Title:** Day 2 stuck pending order 분석 + cleanup
**Category:** 트랜잭션 / Order
**Priority:** P0
**Trigger:** Sprint 15 진입 (BL-001 직후 또는 병렬)
**Est:** S (2h)
**출처:** [`docs/dev-log/2026-04-27-dogfood-day3.md`](dev-log/2026-04-27-dogfood-day3.md) §3
**해결:** Sprint 15 Phase A.3 의 `scan_stuck_orders_task` 가 `list_stuck_pending` 으로 30분 이상 pending 자동 감지 + `execute_order_task.apply_async` 재dispatch + per-order throttled alert. Day 2 stuck order `13705a91` 는 dogfood Day 4 라이브 검증 시 자동 reconcile 예정. root cause 추정: Day 2 hotfix 직후 worker container 코드 outdated 또는 broker 메시지 만료. 본 watchdog 가 동일 패턴 재발 시 자동 복구.

**원인 / 영향:** Day 2 stuck pending order (`13705a91-...`) 가 Day 2 §2.4 hotfix (OrderService outer commit) 후 INSERT + COMMIT 됐으나 14h+ state=pending 그대로. dispatch 또는 worker 처리 누락. **즉 OrderService outer commit fix 외 별도 broken bug 잔존 가능성**.

**권장 접근:**

1. `service.execute()` → `dispatcher.dispatch_order_execution()` → Celery enqueue → `_async_execute` 4단계 trace 로그 분석
2. Celery prefetch / acks_late 설정 + DB row pickup 시점 검증
3. fix 또는 BL-001 watchdog 으로 자동 reconcile 가능한지 결정

**의존성:** BL-001 의 `provider.fetch_order` 가 cleanup 도구로 활용 가능

---

### BL-003

**Title:** Bybit mainnet 진입 runbook + smoke 스크립트
**Category:** Tooling / Infra
**Priority:** P0 (H1 Stealth 종료 직전)
**Trigger:** Bybit Demo 1주 안정 운영 후 + BL-004 완료 후
**Est:** M (4-5h)
**출처:** [`docs/TODO.md`](TODO.md) L646~651

**원인 / 영향:** dogfood 가 Bybit Demo 만으로는 H1 종료 gate 충족 안 됨. mainnet 전환 시 수동 step 누락 위험 (IP whitelist / 출금 권한 차단 / 레버리지 1:1 / 소액 시작).

**권장 접근:**

1. `docs/07_infra/bybit-mainnet-checklist.md` 신규 — IP whitelist · 출금 권한 OFF 확인 · 레버리지 1:1 · 소액 ($10-50) 시작 · Kill Switch 임계값 lower bound
2. `scripts/bybit-smoke.sh` 신규 — mainnet credentials 로 read-only API 호출 (잔고 조회 + 1 USDT limit-order 후 즉시 cancel) dry-run
3. `.env.production` 별도 secret manager + rotation 절차

**의존성:** BL-004 (capital_base 동적 바인딩)

---

### BL-004 ✅ Resolved (Sprint 28 Slice 4 PR #108, 2026-05-04)

**Title:** KillSwitch `capital_base` 동적 바인딩 + leverage cap 검증
**Category:** 트랜잭션 / Risk
**Priority:** P0 (H1 Stealth Step 3)
**Trigger:** ~~mainnet 진입 직전~~ → **Sprint 28 Slice 4 으로 사전 처리**
**Est:** M (4-5h) → **실제 4.5h (Slice 4 estimate 정합)**
**출처:** [`docs/TODO.md`](TODO.md) L658

**원인 / 영향 (Sprint 8 시점):** `capital_base` 정적 설정. 잔고 변동 시 KS 임계값이 실제 위험 노출과 어긋남. mainnet 진입 시 silent over-exposure 위험.

**해결 (Sprint 28 Slice 4 PR #108):**

1. ✅ Sprint 8+ 의 hybrid 구현 검증 — `CumulativeLossEvaluator(balance_provider)` 가 trigger 시 매번 fetch_balance 호출 (ADR-006 Resolved 2026-05-04)
2. ✅ `kill_switch.py:107-121` — provider 예외 → swallow + log + config fallback (resilience)
3. ✅ 9 unit tests PASS — 기존 7 + 신규 2 (provider exception + cache 0 검증)
4. ✅ Bybit Demo integration test infra (`tests/real_broker/test_kill_switch_capital_base.py`, --run-real-broker opt-in)
5. ⏸️ EffectiveLeverageEvaluator (Cross Margin position aggregation) → BL-145 deferred

**관련 ADR:** `docs/dev-log/006-sprint6-design-review-summary.md` "Resolved 2026-05-04 (Sprint 28 Slice 4)" 섹션 (capital_base fetch timing = Option A 결의)

---

### BL-005

**Title:** 본인 실자본 1~2주 dogfood 운영
**Category:** Tooling / dogfood
**Priority:** P0 (H1 종료 확정 조건)
**Trigger:** BL-001~004 모두 완료 + self-assessment ≥ 7/10
**Est:** L (≥ 14 days, 사용자 수동)
**출처:** [`docs/TODO.md`](TODO.md) L652

**원인 / 영향:** 사용자 self-assessment 6/10 → 7/10 gate 통과 필요. 자동 검증으로는 측정 불가능한 운영 신호 (매일 5분 모니터링 / KS 트리거 횟수 / WS reconnect 추이).

**권장 접근:** dev-log/2026-\* 일일 기록 + 통계는 [`docs/07_infra/sprint12-dogfood-checklist.md`](07_infra/sprint12-dogfood-checklist.md) G5 10 항목 매일 점검.

---

## P1 — Risk mitigation / 알려진 broken bug 패턴 재발 방어

| ID                                                    | 제목                                                                                               | Trigger                                     | Est       | 출처                                     |
| ----------------------------------------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------------- | --------- | ---------------------------------------- |
| [BL-010](#bl-010)                                     | commit-spy 도메인 확장 (LESSON-019 backfill)                                                       | 다음 mutation PR 직전                       | S (2-3h)  | architecture-conformance §A2             |
| [BL-011](#bl-011)                                     | Redis lease + heartbeat ✅ Resolved (Sprint 24a)                                                   | -                                           | M (5-6h)  | TODO.md L706                             |
| [BL-012](#bl-012)                                     | prefork 복귀 ✅ Resolved (Sprint 24a)                                                              | -                                           | M (4h)    | TODO.md L707                             |
| [BL-013](#bl-013)                                     | Auth circuit breaker (failures/blocked TTL 분리) ✅ Resolved (Sprint 24a)                          | -                                           | S (2-3h)  | TODO.md L708                             |
| [BL-014](#bl-014)                                     | Partial fill `cumExecQty` tracking                                                                 | partial fill 1건 발견 시                    | M (4-5h)  | TODO.md L709                             |
| [BL-015](#bl-015)                                     | OKX Private WS                                                                                     | Bybit Demo 안정화 후                        | M (6-8h)  | TODO.md L710                             |
| [BL-016](#bl-016)                                     | `__aenter__` first_connect race 강화 (task layer 카운트 + BL-013 trigger) ✅ Resolved (Sprint 24a) | -                                           | S (2h)    | TODO.md L711                             |
| [BL-017](#bl-017)                                     | WebCrypto error 처리 (HTTP local 환경)                                                             | dogfood HTTP 환경 발견 시                   | S (1-2h)  | TODO.md L42 (Sprint 14 이관)             |
| [BL-018](#bl-018)                                     | Strategies/Accounts query loading/error UX                                                         | dogfood Day 4+ 발견 시                      | S (1-2h)  | TODO.md L43 (Sprint 14 이관)             |
| [BL-019](#bl-019)                                     | `NEXT_PUBLIC_API_URL` trailing slash + production 누락                                             | Vercel 프로덕션 배포 직전                   | S (1h)    | TODO.md L44 (Sprint 14 이관)             |
| [BL-020](#bl-020)                                     | webhook 응답 size cap + JSON detail 정규화                                                         | on-demand (대용량 stack trace 노출 발견 시) | S (1h)    | TODO.md L45 (Sprint 14 이관)             |
| [BL-021](#bl-021)                                     | sessionStorage hardening (CSP + Trusted Types + secret masking)                                    | Beta 5명 onboarding 후                      | M (4-6h)  | TODO.md L46 (Sprint 14+ 이관)            |
| [BL-022](#bl-022)                                     | golden expectations 재생성                                                                         | pine_v2 `strategy.exit` 도입 후             | M (3-4h)  | TODO.md L17 (skip #1)                    |
| [BL-023](#bl-023)                                     | KIND-B/C mutation 분류 정밀도 (xfail strict)                                                       | Trust Layer v2 검토 시                      | M (5-6h)  | TODO.md L23 (skip #16)                   |
| [BL-024](#bl-024)                                     | real_broker E2E 본 구현 (nightly cron)                                                             | Bybit Demo credentials + seed data 준비 시  | L (8h+)   | CLAUDE.md Sprint 10 Phase C              |
| [BL-025](#bl-025)                                     | autonomous-parallel-sprints 스킬 patch                                                             | on-demand (BUG-1/2/3 재발 시)               | S (2h)    | TODO.md L653                             |
| [BL-026](#bl-026)                                     | mutation fixture 활성화 회귀 (skip #4-7, #9-15)                                                    | Stage 2c 2차 fixture 활성화 후              | S (1-2h)  | TODO.md L20-22                           |
| [BL-080](#bl-080-✅-resolved-sprint-18-2026-05-02) ✅ | **scan/reconcile/trading prefork-safe architectural fix** (Option C — Persistent worker loop)      | (Sprint 18, 2026-05-02 Resolved)            | L (1-2일) | Sprint 17 dev-log §7 + Sprint 18 dev-log |

### BL-010

**Title:** commit-spy 도메인 확장 (LESSON-019 backfill)
**Category:** 트랜잭션 / 도메인
**Priority:** P1 — 4번째 broken bug 재발 예방 (Sprint 6 webhook_secret → Sprint 13 OrderService → Sprint 15 ExchangeAccount → ?)
**Trigger:** 다음 mutation PR 직전 또는 Sprint 16 직후
**Est:** S (2-3h)
**Status:** ✅ **Resolved** (Sprint 16, 2026-05-01) — 4 도메인 (Strategy / Backtest / Waitlist / StressTest) commit-spy backfill 완료, 11 spy 추가. codex G.0 audit 결과 5 도메인 모두 commit 호출 OK = broken bug 0건 confirmed. Optimizer 는 H1 미구현 (스캐폴드만) → 별도 BL (Optimizer 구현 시점에 spy 추가).
**출처:** [`docs/04_architecture/architecture-conformance.md`](04_architecture/architecture-conformance.md) §A2 / Phase 1 audit TBD

**원인 / 영향:** LESSON-019 가 trading 도메인의 broken bug 3 회 재발에서 승격됐지만, **backtest / strategy / waitlist / stress_test / market_data / auth 도메인의 commit-spy 회귀 테스트 미발견**. 다음 service mutation 추가 시 동일 패턴 재발 가능.

**권장 접근:**

1. `tests/<domain>/test_*_commits.py` 표준 reference 는 `backend/tests/trading/test_webhook_secret_commits.py` (6 spy)
2. AsyncMock spec 기반 spy + db_session fixture 와 분리 + false-positive 방어 (same-session read-your-writes)
3. 6 도메인 × 평균 3 mutation 메서드 = ~18 spy 테스트 추가
4. `.ai/stacks/fastapi/backend.md` §트랜잭션 commit 보장 섹션에 "모든 도메인 적용" 명시

**의존성:** —

**Sprint 16 산출물:**

- `backend/tests/strategy/test_strategy_commits.py` (4 spy: create / atomic auto-issue / update / delete)
- `backend/tests/backtest/test_backtest_commits.py` (3 spy: submit / cancel / delete)
- `backend/tests/waitlist/test_waitlist_commits.py` (2 spy + autouse `_reset_rate_limiter` override)
- `backend/tests/stress_test/test_stress_test_commits.py` (2 spy: monte_carlo / walk_forward)
- 회고: [`docs/dev-log/2026-05-01-sprint16-phase0-live-and-backfill.md`](dev-log/2026-05-01-sprint16-phase0-live-and-backfill.md) §4
- 커밋: `beacc89` (4 files / 460 insertions)

---

### BL-011

**Title:** Redis lease + heartbeat (multi-account scaling)
**Category:** WebSocket / Celery
**Priority:** P1
**Trigger:** 2 계정 이상 dogfood 진입 시
**Est:** M (5-6h)
**출처:** [`docs/TODO.md`](TODO.md) L706 (Sprint 13 이관)

**원인 / 영향:** 현재 `--pool=solo` + process-level set 으로 dogfood 1-user 우회. 2 계정 이상은 lease 필요.

**권장 접근:** Redis SET NX PX + heartbeat (TTL renew) + worker_process_init/shutdown hook + lease release on graceful shutdown. ADR-018 WS supervisor 와 통합.

**의존성:** BL-012 (prefork 복귀 와 짝)

---

### BL-012

**Title:** prefork 복귀
**Category:** WebSocket / Celery
**Priority:** P1
**Trigger:** BL-011 직후
**Est:** M (4h)
**출처:** TODO.md L707

**원인 / 영향:** Sprint 12 G4 revisit fix #4 — `--pool=solo` 단일 process 한계. concurrency=1 = 1 account. prefork + Redis lease + `worker_process_init/shutdown` hook 으로 N account 지원.

**권장 접근:** `docker-compose.yml` ws-stream worker `--pool=prefork --concurrency=N` 복귀 + worker_process_init 에서 lease acquire + worker_shutdown 에서 release. BL-011 lease pattern 전제.

---

### BL-013

**Title:** Auth circuit breaker (`BybitAuthError` 1h TTL)
**Category:** WebSocket / Auth
**Priority:** P1
**Trigger:** dogfood 1주 운영 중 alert flood 발견 시
**Est:** S (2-3h)
**출처:** TODO.md L708

**원인 / 영향:** 현재 Beat 5분마다 재시도 → 동일 alert 반복 (사용자 수동 fix 신호 noise).

**권장 접근:** `BybitAuthError` 시 Redis circuit breaker (1h TTL). 그 사이 supervisor 재연결 시도 0 + Slack alert 1회만 + 만료 후 자동 재개. 단위테스트: TTL 만료 전/후 시도 횟수 검증.

---

### BL-014

**Title:** Partial fill `cumExecQty` tracking
**Category:** 트랜잭션 / Order
**Priority:** P1
**Trigger:** partial fill 1 건 dogfood 발견 시 또는 Sprint 16~17 정기
**Est:** M (4-5h)
**출처:** TODO.md L709

**원인 / 영향:** 현재 terminal status 만 transition (closed + cumExecQty == quantity → filled). partial fill 진행 상황 추적 불가 → Kill Switch 노출 정확도 저하.

**권장 접근:** `order_executions` append-only table 신설 (order_id / executed_at / qty / price / fee). WS event 마다 row insert + Order.filled_quantity 누적 갱신.

---

### BL-015

**Title:** OKX Private WS
**Category:** WebSocket / Exchange
**Priority:** P1
**Trigger:** Bybit Demo 안정화 후 (BL-001 watchdog 완료 + 1주 운영)
**Est:** M (6-8h)
**출처:** TODO.md L710

**원인 / 영향:** Sprint 7d OKX 어댑터는 REST 만 보유. WS event 부재로 BL-001 의 fetch_order polling 부담 가중.

**권장 접근:** OKX private WS signing 방식 구현 (Bybit 와 다름). clOrdId 매핑은 Sprint 12 C-pre 에서 이미 완료.

---

### BL-016

**Title:** `__aenter__` first_connect race 강화
**Category:** WebSocket
**Priority:** P1
**Trigger:** 60s timeout 실측 발견 시
**Est:** S (2h)
**출처:** TODO.md L711 (codex G4 revisit advisory B)

**권장 접근:** 현재 `__aenter__` 60s startup timeout 만. retry + circuit breaker 추가.

---

### BL-017 ~ BL-021 (Sprint 14 G.4 P2 잔존 5건)

**모두 출처:** TODO.md L40-46 "### Sprint 14 이관 (G.4 P2 잔존)"

| ID     | 제목                                                   | 권장 접근                                                                                |
| ------ | ------------------------------------------------------ | ---------------------------------------------------------------------------------------- |
| BL-017 | WebCrypto error 처리                                   | `crypto.subtle.sign` / `randomUUID` 실패 시 inline error (현재 unhandled promise reject) |
| BL-018 | Strategies/Accounts query loading/error UX             | 빈 목록 vs 실패 동일 UX. `useExchangeAccounts` 실패 시 안내 메시지 + retry               |
| BL-019 | `NEXT_PUBLIC_API_URL` trailing slash + production 누락 | string concat `//api/v1` 가능성. Sprint 14 B-3 `lib/api-base.ts::getApiBase()` 보강      |
| BL-020 | webhook 응답 size cap + JSON detail 정규화             | large body / stack trace 노출 방어. Sprint 14 B-4 `readErrorBody` 8KB cap 보강           |
| BL-021 | sessionStorage hardening                               | CSP `connect-src` allowlist + Trusted Types + secret masking                             |

---

### BL-022

**Title:** Golden expectations 재생성 (skip #1 해소)
**Category:** Test infra / Pine
**Priority:** P1
**Trigger:** pine_v2 `strategy.exit` 본격 지원 후
**Est:** M (3-4h)
**출처:** TODO.md L17 / `tests/backtest/engine/test_golden_backtest.py:19`

**권장 접근:** legacy golden expectations 재생성 (pine_v2 strategy.exit 가 도입되면 expected 재계산). dette 카테고리 #1 해소.

---

### BL-023

**Title:** KIND-B/C mutation 분류 정밀도 (xfail strict 해소)
**Category:** Trust Layer / Mutation
**Priority:** P1
**Trigger:** Trust Layer v2 검토 시
**Est:** M (5-6h)
**출처:** TODO.md L23 / `tests/strategy/pine_v2/test_mutation_oracle.py:213`

**권장 접근:** KIND-B/C 가 NaN-tolerance 한계로 mutation 구분 못 함 (현재 `xfail(strict=False)`). NaN-tolerance 알고리즘 정밀화 또는 KIND 분류 재설계.

---

### BL-024

**Title:** real_broker E2E 본 구현 (nightly cron)
**Category:** Test infra
**Priority:** P1
**Trigger:** Bybit Demo credentials + seed data 첫 준비 시
**Est:** L (8h+)
**출처:** CLAUDE.md Sprint 10 Phase C — "실제 E2E 로직은 nightly 첫 실행 시 credentials + seed data 하에 작성 예정"

**권장 접근:** `nightly-real-broker.yml` (cron 0 18 \* \* \*) 의 실제 검증 로직 구현. 현재는 skeleton + marker + flag 만.

---

### BL-025

**Title:** autonomous-parallel-sprints 스킬 patch (BUG-1/2/3 → LESSON-007/008/009)
**Category:** Tooling
**Priority:** P1 (다음 자율 병렬 sprint 시 재발 방지)
**Trigger:** on-demand (다음 자율 병렬 sprint 시도 직전)
**Est:** S (2h)
**출처:** TODO.md L653-657

**권장 접근:**

- BUG-1: kickoff-worker.sh symlink → `--git-common-dir` 기반 교체
- BUG-2: Planner SIG_ID full-id 강제
- BUG-3: Worker plan 저장 경로 worktree-only 강제
- 스킬 repo: `~/.claude/skills/autonomous-parallel-sprints/`

---

### BL-026

**Title:** Mutation fixture 활성화 회귀 검토 (skip #4-7, #9-15)
**Category:** Trust Layer / Test infra
**Priority:** P1
**Trigger:** Stage 2c 2차 fixture 활성화 후 (✅ 2026-04-23 완료, 회귀 PR 생성 필요)
**Est:** S (1-2h)
**출처:** TODO.md L20-22

**권장 접근:** Path β Stage 2c 2차 mutation 8/8 도달 후 12 skip 가 활성화 가능 상태. 회귀 PR 1건으로 일괄 활성화 + 1주 nightly green 후 안정화.

---

### BL-080 ✅ Resolved (Sprint 18, 2026-05-02)

**Title:** scan/reconcile/trading prefork-safe **architectural fix**
**Category:** Trading / WebSocket / Watchdog (Celery prefork + asyncio + SQLAlchemy)
**Priority:** P1 → **Resolved**
**출처:** [`docs/dev-log/2026-05-02-sprint17-prefork-fix.md`](dev-log/2026-05-02-sprint17-prefork-fix.md) §7 → [Sprint 18 dev-log](dev-log/2026-05-02-sprint18-bl080-architectural.md)

**해소 (Option C — Persistent worker loop)**:

- `backend/src/tasks/_worker_loop.py` 신규 — `init_worker_loop()` / `shutdown_worker_loop()` / `run_in_worker_loop(coro)` (running-loop guard + asyncgens drain).
- `worker_process_init` hook 에 init / `worker_process_shutdown` 신규 hook 에 shutdown (codex G.0 P1 #4).
- 9개 task entry point `asyncio.run()` → `run_in_worker_loop()` (`_on_worker_ready` master 만 예외, codex G.0 P1 #5).
- `worker_max_tasks_per_child` 1 → 250 (codex G.2 P2 #1 보수).
- conftest `TEST_DATABASE_URL` / `TEST_REDIS_LOCK_URL` env 우선순위 + 격리 stack 5433/6380 명시 (codex G.0 P1 #7) — Sprint 16/17 의 296 errors → 0.

**라이브 evidence (post-Sprint 18 fix)**: 같은 ForkPoolWorker-2 가 mixed 30 tasks (scan + reconcile + backtest) **30/30 success / 0 raised**. Sprint 17 1/3 → Sprint 18 30/30. self-assessment 5 → 9.

**root cause confirmed**: asyncpg connection 의 `BaseProtocol._on_waiter_completed` callback 이 1st task asyncio.run() loop 에 bound. `engine.dispose()` 후에도 internal transport waiter 가 stale loop 의 Future 보유. 2nd task 의 새 loop 에서 동일 connection (또는 새 connection 의 internal cache) 접근 시 fail. Option C 의 영속 `_WORKER_LOOP` 통일이 모든 binding 일관성 보장.

**codex 검증**: G.0 (high, 824k tokens, iter 1) — REFUTED + 7 P1 + 5 P2 모두 plan v2 반영. G.2 (high, 487k tokens, iter 1) — HIGH risk + P1 #1 (race) + P2 #3 (asyncgens drain) 즉시 fix.

---

### Sprint 19 이관 BL → ✅ 4건 Resolved (Sprint 19, 2026-05-02)

| ID            | 제목                                                                                                                                                          | Priority | Status                                          |
| ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | ----------------------------------------------- |
| **BL-081** ✅ | `qb_pending_alerts` gauge + `track_pending_alert()` idempotent helper (codex G.2 P2 #2 from Sprint 18 + P1 #4 from Sprint 19)                                 | P2       | **Resolved** (Sprint 19, 2026-05-02)            |
| **BL-082**    | 1h prefork soak gate + RSS slope (max_tasks_per_child 250→1000 검증)                                                                                          | P2       | 본인 dogfood (BL-005) 중 자연 측정 — Sprint 20+ |
| **BL-083** ✅ | `tests/test_migrations.py` 격리 stack 호환 — `_resolved_test_db_url` + `_to_psycopg2_url` (4 fail → 0)                                                        | P2       | **Resolved** (Sprint 19, 2026-05-02)            |
| **BL-084** ✅ | AST audit `test_no_module_level_loop_bound_state.py` — module-level asyncio primitive 차단 gate (allowlist: `_SEND_SEMAPHORE`)                                | P3       | **Resolved** (Sprint 19, 2026-05-02)            |
| **BL-085** ✅ | `tests/tasks/test_prefork_smoke_integration.py` — real asyncpg 회귀 + `--run-integration` flag + DSN guard + apply_async/delay no-op (codex G.2 P1 #1+#2 fix) | P3       | **Resolved** (Sprint 19, 2026-05-02)            |

### Sprint 20+ 이관 BL (Sprint 19 codex G.2 P2 잔존 + Sprint 18 BL-082)

| ID                | 제목                                                                                                                                                                                                 | Priority | Est       |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------- | --------- | ----------------------- |
| **BL-086 (신규)** | AST audit factory function detection (codex G.2 P2 #1 Sprint 19) — `_MODULE_LOCK = _make_lock()` 패턴 catch                                                                                          | P3       | S (1-2h)  |
| **BL-087 (신규)** | AST audit target glob `src/tasks/**/*.py` (codex G.2 P2 #2 Sprint 19) — manual list bypass 방어                                                                                                      | P3       | S (30min) |
| **BL-088 (신규)** | `drain_pending_alerts()` helper (codex G.2 P2 #3 Sprint 19) — production drain 사용처 추가 시 idempotent guard                                                                                       | P3       | S (1h)    |
| **BL-089 (신규)** | `qb_pending_alerts` Grafana alert wire-up (>50 임계) — Sprint 30 ε B8 partial: `backend/prometheus/alerts.yml` rule 작성 ✅. Sprint 31 deploy 단계에서 Alertmanager 라우팅 + Slack 채널 wire-up 잔여 | P2       | S (1-2h)  | partial ⚠ (Sprint 30)   |
| **BL-090 (신규)** | `tests/db_url.py` 분리 (codex G.2 P3 #1 Sprint 19) — test_migrations 의 conftest import 정리                                                                                                         | P3       | S (30min) |
| **BL-091**        | ExchangeAccount.mode dynamic dispatch (3-tuple proper fix)                                                                                                                                           | **P1**   | M (1-2일) | ✅ Resolved (Sprint 22) |
| **BL-098**        | strategy.exit coverage/interpreter parity (NOP + warning)                                                                                                                                            | P1       | S (1.5h)  | ✅ Resolved (Sprint 23) |
| **BL-099**        | vline coverage/interpreter parity (NOP)                                                                                                                                                              | P1       | S (10m)   | ✅ Resolved (Sprint 23) |
| **BL-101**        | Makefile up-isolated-build 옵션                                                                                                                                                                      | P3       | S (10m)   | ✅ Resolved (Sprint 23) |
| **BL-102**        | Order 에 dispatch (exchange, mode, has_leverage) snapshot 저장 (G.2 P2 #3)                                                                                                                           | P2       | M (~7-8h) | ✅ Resolved (Sprint 23) |
| **BL-103**        | EXCHANGE_PROVIDER lifespan deprecation warning (G.2 P2 #5)                                                                                                                                           | P3       | S (1h)    | ✅ Resolved (Sprint 23) |
| **BL-104 (신규)** | strategy.exit full PendingExitOrder 구현 (target price trigger + warnings dedupe) — Sprint 23 BL-098 후속 (G.0 P1 #1+#2 + G.2 P2 #4)                                                                 | P2       | M (1-2일) |
| **BL-105 (신규)** | OrderService.execute account fetch transaction 안 이동 + AccountNotFound (G.2 P2 #1) — DELETE race FK violation 회피                                                                                 | P2       | S (1-2h)  |
| **BL-106 (신규)** | Alembic 20260503_0001 idempotency 강화 — `IF NOT EXISTS` / `IF EXISTS` (G.2 P2 #2+#3 TOCTOU)                                                                                                         | P3       | S (30m)   |
| **BL-107 (신규)** | `.husky/pre-push` 가 default 5432 DB 사용 → InvalidPasswordError 298 errors (Sprint 23 push 시 발견). TEST_DATABASE_URL 격리 stack 자동 사용 또는 conftest fallback 강화 (Sprint 18 BL-083 패턴)     | P2       | S (30m)   |
| **BL-108 (신규)** | `_ws_circuit_breaker.record_network_failure` 의 INCR + EXPIRE 비원자성 → Lua wrap (Sprint 24a G.2 P2 #1)                                                                                             | P3       | S (30m)   |
| **BL-109 (신규)** | `test_first_connect_timeout_calls_record_network_failure` 가 account-not-found 조기 return, 실제 timeout path 미검증 (Sprint 24a G.2 P2 #2)                                                          | P3       | S (1h)    |
| **BL-110 (신규)** | prefork SIGTERM + multi-process lease integration test 부재 (Sprint 24a G.2 P2 #3) — `mark.integration` 으로 라이브 검증                                                                             | P2       | S (1-2h)  |
| **BL-111 (신규)** | WS circuit breaker `reset_circuit` admin/CLI path 부재 (Sprint 24a G.2 P2 #4) — 현재 `redis-cli DEL` 만                                                                                              | P3       | S (1-2h)  |
| **BL-112 (신규)** | `test_auto_dogfood.py:scenario2 backtest_engine_smoke` 가 실제 backtest 실행 안 함 — `run_backtest_v2(...)` 호출 + status="ok" assert (Sprint 24b G.2 P1 #1)                                         | P2       | S (1-2h)  |
| **BL-113 (신규)** | `test_auto_dogfood.py:scenario3 order_dispatch_snapshot` 가 Order 직접 INSERT — service auto-fill path 우회. OrderService.execute 통한 검증 (Sprint 24b G.2 P1 #2)                                   | P2       | S (1-2h)  |
| **BL-114 (신규)** | `run_auto_dogfood.py` stdout 텍스트 파싱 fragility (PASSED count + 200자 substring) → pytest-json-report 또는 JUnit XML (Sprint 24b G.2 P2 #2)                                                       | P3       | S (30m)   |
| **BL-115 (신규)** | `run_auto_dogfood.py` HTML output 미escape (스크립트 인젝션 surface) — `html.escape()` 적용 (Sprint 24b G.2 P2 #4)                                                                                   | P3       | S (15m)   |

**BL-091 상세** (Sprint 20 dogfood Day 0 라이브 발견 → Sprint 22 ✅ Resolved 2026-05-03):

- **증상**: 사용자가 `/trading` 의 TestOrderDialog 로 발송 → UI "filled" + DB `state=filled` 표시. 하지만 `exchange_order_id='fixture-1'` + `filled_price=50000.00` (round number) = mock 응답. **broker 까지 안 감**.
- **Root cause**: `backend/src/tasks/trading.py:_build_exchange_provider()` 가 `settings.exchange_provider` (Pydantic env) 기반 lazy singleton. **ExchangeAccount.mode (demo/live) 완전 무시**. + `docker-compose.yml` worker/beat env 에 `EXCHANGE_PROVIDER` 누락 (Sprint 20 hot-fix 로 추가) → Pydantic default `"fixture"` 적용 → `FixtureExchangeProvider()` 반환.
- **사용자 신뢰 위반**: ExchangeAccount UI 에서 mode=demo 명시 + Bybit Demo API key 등록했는데도 worker 가 fixture 응답. **dogfood 의 본질 위반**.
- **Sprint 20 hot-fix** (Day 0 적용): `.env` 에 `EXCHANGE_PROVIDER=bybit_demo` + `docker-compose.yml` 에 env 추가. **mitigation — proper fix 아님**.
- **Sprint 22 proper fix ✅**: `_provider_for_account_and_leverage(exchange, mode, has_leverage)` 3-tuple dispatch + `_build_exchange_provider(account, submit)` public dispatcher. module-level `_exchange_provider` global + `_get_exchange_provider()` 제거. `UnsupportedExchangeError(ProviderError)` 로 graceful rejected. BybitLiveProvider stub (`create_order/cancel_order/fetch_order` 모두 ProviderError raise) — BL-003 까지 deferred. dispatch tuple 에 fixture 분기 부재로 silent fallback 자동 차단. ExchangeAccount.mode mutation endpoint 부재 (PUT/PATCH 없음) audit test 로 race-free 보장. docker-compose env 제거 + .env.example deprecation 주석.
- **codex G.0 (medium) 결과**: P1 5건 (live/stub 충돌 / UnsupportedExchangeError graceful catch 누락 / Protocol cancel_order 누락 / EXCHANGE_PROVIDER 정책 모순 / account.mode race) + P2 5건 (leverage=0 / monkeypatch 카운트 / e2e 마이그레이션 / fixture guard scope / 헤더 주석) 모두 plan v2 반영 후 구현.
- **검증**: 신규 28 tests (test_provider_dispatch.py 27 + test_account_mode_immutable.py 1) 100% pass + 21건 monkeypatch 마이그레이션 회귀 0 fail. 전체 1342 passed / 27 skipped / 0 failed (격리 stack). ruff 0 / mypy 0 (145 src files).
- **Files**: `backend/src/tasks/trading.py` · `backend/src/trading/providers.py` (BybitLiveProvider) · `backend/src/trading/exceptions.py` (UnsupportedExchangeError) · `backend/src/core/config.py` · `docker-compose.yml` · `.env.example` · `backend/src/tasks/funding.py` (docstring) · 신규 `tests/tasks/test_provider_dispatch.py` + `tests/trading/test_account_mode_immutable.py`.
- **Trigger Sprint 23+**: dogfood Day 2-7 broker 도달 evidence (BrokerBadge 녹색 broker) ✅ → Path A Beta 오픈 (BL-070~072). 🔴 → 회귀 분석.

| **BL-092 (신규)** | `qb_active_orders` filled/cancelled 후 dec 누락 (Sprint 20 dogfood Day 0) | P2 | S (분석 + 1-line fix) |
| **BL-093 (신규)** | TestOrderDialog 성공 시 명시적 confirmation (toast/inline) 부재 — dialog 자동 닫힘만 | P3 | S (1h) |
| **BL-094 (신규)** | webhook secret sessionStorage TTL 30분 vs dogfood UX 충돌 — 30분 흐르면 Rotate 강제 | P3 | S (정책 결정 후 1-2h) |
| **BL-095 (신규)** | Backtest 422 inline detail 미흡 — `API 422 /api/v1/backtests` 만 표시, `unsupported builtins` 같은 detail 누락 | P3 | S (1h) |
| **BL-096 (신규)** | **Coverage Analyzer supported list 너무 좁음** + Sprint 8c corpus 와 production supported list 이중 잣대 | **P1** | M (1주) |

**BL-092 상세** (Sprint 20 Day 0 라이브 발견, 2026-05-02):

- 현재 `qb_active_orders=2.0` — 1차 fixture (filled) + 2차 real broker (filled) 후에도 dec 누적 안 됨
- 추정 #1: BL-027 winner-only dec 가 fixture 1차 때 inc 안 했지만 dec 시도 → underflow guard 가 dec block?
- 추정 #2: state_handler 가 WS event 처리 시 winner-only rowcount 0 반환?
- Sprint 21 분석. `qb_active_orders` invariant 검증 (pending/submitted inc, filled/cancelled dec). 현재 monotonically increasing 이라 운영 metric 신뢰도 낮음.

**BL-093 상세** (Sprint 20 Day 0 라이브 발견):

- TestOrderDialog Submit 성공 시 dialog 자동 닫힘만, 사용자 본인이 "주문창이 안 보여서.. 된거긴한것 같은데?" 표현
- 권장: sonner toast (`주문 발송됨 / order_id ${id}`) 또는 dialog 안에 success state 표시

**BL-094 상세** (Sprint 20 Day 0 라이브 발견):

- Sprint 13 의 보안 정책 (1회 노출 + sessionStorage TTL 30분) 이 dogfood 시나리오와 충돌
- Strategy create 11:51 → TestOrder 12:24 (33분 경과) → "Webhook secret 캐시 없음. Strategy 페이지에서 Rotate 후 다시 시도" 발생
- 매번 30분 안에 dogfood 사이클 끝내야 한다는 가정 — 실용적이지 않음
- 옵션: TTL 24h 늘림 / "secret 다시 보기" 버튼 / TestOrderDialog 가 sessionStorage 부재 시 자동 Rotate prompt / 또는 의도된 보안 정책 유지 + 가이드 명시

**BL-095 상세** (Sprint 20 Day 0 라이브 발견):

- Frontend `BacktestForm` 가 422 시 `API 422 /api/v1/backtests` 만 표시, backend 의 `detail.detail` (unsupported builtins 목록) 안 보임
- 사용자가 어떤 builtin 이 미지원인지 알기 위해 강제로 network 탭 또는 console 확인 필요
- Sprint 21+ FE fix: 422 detail.code === "strategy_not_runnable" 인 경우 unsupported builtin list 를 inline 카드로 표시

**BL-096 상세** (Sprint 20 Day 0 backtest 6/6 매트릭스 발견 — **P1 critical**):

- **결정적 모순 발견**: Sprint 8c 의 strict 검증 (i3_drfx, s3_rsid strict=True 통과, **252 pine_v2 tests green**) vs **production parse-preview reject**:
  - DrFXGOD (= i3_drfx 동일): 39 unsupported builtins, `is_runnable: false`
  - RsiD (= s3_rsid 동일): 8 unsupported (abs, barssince, currency.USD, max, pivothigh, pivotlow, strategy.fixed, valuewhen), `is_runnable: false`
- 즉 **Sprint 8c 의 pine_v2 dispatcher 가 처리할 수 있는 builtin 집합** vs **production Sprint Y1 Coverage Analyzer 의 supported list** 가 분리됨
- 흔한 미지원 다수: `abs`, `max`, `min`, `ta.barssince`, `ta.valuewhen`, `ta.pivothigh/low`, `currency.USD`, `strategy.fixed`, `barcolor`, `label.*`, `box.*`, `request.security`, `str.tostring`, `fixnan`, `barstate.*`
- **dogfood 의 큰 friction**: 사용자 본인 6 indicator 중 4 reject (UtBot×2 + DrFX + RsiD), 2 통과 (PbR + LuxAlgo) = **33% 통과율**
- Sprint 21+ 작업:
  - SSOT supported list 단일화 — `pine_v2` corpus 통과 builtin = production supported
  - `abs`, `max`, `min`, `ta.barssince`, `ta.valuewhen`, `ta.pivothigh/low` 등 흔한 builtin 우선 추가
  - 또는 Coverage Analyzer 의 strict mode 옵션 (사용자가 "이건 backtest 거짓 양성 위험 알지만 진행" 토글)
  - 통합 검증: 신규 supported builtin 추가 시 corpus 6/6 + production parse-preview 6/6 동시 통과 의무

**현황:** Sprint 17 Phase A+B+C 가 module-level cached AsyncEngine 제거 + per-call `create_worker_engine_and_sm()` + finally `engine.dispose()` 도입 (backtest.py:31 mirror). **1st task / child success**. 하지만 같은 child 의 2nd+ task 가 RuntimeError "attached to a different loop" / InterfaceError "another operation is in progress" 재발 — SQLAlchemy/asyncpg 의 process-level state (dialect cache 등) 가 stale loop Future 보유. `worker_max_tasks_per_child=1` 효과 약함.

**라이브 evidence (격리 docker, 2026-05-02 post-Sprint 17 fix)**:

```
1st scan_stuck_orders: succeeded (0.11s) — Phase 0 의 100% silent fail 대비 진전
2nd scan_stuck_orders: RuntimeError("attached to a different loop")
3rd scan_stuck_orders: InterfaceError("another operation is in progress")
```

**Question (Sprint 18 G.0 의 핵심)**: backtest.reclaim_stale 이 동일 6h 동안 34/34 success 였는데 우리 task 만 fail — 무엇이 다른가? candidate diff:

1. `_get_redis_lock_pool_for_alert` (alert path) — module-level Redis pool stale loop bind?
2. `_exchange_provider` lazy singleton — CCXT internal state?
3. `OrderRepository.list_stuck_pending` 의 specific SQLAlchemy statement caching?
4. import 순서 (`from src.tasks.trading import execute_order_task`) 가 trading.py top-level state trigger?

**권장 접근**:

1. **diff 정밀 분석** (4-8h) — backtest.py vs orphan_scanner.py runtime state 비교 (profiling, debugging)
2. 후보 fix:
   - **A. Celery solo pool** — scan/reconcile/trading 각각 dedicated worker (`--pool=solo`). Sprint 12 ws-stream worker 패턴 mirror. **운영 복잡도 ↑** (4-6h)
   - **B. asyncpg/SQLAlchemy module-level state reset** — `_get_redis_lock_pool_for_alert` + dialect cache 매 task reset. Hot path overhead. (1일)
   - **C. fork-fresh interpreter** — `worker_pool=prefork` + `worker_init` hook 으로 module reset. Invasive. (1-2일)
3. **G.2 challenge** 의무 — silent failure mode 가 또 있는가?
4. 라이브 검증 — `asyncio.run() 즉시 3회 연속` + `5분 cycle 1시간` 둘 다 성공 확인.

**의존성:** 없음. Sprint 17 의 Phase A+B+C foundation 위에 빌드.

**Cross-link**: Sprint 17 dev-log §7. Sprint 18 master plan v1.

---

## P2 — Hardening / 건강도 작업

| ID                                                 | 제목                                                                                                              | Trigger                                      | Est           | 출처                                                                                                                                                                       |
| -------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | -------------------------------------------- | ------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| BL-027 ✅ Resolved                                 | WS state_handler / reconciliation / tasks/trading dec winner-only commit-then-dec                                 | (Sprint 16, 2026-05-01)                      | M (3-4h)      | dev-log Sprint 15 watchdog G.2 P1 #3 분리, Sprint 16 fix                                                                                                                   |
| [BL-030](#bl-030)                                  | CI lupa C ext 빌드 검증                                                                                           | on-demand                                    | S (1h)        | CLAUDE.md Sprint 11 follow-up                                                                                                                                              |
| [BL-031](#bl-031)                                  | Sentinel/Cluster 검토                                                                                             | Redis 단일 인스턴스 한계 도달 시             | L (다음 분기) | CLAUDE.md Sprint 11 follow-up                                                                                                                                              |
| [BL-032](#bl-032)                                  | cardinality allowlist 조정                                                                                        | 프로덕션 ccxt 예외 실측 후                   | S (1-2h)      | TODO.md L807 (H2 말 이관)                                                                                                                                                  |
| [BL-033](#bl-033)                                  | issue 중복 방지 (auto-label workflow)                                                                             | dogfood 1주 운영 중 issue 중복 발견 시       | S (1h)        | CLAUDE.md Sprint 11 follow-up                                                                                                                                              |
| [BL-034](#bl-034)                                  | slowapi 0.2.x major upgrade 검토                                                                                  | H2 말 (~2026-06-30)                          | M (3-4h)      | TODO.md L806                                                                                                                                                               |
| [BL-035](#bl-035)                                  | Phase B Grafana Cloud (dogfood 통합 대시보드)                                                                     | dogfood 운영 중 본인 필요 metric 식별 후     | M (4-6h)      | TODO.md L715 (Sprint 12 이관)                                                                                                                                              |
| [BL-036](#bl-036)                                  | dogfood 통합 대시보드 `/dashboard/today`                                                                          | "화면 부족" 자각 시                          | M (3-4h)      | TODO.md L716                                                                                                                                                               |
| [BL-037](#bl-037)                                  | Coverage Analyzer AST 정밀화 (regex → pynescript visitor)                                                         | Sprint Y2 또는 사용자 false-positive 보고 시 | M (4h)        | CLAUDE.md Y1 follow-up                                                                                                                                                     |
| [BL-038](#bl-038)                                  | P-3 중복 실행 통합 (`run_backtest_v2` + `parse_and_run_v2`)                                                       | Sprint 16 정리 sprint 시                     | M (3-4h)      | CLAUDE.md codex Gate-2 W-3                                                                                                                                                 |
| [BL-039](#bl-039)                                  | `qb_redis_lock_pool_healthy` startup race                                                                         | dogfood 운영 중 false alert 1건 이상 발견 시 | S (1-2h)      | dogfood-day1 §3 (관찰)                                                                                                                                                     |
| [BL-040](#bl-040)                                  | Path γ — PyneCore transformers 이식                                                                               | H2~H3 path 평가 시                           | XL (~3주)     | CLAUDE.md ADR-011 amendment                                                                                                                                                |
| [BL-041](#bl-041)                                  | Path δ — Bulk stdlib top-N                                                                                        | dogfood 피드백 기반 우선순위 결정 후         | L (1~2주)     | CLAUDE.md ADR-011 amendment                                                                                                                                                |
| [BL-042](#bl-042)                                  | Onboarding 성공률 지표 `qb_onboarding_completion_total{step}`                                                     | Beta 5명 onboarding 후                       | S (1-2h)      | TODO.md L808                                                                                                                                                               |
| [BL-043](#bl-043)                                  | waitlist email_service Resend 미설정 graceful fallback 검증                                                       | Beta 오픈 직전                               | S (1-2h)      | TODO.md L809                                                                                                                                                               |
| [BL-137](#bl-137)                                  | 신규 strategy trading settings UI (메타데이터 tab)                                                                | Sprint 27 hotfix / Beta prereq               | M (1-2h)      | dogfood Day 1 Finding #1                                                                                                                                                   |
| BL-140 ✅ Resolved (Sprint 27 PR #104)             | LiveSignalDetail equity curve chart UI (placeholder dual-line)                                                    |                                              |               | dogfood Day 3 Finding #4                                                                                                                                                   |
| BL-140b ✅ Resolved (Sprint 28 Slice 3 PR #111)    | LiveSignalDetail equity curve real value (BE schema + FE chart)                                                   |                                              |               | dogfood Day 1 finding 후속                                                                                                                                                 |
| BL-141 ✅ Resolved (Sprint 28 Slice 2 PR #110)     | Backtest UI 활성화 + ts.ohlcv hypertable backfill                                                                 |                                              |               | dogfood Day 4-7 D.1                                                                                                                                                        |
| [BL-142](#bl-142)                                  | ts.ohlcv daily refresh task (Slice 2 후속)                                                                        | Sprint 29+                                   | M (2-3h)      | Sprint 28 Slice 2 brainstorming 결정 1 deferred                                                                                                                            |
| [BL-143](#bl-143)                                  | LiveSignal equity_curve JSONB compaction (long-running aggregation)                                               | Sprint 30+                                   | M (2-3h)      | Sprint 28 Slice 3 brainstorming 결정 1 deferred (1000+ entry)                                                                                                              |
| BL-144 ✅ Resolved (Sprint 27 PR #105)             | input step="any" silent submit block fix                                                                          |                                              |               |
| [BL-145](#bl-145)                                  | EffectiveLeverageEvaluator (Cross Margin position aggregation)                                                    | Sprint 30+ Phase 2 prereq                    | M (3-4h)      | Sprint 28 Slice 4 T3 deferred                                                                                                                                              |
| [BL-146](#bl-146)                                  | 메타-방법론 정책 4종 영구 규칙 승격 (lessons.md → common/global.md)                                               | Sprint 29+ Stage 6                           | XS (15-30분)  | Sprint 28 Slice 1a Phase C.1 sprint-template prototype 검증 후                                                                                                             |
| [BL-147](#bl-147)                                  | Bybit Demo integration test CI 환경 wire-up (--run-real-broker workflow)                                          | Sprint 29+                                   | S (1-2h)      | Sprint 28 Slice 4 T4 CI 환경 의존                                                                                                                                          |
| BL-150 ✅ Resolved (Sprint 36 PR #157, 2026-05-06) | Equity chart full migration recharts → lightweight-charts (점진 마이그레이션 완료) + MC bootstrap sign-flip fix   |                                              |               | Sprint 30-β Option B ADR + MC 음수 equity return clip                                                                                                                      |
| BL-152 ✅ Resolved (Sprint 30-γ-BE 04f754d)        | `total_trades` PRD parity = `num_trades` alias 결정 (BacktestMetrics serializer 양 키 응답)                       |                                              |               | Sprint 30 γ-BE plan §2.γ-BE 후속 결정                                                                                                                                      |
| BL-176 ✅ Resolved (Sprint 36 PR #157, 2026-05-06) | SelectWithDisplayName `onClear` prop 추가 (의도적 clear 동선)                                                     |                                              |               | Sprint 33 hotfix BL-176 follow-up (clear button prop, sentinel/nullable 없이 schema required 유지)                                                                         |
| [BL-181](#bl-181)                                  | Docker worker auto-rebuild on PR merge (volume mount 또는 post-merge hook)                                        | Sprint 37 (P2)                               | M (3-4h)      | dogfood Day 6.5 BL-178 silent stale 재발 방지 (BL-181 = BL-178 근본 fix)                                                                                                   |
| [BL-182](#bl-182)                                  | Worker container code version 자동 monitoring + alert (sentinel function 또는 git hash 비교)                      | Sprint 37+                                   | S (2h)        | Sprint 35 Slice 1a BL-181 follow-up                                                                                                                                        |
| [BL-183](#bl-183)                                  | Monte Carlo 결과 요약 통계 FE 미노출 (CI 95% 하한/상한·median·MDD p95 숫자 테이블)                                | Sprint 37 (Day 7 재측정 prereq)              | S (1-2h)      | dogfood Day 7 발견 — BE 계산 완료, FE fan chart만 렌더, 숫자 표 없음                                                                                                       |
| [BL-184](#bl-184)                                  | Equity / Buy&Hold curve 시작점 PnL 정렬 (현재 절대값 10000 USDT, TradingView 표준 = 0 시작)                       | Sprint 37 (PR #161)                          | S (3-4h)      | dogfood Day 7 발견 — 첫눈 비교 불가 + Surface Trust 갭 (codex FE-only 권장)                                                                                                |
| [BL-185](#bl-185)                                  | Pine 포지션 사이징 spot-equivalent (default_qty_type 3종 + leverage/funding UI cleanup)                           | Sprint 37 (PR #159)                          | M (10-14h)    | dogfood Day 7 발견 root cause — qty=1 hardcode → BTC 1 BTC = 수천만원 포지션 → TV 결과 완전 다름                                                                           |
| [BL-186](#bl-186)                                  | Full leverage + funding rate + maintenance margin + cross/isolated margin + liquidation 풀 모델                   | Sprint 38+ (deferred, BL-185 foundation 위)  | M-L (16-24h)  | Sprint 37 BL-185 spot-equivalent 채택 후 풀 모델은 BL-186 후속 — funding/mm/liquidation 정확 시뮬                                                                          |
| [BL-187](#bl-187)                                  | 백테스트 폼 simplify (leverage/include_funding input 제거 + "모델: Spot-equivalent" visible info row 추가)        | Sprint 37 follow-up                          | S (2-3h)      | dogfood Day 7 발견 — Image 5 (Live Settings) vs Image 6 (백테스트) UI 혼란 (사용자 명시) + ui-ux-pro-max 옵션 2 채택. payload 는 default 자동 채움 (graceful upgrade 보존) |
| [BL-187a](#bl-187a)                                | 라벨 simplify ("Spot-equivalent" → "1x · 롱/숏") + assumptions-card 의 레버리지/펀딩비 row 제거 (사용자 명시)     | Sprint 37 follow-up (PR #164 추가 commit)    | S (1h)        | dogfood Day 7 follow-up — "Spot" 단어 오해 (현물=롱만) + 사용자 명시 "레버리지 부분 일단 빼"                                                                               |
| [BL-188](#bl-188)                                  | 백테스트 폼 ↔ Live Session Trading Settings mirror (옵션 C — Position Size / Sessions auto-fetch + Pine override) | Sprint 38 narrowest wedge 후보               | M (8-12h)     | dogfood Day 7 발견 (사용자 명시) — Live 의 Trading Settings 가 백테스트에 적용되어야 한다는 직관. 현재 분리 = trust 갭                                                     |
| [BL-188a](#bl-188a)                                | 백테스트 폼 default_qty 입력 + Pine override priority chain (Pine > 폼 > None)                                    | Sprint 37 follow-up (PR #164 추가 commit)    | S (4-6h)      | dogfood Day 7 발견 — image 12 의 -249% MDD = Pine 미명시 + qty=1.0 silent fallback. 폼 입력 default percent_of_equity 10% 로 silent fallback 차단                          |

(상세 내용은 출처 인용 — 표 형태로 충분, 각 항목 1-3 줄로 충분히 self-contained)

---

## P3 — Nice-to-have / 컨벤션 정합

| ID                | 제목                                                                       | Trigger                           | Est                       | 출처                                                                                 |
| ----------------- | -------------------------------------------------------------------------- | --------------------------------- | ------------------------- | ------------------------------------------------------------------------------------ |
| [BL-050](#bl-050) | `PINE_ALERT_HEURISTIC_MODE` env 사용 ADR 신설 또는 주석 강화               | 신규 sprint 정리 시 on-demand     | S (30min)                 | architecture-conformance §B5                                                         |
| [BL-051](#bl-051) | zod@4 import 경로 정정 (`zod/v4` → `zod`)                                  | Sprint 16 cleanup 시              | S (1h)                    | TODO.md L813                                                                         |
| [BL-052](#bl-052) | `.uuid()` → `z.uuid()` 전수 migration                                      | BL-051 와 묶음                    | S (1h)                    | TODO.md L814                                                                         |
| [BL-053](#bl-053) | `/strategies/[id]/edit` / `/strategies/new` 라우트 loading.tsx + error.tsx | FE Polish 다음 bundle 시          | S (1-2h)                  | TODO.md L815                                                                         |
| [BL-054](#bl-054) | `strategy-list.tsx` useSuspenseQuery 최종 전환                             | FE Polish 다음 bundle 시          | S (2h)                    | TODO.md L816                                                                         |
| [BL-055](#bl-055) | `"use client"` 27개 중 presentational 서버 컴포넌트화                      | RSC 성능 측정 후 우선순위 결정 시 | M (4h)                    | TODO.md L817                                                                         |
| [BL-056](#bl-056) | D-5 A 안 — Termly → 한국 변호사 검토본 교체                                | H2 말 (~2026-06-30)               | M (외부 비용 $500~$1,500) | TODO.md L805                                                                         |
| [BL-057](#bl-057) | requirements.md §4.1 "Mutation 측정 불가 = scope-reducing" 명시화          | Sprint 16 docs sync 시            | S (30min)                 | CLAUDE.md ADR-013 follow-up                                                          |
| [BL-138](#bl-138) | Live Sessions list 두 line layout → detail inline `·` 일관성 개선          | Sprint 27 polish                  | XS (1 line)               | dogfood Day 1 Finding #2 (재정의)                                                    |
| [BL-139](#bl-139) | LiveSignalDetail aggregation scope 검토 (Day 3 정정 후 우선도 낮음)        | on-demand spec 명시               | S (1h)                    | dogfood Day 1 Finding #3 / Day 3 정정                                                |
| [BL-151](#bl-151) | `tests/backtest/test_golden_backtest.py` 24 신규 필드 expected 재생성      | pine_v2 strategy.exit 지원 시점   | S (1-2h)                  | Sprint 30-γ-BE legacy skip 후속 (현재 pytest.skip)                                   |
| [BL-153](#bl-153) | (실험 태그) Strategy DevOps 카테고리 메시징 — TV 커뮤니티 공개 시 검증     | H3 가격 실험 단계 (4-9m)          | XS (가설만)               | Sprint 30 ADR-019 H3 격리 — 외부 LLM YC 브리프 v2 거절 항목 (가격 5배 클레임 무근거) |

---

## Beta 오픈 번들 — 단일 milestone, 18 sub-task

> **출처:** TODO.md L748~801 "[BLOCKED/DEFERRED] Beta 퍼블릭 오픈 번들 (Sprint 12)"
> **Trigger:** H1 Stealth 종료 (BL-005 self-assessment ≥ 7/10) 후
> **Est:** 4~8h + DNS 전파 24h. **A·B·C 상호 의존, 개별 진행 시 재작업 2~3배 → 번들 처리 필수**

| ID                | 제목                                | Sub-task  | Est               |
| ----------------- | ----------------------------------- | --------- | ----------------- |
| [BL-070](#bl-070) | A. 도메인 + DNS + (옵션) Cloudflare | A1~A3 (3) | 1-2h + 24h DNS    |
| [BL-071](#bl-071) | B. Backend 프로덕션 배포            | B1~B9 (9) | 2~4h              |
| [BL-072](#bl-072) | C. Resend 이메일 + Waitlist 활성화  | C1~C6 (6) | 1-2h + 24h verify |

상세 sub-task 는 TODO.md L750-801 에 그대로 있으므로 본 백로그에서는 ID + 묶음만 트래킹. **Trigger 도래 시 TODO.md 의 해당 섹션을 active 로 승격하고 본 BL-070~072 는 "in_progress" 마킹**.

추가 milestone 작업:

| ID                | 제목                                                                                           | Trigger                               | Est                                |
| ----------------- | ---------------------------------------------------------------------------------------------- | ------------------------------------- | ---------------------------------- | ------------ |
| [BL-073](#bl-073) | Twitter/X #buildinpublic 캠페인 시작                                                           | BL-070~072 완료 후                    | S (사용자 수동)                    |
| [BL-074](#bl-074) | Beta 인터뷰 3명 × 3회 (narrowest wedge 60% 검증)                                               | BL-073 후 + Beta 5~10명 onboarding 시 | L (사용자 수동, 9 interview slots) |
| [BL-075](#bl-075) | H2 진입 게이트 설계 (`/office-hours` Q4 narrowest wedge + Monte Carlo / Walk-Forward 우선순위) | BL-005 self-assessment ≥ 7/10 직후    | M (3-5h)                           | TODO.md L658 |

---

## Cross-reference

### ADR ↔ Backlog

| ADR                                                                                      | 미해소 BL                                                                                                                                                           |
| ---------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [ADR-005](dev-log/005-datetime-tz-aware.md) DateTime tz-aware                            | (Sprint 5 backfill 완료, 잔여 없음)                                                                                                                                 |
| [ADR-011](dev-log/011-pine-execution-strategy-v4.md) Pine Execution v4                   | BL-040 (Path γ), BL-041 (Path δ)                                                                                                                                    |
| [ADR-013](dev-log/013-trust-layer-ci-design.md) Trust Layer CI                           | BL-026 (skip 활성화 회귀), BL-023 (KIND-B/C 정밀도)                                                                                                                 |
| [ADR-016](dev-log/016-sprint-y1-coverage-analyzer.md) Coverage Analyzer                  | BL-037 (AST 정밀화)                                                                                                                                                 |
| [ADR-018](dev-log/018-sprint12-ws-supervisor-and-exchange-stub-removal.md) WS Supervisor | BL-001 (submitted watchdog), BL-011/012 (Redis lease + prefork), BL-013 (auth circuit breaker), BL-014 (partial fill), BL-015 (OKX WS), BL-016 (first_connect race) |

### Lessons ↔ Backlog

| LESSON                                                     | 미해소 BL                                           |
| ---------------------------------------------------------- | --------------------------------------------------- |
| LESSON-019 (commit-spy 회귀 의무화)                        | BL-010 (도메인 확장)                                |
| LESSON-004 (CPU 100% set-state-in-effect)                  | BL-018 (loading/error UX 추가 시 LESSON-004 재확인) |
| LESSON-007/008/009 (autonomous-parallel-sprints BUG-1/2/3) | BL-025 (스킬 patch)                                 |

### Test Skip 추적표 ↔ Backlog

[`docs/TODO.md` "Test Skip / xfail 추적표"](TODO.md) 의 dette 2 건이 백로그로 이관:

| Skip #                | 위치                                                 | BL ID                |
| --------------------- | ---------------------------------------------------- | -------------------- |
| #1                    | `tests/backtest/engine/test_golden_backtest.py:19`   | BL-022               |
| #16                   | `tests/strategy/pine_v2/test_mutation_oracle.py:213` | BL-023               |
| #4-7, #9-15 (12 skip) | `tests/strategy/pine_v2/test_*.py`                   | BL-026 (활성화 회귀) |

---

## 운영 규약

### 신규 항목 추가

1. 적절한 priority 결정 (P0~P3 정의 표 참조)
2. 다음 BL ID 부여 (현재 사용 범위: BL-001~005, BL-010~026, BL-030~043, BL-050~057, BL-070~075)
3. 표준 8 필드 모두 채우기: ID / 제목 / 카테고리 / priority / trigger / est / 출처 / 권장 접근
4. 출처 cross-link (파일:라인 또는 dev-log 파일명) 필수
5. 의존성 있으면 명시 (다른 BL ID 또는 외부 자원)
6. CLAUDE.md / dev-log / TODO.md 의 자연어 표현 옆에 ` → BL-XXX` cross-link 추가

### 항목 해소

1. 해당 BL 절에 `**Status:** ✅ Resolved (2026-XX-YY, PR #NN)` 추가
2. 출처 (CLAUDE.md / TODO.md) 의 cross-link 옆에 `(✅ Resolved BL-XXX)` 표기
3. **삭제하지 말 것** — 회귀 시 출처 추적 가치. "변경 이력" 섹션에 한 줄 기록

### Trigger 도래 확인

신규 sprint 진입 시:

1. 본 문서 P0 섹션 전체 review — trigger 도래 항목이 있는가?
2. P1~P2 섹션의 trigger 도 함께 review (예: "2 계정 이상 dogfood 진입 시" → 현재 1 계정인가?)
3. 도래 항목이 있으면 active TODO.md 의 "Next Actions" 로 승격 + 본 문서에서 `**Status:** 🟡 In progress (Sprint NN)` 마킹
4. 신규 발견 follow-up 은 본 문서에 BL-XXX 로 우선 등록 후, 즉시 처리할 것만 active TODO 로

---

## 변경 이력

- **2026-05-04 (dogfood Day 1-7 / Sprint 27 launch)** — `stage/h2-sprint27-dogfood-day1` PR #102 (docs-only).
  - **신규 등록 (5건)**: BL-137 (P2 신규 strategy trading settings UI), BL-138 (P3 list inline `·` 일관성), BL-139 (P3 detail aggregation scope), BL-140 (P2 LiveSignalDetail equity curve chart), BL-141 (P2 Backtest UI 활성화 + ts.ohlcv backfill).
  - **출처**: `docs/dev-log/2026-05-04-dogfood-day1-sprint27-launch.md` (4 commits 누적 — Day 1 / Day 2 + L-S27-2 / Day 3 + multi-account / Day 4-7 압축).
  - **합계**: 76 → 81 BL (5 신규, 0 Resolved).
  - **LESSON 후보 2건** — L-S27-1 multi-schema 인지 (`pg_tables` schemaname IN), L-S27-2 innerText 단독 UI bug 결정 금지 (screenshot cross-check 의무). 둘 다 `.ai/common/global.md` 승격 후보.
  - **Auto-Loop §0.5 첫 실측**: 4 cycle 무중단 + 사용자 prompt 5개 + 0 production blocker + 26h+ infrastructure 무결.

- **2026-04-30** — 초기 작성. CLAUDE.md / TODO.md / dev-log/2026-04-\* / docs/superpowers/plans 4 곳에서 47 follow-up 통합 + Phase 1 architecture-conformance audit TBD 2 건 (BL-010, BL-050) 등록 = **총 50 BL (P0 5 + P1 17 + P2 14 + P3 8 + Beta 6)**. 중복 4 건 통합 (WebSocket 안정화 4 곳 → BL-001/011/012/013/014/015/016 분리, Bybit infra 3 곳 → BL-003 통합, Backtest UX 422 inline 은 Sprint 13 완료로 등록 X, OrderService broken bug 는 Sprint 13~14 hotfix 완료 — Day 2 stuck pending 잔여 BL-002 만).

- **2026-05-01** — Sprint 15 (`stage/h2-sprint15`) 결과 반영.
  - **Resolved**: BL-001 (submitted watchdog), BL-002 (Day 2 stuck pending cleanup) — `docs/dev-log/2026-05-01-sprint15-watchdog.md`. 1216 BE tests / mypy 0 / ruff 0.
  - **신규 등록 (Sprint 15 codex G.2 + scope minimization 결과)**:
    - **BL-027** WS state_handler.py:176 unconditional `qb_active_orders.dec()` + reconciliation.py:182 dec 누락 — codex G.2 P1 #3 분리, Sprint 15 watchdog 가 worse 만들지 않음 확인. trigger: Sprint 16 직후 cleanup. est M (3-4h)
    - **BL-028** `scripts/force-reject-stuck.py` — submitted+null exchange_order_id manual cleanup (codex G.0 P1 #3 잔존 surface). trigger: submission_interrupted alert 발화 시. est S (1-2h)
    - **BL-029** provider.fetch_order CCXT rate limit Redis throttle middleware — Sprint 15 watchdog 가 retry 마다 fetch_order 호출. dogfood 1-user 영향 적지만 BL-005 (1-2주 dogfood) 완료 후 점검. trigger: rate limit alert 다발 시. est M (3-4h)
  - **합계 변동**: 50 → 53 BL. P0 잔여 3 (BL-003/004/005). P1 잔여 17 (변동 없음, BL-010 trigger 도래 — Sprint 16 우선). P2 신규 3 (BL-027/028/029).

- **2026-05-01 (Sprint 16)** — `stage/h2-sprint16` 결과 반영.
  - **Resolved**:
    - **BL-027** WS state_handler / reconciliation / tasks/trading dec winner-only commit-then-dec — codex G.0 P1 #1 (silent corruption: dec 가 commit 전 발화) + P1 #2 (scope 누락: `tasks/trading.py:165/200/253` 의 \_async_execute rejected 분기) 모두 fix. Sprint 15 watchdog `tasks/trading.py:458` 표준 패턴 (rows==1 → commit → dec) 3 path 통일. 신규 15 tests. 커밋 `a3d4a20`.
    - **BL-010** commit-spy 도메인 확장 — 4 도메인 (Strategy / Backtest / Waitlist / StressTest) backfill 11 spy. codex G.0 audit 결과 5 도메인 모두 commit 호출 OK = broken bug 0건 confirmed. Optimizer 는 H1 미구현 → 별도 BL. 커밋 `beacc89`.
  - **codex 게이트**:
    - **G.0** (medium, iter cap 2) — P1 #1 silent corruption + P1 #2 scope 누락 + Phase B broken bug 0건 confirm. 426k tokens. iter 1 만으로 종료.
    - **G.2** (high, iter cap 2) — 6 break vector 검토 (silent rollback / SQLAlchemy lazy flush / 변수 shadowing / spy false negative / pytest fixture / OrderState fallthrough). **P1 critical 0건** confirm. 515k tokens. iter 1 만으로 종료.
  - **신규 등록** (Optimizer 구현 시점에 추가): Optimizer commit-spy backfill (BL-010 의 5번째 도메인, H1 구현 후).
  - **합계 변동**: 53 BL. P0 잔여 3 (BL-003/004/005). P1 잔여 16 (BL-010 ✅). P2 잔여 2 (BL-028/029, BL-027 ✅). dev-log: [`docs/dev-log/2026-05-01-sprint16-phase0-live-and-backfill.md`](dev-log/2026-05-01-sprint16-phase0-live-and-backfill.md).

- **2026-05-02 (Sprint 21 BE+FE)** — `stage/h2-sprint21` 결과 반영.
  - **Resolved**:
    - **BL-093** TestOrderDialog success confirmation — toast description 에 broker order id slice / idempotency_key fallback. + OrdersPanel 7번째 컬럼 `Broker ID` + `<BrokerBadge>` (fixture-\* 오렌지 mock vs broker 녹색 시각 분기).
    - **BL-095** Backtest 422 inline detail — backend 422 shape `{detail:{code,detail,unsupported_builtins:list[str]}}` 표준화 (Phase A.0). FE friendly hints inline 카드 + edit link (Phase D). `unsupported-builtin-hints.ts` 신규 mapping table.
    - **BL-097** (신규+Resolved) interpreter alias ordering correctness — `_eval_call` 시작 직후 user_functions 우선 dispatch + `"." not in name` guard. 사용자 `abs(x) =>` / `max(a,b) =>` 정의 시 v4 alias 압도 차단 (Sprint 8c 의 silent correctness bug 해소). codex G.0 P1 #1+#4.
    - **BL-096 Partial** — coverage.py supported list 확장 (V4 alias 8 + 2 explicit constant frozenset (currency 12 / strategy_extra 6) + study NOP). RsiD 통과 (8 unsupported 모두 fix). UtBot×2 잔존 (heikinashi/security Trust Layer 정합 의도, codex G.0 P1 #2). DrFX scope (Sprint 22+).

  - **신규 등록 (codex G.2 challenge P1 — Sprint 21 무관 pre-existing)**:
    - **BL-098** `strategy.exit` coverage/interpreter parity — coverage.py:40 supported 인데 interpreter `_eval_call` dispatch 미구현. preflight pass 후 runtime fail risk. P1. est S (1h).
    - **BL-099** `vline` coverage/interpreter parity — coverage.py:52 `_PLOT_FUNCTIONS` supported 인데 interpreter `_NOP_NAMES` 미포함. P1. est S (30m).
    - **BL-100** `timeframe.*` runtime NOP — Sprint 21 v2 plan 에서 추가했으나 G.2 P1 #1 발견 (interpreter `_eval_attribute` 미구현 = silent corruption risk). 본 Sprint 에서 `_TIMEFRAME_CONSTANTS` 빈 frozenset 으로 회수. interpreter NOP 추가 또는 strict toggle 설계 후 supported 전환. P2. est M (2-4h).

  - **codex 게이트**:
    - **G.0 round 1** (medium, 397k tokens) RETHINK + P1 9건. round 2 (medium, 254k tokens) GO_WITH_FIXES + 신규 P1 0건.
    - **G.2** (high, 808k tokens) GO_WITH_FIXES + 신규 P1 3건. #1 즉시 fix (timeframe 회수). #2/#3 BL 분리.
    - **G.5 self-checklist**: 자동 검증 ✅. 라이브 RsiD 검증 + self-assessment 8 → 9 = Phase H 후속.

  - **누적**: BE +38 신규 tests (385+/0/16 skip), FE +8 신규 tests (251/0). ruff/mypy/tsc/eslint 0/0/0/0. Sprint 8c 388 회귀 PASS. SLO: 본인 6 pine 통과율 33% → 50% (3/6, +1 RsiD).
  - **Self-assessment 본질** (codex G.0 free-2): 통과율 절대값 < 신뢰. alias ordering correctness fix + backend shape 표준화 + Trust Layer 정합 = trust ↑ (Phase H 라이브 검증 후 8 → 9 측정).
  - **합계 변동**: 67 BL (BL-093/095/097 ✅ Resolved, BL-096 Partial Resolved + BL-098/099/100 신규 3).
  - **dev-log**: [`docs/dev-log/2026-05-02-sprint21-bl096-coverage-expansion.md`](dev-log/2026-05-02-sprint21-bl096-coverage-expansion.md).

- **2026-05-02 (Sprint 17)** — `stage/h2-sprint17` 결과 반영.
  - **Phase 0 라이브 검증 발견**: Sprint 15 watchdog (BL-001) 6h 동안 **141/141 silent fail** + Sprint 12 reconcile_ws_streams 6h **18/35 fail**. Root cause: module-level cached AsyncEngine + Celery prefork 의 asyncio.run() 새 loop 가 SQLAlchemy/asyncpg connection pool loop binding mismatch. self-assessment 2/10 = Path C emergency.
  - **Partial fix (Phase A+B+C)**: orphan_scanner.py / websocket_task.py / tasks/trading.py 모두 module-level singleton 제거 + per-call `create_worker_engine_and_sm()` + finally `engine.dispose()` (backtest.py:31 mirror). 신규 19 tests + 회귀 fix (test_celery_task / test_fetch_order_status_task / test_orphan_scanner). ruff 0 / mypy 0. **1st task / child success** 검증.
  - **잔존 P1 (라이브 검증으로 Phase 4.5 architectural problem 발견)**: 같은 child 의 2nd+ task 가 RuntimeError "attached to a different loop" / InterfaceError 재발. SQLAlchemy/asyncpg 의 process-level state (dialect cache 등) 가 stale loop Future 보유. `worker_max_tasks_per_child=1` 효과 약함 (broker prefetch + max 도달 전 multi-task).
  - **codex 게이트**:
    - **G.0** (medium, iter cap 2) — P1 #1 (trading.py wedge 확장) + P1 #2 (real DB integration test 필수) + P1 #3 (BaseException dispose) 모두 발견. wedge 확장 = 사용자 재결정 채택. 219k tokens. iter 2 codex resume empty 응답.
    - **G.2 challenge** skip — 시간 제약 + master plan 자체가 narrowest wedge + 잔존 P1 codex G.0 가 예측 (asyncio.run 두 번 연속 fail).
  - **신규 등록**:
    - **BL-080** scan/reconcile/trading prefork-safe **architectural fix** (asyncpg/SQLAlchemy module-level state reset). Sprint 17 의 narrowest wedge 한계. Sprint 18 우선. trigger: self-assessment 5 → ≥7. est L (1-2일).
  - **self-assessment**: 2/10 → **5/10** (+3 진전). H1→H2 gate (≥7) 미통과 — Sprint 18 BL-080 root fix 후 재평가.
  - **합계 변동**: 54 BL. P0 잔여 3. P1 잔여 17 (BL-080 신규). P2 잔여 2. dev-log: [`docs/dev-log/2026-05-02-sprint17-prefork-fix.md`](dev-log/2026-05-02-sprint17-prefork-fix.md).

- **2026-05-03 (Sprint 25 Hybrid)** — `stage/h2-sprint25` 결과 반영. Frontend E2E Playwright + Backend test 강화 + codex G.0/G.2.
  - **Resolved (5건)**:
    - **BL-110a** In-process lease integration test (heartbeat / lost_event / lease contention) — `tests/tasks/test_ws_lease_integration.py` 7 시나리오 (acquire / duplicate None / 격리 / extend True 정상 / extend False → lost_event.set / extend Exception → lost_event.set / **aexit** Lua CAS DEL). codex G.0 iter 2 P1 #8 + G.2 P1 #2 모두 반영. autouse `_reset_pool_each_test` fixture 로 pytest-asyncio per-test event loop + redis-py asyncio connection bound 충돌 회피.
    - **BL-112** scenario2 실 backtest 실행 — `make_trending_ohlcv` (8 segments × 25 bars = 200 bars, EMA 3/8 cross 3 회 발생 코드 실측 보장) + `EMA_CROSS_PINE_SOURCE` + precondition test (num_trades >= 3). scenario2 강한 assert (status=='ok' + result + equity > 0 + num_trades >= 1). codex G.0 iter 2 P1 #5+#6 반영 (plan v2 의 "기존 fixture 재사용" 가설 코드 실측으로 refuted).
    - **BL-113** scenario3 OrderService.execute 정확한 args — `OrderService(session=db_session, repo=OrderRepository(db_session), dispatcher=_FakeOrderDispatcher(), kill_switch=_NoopKillSwitch(), exchange_service=ExchangeAccountService(...))`. uuid4 idempotency_key per test. dispatch_snapshot 자동 채움 검증 + provider 정합성 검증. codex G.0 iter 2 P1 #7 (`repo=` param 이름) + iter 1 P2 #1 (uuid4) + iter 2 P1 #10 (FakeOrderDispatcher Celery 우회) 반영.
    - **BL-114** pytest-json-report 도입 — `importlib.util.find_spec('pytest_jsonreport')` plugin detect first. `_build_summary(rc, stdout, stderr, json_report=None)` backward compat (scenario6 호환). plugin 부재 시 graceful fallback. codex G.0 iter 2 P1 #9 (pytest CLI behavior 정확화) 반영.
    - **BL-115** HTML escape full coverage — `html.escape` 전수 적용 (stdout_tail / stderr_tail / table cells / 헤더 date / counts). `tests/scripts/test_run_auto_dogfood_html_escape.py` 3 회귀 unit test (`<script>` 주입 / `<img onerror>` / safe content 정상 렌더).
  - **신규 등록 (Sprint 26+ 이관, 14건)** — codex G.0 iter 2 + G.2 P2/P3 결과:
    - **BL-110b** Real Celery prefork SIGTERM integration test — pytest-celery 또는 subprocess.Popen worker. P2 M (4-6h). plan v3 split.
    - **BL-116** CI workflow_dispatch authed E2E — secret + storageState decode. P2 S (2-3h).
    - **BL-117** Clerk emailAddress 방식 마이그레이션 (password → emailAddress, MFA/verification 우회 회피). P2 S (1-2h). codex G.2 P2 #1.
    - **BL-118** baseURL 통합 (config + setup) — playwright.config.ts baseURL 단일 source. P3 S. codex G.2 P2 #2.
    - **BL-119** API_ROUTES URL predicate (orders-v2 false-match 차단) — route handler pathname predicate. P3 S. codex G.2 P2 #3.
    - **BL-120** leak guard fail-on-leak (현재 observability only, afterEach assert). P2 S (2h). codex G.2 P2 #4.
    - **BL-121** production guard host allowlist (NODE*ENV 외 PLAYWRIGHT_BASE_URL host + pk_test*/sk*test* prefix). P2 S. codex G.2 P2 #5.
    - **BL-122** pytest-json-report uv-aware detect (`uv run python -c` 기반). P3 S. codex G.2 P2 #6.
    - **BL-123** mkstemp fd leak fix (NamedTemporaryFile or os.close(fd)). P3 XS. codex G.2 P2 #7.
    - **BL-124** run_auto_dogfood subprocess timeout — DB/Redis hang cron 무한 대기 차단. P2 XS. codex G.2 P2 #8.
    - **BL-125** report 파일명 timestamp + symlink — 동시 실행 overwrite 차단. P3 S. codex G.2 P2 #9.
    - **BL-126** FakeOrderDispatcher edge case (broker outage / dispatch exception / pending stuck). P2 M. codex G.2 P2 #10.
    - **BL-127** BL-110a xdist 격리 (pool reset autouse fixture serial marker 또는 isolated Redis DB/key namespace). P3 S. codex G.2 P2 #11.
    - **BL-128** trading-ui scenario 3 KS bypass disabled assert — OrdersPanel 주문 버튼 추가 후 활성화. P2 XS. codex G.2 P1 #4 (partial).
    - **BL-129** ANSI/control seq HTML 처리 (XSS 아님, 가독성). P3 XS. codex G.2 P3 #2.
  - **codex 게이트**:
    - **G.0 iter 1** (medium, 617k tokens) — P1 14 + P2 10 + P3 4 → plan v2 surgery 28건 모두 반영.
    - **G.0 iter 2** (medium, 1.28M tokens, resume) — plan v2 NOT READY 판정 (코드 실측 까지 진행). P1 9 + P2 8 + P3 4 → plan v3 surgery 21건 (Clerk auth wrong / BL-112 fixture 가설 refute / OrderService param 이름 / heartbeat exception path / pytest CLI behavior / mock URL prefix 등).
    - **G.2 challenge** (high, 992k tokens) — P1 4 즉시 fix + P2 12 + P3 2 = BL-117~129 신규 등록. P1 critical 0 잔존.
    - **누적**: ~3M tokens / 47 finding 모두 plan v3 또는 implementation 반영.
  - **사용자 명시 요구 반영**: (1) Edge Cases 19 영구 기록 (plan v3 §5.5 + dev-log §3) — 사용자 "엣지케이스가 없는지" 요구. (2) codex G.0 iter 2 재호출 — 사용자 "codex 잘 확인한거야?" 요구 (Sprint 22+24a 의 G.0 1 iter 만 패턴 보강).
  - **합계 변동**: 67 → 76 BL (5 Resolved + 14 신규 = 9 net 증가). P1 잔여 동일. P2 신규 7. P3 신규 7. dev-log: [`docs/dev-log/2026-05-03-sprint25-hybrid.md`](dev-log/2026-05-03-sprint25-hybrid.md). plan: `~/.claude/plans/claude-plans-h2-sprint-25-prompt-md-snappy-bee.md` (v3, ~770 lines + Edge Cases 19).

- **2026-05-05 (Sprint 32 진입 — Surface Trust Recovery)** — `~/.claude/plans/giggly-exploring-marshmallow.md` plan 승인. dogfood Day 4 = 5/10. codex `019df68f` 풀 scope 분기. 신규 등록 11건 (BL-156/163/164/166/168~174). 합계 76 → 87. handoff [`docs/dev-log/2026-05-05-sprint31-day4-handoff.md`](dev-log/2026-05-05-sprint31-day4-handoff.md).

- **2026-05-05 (Sprint 32 종료 — 7 PR all merged)** — `main @ f17421d`. dogfood Day 5 = **6~7/10 (borderline)** = +1.5~2 점 progress (Day 3=4 → Day 4=5 → Day 5=6~7). Sprint 33 분기 = **6.5 양다리 (polish 잔여 + Beta 인프라 BL-070 prep 병행)**.
  - **Resolved (7건, 6 BL + 2 gate spec PR)**: BL-168 (PR #134) / BL-169+170 (PR #133) / BL-156 (PR #136) / BL-163 (PR #135) / BL-171+172 (PR #138). 추가 PR #137 (sprint32-dogfood-gate.spec.ts) / PR #139 (gate §4 axis labels unblock).
  - **codex G.0 P1 4건 surgery 적용** (Verdict GO): BL-168 ownership (root Makefile + migrate-isolated 신규) / BL-157 live-smoke 과신 보완 (Sprint 32 dogfood gate 신규) / Worker B/C 충돌 해소 (B 선행 → C MarkerLayer rebase) / BL-172 P1 확정.
  - **dogfood Day 5 = 6~7 borderline** — Surface fix 효과 / sprint = 1.5 점 (Sprint 31 = 1, Sprint 30 = 0). gate ≥7 잠정 통과 + 1주 안정 검증 의무.
  - **Partial Resolved**: BL-005 (1주 안정 검증 후 final) / BL-150 (EquityChartV2 만, recharts 잔존).
  - **자율 병렬 worker isolation 위반 lesson**: Worker C/D 가 메인 worktree branch swap (자체 worktree 에서 cd 로 메인 이동 + push). prompt 명시 만으론 부족 → tooling 강화 (pre-push hook worktree path 검사) Sprint 33+ 후보.
  - **Sprint 33 BL 후보**: BL-164 / BL-166 / BL-174 / BL-150 / BL-070~072 점진 prep / 일별 dogfood self-assess Day 6+
  - **합계 변동**: 87 → 80 BL (7 Resolved). 상세: [`docs/dev-log/2026-05-05-sprint32-master-retrospective.md`](dev-log/2026-05-05-sprint32-master-retrospective.md).

- **2026-05-05 (Sprint 33 종료 — 7 PR all merged + dogfood Day 6 hotfix 2건)** — `main @ 06f5512`. dogfood Day 6 = **TBD (사용자 입력 대기, Day 5 = 6~7 borderline 후속, BL-175 + BL-176 hotfix 후 재측정)**. Sprint 34 분기 = dogfood Day 6 결과 따라 결정 (≥7 → Beta 본격 진입 / 6~7 유지 → polish iter 2).
  - **Resolved (1건)**: BL-164 (PR #143, live-session-form SelectWithDisplayName helper). pre-push hook tooling 신규 (PR #141, **자율 병렬 worker isolation 영구 차단** — Sprint 32 lesson 즉시 적용).
  - **Partial / Follow-up required**: BL-150 (PR #145, Activity Timeline 만 — walk-forward+monte-carlo Sprint 34 defer) / BL-071 audit (PR #142, runbook 393 lines + Sprint 34 unresolved gap 16건) / BL-174 (PR #144, list-only — detail 분기 Sprint 34 defer).
  - **dogfood Day 6 발견 BUG hotfix (PR #146 BL-175)**: `computeBuyAndHold` 가 `initialCapital * (last_equity / first_equity)` 로 BH 계산 → strategy line 과 거의 동일 → legend 와 chart 데이터 mismatch (Sprint 30 ADR-019 Surface Trust 위반). 자본 초과 손실 시 BH 도 음수. 임시 mitigation: 빈 배열 반환 → BH series 미렌더 + ChartLegend BH 항목 자동 hide.
  - **dogfood Day 6 발견 BUG hotfix (PR #147 BL-176)**: Worker B BL-164 PR #143 의 `SelectWithDisplayName.handleValueChange` 가 base-ui `null → ""` 변환 → form zod UUID schema reject → Runtime ZodError (`exchange_account_id: invalid_format`). hotfix: `v=null` 시 callback skip → form prior valid value 보존.
  - **신규 등록 BL-175** (P1, Sprint 34 fix prereq): Buy & Hold 정확 계산 (backend `BacktestMetrics.buy_and_hold_curve` 신규 + OHLCV 첫/끝 가격 기반 `initialCapital * (last_BTC_price / first_BTC_price)` + frontend 자체 계산 폐기). est M (3-4h).
  - **신규 등록 BL-176** (P2, Sprint 33 hotfix Resolved + Sprint 34 follow-up): SelectWithDisplayName clear 동선 정합화 (현재 v=null skip = silent. 의도적 unset 동선 추가 시 form 측 nullable schema 또는 별도 clear button 필요). est S (1-2h).
  - **신규 등록 BL-177** (P2, Sprint 34 — dogfood Day 6 발견): `/backtests/[id]` chart marker readability — Sprint 32 BL-171 MarkerLayer 가 trade marker 너무 많을 때 (157+ trades 검증) text 겹쳐 읽을 수 없음. zoom 영역 따라 marker count limit / cluster / text shorten ("S"/"L" 만) 또는 hover tooltip 으로 detail 분리. est M (3-4h).
  - **codex G.0 P1 surgery 3건 적용** (session `019df729`, 124k tokens, Verdict GO_WITH_FIXES): P1-1 hook 선행 (D 삭제 → 메인 step 0) / P1-2 BL-071 scope 재정의 (dry-run+runbook → topology gap audit + Sprint 34 unresolved gap 16건) / P1-3 scope 정직화 (필수 3 BL + stretch 3 BL, BL-150 kill criterion, Resolved → Partial).
  - **codex G.0 운영 규칙 갱신**: P1 surgery ≤1건 한도 = 잘못된 운영 규칙 (codex challenge). 제거. iter cap 2 만 유지. memory feedback `feedback_codex_g0_pattern.md` 갱신 완료.
  - **자율 병렬 worker isolation 영구 차단 검증**: main worktree branch swap **0건** (Sprint 32 = 2건 → Sprint 33 = 0건). pre-push hook hybrid (reject + bypass env) + 메인 세션 step 0 선행 패턴 효과 검증.
  - **defer Sprint 34**: BL-166 (root cause = uvicorn watch list `.env*` 미포함, plan 가정 noop 검출) / BL-070~072 (도메인+DNS 사용자 manual prereq) / BL-150 잔여 (walk-forward+monte-carlo) / BL-174 detail / BL-175 본격 fix.
  - **lesson 후보**: plan agent 가정 검증 필수 (BL-166 plan 가정 noop). codex 운영 규칙 challenge 가능 (P1 ≤1건 한도 잘못 판정). **dogfood = critical BUG 발견 mechanism** (BL-175 — production-quality 검증의 마지막 gate).
  - **합계 변동**: 80 → 80 BL (BL-164 Resolved 1 + BL-175 신규 1 + Partial 3 + tooling 신규 1 BL ID 미부여). 상세: [`docs/dev-log/2026-05-05-sprint33-master-retrospective.md`](dev-log/2026-05-05-sprint33-master-retrospective.md).

- **2026-05-05 (Sprint 34 종료 — 3 PR all merged + mid-dogfood Day 6.5 PASS)** — `main @ 27ff836`. dogfood Day 7 = **TBD (사용자 입력 대기)**. Sprint 35 분기 = Day 7 결과 따라 결정 (≥7 → Beta 본격 진입 BL-070~072 / <7 → polish iter 3 BL-178 + BL-179 + BL-176 follow-up + BL-174 detail + BL-177-A/B/C). **[Sprint 35 retroactive 정정 2026-05-05 office-hours]**: "≥7 → Beta 본격 진입" = **fictitious gate** detection (BL-005 자체 skip). 정정 후 = "Day 7 4중 AND gate 통과 → Sprint 36 BL-003 mainnet runbook + BL-005 본격 (1-2주 mainnet 소액). Beta 본격 진입 (BL-070~075) = BL-005 통과 후 별도 trigger". 상세 = Sprint 35 transition entry.
  - **Resolved (2건)**: BL-175 (PR #150 본격 fix, codex P1-1+P1-2+P1-3 모두 적용 — backend `BacktestMetrics.buy_and_hold_curve` 신규 + 2-stage fail-closed gate + service spread + FE wiring + 8 backend test). BL-177 partial (PR #149 dense text shorten only — codex P1-4 scope 축소, visible-range/tooltip/cluster Sprint 35+ 분리).
  - **Cancel (kill K-2)**: BL-166 (Sprint 33 lesson #7 본 sprint 직접 적용) — Makefile `--reload-include "*.env*"` 추가 후 사후 검증 FAIL (`Reloading` log 미발생). 추정 root cause = `*.env*` glob 이 `.env.local` (leading dot file) 미매치 또는 watchfiles default hidden file ignore. Makefile rollback + branch 폐기 (push 0) + retro 안 noop 발견 lesson 기록.
  - **mid-dogfood Day 6.5 PASS** (Sprint 33 lesson #1 본 sprint 직접 적용 검증) — Playwright MCP 자동화 (Clerk JWT 발급 + backend 직접 fetch + 화면 snapshot) + 사용자 dogfood 분담. 3 backtest numeric 검증. 회귀 0건 + 검증 #6 legacy backward-compat PASS (BH null → 미렌더 + Legend hide 시각 검증) + 검증 #7 P1-3 fail-closed PASS.
  - **codex G.0 P1 surgery 6건 모두 적용** (session `019df7cc`, medium tier, iter cap 2, 327k tokens, Verdict GO_WITH_FIXES) — Sprint 33 lesson #2 (codex P1 한도 제거) 정합. P1-1 FE wiring 누락 (R-0, plan 가장 큰 hole) / P1-2 service.py 회귀 테스트 (R-2 silent BUG 차단) / P1-3 fail-closed 정책 (invalid close 1건 → None) / P1-4 BL-177 scope 축소 / P1-5 K-4 fallback 변경 / P1-6 mid-dogfood numeric fixture 7항목.
  - **신규 등록 BL-177-A** (P2, Sprint 35+): visible-range subscription + zoom-aware count (TradingChart wrapper API 의무 — `marker-layer.tsx` 권한 외). est M (3-4h).
  - **신규 등록 BL-177-B** (P2, Sprint 35+): hover tooltip overlay (`MarkerTooltipOverlay` hook + ChartMarker payload 설계 + `subscribeCrosshairMove` 콜백). est M (3-4h).
  - **신규 등록 BL-177-C** (P3, Sprint 35+): cluster (인접 markers → 1 cluster, click expand). lightweight-charts 4.x native 미지원 → 자체 구현 의무. est M (3-4h).
  - **신규 등록 BL-178** (P2, Sprint 35+): production OHLCV invalid close root cause 분석 + fix. mid-dogfood Day 6.5 발견 — 3 backtest 모두 `metrics.buy_and_hold_curve = null` (P1-3 fail-closed gate trigger). 가능성: TimescaleDB BTC/USDT 일부 bar 누락 close NaN / dtype 변환 NaN 그대로. Surface Trust 차단 작동 (가짜 data 표시 risk 0), 단 정확한 BH 표시 미달성. est M (3-4h).
  - **신규 등록 BL-179** (P3, Sprint 35+): uvicorn watchfiles `.env*` 감지 root cause + fix (Sprint 34 BL-166 kill K-2 발동 후속). 추정 = `--reload-include "*.env*"` glob 이 `.env.local` (leading dot file) 미매치. 다른 glob (`.env*` / `**/*.env*` / `--reload-dir backend`) 시도 + watchfiles version 검증. est S (1-2h).
  - **자율 병렬 worker isolation 영구 차단 검증 (2 sprint 연속)**: main worktree branch swap **0건** (Sprint 32 = 2건 → Sprint 33 = 0건 → Sprint 34 = 0건). pre-push hook hybrid 효과 검증. Worker A 12분 (748s, 184k tokens) / Worker B 6분 (363s, 92k tokens).
  - **lesson 후보**: kill K-2 (BL-166) plan 가정 사후 검증 FAIL → cancel + BL 분리 패턴 (Sprint 33 lesson #7 본 sprint 직접 적용 사례) / production OHLCV fail-closed gate (BL-178) production 환경 정상 발동 / Playwright MCP + 사용자 dogfood 분담 효율적 패턴 (Clerk JWT `window.Clerk.session.getToken()` → backend 직접 fetch + snapshot 시각 검증).
  - **defer Sprint 35+**: BL-176 follow-up (silent — SelectWithDisplayName clear 동선 정합화) / BL-174 detail (silent — live-session-detail Empty/Failed/Loading) / BL-150 잔여 (walk-forward + monte-carlo lightweight-charts native 미지원) / BL-070~072 (도메인 + DNS + Resend, 사용자 manual prereq).
  - **합계 변동**: 80 → 86 BL (BL-175 Resolved 1 + BL-177 partial Resolved 1 + BL-166 Cancel + 신규 5 = +5 net). 상세: [`docs/dev-log/2026-05-05-sprint34-master-retrospective.md`](dev-log/2026-05-05-sprint34-master-retrospective.md).

- **2026-05-05 (Sprint 35 진입 — office-hours session 2026-05-05 결정 + codex G.0 iter cap 2 도달)** — `main @ 78fb39b` (PR #152 office-hours dev-log squash merge). Sprint 35 = **Wedge A backtest 단독 정밀화 (polish iter 3)** + Day 7 4중 AND gate. office-hours session 의 P3 fictitious gate detection 결과 영구 반영.
  - **Active (Mandatory + Stretch 구조, codex P1-7 surgery)**:
    - Mandatory: BL-178 root cause + fix (Path A reject/quarantine + observable reason 또는 Path B escape) / **BL-180 신규 = backtest engine golden oracle (hand-computed minimal 2 strategy + tiny OHLCV + checked-in JSON expected)** / mid-dogfood 4a 6항목 / retro
    - Stretch: BL-180 dogfood snapshot integration oracle (1.5b) / BL-176 SelectWithDisplayName clear button prop (sentinel/nullable X, schema required 유지) / BL-150 잔여 walk-forward = 기존 `stress_test` API/UI wiring 만
  - **신규 등록 BL-180** (P1, codex G.0 P1-3 finding): backtest engine golden oracle. circular oracle 함정 회피 = engine 외부 hand-computed minimal strategy + tiny OHLCV + checked-in JSON expected (entries/exits/equity/BH curve). `BacktestConfig(fees=0, slippage=0)` 명시 pin (codex iter2-P1-1 surgery). category = "Test infra / Golden / Fixture". Trigger = Sprint 35 Slice 1.5a 진입. Est = M (3-4h).
  - **codex G.0 master plan validation 누적 1.34M tokens, surgery 18건** (session `019df85d-bcbf-7d63`, medium tier, model_reasoning_effort=high, iter cap 2 도달):
    - iter 1 (862k tokens, P1=7/P2=7): vectorbt native premise 폐기 (P1-4) / BL-180 circular oracle 회피 = hand-computed (P1-3) / Slice 1.5 sequencing 독립 (P1-6) / mandatory + stretch 구조 (P1-7) / Path B escape → Day 7 (b) FAIL/UNKNOWN (P1-2) / Slice 2 schema required 유지 (P1-5) / 6항목 진단 query (P1-1) + reject/quarantine policy (P2-2) + Worker write-set (P2-4) + named assertion (P2-5) + Day 7 (d) 강화 (P2-7)
    - iter 2 (482k tokens, P1=2/P2=5): hand oracle JSON checked-in + 0-based index + BacktestConfig pin (iter2-P1-1) / quarantine fail-closed propagate = invalid OHLCV typed error 또는 metadata propagate (iter2-P1-2) / resetField → "" assertion (iter2-P2-1) / canonical SQL predicate (iter2-P2-2) / production DB fallback path (iter2-P2-3) / Playwright 3-tier fallback (iter2-P2-4) / **각 PR 안 BACKLOG status 갱신 의무** (iter2-P2-5)
  - **BL-070~075 Beta bundle trigger 정정 (P3 fictitious gate detection)**: 기존 = "BL-005 self-assessment ≥ 7/10 직후 → BL-070~075 Beta 본격". 정정 = "Sprint 35 Day 7 4중 AND gate 통과 → Sprint 36 BL-003 mainnet runbook + BL-005 본격 (1-2주 mainnet 소액). **BL-070~075 Beta 본격 진입 = BL-005 통과 후 별도 trigger**" (Day 7 통과 즉시 Beta 진입 X)
  - **BL-174 status 갱신**: Sprint 35 active (defer Sprint 35+) → **Sprint 36+ defer confirmed** (codex P1-4 정합 — backtest trust root cause 가 아니므로 본 sprint 외)
  - **defer Sprint 36+ confirmed**: BL-174 detail / BL-177-A/B/C / BL-179 (uvicorn watchfiles) / BL-070~075 Beta 본격 (BL-005 통과 후 별도 trigger) / vectorbt native walk-forward + monte-carlo (codex P1-4 발견 = repo 안 path 제거됨)
  - **Day 7 4중 AND gate (codex P1-2 + P2-7 surgery)**: (a) self-assess ≥7 + (b) BL-178 production BH 정상 (Path B escape 시 FAIL/UNKNOWN, free pass X) + (c) BL-180 hand oracle 8 test all GREEN + (d) new P0=0 AND unresolved Sprint-35-caused P1=0 + 기존 deferred P1 명시
  - **합계 변동**: 86 → 87 BL (BL-180 신규 +1). master plan: [`~/.claude/plans/quantbridge-sprint-35-anchored-oracle.md`](../../.claude/plans/quantbridge-sprint-35-anchored-oracle.md). dev-log: [`docs/dev-log/2026-05-05-office-hours-sprint-35-decision.md`](dev-log/2026-05-05-office-hours-sprint-35-decision.md).

- **2026-05-05 (Sprint 35 Slice 1a — BL-178 root cause spike 결과: Docker worker stale 확정)** — `feat/sprint35-bl178-rootcause-spike` 브랜치. Slice 1a 진단 결과 BL-178 = **Docker worker container STALE** (NOT OHLCV NaN/<=0, NOT v2_adapter NaN 도입). codex G.0 surgery 18건 중 3건 wrong premise (P1-1 / P2-2 / iter2-P1-2 quarantine 가설). 11건 valid (BL-180 oracle / vectorbt 폐기 / BL-176 schema / Day 7 gate / Worker write-set / 등). 검증: `make up-isolated-build` 후 BL-175 회귀 test 8/8 GREEN. dev-log: [`docs/dev-log/2026-05-05-bl178-rootcause-spike.md`](dev-log/2026-05-05-bl178-rootcause-spike.md).
  - **BL-178 status 갱신** = **Resolved (worker rebuild)**. Slice 1b "code fix path" / "escape hatch backfill" 모두 N/A. Day 7 (b) gate 자동 PASS prereq.
  - **신규 등록 BL-181** (P1, Sprint 35 active stretch 후보) — Docker worker auto-rebuild on PR merge mechanism. ops gap = `docker-compose.yml` 안 backend-worker `volumes: mount` 부재 = code image 안 baked-in. PR 머지 후 `make up-isolated-build` 의무 = 운영 진행 안 자동화 안 됨 → silent failure (mid-dogfood Day 6.5 시점 stale worker 가 PR #150 BL-175 이전 코드로 task 실행 → BH 계산 함수 자체 부재 → BL-178 false detection). 가능한 fix: (i) docker-compose dev override volumes mount / (ii) GitHub Actions image push + 환경 자동 pull + restart / (iii) Makefile post-merge target 의무 명시 + post-merge git hook. Est M (3-4h).
  - **신규 등록 BL-182** (P2, Sprint 35+ defer 후보) — worker container code version 자동 monitoring + alert. e.g. `_v2_buy_and_hold_curve` 같은 sentinel function 존재 검증 startup health check 또는 git commit hash 비교. Est S (2h).
  - **Sprint 35 master plan footnote 추가** = wrong premise 3건 명시 + Slice 1b cancel + BL-181 active + valid 11건 surgery 유지 + Day 7 (b) 자동 PASS + 4중 AND gate 정합 유지. mandatory scope 재정의 = BL-181 (or 사용자 결정) + Slice 1.5a (BL-180) + Slice 4a + Slice 5
  - **신규 lesson 후보 3건** (Sprint 35 retro 시 `.ai/project/lessons.md` 영구 승격 검토): LESSON-038 (Docker worker auto-rebuild on PR merge 의무) / LESSON-039 (Surface Trust 차단 ≠ 실제 fix 작동, codex BL-180 hand oracle = 본 mechanism 사전 detection 정합) / LESSON-040 (codex G.0 wrong premise risk → rapid prereq verification spike 의무)
  - **합계 변동**: 87 → 89 BL (BL-181 / BL-182 신규 +2). BL-178 Resolved (-1 active). 87 + 2 - 1 = **88 active BL**.

- **2026-05-05 (Sprint 35 종료 — polish iter 3 완료, Day 7 4중 AND gate 미통과)** — `main @ 8df5e58` (4 PR all merged: #152~#155). Day 7 self-assess = **6/10 → gate (a) FAIL**. 4중 AND gate: (a) FAIL / (b) PASS / (c) PASS / (d) 평가 불필요. Sprint 36 = **polish iter 4**.
  - **Resolved (2건)**: BL-178 (Docker worker stale 확정 + `make up-isolated-build` 워크어라운드 완료 — 근본 fix는 BL-181로 분리) / BL-180 (engine golden oracle 8 tests GREEN, PR #155, backend pytest +8)
  - **Slice 4a mid-dogfood 6/6 PASS**: BH curve 첫 정상 렌더링 확인 (isolated env, init_capital=10,000, `bh_curve[0][1] == "10000.00000000"`)
  - **Stretch 전체 미착수**: Slice 1.5b / BL-176 SelectWithDisplayName / BL-150 walk-forward — Sprint 36 재검토
  - **BL-181 status 갱신**: Sprint 35 active stretch → **Sprint 36 P2 (auto-rebuild trigger 우선 구현 권장)**
  - **합계 변동**: 88 → 87 active BL (BL-178 + BL-180 Resolved -2). 총 **87 active BL**.

- **2026-05-06 (Sprint 36 진입 — polish iter 4, BL-150 + BL-176 완료)** — PR #157 (`feat/sprint36-bl150-bl176`, **merged** `main`). BL-150 MC bootstrap sign-flip 버그 fix + BL-176 SelectWithDisplayName onClear prop 추가.
  - **BL-150 ✅ Resolved**: Monte Carlo bootstrap 음수 equity return sign-flip 차단 (`eq_base = abs(eq)` + `clip(-0.9999, None)`). fan chart Y축 정상 렌더 확인 (Playwright smoke). Walk-Forward E2E (20/38 folds) 정상 확인. BE 테스트 +3 (test_monte_carlo_negative_equity.py).
  - **BL-176 ✅ Resolved**: `SelectWithDisplayName`에 `onClear?: () => void` prop 추가. value 있고 prop 제공 시 ✕ 버튼 렌더, 클릭 시 onClear 호출. sentinel/nullable 없이 schema required 유지. FE 테스트 +3 (clear 버튼 렌더 조건 / onClear 미전달 시 숨김 / 클릭 동작).
  - **합계 변동**: 87 → **85 active BL** (BL-150 + BL-176 Resolved -2).

- **2026-05-06 (Sprint 36 종료 — dogfood Day 7 gate (a) FAIL, Sprint 37 진입)** — Day 7 4중 AND gate: (b)(c)(d) PASS / **(a) FAIL (≤6/10)**. Playwright dogfood 6/6 시나리오 확인.
  - **PASS 확인**: BH curve 파란 점선 + crosshair 렌더 / MC fan chart Y축 0~140,000 USDT (천조 해소) / Walk-Forward 20/38 folds / 거래 분석 5섹션 / 가정 박스 5개 / 거래 목록 200건
  - **신규 발견 BL-183**: MC fan chart 렌더 정상이나 CI 95% 하한/상한·median_final_equity·MDD p95 **요약 통계 테이블 FE 미노출** — BE 계산값 있으나 숫자 기반 의사결정 불가. Surface Trust 관점 UX 갭.
  - **Day 7 gate (a) FAIL 근거**: MC 숫자 미노출(BL-183) + 기존 6/10이 후한 측정 = 실질 ≤6. 수치 기반 의사결정 불가 = "돈 내고 쓰고 싶다" 미달.
  - **Sprint 37 = polish iter 5** + Day 7 재측정 목표. BL-183 fix 우선. 사용자 추가 피드백 기반 BL 조정 예정.
  - **합계 변동**: 85 + BL-183 신규 +1 = **86 active BL**.

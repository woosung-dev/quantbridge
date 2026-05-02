# QuantBridge — Refactoring Backlog

> **deferred 작업 백로그.** active sprint 작업은 [`TODO.md`](./TODO.md), 정합성 검증은 [`04_architecture/architecture-conformance.md`](./04_architecture/architecture-conformance.md).
>
> 본 문서는 **"특정 시점 또는 조건 도래 시 trigger 되는 작업"** 의 SSOT. CLAUDE.md "현재 작업" 섹션 / dev-log 회고 / TODO.md 의 "Sprint N 이관" 자연어 표현은 모두 본 문서의 BL-XXX ID 로 cross-link.
>
> **신규 sprint 진입 시 본 문서 review 의무** — 각 BL 의 trigger 가 도래했는지 확인 후 active TODO 로 승격할지 결정.

**작성일:** 2026-04-30
**최종 갱신:** 2026-04-30
**총 항목:** 50 BL — P0 5 (BL-001~005) / P1 17 (BL-010~026) / P2 14 (BL-030~043) / P3 8 (BL-050~057) / Beta 오픈 milestone 6 (BL-070~075)

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

### BL-004

**Title:** KillSwitch `capital_base` 동적 바인딩 + leverage cap 검증
**Category:** 트랜잭션 / Risk
**Priority:** P0 (H1 Stealth Step 3)
**Trigger:** mainnet 진입 직전 (BL-003 의 prereq)
**Est:** M (4-5h)
**출처:** [`docs/TODO.md`](TODO.md) L658

**원인 / 영향:** 현재 `capital_base` 는 정적 설정. 잔고 변동 시 KS 임계값이 실제 위험 노출과 어긋남. mainnet 진입 시 silent over-exposure 위험.

**권장 접근:**

1. `KillSwitchService.refresh_capital_base()` — exchange API `fetch_balance` 호출 후 `capital_base` 갱신 (Beat 5분)
2. leverage cap 검증 — 신규 주문 시 `(qty * leverage) / capital_base` 가 limit 초과 시 reject
3. tests: capital 변동 시뮬레이션 + leverage cap 경계값

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

| ID                                                    | 제목                                                                                          | Trigger                                     | Est       | 출처                                     |
| ----------------------------------------------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------- | --------- | ---------------------------------------- |
| [BL-010](#bl-010)                                     | commit-spy 도메인 확장 (LESSON-019 backfill)                                                  | 다음 mutation PR 직전                       | S (2-3h)  | architecture-conformance §A2             |
| [BL-011](#bl-011)                                     | Redis lease + heartbeat (multi-account scaling)                                               | 2 계정 이상 dogfood 진입 시                 | M (5-6h)  | TODO.md L706                             |
| [BL-012](#bl-012)                                     | prefork 복귀 (`--pool=solo` 한계 해소)                                                        | BL-011 직후                                 | M (4h)    | TODO.md L707                             |
| [BL-013](#bl-013)                                     | Auth circuit breaker (`BybitAuthError` 1h TTL)                                                | dogfood 1주 운영 중 alert flood 시          | S (2-3h)  | TODO.md L708                             |
| [BL-014](#bl-014)                                     | Partial fill `cumExecQty` tracking                                                            | partial fill 1건 발견 시                    | M (4-5h)  | TODO.md L709                             |
| [BL-015](#bl-015)                                     | OKX Private WS                                                                                | Bybit Demo 안정화 후                        | M (6-8h)  | TODO.md L710                             |
| [BL-016](#bl-016)                                     | `__aenter__` first_connect race 강화                                                          | 60s timeout 실측 발견 시                    | S (2h)    | TODO.md L711                             |
| [BL-017](#bl-017)                                     | WebCrypto error 처리 (HTTP local 환경)                                                        | dogfood HTTP 환경 발견 시                   | S (1-2h)  | TODO.md L42 (Sprint 14 이관)             |
| [BL-018](#bl-018)                                     | Strategies/Accounts query loading/error UX                                                    | dogfood Day 4+ 발견 시                      | S (1-2h)  | TODO.md L43 (Sprint 14 이관)             |
| [BL-019](#bl-019)                                     | `NEXT_PUBLIC_API_URL` trailing slash + production 누락                                        | Vercel 프로덕션 배포 직전                   | S (1h)    | TODO.md L44 (Sprint 14 이관)             |
| [BL-020](#bl-020)                                     | webhook 응답 size cap + JSON detail 정규화                                                    | on-demand (대용량 stack trace 노출 발견 시) | S (1h)    | TODO.md L45 (Sprint 14 이관)             |
| [BL-021](#bl-021)                                     | sessionStorage hardening (CSP + Trusted Types + secret masking)                               | Beta 5명 onboarding 후                      | M (4-6h)  | TODO.md L46 (Sprint 14+ 이관)            |
| [BL-022](#bl-022)                                     | golden expectations 재생성                                                                    | pine_v2 `strategy.exit` 도입 후             | M (3-4h)  | TODO.md L17 (skip #1)                    |
| [BL-023](#bl-023)                                     | KIND-B/C mutation 분류 정밀도 (xfail strict)                                                  | Trust Layer v2 검토 시                      | M (5-6h)  | TODO.md L23 (skip #16)                   |
| [BL-024](#bl-024)                                     | real_broker E2E 본 구현 (nightly cron)                                                        | Bybit Demo credentials + seed data 준비 시  | L (8h+)   | CLAUDE.md Sprint 10 Phase C              |
| [BL-025](#bl-025)                                     | autonomous-parallel-sprints 스킬 patch                                                        | on-demand (BUG-1/2/3 재발 시)               | S (2h)    | TODO.md L653                             |
| [BL-026](#bl-026)                                     | mutation fixture 활성화 회귀 (skip #4-7, #9-15)                                               | Stage 2c 2차 fixture 활성화 후              | S (1-2h)  | TODO.md L20-22                           |
| [BL-080](#bl-080-✅-resolved-sprint-18-2026-05-02) ✅ | **scan/reconcile/trading prefork-safe architectural fix** (Option C — Persistent worker loop) | (Sprint 18, 2026-05-02 Resolved)            | L (1-2일) | Sprint 17 dev-log §7 + Sprint 18 dev-log |

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

| ID                | 제목                                                                                                           | Priority | Est       |
| ----------------- | -------------------------------------------------------------------------------------------------------------- | -------- | --------- |
| **BL-086 (신규)** | AST audit factory function detection (codex G.2 P2 #1 Sprint 19) — `_MODULE_LOCK = _make_lock()` 패턴 catch    | P3       | S (1-2h)  |
| **BL-087 (신규)** | AST audit target glob `src/tasks/**/*.py` (codex G.2 P2 #2 Sprint 19) — manual list bypass 방어                | P3       | S (30min) |
| **BL-088 (신규)** | `drain_pending_alerts()` helper (codex G.2 P2 #3 Sprint 19) — production drain 사용처 추가 시 idempotent guard | P3       | S (1h)    |
| **BL-089 (신규)** | `qb_pending_alerts` Grafana alert wire-up (>50 임계)                                                           | P2       | S (1-2h)  |
| **BL-090 (신규)** | `tests/db_url.py` 분리 (codex G.2 P3 #1 Sprint 19) — test_migrations 의 conftest import 정리                   | P3       | S (30min) |

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

| ID                 | 제목                                                                              | Trigger                                      | Est           | 출처                                                     |
| ------------------ | --------------------------------------------------------------------------------- | -------------------------------------------- | ------------- | -------------------------------------------------------- |
| BL-027 ✅ Resolved | WS state_handler / reconciliation / tasks/trading dec winner-only commit-then-dec | (Sprint 16, 2026-05-01)                      | M (3-4h)      | dev-log Sprint 15 watchdog G.2 P1 #3 분리, Sprint 16 fix |
| [BL-030](#bl-030)  | CI lupa C ext 빌드 검증                                                           | on-demand                                    | S (1h)        | CLAUDE.md Sprint 11 follow-up                            |
| [BL-031](#bl-031)  | Sentinel/Cluster 검토                                                             | Redis 단일 인스턴스 한계 도달 시             | L (다음 분기) | CLAUDE.md Sprint 11 follow-up                            |
| [BL-032](#bl-032)  | cardinality allowlist 조정                                                        | 프로덕션 ccxt 예외 실측 후                   | S (1-2h)      | TODO.md L807 (H2 말 이관)                                |
| [BL-033](#bl-033)  | issue 중복 방지 (auto-label workflow)                                             | dogfood 1주 운영 중 issue 중복 발견 시       | S (1h)        | CLAUDE.md Sprint 11 follow-up                            |
| [BL-034](#bl-034)  | slowapi 0.2.x major upgrade 검토                                                  | H2 말 (~2026-06-30)                          | M (3-4h)      | TODO.md L806                                             |
| [BL-035](#bl-035)  | Phase B Grafana Cloud (dogfood 통합 대시보드)                                     | dogfood 운영 중 본인 필요 metric 식별 후     | M (4-6h)      | TODO.md L715 (Sprint 12 이관)                            |
| [BL-036](#bl-036)  | dogfood 통합 대시보드 `/dashboard/today`                                          | "화면 부족" 자각 시                          | M (3-4h)      | TODO.md L716                                             |
| [BL-037](#bl-037)  | Coverage Analyzer AST 정밀화 (regex → pynescript visitor)                         | Sprint Y2 또는 사용자 false-positive 보고 시 | M (4h)        | CLAUDE.md Y1 follow-up                                   |
| [BL-038](#bl-038)  | P-3 중복 실행 통합 (`run_backtest_v2` + `parse_and_run_v2`)                       | Sprint 16 정리 sprint 시                     | M (3-4h)      | CLAUDE.md codex Gate-2 W-3                               |
| [BL-039](#bl-039)  | `qb_redis_lock_pool_healthy` startup race                                         | dogfood 운영 중 false alert 1건 이상 발견 시 | S (1-2h)      | dogfood-day1 §3 (관찰)                                   |
| [BL-040](#bl-040)  | Path γ — PyneCore transformers 이식                                               | H2~H3 path 평가 시                           | XL (~3주)     | CLAUDE.md ADR-011 amendment                              |
| [BL-041](#bl-041)  | Path δ — Bulk stdlib top-N                                                        | dogfood 피드백 기반 우선순위 결정 후         | L (1~2주)     | CLAUDE.md ADR-011 amendment                              |
| [BL-042](#bl-042)  | Onboarding 성공률 지표 `qb_onboarding_completion_total{step}`                     | Beta 5명 onboarding 후                       | S (1-2h)      | TODO.md L808                                             |
| [BL-043](#bl-043)  | waitlist email_service Resend 미설정 graceful fallback 검증                       | Beta 오픈 직전                               | S (1-2h)      | TODO.md L809                                             |

(상세 내용은 출처 인용 — 표 형태로 충분, 각 항목 1-3 줄로 충분히 self-contained)

---

## P3 — Nice-to-have / 컨벤션 정합

| ID                | 제목                                                                       | Trigger                           | Est                       | 출처                         |
| ----------------- | -------------------------------------------------------------------------- | --------------------------------- | ------------------------- | ---------------------------- |
| [BL-050](#bl-050) | `PINE_ALERT_HEURISTIC_MODE` env 사용 ADR 신설 또는 주석 강화               | 신규 sprint 정리 시 on-demand     | S (30min)                 | architecture-conformance §B5 |
| [BL-051](#bl-051) | zod@4 import 경로 정정 (`zod/v4` → `zod`)                                  | Sprint 16 cleanup 시              | S (1h)                    | TODO.md L813                 |
| [BL-052](#bl-052) | `.uuid()` → `z.uuid()` 전수 migration                                      | BL-051 와 묶음                    | S (1h)                    | TODO.md L814                 |
| [BL-053](#bl-053) | `/strategies/[id]/edit` / `/strategies/new` 라우트 loading.tsx + error.tsx | FE Polish 다음 bundle 시          | S (1-2h)                  | TODO.md L815                 |
| [BL-054](#bl-054) | `strategy-list.tsx` useSuspenseQuery 최종 전환                             | FE Polish 다음 bundle 시          | S (2h)                    | TODO.md L816                 |
| [BL-055](#bl-055) | `"use client"` 27개 중 presentational 서버 컴포넌트화                      | RSC 성능 측정 후 우선순위 결정 시 | M (4h)                    | TODO.md L817                 |
| [BL-056](#bl-056) | D-5 A 안 — Termly → 한국 변호사 검토본 교체                                | H2 말 (~2026-06-30)               | M (외부 비용 $500~$1,500) | TODO.md L805                 |
| [BL-057](#bl-057) | requirements.md §4.1 "Mutation 측정 불가 = scope-reducing" 명시화          | Sprint 16 docs sync 시            | S (30min)                 | CLAUDE.md ADR-013 follow-up  |

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

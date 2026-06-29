# QuantBridge — Refactoring Backlog

> **Active 백로그.** 명백한 Resolved + stale 항목은 [`refactoring-backlog/_archived.md`](refactoring-backlog/_archived.md), trigger 미도래 의도적 부활 가능 항목은 [`refactoring-backlog/_deferred.md`](refactoring-backlog/_deferred.md). 정합성 검증은 [`04_architecture/architecture-conformance.md`](04_architecture/architecture-conformance.md).
>
> **신규 sprint 진입 시 본 문서 review 의무** — 각 BL 의 trigger 가 도래했는지 확인 후 active TODO 로 승격할지 결정. `_deferred.md` 도 6-8주마다 재평가.

**작성일:** 2026-04-30
**최종 갱신:** 2026-05-17 (**Beta 본격 진입 결정** — Sprint 60→61→62 누적 3-sprint cycle 완료, 34 BL Resolved + BL-070~075 트랙 활성화)
**현재 상태:** **45 active BL** (Sprint 62 6 Resolved + Sprint 61 11 Resolved 누적, 신규 14 = 17 → 54 → 48 → 45). main @ `36bb4e0` (PR #288 + #289 + #290 모두 merge). **BL-070~075 milestone active 승격** (deferred → P0 prep).

**최근 sprint BL 변경 (Sprint 55~Sprint 62 Beta 진입):**

- **2026-05-17 Sprint 62 PR #290 merge (Beta 본격 진입 결정 ★★★★★)**: 6 BL fix-first (BL-350+354 ★★★ Optimizer Zod resilience + BL-353 step 01 라벨 + BL-356/357/358/359 모바일 터치 ≥44pt 묶음). 실측 ~2-3h vs plan 6-8h (LESSON-067 6차 검증). main `36bb4e0`. **BL-070~072 milestone active 승격**. **재측정 skip + 본인 의지 (d) 통과**.
- **2026-05-17 Multi-Agent QA 재측정 (post-Sprint 61)**: Composite 6.08 → **7.5/10** (+1.42 목표 도달). 신규 BL-347~360 (14건, Critical 0 / P0 2 ★★★ 공통 BL-350+354 / P1 4 / P2 5 / P3 3). Sprint 61 11 BL Resolved 마킹 (PASS 8 + PARTIAL 2 + manual 1). 상세 = [`docs/qa/2026-05-17-post-sprint61/integrated-report.html`](qa/2026-05-17-post-sprint61/integrated-report.html).
- **2026-05-17 Sprint 61 PR #288 merge**: 11 BL fix (BL-310/311/312/319/322/323/327/328/339/340) source 적용 + hotfix PR #289 (BL-348/349). docs/qa/2026-05-17/ baseline 별도.
- **2026-05-17 Multi-Agent QA 1차**: 신규 BL-310~346 (37건). 상세 = [`docs/qa/2026-05-17/integrated-report.html`](qa/2026-05-17/integrated-report.html) + [`docs/sprint-61-plan.md`](sprint-61-plan.md). 17 → 54 net.
- **Sprint 58** (2026-05-11~12): ✅ BL-241/242/243 Resolved (Pine TA 확장). 92 → 89 net.
- **Sprint 57** (2026-05-11): ✅ BL-234/237 Resolved (Optimizer Polish + heavy queue). 신규 BL-241~243. 91 → 92 net.
- **Sprint 56** (2026-05-11): ✅ BL-233 Resolved (Genetic). 신규 BL-238/239/240 chore. 91 net.
- **Sprint 55** (2026-05-11): ✅ BL-232 Resolved (Bayesian). 신규 BL-233~237. 88 → 92 net.

**Sprint 59 트리아주 결과 (PR-D, 2026-05-13):** 158 BL → **13 Active** (본 문서 본문) + **8 Deferred** ([`_deferred.md`](refactoring-backlog/_deferred.md) — Beta 6 + BL-005 + BL-145) + **137 Archived** ([`_archived.md`](refactoring-backlog/_archived.md) — Resolved + Sprint 16~30 stale).

**P0 / P1 active short list (Beta 본격 진입 prep):**

- **🚀 Beta 진입 milestone (BL-070~072) — active P0** ([\_deferred.md](refactoring-backlog/_deferred.md) 에서 승격):
  - **BL-070** 도메인 + DNS + Cloudflare (사용자 manual 1-2h + DNS 전파 24h)
  - **BL-071** Backend 프로덕션 배포 (Cloud Run/Railway/Render + Postgres prod + Redis prod + Clerk production + 보안 헤더 gunicorn) — 2-4h. **BL-347 server strip 동시 처리** (gunicorn `--server_header False`).
  - **BL-072** Resend 이메일 + Waitlist 활성화 — 1-2h + 24h verify
  - BL-073/074/075 = 위 완료 후 자연 trigger (Twitter/X 캠페인 + Beta 인터뷰 + H2 진입 gate)
- **Sprint 62 Resolved (6 BL)** ✅:
  - BL-350+354 ★★★ Optimizer Zod resilience / BL-353 step 01 라벨 / BL-356/357/358/359 모바일 터치 ≥44pt 묶음
- **Sprint 61 Resolved (11 BL)** ✅ (요약): BL-310/311/312/319/322/323/327/328/339/340/348/349 (PASS 9 + PARTIAL 2 + manual 1)
- **Production deploy 시점 자동 해소 묶음** (BL-070/071 시점):
  - BL-320 Development mode 배지 / BL-321/352 Clerk application name / BL-347 server header / BL-261 Clerk custom domain
- **기존 P0**: BL-003 (Bybit mainnet runbook, H1 종료 gate — BL-073 캠페인 후 trigger)
- **잔존 P1/P2/P3** (Beta 본격 진입 후 polish 또는 dogfood 발견 시 trigger):
  - P1: BL-014/015/022/023/024/025/026/308
  - P2: BL-186/190/195/235/236/309/313/314/315/316/329/330/332/344/345/351
  - P3: BL-306/307/317/318/324/325/326/331/333/334/335/336/337/338/346/355/360

> **신규 BL-347~360 상세**: `docs/qa/2026-05-17-post-sprint61/integrated-report.html` §3 + 페르소나별 원본 보고서 4종.
> **Beta 진입 milestone 상세**: [\_deferred.md](refactoring-backlog/_deferred.md) BL-070~075 섹션.

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

---

## P0 — Dogfood / H1 종료 blocker

| ID                | 제목                                        | Trigger              | Est      | 출처             |
| ----------------- | ------------------------------------------- | -------------------- | -------- | ---------------- |
| [BL-003](#bl-003) | Bybit mainnet 진입 runbook + smoke 스크립트 | H1 Stealth 종료 직전 | M (4-5h) | TODO.md L646~651 |

> 추가 P0 — [BL-005 본인 dogfood](refactoring-backlog/_deferred.md) + [BL-145 EffectiveLeverageEvaluator](refactoring-backlog/_deferred.md) (deferred). Resolved P0 = BL-001/002/004 ([\_archived.md](refactoring-backlog/_archived.md)).

### BL-003

**Title:** Bybit mainnet 진입 runbook + smoke 스크립트
**Category:** Tooling / Infra
**Priority:** P0 (H1 Stealth 종료 직전)
**Trigger:** Bybit Demo 1주 안정 운영 후 + BL-004 완료 후 (BL-004 ✅ Resolved Sprint 28)
**Est:** M (4-5h)
**출처:** [`docs/TODO.md`](TODO.md) L646~651

**원인 / 영향:** dogfood 가 Bybit Demo 만으로는 H1 종료 gate 충족 안 됨. mainnet 전환 시 수동 step 누락 위험 (IP whitelist / 출금 권한 차단 / 레버리지 1:1 / 소액 시작).

**권장 접근:**

1. `docs/07_infra/bybit-mainnet-checklist.md` 신규 — IP whitelist · 출금 권한 OFF 확인 · 레버리지 1:1 · 소액 ($10-50) 시작 · Kill Switch 임계값 lower bound
2. `scripts/bybit-smoke.sh` 신규 — mainnet credentials 로 read-only API 호출 (잔고 조회 + 1 USDT limit-order 후 즉시 cancel) dry-run
3. `.env.production` 별도 secret manager + rotation 절차

**의존성:** BL-004 ✅ Resolved (Sprint 28 PR #108).

---

## P1 — Risk mitigation / 알려진 broken bug 패턴 재발 방어

| ID                | 제목                                            | Trigger                                    | Est        | 출처                            |
| ----------------- | ----------------------------------------------- | ------------------------------------------ | ---------- | ------------------------------- |
| [BL-014](#bl-014) | Partial fill `cumExecQty` tracking              | partial fill 1건 발견 시                   | M (4-5h)   | TODO.md L709                    |
| [BL-015](#bl-015) | OKX Private WS                                  | Bybit Demo 안정화 후                       | M (6-8h)   | TODO.md L710                    |
| [BL-022](#bl-022) | golden expectations 재생성                      | pine_v2 `strategy.exit` 도입 후            | M (3-4h)   | TODO.md L17 (skip #1)           |
| [BL-023](#bl-023) | KIND-B/C mutation 분류 정밀도 (xfail strict)    | Trust Layer v2 검토 시                     | M (5-6h)   | TODO.md L23 (skip #16)          |
| [BL-024](#bl-024) | real_broker E2E 본 구현 (nightly cron)          | Bybit Demo credentials + seed data 준비 시 | L (8h+)    | CLAUDE.md Sprint 10 Phase C     |
| [BL-025](#bl-025) | autonomous-parallel-sprints 스킬 patch          | on-demand (BUG-1/2/3 재발 시)              | S (2h)     | TODO.md L653                    |
| [BL-026](#bl-026) | mutation fixture 활성화 회귀 (skip #4-7, #9-15) | Stage 2c 2차 fixture 활성화 후             | S (1-2h)   | TODO.md L20-22                  |
| [BL-308](#bl-308) | trading websocket test coverage 4% → ≥70%       | dogfood 직후 (Day 7 후)                    | L (12-16h) | 2026-05-15 trading-deepen audit |

> Resolved P1 = BL-001/002/010/011/012/013/016/017~021/080/091~099/101~103/110a 등 18+ 건 ([\_archived.md](refactoring-backlog/_archived.md)).

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

### BL-308

**Title:** trading websocket subsystem test coverage boost (4% → ≥70%)
**Category:** Test infra / Trading
**Priority:** P1
**Trigger:** dogfood 직후 (Day 7 인터뷰 2026-05-16 후) — websocket reconciliation 미검증 = 거래 silent failure risk
**Est:** L (12-16h)
**출처:** [`docs/dev-log/2026-05-15-trading-deepen.md`](dev-log/2026-05-15-trading-deepen.md) Phase 2

**✅ Resolved (W3, 2026-06-29):** baseline 재측정 결과 "4%" 는 stale (2026-05-15, PR #305 money-path 감사 + TP/SL·트레일링 wave 이전). 실측 baseline = `websocket/` **85% combined branch cov** (bybit_private_stream 75% / reconciliation 90% / reconcile_fetcher 100% / state_handler 86%). W3 가 진짜 미커버 머니패스 분기만 보강 (replay_orphan / orphan TTL eviction / _receive_loop json·topic·handler-None·exception-swallow / _heartbeat_loop / _maybe_reconcile 예외 / auth timeout / _find_match orderLinkId·clOrdId fallback / Rejected 전이 / _handle_unknown alert 예외) → **96% combined** (bybit 93% / reconciliation 97% / state_handler 96%). 잔여 미커버 = supervisor reconnect/timeout 타이밍 분기 + trivial getter (deterministic 테스트 불가 → vacuous 회피로 의도적 제외). CI `--cov-fail-under=90` ratchet 게이트 추가. 게이트: G1 codex plan + G2 codex challenge(4 P1 false-green 수정) + G3 fresh review(mutation 검증) PASS.

**현 상태 (2026-05-15 당시):** `backend/src/trading/websocket/` 904 LOC (도메인 19.4%) = 3 file (`bybit_private_stream.py` 319L + `reconciliation.py` 225L + `state_handler.py` 221L 등) 안 test 2/48 file 만 reference = **~4% 추정 coverage**. WS event reconciliation logic = order state cascade 핵심 = silent corruption risk.

**권장 접근:**

1. `tests/trading/websocket/` 폴더 신규 — bybit_private_stream / reconciliation / state_handler 각 file 1-2 test module
2. fixture = `BybitPrivateStream` async context manager mock + WS message replay (json fixture)
3. reconciliation engine end-to-end test (open order → WS event sequence → terminal state 검증)
4. coverage `pytest --cov=src.trading.websocket --cov-fail-under=70` CI gate 추가

**Risk:** 🔴 (현재 silent failure risk = order state mismatch 가능). dogfood 직후 = order 발송 후 reconciliation 깨짐 시 사용자 발견 어려움.

**의존성:** BL-024 real_broker E2E 와 묶음 sprint 가능 (양쪽 모두 trading 안정화 sprint).

---

### BL-361

**Title:** Pine Trust Layer 누출 — coverage SUPPORTED ↔ interpreter dispatch SSOT drift (28 symbols)
**Category:** Strategy / pine_v2 SSOT / Trust Layer
**Priority:** P1
**Trigger:** 전체 정검 2026-05-30 (P1-10/13) — ✅ **Resolved S2** (`stage/fix-trust-layer-leak`)
**Est:** S (2-3h) — 실측 ~1.5h
**출처:** [`docs/audit/2026-05-30-full-inspection.md`](audit/2026-05-30-full-inspection.md) §4.3

**원인 / 영향:** `coverage.py` 가 SUPPORTED 표기하나 interpreter 미구현 → `is_runnable=True` preflight 통과 후 runtime `PineRuntimeError`. backtest=FAILED(strict=True), live=silent swallow 후 오신호(strict=False, event_loop.py:128). ADR-003 부분실행 금지 위반.

**해소:** 망라 parity 테스트(`tests/strategy/pine_v2/test_coverage_interpreter_parity.py` 의 `SUPPORTED_ATTRIBUTES`/`_STRING_FUNCTIONS`/`_MATH_FUNCTIONS` 전수 순회)로 audit hand-found ~10 + **미발견 18** = 총 **28 누출** 검출 → `interpreter.py` 전부 구현: hl2/hlc3/ohlc4(`_resolve_name`, Pine 정의 1:1), barstate.isfirst/islast/ishistory/isconfirmed(`_eval_attribute`, bar*index/len), str.tostring/tonumber/format/length + bare tonumber(`_eval_call`, NOP-safe/정확 parse), currency.\* 12(`_eval_attribute` prefix), strategy.commission*\* 3(`_ATTR_CONSTANTS`), math.log10. TDD RED 28→GREEN. **codex challenge(769k) 교차검증 → Finding 1 추가 fix**: `hl2[1]`/`hlc3[1]`/`ohlc4[1]` lagged 참조가 history series 누락으로 na 반환하던 silent 오값 → `_synthetic_source(name, offset)` helper (current+history 공용) 로 보완 (`test_synthetic_source_history_lag`). codex Findings 2~6 은 재검증으로 out-of-scope/pre-existing/consistent (audit §7). pine_v2 612 pass 회귀 0. 향후 SUPPORTED 추가 누출 = 망라 테스트가 CI 자동 차단(영구 tripwire).

---

## P2 — Hardening / 건강도 작업

| ID                | 제목                                                                                 | Trigger                                    | Est          | 출처                                                |
| ----------------- | ------------------------------------------------------------------------------------ | ------------------------------------------ | ------------ | --------------------------------------------------- |
| [BL-186](#bl-186) | Full leverage + funding + mm + liquidation 풀 모델                                   | Sprint 38+ (BL-185 foundation 위)          | M-L (16-24h) | Sprint 37 BL-185 후속                               |
| [BL-190](#bl-190) | PDF export (jsPDF / Playwright)                                                      | 외부 사용자 요청 시                        | M (3-5h)     | Sprint 41 Worker H 결정                             |
| [BL-195](#bl-195) | qb-form-slide-down animation 영구 truncation                                         | Sprint 45 codex G.4                        | XS (30m)     | Sprint 45 codex G.4 발견                            |
| [BL-235](#bl-235) | N-dim acquisition surface viz (Bayesian 전용)                                        | Sprint 57+                                 | M (8-12h)    | ADR-013 §6 #8 deferred                              |
| [BL-236](#bl-236) | `objective_metric` whitelist 자유화 (BacktestMetrics 24+)                            | Sprint 56+                                 | S (3-5h)     | Sprint 55 deferred                                  |
| [BL-309](#bl-309) | trading registry/webhook/fees test 0% → ≥80%                                         | BL-308 묶음 또는 dogfood 직후              | M (4-6h)     | 2026-05-15 trading-deepen audit                     |
| [BL-362](#bl-362) | live 경로 coverage↔interpreter divergence silent swallow observability               | S5 (trading kill-switch 묶음)              | S (2-4h)     | 2026-05-30 full-inspection §4.3                     |
| [BL-363](#bl-363) | stress*test `\_execute*\*` 4-method boilerplate 추출 (config drift 근본원인)         | deepening sprint 또는 5번째 engine 추가 시 | S (2-3h)     | 2026-05-30 full-inspection §appendix P1-9           |
| [BL-364](#bl-364) | Optimizer 진짜 string-label CategoricalField sweep (Genetic+Bayesian ordinal 인코딩) | string 카테고리 sweep 요청 시              | M (4-6h)     | 2026-05-30 full-inspection §appendix P1-9 (S4 후속) |
| [BL-365](#bl-365) | `trigger_direction_for`/`map_exit_kind` dead + 서버 미배선 (standalone-trigger 방향) | 서버 standalone 트리거 발주 시             | S (2-4h)     | 2026-06-26 trading-deepen-2                         |
| [BL-366](#bl-366) | live-signal dispatch OrderService DI 인라인 조립 중복 (HTTP 와 drift)                | trading deepening sprint                   | S-M (3-5h)   | 2026-06-26 trading-deepen-2                         |
| [BL-368](#bl-368) | `_merge_exit_params` ccxt 키명 3 call site 누설 (shallow interface)                  | trading deepening / 4번째 provider         | S-M (3-5h)   | 2026-06-26 trading-deepen-2                         |
| [BL-369](#bl-369) | 3 provider `create_order` try/except/finally ~40 LOC 복붙                            | trading deepening sprint                   | S (2-4h)     | 2026-06-26 trading-deepen-2                         |
| [BL-372](#bl-372) | STEP B 트레일링 live-placement 3-리뷰어 검증 follow-up 번들 (9 항목, P2/P3)          | Wave 3 실자금 cutover 전                   | M (6-10h)    | 2026-06-26 trailing 3-reviewer (codex+Opus 6-lens)  |
| [BL-373](#bl-373) | OCO 형제취소 (sibling-cancel) — standalone exit order 시점 구현                       | BL-365 standalone-trigger 발주 시         | S-M (3-5h)   | 2026-06-28 grilling (트레일링 후속 scope)            |
| [BL-374](#bl-374) | pine_v2 interpreter na-semantics — `x/0`·`math.sqrt(-1)` 등 raw 예외 → Pine `na`     | pine_v2 robustness sprint                  | M (4-6h)     | 2026-06-28 BL-362 G2 codex challenge                 |
| [BL-375](#bl-375) | trailing same-side stale 잔여 — reconcile-lag late filled_at 시 reopen 미탐 (거래소 fill-time 소싱) | Wave 3 실자금 cutover 전                   | S-M (3-5h)   | 2026-06-29 BL-372 same-side stale G1 codex           |

> Resolved P2 = BL-027/137/140/140b/141/144/150/152/176/178/180/181/183/184/185/187/187a/188/188a/189/200~206/219~234/237 + 30+ Sprint 16~30 stale ([\_archived.md](refactoring-backlog/_archived.md)).

### BL-186

**Title:** Full leverage + funding rate + maintenance margin + cross/isolated margin + liquidation 풀 모델
**Category:** 트랜잭션 / Risk / Pine v2
**Priority:** P2
**Trigger:** Sprint 38+ deferred (BL-185 spot-equivalent foundation 위)
**Est:** M-L (16-24h)
**출처:** Sprint 37 BL-185 spot-equivalent 채택 후 풀 모델 후속

**원인 / 영향:** Sprint 37 BL-185 는 spot-equivalent (1x, 롱/숏) 만 보장. 실제 dogfood / Beta 사용자가 high-leverage strategy 운영 시 funding rate / maintenance margin / liquidation 정확 시뮬레이션 불가.

**권장 접근:** funding/mm/liquidation 정확 시뮬. exchange-specific (Bybit linear funding interval / Binance / OKX) parameter 화. Pine `strategy.entry(leverage=N)` 와 정합.

---

### BL-190

**Title:** PDF export (jsPDF + html2canvas client-side 또는 Playwright server-side) — backtest 결과 인쇄/오프라인 공유
**Category:** Frontend UX
**Priority:** P2 (deferrable)
**Trigger:** 외부 사용자 요청 또는 인쇄 use case 발견 시
**Est:** M (3-5h)
**출처:** Sprint 41 Worker H 결정 — share link 충분 P1 deferrable, demo 첫인상 단계 미구현

**권장 접근:** share link 가 충분히 우선이라 demo 단계 미구현. 사용자 요청 시 jsPDF + html2canvas (client) 또는 Playwright (server-side) 둘 중 선택.

---

### BL-195

**Title:** qb-form-slide-down animation 영구 truncation (max-height 600px + overflow-hidden, 600px 초과 시 hint list 잘림)
**Category:** Frontend UX
**Priority:** P2
**Trigger:** Sprint 45 codex G.4 review 발견
**Est:** XS (30m)
**출처:** Sprint 45 codex G.4

**원인 / 영향:** `frontend/src/styles/globals.css:582` `qb-form-slide-down` `both` fill mode + `FormErrorInline` `overflow-hidden` 조합 = Pine Script 다수 미지원 함수 시 unsupported-builtins hint list 영구 truncation.

**권장 접근:** fill-mode `forwards` 제거 또는 max-height 풀림 패턴 적용.

---

### BL-309

**Title:** trading 핵심 dispatch 모듈 test 추가 (registry / webhook / fees, 0% → ≥80%)
**Category:** Test infra / Trading
**Priority:** P2
**Trigger:** BL-308 묶음 또는 dogfood 직후
**Est:** M (4-6h)
**출처:** [`docs/dev-log/2026-05-15-trading-deepen.md`](dev-log/2026-05-15-trading-deepen.md) Phase 2

**✅ Resolved (W3, 2026-06-29) — baseline stale + fees obsolete:** "0%" 는 2026-05-15 수치. 실측 결과:
- **`fees.py` 는 파일 자체 삭제됨** (PR #344 dead vectorbt-era cleanup). fee 로직은 `providers.py`/backtest 로 이전 — fees 항목 **무효** (복원/테스트 안 함).
- **`registry.py` = 이미 100% cov** (`tests/tasks/test_provider_dispatch.py` 가 5-tuple + unsupported + `.key` + ProviderError 서브클래스 전수 검증, `_provider_for_account_and_leverage` wrapper 경유). W3 = 미검증 잔여 불변식만 추가 (per-call factory identity = prefork-safe iron law + 미지원 매트릭스 빈칸 `(okx,live,True)`). 풀 dispatch-parity 스위트는 vacuous 중복이라 의도적 미작성 (G1 codex 검증).
- **`webhook.py` = ~94% cov** (HMAC verify grace 안/밖 + parse_tv_payload happy/error 광범위). 잔여 1 line(`ensure_authorized` raise)은 router 401 테스트로 행동 커버 → pure unit 은 cosmetics 라 미작성 (G1/G2 합의).

BL-308 묶음 PR 에 포함. CI ratchet 게이트가 registry/webhook 도 합산 커버.

**현 상태 (2026-05-15 당시):** **0% test coverage** 3 file = `registry.py` 64L (provider dispatch 핵심, 5 entry tuple) + `webhook.py` 81L (TV payload 파싱) + `fees.py` 55L (fee calculation). 합계 200L 핵심 dispatch 로직 미검증.

**권장 접근:**

1. `tests/trading/test_registry.py` — 5 tuple (Bybit demo spot/futures + OKX demo + Bybit live) provider factory 검증 + UnsupportedExchangeError raise 검증
2. `tests/trading/test_webhook.py` — TV payload parsing positive/negative + secret rotation
3. `tests/trading/test_fees.py` — fee calculation per-exchange parity (Bybit vs OKX 수수료 형식 차이)
4. coverage `pytest --cov=src.trading.registry --cov=src.trading.webhook --cov=src.trading.fees --cov-fail-under=80` CI gate

**Risk:** 🟡 (dispatch 깨짐 = 신규 거래소 추가 시 silent failure).

**의존성:** BL-308 와 묶음 권고 (양쪽 = trading test 보강 sprint).

---

### BL-235

**Title:** N-dim acquisition surface viz (3D+ surface 또는 parallel-coord, Bayesian 전용)
**Category:** Frontend UX / Optimizer
**Priority:** P2
**Trigger:** Sprint 57+
**Est:** M (8-12h, estimate)
**출처:** ADR-013 §6 #8 deferred. Sprint 55 = inline SVG iteration-chart (1D best_so_far) 만 구현.

**권장 접근:** recharts 또는 plotly.js 의존성 추가 검토 + cross-page consistency 의무. Bayesian / Genetic 공용.

---

### BL-236

**Title:** `objective_metric` whitelist 자유화 (BacktestMetrics 24+ 지표 노출)
**Category:** Optimizer
**Priority:** P2
**Trigger:** Sprint 56+
**Est:** S (3-5h, estimate)
**출처:** Sprint 55 = `_SUPPORTED_OBJECTIVE_METRICS = {sharpe_ratio, total_return, max_drawdown}` 3종만 노출

**권장 접근:** BacktestMetrics 24 metric (sortino_ratio / calmar_ratio / win_rate / profit_factor 등) 노출 검토. `_objective_from_metrics` switch + FE select option 확장.

---

### BL-362

**Title:** live 경로 coverage↔interpreter divergence silent swallow observability
**Category:** Strategy / pine_v2 / Trading (money path)
**Priority:** P2
**Trigger:** S5 (trading kill-switch/notional/reconcile 묶음) — money path 변경이라 trading 테마와 함께
**Est:** S (2-4h)
**출처:** [`docs/audit/2026-05-30-full-inspection.md`](audit/2026-05-30-full-inspection.md) §4.3 (strategy/D 관찰 — observability gap)

**원인 / 영향:** `run_live` 가 `run_historical(..., strict=False)`(event_loop.py:219) 호출 → `PineRuntimeError` 를 `result.errors` 에 기록만 하고 **그 bar statement 만 건너뛴 채 실행 계속**(event_loop.py:128-133). live 경로엔 coverage preflight 게이트도 없음. BL-361 이 현재 28 누출을 닫았으나, **향후 임의의 coverage↔interpreter divergence 가 라이브에서 조용히 오신호 생성**할 latent risk 상존. (S2 는 DEC-16=A 로 본 갭을 S5 이관.)

**권장 접근:** (a) live 진입 전 `analyze_coverage` preflight reject 적용, 또는 (b) `run_live` 의 swallowed `result.errors` 를 Slack/Prometheus alert + (선택) 세션 abort 로 표면화. money path 변경이므로 S5 에서 commit-spy + kill-switch 회귀와 함께 신중 검토.

---

### BL-363

**Title:** stress*test `StressTestService.\_execute*\*` 4-method boilerplate 추출
**Category:** Stress / Architecture (deep module)
**Priority:** P2
**Trigger:** deepening sprint 또는 5번째 stress engine 추가 시
**Est:** S (2-3h)
**출처:** [`docs/audit/2026-05-30-full-inspection.md`](audit/2026-05-30-full-inspection.md) appendix P1-9

**원인 / 영향:** `_execute_walk_forward`/`_execute_cost_assumption_sensitivity`/`_execute_param_stability` 가 동일 전처리(strategy.find_by_id_and_owner → provider.get_ohlcv → param 파싱 → `build_engine_config_from_db`)를 복붙. 이 중복이 전체 정검 S3(WF config 누락)의 **직접 원인** — Sprint 52 가 CA/PS 에만 config 추가하고 WF 를 누락. 향후 5번째 engine 도 동일 누락 위험.

**권장 접근:** 공통 전처리 `_load_strategy_ohlcv_config(bt) → (pine_source, ohlcv, backtest_config)` helper 추출 → 각 `_execute_*` 는 엔진 호출 + 직렬화만. config 빌드를 helper 에 넣으면 누락이 구조적으로 불가능. (MC 는 equity_curve 기반이라 helper 비대상.) 현재는 per-engine propagation 테스트(WF+CA+PS 각 1건)가 drift 가드 — extraction 은 가드 + 중복 제거.

---

### BL-364

**Title:** Optimizer 진짜 string-label CategoricalField sweep (Genetic + Bayesian)
**Category:** Optimizer / Feature
**Priority:** P2
**Trigger:** 사용자 string 카테고리 sweep 요청 시 (예: maType ∈ {ema,sma,wma})
**Est:** M (4-6h)
**출처:** [`docs/audit/2026-05-30-full-inspection.md`](audit/2026-05-30-full-inspection.md) appendix P1-9 (S4 Option A 후속)

**원인 / 영향:** S4(Option A)는 비숫자 CategoricalField 를 명확히 거부(InvalidOperation 크래시 차단)했으나, 스키마 docstring 의 본래 의도(`pine input.string / 사용자 정의 선택지` = `['ema','sma']`)는 미지원 상태. GA/Bayesian 이 individual 을 Decimal(ordinal)로 표현하기 때문.

**권장 접근:** ordinal 인코딩 — GA/Bayesian 이 categorical 차원을 index(Decimal 0..N-1)로 sample/mutate, backtest 호출 시 `field.values[int(idx)]` 로 string 디코드하여 input override 전달, best-params 에서 라벨 복원. Genetic `_sample_individual`/`_gaussian_mutation`/run-loop + Bayesian `_coerce_skopt_to_decimal`/skopt `Categorical(transform="label")` 양쪽 일관 처리. (S4 에서 사용자 결정 = Option A 우선, 본 feature 는 후속.)

---

### BL-365

**Title:** `trigger_direction_for` / `map_exit_kind` dead-code + 서버 미배선 (standalone-trigger 방향 latent gap)
**Category:** Trading / pine_v2 (money path, latent correctness)
**Priority:** P2
**Trigger:** standalone 조건부 트리거 주문(SL/Trail) 을 서버가 발주하게 되는 시점 (manual API trigger_price 노출 강화 또는 Wave 4+ standalone exit)
**Est:** S (2-4h)
**출처:** [`docs/dev-log/2026-06-26-trading-deepen-2.md`](dev-log/2026-06-26-trading-deepen-2.md) (deepen-modules trading 2차 audit)

**원인 / 영향:** `exit_order_mapping.py:48/76` 의 `map_exit_kind`/`trigger_direction_for` 는 production caller 0 (doc-comment 만 `models.py:212` / `providers.py:77`). 현재 라이브 자율 exit 는 entry-attached bracket 으로 Bybit 가 방향을 포지션에서 추론 → 영향 없음 (Phase 3 PASS). **단 manual order API 는 `trigger_direction` 을 client 가 공급**(`schemas.py:67` `int|None ge=1 le=2`) — 서버가 SSOT (`trigger_direction_for`)로 계산하지 않아, 향후 서버 발주 standalone 트리거가 방향 미산정 시 역방향 트리거 / 거부 위험. 트레일링 live-placement(STEP B)는 trading-stop 엔드포인트(position-inferred)라 본 BL 미소비 — deferred 확정.

**권장 접근:** 서버가 standalone 트리거 exit 를 발주하는 첫 경로에서 `trigger_direction_for(exit_side, kind)` 호출로 SSOT 산정 + manual API 의 client-supplied 값 검증/override. 그 전까진 dead-code 유지 (제거 시 SSOT 의도 상실). 진리표 테스트(LONG-SL→2 / LONG-TP→1 / SHORT-SL→1 / SHORT-TP→2) 의무.

**영향 파일:** `tasks/live_signal.py` 또는 신규 standalone-trigger 경로 + `exit_order_mapping.py` (배선만).

**Risk:** 🟢 (현재 미소비 — 배선 시점에만 검증 필요).

---

### BL-366

**Title:** live-signal dispatch 의 OrderService DI 인라인 조립 중복 (HTTP `get_order_service` 와 drift)
**Category:** Trading / Architecture (locality / DI-dup)
**Priority:** P2
**Trigger:** trading deepening sprint 또는 OrderService 의존성 추가 시
**Est:** S-M (3-5h)
**출처:** [`docs/dev-log/2026-06-26-trading-deepen-2.md`](dev-log/2026-06-26-trading-deepen-2.md)

**원인 / 영향:** `tasks/live_signal.py:650-682` 가 OrderService + 9 deps(order/account/kse repo, crypto, `BybitFuturesProvider()`, exchange_svc, 2 evaluator, ks_svc) 를 **인라인 조립** — `dependencies.py get_order_service`(HTTP 경로) 와 별도. 신규 인스턴스 vs singleton provider, threshold 값 등 **config drift** + 한쪽만 테스트되는 blind spot. money-path 조립이라 drift 시 dispatch 와 HTTP 가 다른 동작.

**권장 접근:** 공유 factory `create_order_service_for_dispatch(session, crypto=None)` 추출 → HTTP `get_order_service` 와 Celery dispatch 양쪽이 호출. (트레일링 안정화 후 — money-path churn 회피.)

**영향 파일:** `tasks/live_signal.py` + `trading/dependencies.py` + (선택) 신규 factory module.

**Risk:** 🟡 (money-path 조립 — CCXT 호출 전 조립 경로라 신중).

---

### BL-368

**Title:** `_merge_exit_params` 가 ccxt 키명 문자열을 3 call site 로 누설 (shallow interface)
**Category:** Trading / Architecture (shallow interface / information hiding)
**Priority:** P2
**Trigger:** trading deepening sprint 또는 4번째 provider / exchange 추가 시
**Est:** S-M (3-5h)
**출처:** [`docs/dev-log/2026-06-26-trading-deepen-2.md`](dev-log/2026-06-26-trading-deepen-2.md)

**원인 / 영향:** `providers.py:135-207` 의 `_merge_exit_params` 가 `client_order_id_key`/`trigger_by_key`/`trigger_direction_key`/`trailing_stop_key` 등 **ccxt 필드명을 caller 가 알아야 하는 param** 으로 받음 → 3 call site(`:299/:480/:752`)가 `"orderLinkId"`/`"triggerBy"` 등 문자열을 분산 보유. exchange-specific 지식이 함수 안에 은닉되지 못함 → 새 exchange 추가 시 call site 마다 키 지식 복제.

**권장 접근:** `build_ccxt_params_for_order(exchange_name: ExchangeName, order: OrderSubmit) -> dict` 로 exchange→키명 dispatch 를 함수 내부로 은닉 (call site 는 ExchangeName 만 전달). lateral move + money-path 라 ccxt 전수 검증 필요.

**영향 파일:** `providers.py` (`_merge_exit_params` + 3 call site).

**Risk:** 🟡 (money-path ccxt 전수 검증).

---

### BL-369

**Title:** 3 provider `create_order` 의 try/except/finally + receipt 정규화 ~40 LOC 복붙
**Category:** Trading / Architecture (DRY / locality)
**Priority:** P2
**Trigger:** trading deepening sprint 또는 provider 예외 처리 변경 시
**Est:** S (2-4h)
**출처:** [`docs/dev-log/2026-06-26-trading-deepen-2.md`](dev-log/2026-06-26-trading-deepen-2.md)

**원인 / 영향:** `providers.py:279-349`(BybitDemo) / `:431-529`(BybitFutures) / `:728-795`(OkxDemo) 의 `create_order` 가 동일한 `try / except ProviderError / except ccxt BaseError / except Exception / finally close` + receipt 정규화 ~40 LOC 를 character-identical 복붙. 예외 처리 1곳 변경 시 3곳 동기화 누락 위험.

**권장 접근:** `_execute_create_order_with_ccxt(exchange, symbol, type, side, amount, price, params, timer_label) -> OrderReceipt` helper 추출 → 각 provider 는 client 구성 + helper 호출. money-path 라 거래소별 미세 차이 보존 검증 필요.

**영향 파일:** `providers.py` (3 provider create_order).

**Risk:** 🟡 (money-path — 거래소별 분기 보존 검증).

---

### BL-372

**Title:** STEP B 트레일링 live-placement — 3-리뷰어 검증 follow-up 번들 (9 항목)
**Category:** Trading / money-path / Architecture / Security / Tests
**Priority:** P2 (bundle — 개별 항목 P2/P3 혼재)
**Trigger:** Wave 3 실자금 cutover 전 (데모 기간엔 고정 bracket SL floor 가 모든 손실 경로 보호)
**Est:** M (6-10h, 항목별 분리 가능)
**출처:** 2026-06-26 트레일링 PR 3-리뷰어 검증 (codex CLI + Opus 6-lens 워크플로 + adversarial verify). P1 blocker 0.

**원인 / 영향:** STEP B 머지 전 Tier-1(false-flat 재시도 + 3 P2 테스트)은 본 PR 에서 해소. 아래는 adversarial 검증 통과한 잔여 follow-up. 전부 degraded-protection / 방어심화 / 문서 수준 (현재 무버그 또는 narrow). 라이브 실자금 진입 전 처리 권장.

- **(P2, money-path) same-side stale 오부착** — 🟡 **Mitigated — common path (2026-06-29, `fix/trailing-372-same-side-stale`).** `_do_place_trailing_stop` 가드가 flat/flip 만 차단하던 것에 **createdTime ↔ filled_at 불변식** 추가: `PositionInfo.created_at`(Bybit raw `info.createdTime`/`createdAt`, ADD 시 불변 — ccxt normalized `timestamp` 가 아닌 raw 사용으로 ADD 오탐 회피[G1]) > `order.filled_at` + 2s tol → reopened 판정 → benign skip(`skipped_position_reopened` metric). 타임스탬프 결측 시 side-only degrade. placement 창의 **common(>2s) 구간을 닫음**(원 버그의 ~30s 창 대부분). 검증 = G1 codex(GO_WITH_FIXES) → TDD(매핑 4 + 가드 7 + session 전달 1 + helper 단위 1) → G2 codex(NO_GO=완전성 기준, 잔여 지적) + G3 fresh(SOUND, **mutation 4/4 catch**). **잔여(narrow, 전부 [BL-375](#bl-375)): (a) sub-2s reopen (b) fetch↔set TOCTOU (c) reconcile-lag late filled_at (d) worker clock-skew>2s false-skip.** 데모 기간 = 고정 bracket SL floor 가 손실 경로 보호. (이력) codex Evaluator(2026-06-28) [P1] = 실자금 cutover 전 필수 → common path 해소, 완전 닫기는 BL-375(거래소 fill-time).
- **(P2) tick-normalization** — `set_trading_stop` 가 `trailingStop` distance 를 price precision 정규화 없이 raw `str(Decimal)` 전송 → coarse-tick 심볼 Bybit 거부 가능(fail-safe: 거부→retry→critical alert). `providers.py:586-591`.
- **(P3, architect) 하드코딩 provider** — `_place_trailing_stop_with_session` 가 `BybitFuturesProvider()` 직접 생성, dispatch registry 우회(LESSON-063). Protocol 미노출 강제 + live=BL-003 stub 라 현재 무버그. 2nd native-trailing 거래소 추가 시 SSOT 라우팅. `tasks/trading.py:954-958`.
- **(P3, architect) hedge-mode 가정** — `fetch_position` first-size>0 = one-way mode 암묵 가정. hedge-mode 면 wrong-leg 가능(expected_side 가드가 benign skip 으로 중화). 문서화 또는 side/positionIdx 필터. `providers.py:637-644`.
- **(P3, money-path) docstring 모순** — `set_trading_stop` docstring 이 "독립 fetch_position 사후검증" 주장하나 미구현(ccxt retCode raise 로 실거부는 잡힘). 주석 정정 또는 재조회 구현. `providers.py:598`.
- **(P3, security) kill-switch bypass 2nd-line 부재** — trailing placement 가 kill-switch 우회(엔드포인트가 포지션 증가 불가 전제). `reduceOnly`/`positionIdx`/ccxt-version-assert 등 belt-and-suspenders 없음. one-way 모드선 exit-side market 이 포지션 close 라 framing 다소 과장. `providers.py:600` / `tasks/trading.py`.
- **(P3, security) alert 정보 노출** — catch-all `str(exc)` 가 미정제로 Slack 전송(사설 채널, api_secret 부재이나 sign-error 시 public apiKey/params 가능). classified reason 만 전송 + raw 는 `logger.exception`(team 기존 stance `providers.py:357` 정합). `tasks/trading.py:980-990,1007-1015`.
- **(P3, qa) 회귀 가드 2건** — `leverage is None` spot-skip 분기 + `expire_on_commit=False` 불변식 (4 enqueue 사이트 post-commit attr read load-bearing) 전용 테스트 신설.
- **(P3, ponytail) dead param cut** — `set_trading_stop` 의 `trigger_price`/`trailingTriggerPrice`(activePrice) 라이브 caller 0 + 그 테스트(~17L) 제거 (activation-price 스토리 실현 시 재추가).

**Risk:** 🟢 (전부 degraded-protection / 방어심화 / 문서 — 데모 기간 bracket SL floor 보호).

---

### BL-373

**Title:** OCO 형제취소 (sibling-cancel) — standalone exit order 시점에 구현
**Category:** Trading / money-path
**Priority:** P2 (defer)
**Trigger:** BL-365 standalone-trigger 발주 도입 시 (= app-side OCO 가 실제 필요해지는 시점)
**Est:** S-M (3-5h)
**출처:** 2026-06-28 grilling (트레일링 후속 scope 결정)

**원인 / 영향:** `oco_group_id` DB 컬럼 + OrderSubmit 전달은 이미 존재하나 sibling-cancel 오케스트레이션은 미구현. 현재는 entry-attached bracket 이라 거래소가 네이티브 OCO(한 다리 체결 시 형제 자동취소)를 처리 → app-side sibling-cancel 은 YAGNI. standalone exit order(BL-365) 발주 시점에 두 다리가 독립 주문이 되면 그때 app-side 형제취소가 필요.

**Risk:** 🟢 (현재 네이티브 OCO 로 커버 — defer 안전).

---

### BL-374

**Title:** pine_v2 interpreter na-semantics — `x/0` · `math.sqrt(-1)` 등 raw Python 예외를 Pine `na` 로 정규화
**Category:** Strategy / pine_v2 (interpreter robustness)
**Priority:** P2
**Trigger:** pine_v2 robustness sprint 또는 사용자 div-by-zero/도메인 오류 전략 제보 시
**Est:** M (4-6h)
**출처:** 2026-06-28 BL-362 G2 codex challenge (live 발산 observability)

**원인 / 영향:** pine_v2 인터프리터가 `/`(`operator.truediv`)·`math.sqrt`·`math.log` 등에서 raw Python 예외(`ZeroDivisionError`/`ValueError: math domain error`)를 그대로 전파한다. TradingView Pine 의미상 `1/0`·`math.sqrt(-1)` 은 `na` 를 반환해야 한다(crash 아님). 이 예외들은 `PineRuntimeError` 가 아니라서 `run_historical(strict=False)` 의 `except PineRuntimeError` 가 안 잡고 `run_live` 밖으로 raise → 백테스트는 실패, **라이브는 BL-362 가 `run_live_error` 로 fail-closed 세션 비활성화**(crash-loop 차단). 즉 현재는 안전하지만, 정상 작동하는 TradingView 전략이 우리 인터프리터에선 비활성화되는 false-positive 가 남는다.

**권장 접근:** `BinOp` Div/Mod 0-분모 → `na`(float nan), `math.sqrt/log/...` 도메인 밖 입력 → `na` 로 정규화(Pine 의미 일치). stdlib/interpreter 산술 경로에 na-guard 추가 + 골든 테스트(`1/0 == na`, `sqrt(-1) == na`). 완료 시 BL-362 의 `run_live_error` 비활성화는 진짜 구조적 crash(parse error 등)에만 발생.

**Risk:** 🟢 (BL-362 fail-closed 로 라이브 money-path 는 이미 안전 — 본 BL 은 false-positive 정밀도 개선).

---

### BL-375

**Title:** trailing same-side stale — 완전 닫기 (거래소 fill-time 소싱 + TOCTOU/sub-tol 잔여)
**Category:** Trading / money-path
**Priority:** P2
**Trigger:** Wave 3 실자금 cutover 전 (데모 기간엔 고정 bracket SL floor 가 손실 경로 보호)
**Est:** M (4-8h)
**출처:** 2026-06-29 BL-372 same-side stale fix 의 G1/G2 codex Evaluator (BL-372 가 common path 만 닫음)

**원인 / 영향:** BL-372 가드(`position.createdTime > order.filled_at + 2s`)는 placement 창의 common(>2s) 구간만 닫는다. 4 narrow 잔여:
- **(a) sub-tolerance reopen** — fill 후 2s 내 close+reopen 은 미탐(2s 는 clock-skew 흡수용 tolerance). codex G2 [P1].
- **(b) fetch↔set TOCTOU** — `_do_place_trailing_stop` 가 createdTime 을 read 한 뒤 `set_trading_stop` 보내는 ms 윈도에 reopen 되면 거래소가 현재 포지션에 부착(check-then-act inherent race). codex G2 [P1].
- **(c) reconcile-lag late filled_at** — `filled_at` 은 fill *처리* 시각(`datetime.now(UTC)`)이지 거래소 체결 시각이 아님. reconcile 경로(watchdog/reconciler)에선 실제 체결보다 늦게 기록 → reopened `createdTime < filled_at` 이면 가드 통과. codex G1 [P1-3].
- **(d) worker clock-skew** — worker clock 이 거래소보다 >2s 느리면 정상 open 도 `createdTime > filled_at + 2s` 로 false-skip(저위험: trailing 미부착, bracket SL floor 유효). codex G2 [P2].

**권장 접근:** 근본 = **거래소 보고 체결 시각 소싱**. 4 fill-recording 경로(sync receipt / WS event / watchdog / reconciler)에서 exchange order/exec timestamp 추출 → 비교 기준으로 사용(전용 컬럼 또는 전달) → (c)(d) 해소. (a)(b) inherent race 는 거래소-side conditional(예 createdTime 조건부 trading-stop) 또는 placement 전 재확인(refetch-after-set verify)으로 좁힘. clock-skew 는 NTP 전제 문서화.

**Risk:** 🟡 (전부 narrow residual — common WS/sync path 는 BL-372 로 차단, 데모 bracket SL floor 보호. 실자금 cutover 전 처리 권장).

---

## P3 — Nice-to-have / 컨벤션 정합

> 12 archived ([BL-050/051/052/053/054/055/056/057/138/139/151/153](refactoring-backlog/_archived.md#p3-전부-nice-to-have-컨벤션-정합)). **활성 P3 = 5** (BL-306/307 2026-05-15 CLAUDE.md align audit + BL-367/370/371 2026-06-26 trading-deepen-2).

### BL-306

**Title:** `~/.claude/CLAUDE.md` §5 한국어 콜론 종결 lint mechanism 도입
**Category:** Docs / Lint
**Priority:** P3
**Trigger:** 누적 위반 181 line 검출 (2026-05-15 audit) — auto-fix 가능
**Est:** S (3-5h)
**출처:** [`docs/dev-log/2026-05-15-claudemd-align-audit.md`](dev-log/2026-05-15-claudemd-align-audit.md) §6 Track C1, [LESSON-068](.ai/project/lessons.md)

**현 상태:** docs/dev-log 161 + dogfood 12 + guides 8 = 181 line 한국어 sentence + `:` end-of-line 위반. false positive 0. lint mechanism 0 = LLM 매 generation 자연 위반.

**권장 접근:**

1. markdownlint custom rule 또는 ruff custom plugin 으로 한국어 콜론 종결 검출 (regex `[가-힣]+\s*:\s*$` minus 코드 fence + URL + table cell + frontmatter)
2. auto-fix script — 검출 line `:` → `.` 일괄 sed (false positive 0 검증된 docs/\* scope 만)
3. pre-commit hook 추가 + CI gate
4. LESSON-068 2/3 누적 → 3차 시 `.ai/common/global.md` §5 mechanism 의무 영구 승격

**영향 파일:** 새 lint config 1 + auto-fix script 1 + pre-commit hook 1 + 검출 181 line edit (auto-fix 1회).

**Risk:** 🟢 (lint + docs only, code 영향 0).

---

### BL-307

**Title:** `~/.claude/CLAUDE.md` §6 한국어 file header lint + 누락 70 file backfill
**Category:** Lint / Source
**Priority:** P3
**Trigger:** 누적 누락 70 file 검출 (BE 14 + FE 56, 2026-05-15 audit). main.py / core/config.py / trading/registry.py / app/layout.tsx 등 핵심 file 포함
**Est:** M (8-12h — lint rule 4-6h + 70 file 의미 있는 한국어 1줄 주석 작성 4-6h)
**출처:** [`docs/dev-log/2026-05-15-claudemd-align-audit.md`](dev-log/2026-05-15-claudemd-align-audit.md) §6 Track C2, [LESSON-068](.ai/project/lessons.md)

**현 상태:** BE 14/157 (8.9%) + FE 56/243 (23%) = 70 file 신규 source 첫 3줄 한국어 주석 누락. config / test / **init** / index.ts / \*.d.ts 제외. ESLint custom rule 부재 + ruff custom rule 부재.

**권장 접근:**

1. ESLint custom rule (`require-korean-file-header.js`) — 첫 3줄 안 한국어 char 검출 의무. exempt list = config / test / spec / d.ts / index / generated.
2. ruff custom plugin 또는 pre-commit hook 으로 .py file 동일 검증.
3. 누락 70 file 일괄 한국어 1줄 주석 추가 (의미 = file 역할 한 줄 — LLM 일괄 생성 가능).
4. CI gate + pre-commit hook 추가. 신규 file 차단 mechanism.

**영향 파일:** ESLint config 1 + ruff config 1 + pre-commit hook 1 + 70 file 첫 줄 주석 추가.

**Risk:** 🟡 (lint config 변경 + 70 file touch — risk 낮으나 large diff).

**의존성:** BL-306 과 묶음 sprint 가능 (양쪽 모두 lint mechanism + 누적 누락 backfill).

---

### BL-367

**Title:** `_async_dispatch_event` 205 LOC + 8× `mark_failed+commit+metric` 반복 블록 추출
**Category:** Trading / Architecture (shallow-by-size)
**Priority:** P3
**Trigger:** trading deepening sprint (clean win, 단독 가치 낮음)
**Est:** XS-S (1-2h)
**출처:** [`docs/dev-log/2026-06-26-trading-deepen-2.md`](dev-log/2026-06-26-trading-deepen-2.md)

**현 상태:** `tasks/live_signal.py` `_async_dispatch_event`(:572-776, 205 LOC, nesting 4-5) 안에 `await event_repo.mark_failed(...) + commit() + qb_live_signal_dispatch_total.labels(...).inc() + return/raise` 패턴이 8회 반복(session_inactive / strategy_missing / invalid_settings / settings_unset / rejected / kill_switched / NotionalExceeded계열 / idempotency_conflict).

**권장 접근:** `_mark_failed_and_return(event_id, error, action, outcome, repo) -> dict` + `_mark_failed_and_raise(...)` 추출 → 함수 길이/중첩 감소. 단일 파일, 저위험 clean win.

**영향 파일:** `tasks/live_signal.py`.

**Risk:** 🟢 (단일 파일, 동작 불변).

---

### BL-370

**Title:** exit-field multi-SSOT — 8 필드 × OrderSubmit/Order/OrderRequest 평행 재정의
**Category:** Trading / Architecture (locality / distributed schema)
**Priority:** P3
**Trigger:** exit-field 추가 시 3곳 동시 수정이 부담될 때 (현재는 견딜 만함)
**Est:** S-M (3-5h)
**출처:** [`docs/dev-log/2026-06-26-trading-deepen-2.md`](dev-log/2026-06-26-trading-deepen-2.md)

**현 상태:** `reduce_only`/`trigger_price`/`trigger_by`/`take_profit`/`stop_loss`/`trigger_direction`/`oco_group_id`/`trailing_stop` 8 필드가 `OrderSubmit`(dataclass, providers.py:67-83) / `Order`(SQLModel, models.py:193-218) / `OrderRequest`(pydantic, schemas.py:60-71) 3 boundary type 에 동일 타입·주석으로 재정의 (+ LiveSignalEvent subset). 필드 추가 시 3곳 동시 수정.

**권장 접근:** `ExitFields` mixin/base 추출 검토 — **단 3 base(dataclass/SQLModel/pydantic)를 가로지르는 mixin 은 awkward → over-abstraction 함정 주의.** ROI 낮으면 보류. 등재 = 가시성 확보용.

**영향 파일:** `providers.py` / `models.py` / `schemas.py`.

**Risk:** 🟡 (3 base 가로지르는 추상화 — 잘못하면 복잡도 증가).

---

### BL-371

**Title:** ws-stream 고빈도 fill 스트레스 — orphan buffer cap 1000 + concurrent 순서 미검증
**Category:** Trading / Hardening (observability)
**Priority:** P3
**Trigger:** post-Beta 실거래 빈도 상승 시 (monitor)
**Est:** S (2-4h)
**출처:** [`docs/dev-log/2026-06-26-trading-deepen-2.md`](dev-log/2026-06-26-trading-deepen-2.md)

**현 상태:** `state_handler.py` orphan buffer FIFO cap 1000(`_ORPHAN_MAX`) + out-of-order WS fill message / supervisor crash-restart cycle 가 고빈도(>100 fills/s) 스트레스 테스트 미검증. 현재 데모 빈도엔 충분.

**권장 접근:** post-Beta 모니터링(`qb_ws_orphan_buffer_size` gauge alert >800) + 필요 시 concurrent ordering 테스트 추가. 현재는 등재만.

**영향 파일:** `trading/websocket/state_handler.py` + 테스트.

**Risk:** 🟢 (현재 미발현, monitor).

---

## Beta 오픈 번들 — 단일 milestone

> **deferred** — Beta 본격 진입 trigger (BL-005 self-assessment ≥ 7/10 + 본인 의지 second gate) 도래 시 main 으로 row 이동.
>
> 상세 sub-task ([BL-070~075](refactoring-backlog/_deferred.md#beta-본격-진입-milestone-bl-070075)) + TODO.md L748~801 보존.

---

## Cross-reference

### ADR ↔ Backlog

| ADR                                                                                      | 미해소 BL                                           |
| ---------------------------------------------------------------------------------------- | --------------------------------------------------- |
| [ADR-005](dev-log/005-datetime-tz-aware.md) DateTime tz-aware                            | (Sprint 5 backfill 완료, 잔여 없음)                 |
| [ADR-011](dev-log/011-pine-execution-strategy-v4.md) Pine Execution v4                   | (Path γ/δ archived — BL-040/041)                    |
| [ADR-020](dev-log/020-trust-layer-ci-design.md) Trust Layer CI (구 ADR-013)              | BL-026 (skip 활성화 회귀), BL-023 (KIND-B/C 정밀도) |
| [ADR-016](dev-log/016-sprint-y1-coverage-analyzer.md) Coverage Analyzer                  | (BL-037 archived)                                   |
| [ADR-018](dev-log/018-sprint12-ws-supervisor-and-exchange-stub-removal.md) WS Supervisor | BL-014 (partial fill), BL-015 (OKX WS)              |

### Lessons ↔ Backlog

| LESSON                                                     | 미해소 BL                                 |
| ---------------------------------------------------------- | ----------------------------------------- |
| LESSON-019 (commit-spy 회귀 의무화)                        | (BL-010 archived, 4 도메인 backfill 완료) |
| LESSON-007/008/009 (autonomous-parallel-sprints BUG-1/2/3) | BL-025 (스킬 patch)                       |

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
2. 다음 BL ID 부여 (현재 사용 범위: BL-001~005, BL-010~243)
3. 표준 8 필드 모두 채우기: ID / 제목 / 카테고리 / priority / trigger / est / 출처 / 권장 접근
4. 출처 cross-link (파일:라인 또는 dev-log 파일명) 필수
5. 의존성 있으면 명시 (다른 BL ID 또는 외부 자원)
6. CLAUDE.md / dev-log / TODO.md 의 자연어 표현 옆에 ` → BL-XXX` cross-link 추가

### 항목 해소

1. 해당 BL 절에 `**Status:** ✅ Resolved (2026-XX-YY, PR #NN)` 추가
2. [`_archived.md`](refactoring-backlog/_archived.md) 의 Resolved 테이블에 1-line row 추가
3. 본 문서에서 본문 + main table row 제거
4. 출처 (CLAUDE.md / TODO.md) 의 cross-link 옆에 `(✅ Resolved BL-XXX)` 표기
5. "변경 이력" 섹션에 한 줄 기록

### Trigger 도래 확인

신규 sprint 진입 시:

1. 본 문서 P0 섹션 전체 review — trigger 도래 항목이 있는가?
2. P1~P2 섹션의 trigger 도 함께 review (예: "Bybit Demo 안정화 후" → 현재 안정화 됐는가?)
3. [`_deferred.md`](refactoring-backlog/_deferred.md) 의 6-8주 재평가 (BL-005 본인 의지 second gate, BL-070~075 Beta milestone)
4. 도래 항목이 있으면 active TODO.md 의 "Next Actions" 로 승격 + 본 문서에서 `**Status:** 🟡 In progress (Sprint NN)` 마킹

---

## 변경 이력

> Sprint 별 BL 변경 1-line 요약. 상세는 [`dev-log/INDEX.md`](./dev-log/INDEX.md) 또는 해당 sprint dev-log.

### `/deepen-modules trading` 2차 audit-only (2026-06-26, 트레일링 live-placement 직전)

- Wave 1/2/3(라이브 TP/SL) 누적 부채 7건 신규: P2 BL-365(trigger_direction dead+미배선) / BL-366(dispatch DI 중복) / BL-368(`_merge_exit_params` ccxt-key 누설) / BL-369(create_order 3×복붙), P3 BL-367(dispatch boilerplate) / BL-370(exit-field multi-SSOT) / BL-371(ws-stream fill 스트레스). 3 병렬 Explore + adversarial 검증(Agent 2건 과대평가 교정: trigger_direction=현재 버그 아님 latent / risk-sizing test 7건 존재→STOP 미발동). [`2026-06-26-trading-deepen-2.md`](dev-log/2026-06-26-trading-deepen-2.md). BL-202/205 와 무중복. money-path churn 회피로 **리팩터는 트레일링 안정화 후** — C1(BL-365)도 trading-stop 엔드포인트(position-inferred)라 트레일링 미소비, deferred 확정.

### Track B `/deepen-modules trading` audit-only (2026-05-15)

- BL-308 P1 (websocket test coverage 4% → ≥70%) + BL-309 P2 (registry/webhook/fees 0% test 추가) 신규. 15 → 17 active. [`2026-05-15-trading-deepen.md`](dev-log/2026-05-15-trading-deepen.md). **Architectural debt 적음** 결론 (Deep module + dispatch dict + 0 SSOT 중복). skill STOP condition (test coverage <70%) 매치 = test 우선 권고.

### CLAUDE.md align audit Track C (2026-05-15)

- BL-306 (§5 한국어 콜론 종결 lint) + BL-307 (§6 한국어 file header lint + 70 file backfill) 신규 P3. 13 → 15 active. [`2026-05-15-claudemd-align-audit.md`](dev-log/2026-05-15-claudemd-align-audit.md). LESSON-068 1/3 등재.

### Sprint 59 — PR-D 트리아주 (2026-05-13)

- 158 BL → 13 Active + 8 Deferred + 137 Archived. [`_archived.md`](refactoring-backlog/_archived.md) + [`_deferred.md`](refactoring-backlog/_deferred.md) 신설.

### 최근 sprint (Sprint 53~58)

- **Sprint 58** (2026-05-11) — BL-241/242/243 Pine TA 확장 Resolved (ta.wma/hma/bb/cross/mom/obv+fixnan + strategy.equity + UTC 라벨). 92 → 89. [`sprint58-close`](dev-log/2026-05-11-sprint58-close.md).
- **Sprint 57** (2026-05-11) — BL-234 Optimizer Polish (prior=normal+one_hot+roulette) + BL-237 optimizer_heavy queue Resolved. 신규 BL-241~243. 91 → 92. [`sprint57-close`](dev-log/2026-05-11-sprint57-close.md).
- **Sprint 56** (2026-05-11) — BL-233 Genetic executor 본격 Resolved + 신규 BL-238/239/240 chore. 91 net.
- **Sprint 55** (2026-05-11) — BL-232 Bayesian executor 본격 Resolved + 신규 BL-233~237 (5건). 88 → 92. [`sprint55-master`](dev-log/2026-05-11-sprint55-master.md).
- **Sprint 54** (2026-05-12) — Phase 3 Optimizer 본격 진입 (Grid Search MVP). BL-226/227/228/229/230/231 Resolved. 93 → 88.
- **Sprint 53** (2026-05-11) — Optimizer prereq spike. BL-226 Resolved + BL-227~231 신규.

### 이전 sprint (Sprint 15~52, 1-line 요약)

- **Sprint 52** (2026-05-11) — Stress Test follow-up. BL-222~225 Resolved + BL-226 신규.
- **Sprint 51** (2026-05-11) — BL-220 Param Stability MVP Resolved + BL-222~225 신규.
- **Sprint 50** (2026-05-10) — Cost Assumption Sensitivity 본격. BL-219 Resolved.
- **Sprint 45** (2026-05-09) — Surgical Cleanup #4/#3. dashboard-shell 추출 + codex G.4. 신규 BL-195. 92 → 93.
- **Sprint 42** (2026-05-08) — Phase 1.1/1.2 demo onboarding. 신규 BL-193/194. 90 → 92.
- **Sprint 41** (2026-05-07) — 외부 demo 첫인상 패키지. 신규 BL-190/191/192. 87 → 90.
- **Sprint 39** (2026-05-07) — BL-189 Resolved. 88 → 87.
- **Sprint 38** (2026-05-07) — BL-181 Resolved + BL-189 신규 P0.
- **Sprint 37** (2026-05-06) — polish iter 5 (BL-183/184/185/187/187a/188a Resolved, 6건) + 신규 BL-186/188. 86 → 88.
- **Sprint 36** (2026-05-06) — polish iter 4. BL-150/176 Resolved + BL-183 신규.
- **Sprint 35** (2026-05-05) — polish iter 3 + Day 7 4중 AND gate. BL-178/180 Resolved + BL-181/182 신규.
- **Sprint 34** (2026-05-05) — BL-175 Resolved + BL-177 partial + BL-166 cancel + 신규 BL-177-A/B/C/178/179. 80 → 86.
- **Sprint 33** (2026-05-05) — BL-164 Resolved + 신규 BL-175/176/177. 80 net.
- **Sprint 32** (2026-05-05) — Surface Trust Recovery (7 Resolved). 87 → 80. [`sprint32-master-retro`](dev-log/2026-05-05-sprint32-master-retrospective.md).
- **Sprint 27** (2026-05-04) — dogfood Day 1-7 launch. 신규 BL-137~141. 76 → 81.
- **Sprint 25 Hybrid** (2026-05-03) — Frontend E2E Playwright. 5 Resolved + 14 신규.
- **Sprint 21** (2026-05-02) — BL-093/095/097 Resolved + BL-096 partial + 신규 BL-098/099/100.
- **Sprint 18** (2026-05-02) — BL-080 Option C persistent worker loop Resolved.
- **Sprint 17** (2026-05-02) — prefork-safe Partial fix. 신규 BL-080.
- **Sprint 16** (2026-05-01) — BL-010 commit-spy 4 도메인 backfill + BL-027 Resolved.
- **Sprint 15** (2026-05-01) — BL-001 + BL-002 Resolved + 신규 BL-027/028/029.
- **2026-04-30** — 초기 작성 50 BL (P0 5 + P1 17 + P2 14 + P3 8 + Beta 6).

> 누락 sprint (19/20/22~24/26/28~31/40/43/44/46~49)은 [`dev-log/INDEX.md`](./dev-log/INDEX.md) 본문 참조.

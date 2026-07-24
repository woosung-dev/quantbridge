# QuantBridge — Refactoring Backlog

> **Active 백로그.** 명백한 Resolved + stale 항목은 [`refactoring-backlog/_archived.md`](refactoring-backlog/_archived.md), trigger 미도래 의도적 부활 가능 항목은 [`refactoring-backlog/_deferred.md`](refactoring-backlog/_deferred.md). 정합성 검증은 [`04_architecture/architecture-conformance.md`](04_architecture/architecture-conformance.md).
>
> **신규 sprint 진입 시 본 문서 review 의무** — 각 BL 의 trigger 가 도래했는지 확인 후 active TODO 로 승격할지 결정. `_deferred.md` 도 6-8주마다 재평가.

**작성일:** 2026-04-30
**최종 갱신:** 2026-07-24 (**trading-surface-pack 스프린트** — BL-431/416/425/432/433 Resolved + 신규 BL-434~436. 코크핏 §03 TP/SL 열 + reduce-only 시장가 청산 완성.) // 이전: position-cockpit — 신규 BL-431~433.
**직전 갱신:** 2026-07-24 (**position-cockpit 스프린트** — 신규 BL-431~433. WS position 채널 + 코크핏 잔고/포지션 후속.)
**현재 상태:** **49 active BL** (trading-surface-pack 5 Resolved + 신규 3 → 51-5+3=49). **BL-070~075 milestone active 승격** (deferred → P0 prep).

**최근 sprint BL 변경 (Sprint 55~Sprint 62 Beta 진입):**

- **2026-07-24 trading-surface-pack 스프린트 (codex 2-generator ∥ + Claude 적대평가 per-worker + Opus dogfood)**: position-cockpit(#472) 후속. 코크핏 §03 포지션 표에 TP/SL 열 + reduce-only 시장가 청산 완성 + 부채 4종. **BL-431 Resolved**(BE: 포지션-보고 TP/SL read-time 0→null 정규화 + `POST /live-sessions/{id}/positions/close` reduce-only 청산 = 신규 `close_service.py` + `OrderService.execute(flatten=True)` 진입-위험 가드 ②~⑧ bypass·ownership 유지·reduce_only 불변식·**청산 leverage=포지션값**으로 set_leverage no-op·cap-bypass 방지 / FE: 익절·손절 2열 + 청산 액션·확인 모달(정직 고지)·colSpan 14) + **BL-416 Resolved**(주문취소 행별 disabled `cancelOrder.variables` + 비-409 broad toast + 실 ACTIVE_ORDER_STATES import) + **BL-425 Resolved**(alert-rule 중복 유형 사전검사 = 마운트 목록 재사용, 409 요청·콘솔 노이즈 회피) + **BL-432 Resolved**(positions select→combine 인덱스 zip + 고아 삭제) + **BL-433 Resolved**(`qb_ws_subscribe_rejected_total{account_id}` counter). 마이그레이션 0. 게이트: BE **2601**(+18) / FE **1083**(+8) / canon **32** / authed **66**(+2 코크핏 §03 구조) / build ✓ / alembic 무변경. **검증 체인**: codex G0 14건(코드 대조 후 반영, BLOCKING 3=leverage 라우팅·flatten 불변식·hedge 거부) → codex 2워커 병렬(backend/frontend 교집합 0) ↔ Claude 적대평가 per-worker(게이트 직접 실행, W1 RUF059 1건 codex resume) → 최종 codex 누적 diff(MAJOR 1=청산 leverage cap-bypass → 포지션값 사용 fix) → **Opus dogfood 2계통**(독립 Bybit HMAC 오라클 ↔ 코크핏 §03: TP/SL 값 66000/62000 정확 일치·빈값→— 정직 / 청산 종단 flat+Order row / **kill-switch 활성 청산 성공 = 가드 bypass 실증, KS 미소비** / 콘솔 error 0). 신규 **BL-434~436**.
- **2026-07-23 functional-parity 스프린트 (codex 4-generator ∥ + Claude 적대평가 + Opus dogfood)**: C 디자인 이식 후 기능 격차 마감. **BL-401 Resolved**(3폼 `formState.errors` → `.field-error` 프리미티브, superRefine 평탄 경로 row 매핑, 메시지 한국어화 — grid min>max 만 거부로 BE 계약 정합) + **BL-411 Resolved**(지원 kind 목록 `OptimizationKind` enum 파생 + Sprint 넘버 문구 중립화) + **BL-402 Resolved (구조 소멸)** — C 이식이 4사이트 전부 네이티브 `<select>` 로 재작성해 uncontrolled/raw-UUID 결함 자체가 소멸(실측 재확인, 코드 변경 0). 신규 A2(주문취소 액션 열 — "API 없음" 미렌더 전제가 거짓이었음, CF4 완비)·B2(orders state 반복 Query + 미체결 nav-count 캐논 §4.6 복원)·B1(strategy.backtest_count read-time GROUP BY, COMPLETED 기준)·A7-lite(스트레스 최신 결과 리로드 복원)·A1(대시보드 전략 링크 404→edit). 게이트: vitest 965→980 / BE 2416+18 / canon 32 불변 / authed 56→62. 신규 **BL-413~416**. **Opus MCP dogfood(10항목)가 잠복 P1 2건 추가 발굴·동일 스프린트 해소**: (a) stress_test enum 혼합 케이싱 — 최초 migration 소문자 라벨 vs SAEnum 대문자 저장으로 실 DB 에서 MC/WF 생성 전부 500 → RENAME VALUE migration `20260723_0001` + alembic-경로 enum 라벨 sentinel 테스트(즉시 status enum 드리프트도 추가 검출). (b) provider cancel_order 전 구현이 ccxt 에 symbol 미전달 — 실거래소 취소가 전부 ArgumentsRequired(CF4 fail-closed 로 submitted 영구 잔존, BL-404 동형) → Protocol+5 provider symbol 관통 + futures linear 정규화. dogfood 최종 V1~V10 전 항목 PASS (취소 200/202 실클릭 + DB 오라클 3점 + A7-lite 리로드 복원 실측).

- **2026-06-30 stress_test-deepen (deepen-modules)**: stress_test 도메인 1차 deepen (`/deepen-modules`, 코드 변경 0). C1 = **BL-363 sharpen**(money-path framing + git 실증 `6c7adfba`→`ffb2299b` + `_load_run_context`/`_execute_grid_sweep` 구체 인터페이스) / C2 = 신규 **BL-392**(CA/PS "2D grid sweep" DTO 8-site 평행 정의 통합, untyped JSONB seam). 거부 = C3(`StressTestKind` dispatch registry — blast radius 최대 + 4타입 over-eng, 5번째 타입 등장 시 재평가) / C4(invariant SSOT — C2 graft 권장). engine 은 이미 `run_grid_sweep` 공유 = Deep 유지(건드리지 않음). dev-log [`2026-06-30-stress_test-deepen.md`](dev-log/2026-06-30-stress_test-deepen.md).
- **2026-06-30 backtest-deepen (verification loop)**: backtest 도메인 1차 deepen (improve-codebase-architecture + codex challenge, 코드 변경 0). 신규 **BL-387~391** (5건) — BL-387 sizing-canonical typed seam(P2 money-path) / BL-388 BacktestMetrics 4-site multi-SSOT(P2) / BL-389 finance-math `engine/metrics.py` 추출(P3) / BL-390 exit `fill_type` 중복 위임(P3) / BL-391 equity↔PnL reconciliation oracle(P3 test-first). codex KILL C3(idempotency dual-lock 통합 = 의도적 layered + 잘 테스트됨) → [ADR-021](dev-log/021-backtest-idempotency-dual-lock.md). **codex C1 DOWNGRADE 는 phantom `metrics.py` 오인 → 직접 검증 후 KEEP 정정**(§7.3 circular-trust 차단). dev-log [`2026-06-30-backtest-deepen.md`](dev-log/2026-06-30-backtest-deepen.md).
- **2026-06-30 BL-378 Resolved (`fix/pine-378-atr-wilder`)**: pine_v2 `ta.atr` 가 Wilder RMA (TV `ta.atr = ta.rma(ta.tr, len)`) 아닌 rolling SMA 사용 → 비-상수 TR(=모든 실데이터)에서 TradingView 와 silent divergence (헤드라인 harm-class). 실세계 8 전략 티어드 백테스트 QA (`docs/qa/2026-06-30-pine-tiered-backtest/report.md`) 의 大-tier anti-circular hand-oracle 에서 발견 (5중 교차검증: codex G1 + 직접 oracle 9/9 bar + generator panel discriminator + panel 실행 15.0 vs 14.818 + codex G2). 수정 = `ta_atr` 가 기존 Wilder `ta_rma` 재사용 (~2줄, seed 동일·이후 TV 정합). G1-G4 (codex G1 plan eval + Workflow 12-agent generator panel + codex G2 challenge[B1 CONFIRMED] + codex diff-challenge[no P1] + G3 fresh review + mutation 2/2 CAUGHT) + full **2301 pass** (+6 pre-existing env, stash 대조 확인) + ruff/mypy clean + trust-layer golden 재생성(s2_utbot/i1_utbot num_trades 461→433, ATR→trailing 신호 변화). migration 0. 신규 **BL-379~386** (QA 부수 발견 9건: fn-local subscript / Track A alert warning / valuewhen na 등).
- **2026-06-30 BL-376 Resolved (`fix/pine-376-na-inf`)**: pine*v2 na/inf *소비\_ 사이트 robustness (BL-374 후속). 3 사이트 — (1) na/inf/<1 → ta.\* length: `_coerce_length` 헬퍼를 14 ta 함수 + dispatcher(change/stdev/variance int() 제거) + pivothigh/pivotlow 양 window + valuewhen occurrence(별도 non-finite 가드, occ=0 보존) 에 적용 → na 반환. (2) na/inf qty → `StrategyState.entry` skip + warning (라이브 reject 미러, 유한 0.0 보존). (3) inf → `math.floor/ceil/round`(per-branch, 공유 가드 미변경 — abs/sign/max 통과 유지) / subscript offset isfinite / timestamp +OverflowError. G1-G4(codex plan eval GO_WITH_FIXES + 4-candidate generator panel byte-수렴 + codex challenge[P1 valuewhen Decimal NaN 갭 → `(float, Decimal)` 가드] + fresh review SHIP + mutation 6/6 CAUGHT) + full suite 2305 pass(cov ≥90) + Playwright E2E(na/inf 백테스트 FAILED→COMPLETED, console.error 0). migration 0. 신규 [BL-377] (deferred: non-finite 주문/청산 가격 + 초대형 유한 length OverflowError).
- **2026-06-29 BL-374 Resolved (`fix/pine-374-na-semantics`)**: pine_v2 인터프리터 산술/math 도메인 오류 → Pine `na` 정규화 (`_na_safe`, 숫자 산술 한정, `math.pow` `**`→`math.pow()`). G1-G4 게이트(codex plan eval + 3-candidate generator panel + codex challenge[F1 dead stdlib-clamp 제거 + F2 문자열 `%` fail-closed] + fresh review GO + mutation 5/5) + full suite 2226 pass(cov 95.6%) + Playwright E2E(div-by-zero 백테스트 FAILED→COMPLETED, console.error 0). 신규 [BL-376] (deferred: na→length/qty, inf→floor·ceil·round).
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

| ID                | 제목                                                                                               | Trigger                                         | Est        | 출처                            |
| ----------------- | -------------------------------------------------------------------------------------------------- | ----------------------------------------------- | ---------- | ------------------------------- |
| [BL-014](#bl-014) | Partial fill `cumExecQty` tracking                                                                 | partial fill 1건 발견 시                        | M (4-5h)   | TODO.md L709                    |
| [BL-015](#bl-015) | OKX Private WS                                                                                     | Bybit Demo 안정화 후                            | M (6-8h)   | TODO.md L710                    |
| [BL-022](#bl-022) | golden expectations 재생성                                                                         | pine_v2 `strategy.exit` 도입 후                 | M (3-4h)   | TODO.md L17 (skip #1)           |
| [BL-023](#bl-023) | KIND-B/C mutation 분류 정밀도 (xfail strict)                                                       | Trust Layer v2 검토 시                          | M (5-6h)   | TODO.md L23 (skip #16)          |
| [BL-024](#bl-024) | real_broker E2E 본 구현 (nightly cron)                                                             | Bybit Demo credentials + seed data 준비 시      | L (8h+)    | CLAUDE.md Sprint 10 Phase C     |
| [BL-025](#bl-025) | autonomous-parallel-sprints 스킬 patch                                                             | on-demand (BUG-1/2/3 재발 시)                   | S (2h)     | TODO.md L653                    |
| [BL-026](#bl-026) | mutation fixture 활성화 회귀 (skip #4-7, #9-15)                                                    | Stage 2c 2차 fixture 활성화 후                  | S (1-2h)   | TODO.md L20-22                  |
| [BL-308](#bl-308) | trading websocket test coverage 4% → ≥70%                                                          | dogfood 직후 (Day 7 후)                         | L (12-16h) | 2026-05-15 trading-deepen audit |
| [BL-404](#bl-404) | ✅ Resolved — watchdog `fetch_order` Bybit 전면 실패 (acknowledged 게이트 + futures 심볼 미정규화) | ✅ `fix/trading-bl404-fetch-order-acknowledged` | S (1-2h)   | 2026-07-05 데모 라이브 dogfood  |

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

**✅ Resolved (W3, 2026-06-29):** baseline 재측정 결과 "4%" 는 stale (2026-05-15, PR #305 money-path 감사 + TP/SL·트레일링 wave 이전). 실측 baseline = `websocket/` **85% combined branch cov** (bybit_private_stream 75% / reconciliation 90% / reconcile_fetcher 100% / state_handler 86%). W3 가 진짜 미커버 머니패스 분기만 보강 (replay_orphan / orphan TTL eviction / \_receive_loop json·topic·handler-None·exception-swallow / \_heartbeat_loop / \_maybe_reconcile 예외 / auth timeout / \_find_match orderLinkId·clOrdId fallback / Rejected 전이 / \_handle_unknown alert 예외) → **96% combined** (bybit 93% / reconciliation 97% / state_handler 96%). 잔여 미커버 = supervisor reconnect/timeout 타이밍 분기 + trivial getter (deterministic 테스트 불가 → vacuous 회피로 의도적 제외). CI `--cov-fail-under=90` ratchet 게이트 추가. 게이트: G1 codex plan + G2 codex challenge(4 P1 false-green 수정) + G3 fresh review(mutation 검증) PASS.

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

### BL-404

**Title:** watchdog `fetch_order` Bybit 전면 실패 — ccxt `acknowledged` 게이트 미대응 + futures 심볼 카테고리 미정규화 (라이브 주문 submitted 영구 고착)
**Category:** Trading / provider (money-path 안전망)
**Priority:** P1
**Trigger:** 즉시 (2026-07-05 데모 라이브 dogfood 실측 발견)
**Est:** S (1-2h) — 실측 ~1h
**출처:** 2026-07-05 데모 라이브 dogfood — 라이브 주문 9건 전부 submitted 고착 + 재현 1줄(`BybitFuturesProvider.fetch_order(creds, exid, "BTC/USDT")`)

**원인 / 영향:** 2중 결함. (1) ccxt bybit `fetchOrder()` 가 `params["acknowledged"]=True` 없이 `ArgumentsRequired` raise(last-500-orders 제약 인지 게이트) — `_bybit_fetch_order_impl` 미대응으로 watchdog `trading.fetch_order_status` 가 전량 ProviderError → 무한 백오프 재시도. (2) 게이트를 통과해도 futures fetch 가 DB `order.symbol`(spot 포맷 `BTC/USDT`)을 미정규화 전달 → ccxt market 해석이 category=spot → linear 주문 `OrderNotFound` (실 demo 대조: `BTC/USDT:USDT`=OK / `BTC/USDT`=NotFound. BL-124 정규화가 create/trailing/position 3 call-site 에만 적용, fetch 만 누락 — (1) 게이트가 가려온 latent). 결과 = 라이브 주문이 거래소에선 체결돼도 DB submitted 영구 고착 → filled_price/realized_pnl 미기록 → 코크핏 집계·kill-switch CumulativeLoss 평가 무력화. ws_stream Reconciler(fetch_open/closed/canceled 사용)가 뜨면 커버되나, ws 워커 부재 환경(host 단독 기동 등)에선 fill 확정 안전망 0겹.

**해소:** `_bybit_fetch_order_impl` 에 `params={"acknowledged": True}`(게이트 도입 전 realtime 조회 동작 복원) + `BybitFuturesProvider.fetch_order` 에 `_to_bybit_linear_symbol()` 적용. TDD(red 3 → green, `test_provider_fetch_order.py` 회귀 2건 추가) + trading 스위트 440 pass + 실 Bybit demo end-to-end(신선 주문 생성 → spot 포맷 경로 fetch `status=filled` 확인 → flatten). **잔여(후속 후보):** `fetch_mark_price` 도 spot 티커 근사 사용(동일 계열, 실패 아님 — notional 가드 정밀도) / realtime 범위(최근 500) 밖 장기 고착 주문은 여전히 미조회 → Reconciler 커버(BL-375 계열) / BL-003 mainnet 시 재점검: classic(비-UTA) live 계정 경로(`fetch_orders_classic`)에선 acknowledged 가 쿼리 param 으로 누수(현재는 live stub 이라 dead, adversarial 리뷰 footnote).

**Status:** ✅ Resolved (2026-07-05, `fix/trading-bl404-fetch-order-acknowledged`)

---

## P2 — Hardening / 건강도 작업

| ID                | 제목                                                                                                                                                           | Trigger                                                                        | Est          | 출처                                                   |
| ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ | ------------ | ------------------------------------------------------ |
| [BL-186](#bl-186) | Full leverage + funding + mm + liquidation 풀 모델                                                                                                             | Sprint 38+ (BL-185 foundation 위)                                              | M-L (16-24h) | Sprint 37 BL-185 후속                                  |
| [BL-190](#bl-190) | PDF export (jsPDF / Playwright)                                                                                                                                | 외부 사용자 요청 시                                                            | M (3-5h)     | Sprint 41 Worker H 결정                                |
| [BL-195](#bl-195) | qb-form-slide-down animation 영구 truncation                                                                                                                   | Sprint 45 codex G.4                                                            | XS (30m)     | Sprint 45 codex G.4 발견                               |
| [BL-235](#bl-235) | N-dim acquisition surface viz (Bayesian 전용)                                                                                                                  | Sprint 57+                                                                     | M (8-12h)    | ADR-013 §6 #8 deferred                                 |
| [BL-236](#bl-236) | `objective_metric` whitelist 자유화 (BacktestMetrics 24+)                                                                                                      | Sprint 56+                                                                     | S (3-5h)     | Sprint 55 deferred                                     |
| [BL-309](#bl-309) | trading registry/webhook/fees test 0% → ≥80%                                                                                                                   | BL-308 묶음 또는 dogfood 직후                                                  | M (4-6h)     | 2026-05-15 trading-deepen audit                        |
| [BL-362](#bl-362) | live 경로 coverage↔interpreter divergence silent swallow observability                                                                                         | S5 (trading kill-switch 묶음)                                                  | S (2-4h)     | 2026-05-30 full-inspection §4.3                        |
| [BL-363](#bl-363) | stress*test `\_execute*\*` 4-method boilerplate 추출 (config drift 근본원인)                                                                                   | deepening sprint 또는 5번째 engine 추가 시                                     | S (2-3h)     | 2026-05-30 full-inspection §appendix P1-9              |
| [BL-364](#bl-364) | Optimizer 진짜 string-label CategoricalField sweep (Genetic+Bayesian ordinal 인코딩)                                                                           | string 카테고리 sweep 요청 시                                                  | M (4-6h)     | 2026-05-30 full-inspection §appendix P1-9 (S4 후속)    |
| [BL-365](#bl-365) | `trigger_direction_for`/`map_exit_kind` dead + 서버 미배선 (standalone-trigger 방향)                                                                           | 서버 standalone 트리거 발주 시                                                 | S (2-4h)     | 2026-06-26 trading-deepen-2                            |
| [BL-366](#bl-366) | live-signal dispatch OrderService DI 인라인 조립 중복 (HTTP 와 drift)                                                                                          | trading deepening sprint                                                       | S-M (3-5h)   | 2026-06-26 trading-deepen-2                            |
| [BL-368](#bl-368) | `_merge_exit_params` ccxt 키명 3 call site 누설 (shallow interface)                                                                                            | trading deepening / 4번째 provider                                             | S-M (3-5h)   | 2026-06-26 trading-deepen-2                            |
| [BL-369](#bl-369) | 3 provider `create_order` try/except/finally ~40 LOC 복붙                                                                                                      | trading deepening sprint                                                       | S (2-4h)     | 2026-06-26 trading-deepen-2                            |
| [BL-372](#bl-372) | STEP B 트레일링 live-placement 3-리뷰어 검증 follow-up 번들 (9 항목, P2/P3)                                                                                    | Wave 3 실자금 cutover 전                                                       | M (6-10h)    | 2026-06-26 trailing 3-reviewer (codex+Opus 6-lens)     |
| [BL-373](#bl-373) | OCO 형제취소 (sibling-cancel) — standalone exit order 시점 구현                                                                                                | BL-365 standalone-trigger 발주 시                                              | S-M (3-5h)   | 2026-06-28 grilling (트레일링 후속 scope)              |
| [BL-374](#bl-374) | ✅ Resolved (2026-06-29) — pine_v2 interpreter na-semantics — `x/0`·`math.sqrt(-1)` 등 raw 예외 → Pine `na`                                                    | ✅ `fix/pine-374-na-semantics`                                                 | M (4-6h)     | 2026-06-28 BL-362 G2 codex challenge                   |
| [BL-375](#bl-375) | trailing same-side stale 잔여 — reconcile-lag late filled_at 시 reopen 미탐 (거래소 fill-time 소싱)                                                            | Wave 3 실자금 cutover 전                                                       | S-M (3-5h)   | 2026-06-29 BL-372 same-side stale G1 codex             |
| [BL-376](#bl-376) | ✅ Resolved (2026-06-30) — pine_v2 na/inf 소비 사이트 robustness — na/inf→ta.\* length / na/inf→entry qty skip / inf→math.floor·ceil·round·subscript·timestamp | ✅ `fix/pine-376-na-inf`                                                       | M (4-6h)     | 2026-06-29 BL-374 G1/G2/G3 + generator panel 합의      |
| [BL-377](#bl-377) | pine_v2 non-finite 주문/청산 가격 + 초대형 유한 length OverflowError (BL-376 후속 잔여)                                                                        | pine_v2 robustness 후속 또는 실자금 cutover 전                                 | S (2-4h)     | 2026-06-30 BL-376 G2 codex challenge + G3 fresh review |
| [BL-378](#bl-378) | ✅ Resolved (2026-06-30) — pine_v2 `ta.atr` rolling SMA → Wilder RMA (TV parity, headline harm-class)                                                          | ✅ `fix/pine-378-atr-wilder`                                                   | S (2-4h)     | 2026-06-30 티어드 백테스트 QA 大-tier oracle           |
| [BL-379](#bl-379) | pine_v2 user-function 지역변수 `x[1]` history = na (subscript in `=>` 깨짐, latent harm-class)                                                                 | pine_v2 robustness 후속                                                        | M (4-6h)     | 2026-06-30 QA codex G2 + 직접 재현                     |
| [BL-380](#bl-380) | Track A INFORMATION/UNKNOWN alert 무경고 drop (docstring 계약 위반) + VirtualRunResult.warnings 미전파                                                         | Track A 신뢰 표면 sprint                                                       | S-M (3-5h)   | 2026-06-30 QA LuxAlgo 0-trade                          |
| [BL-381](#bl-381) | Track A `VirtualRunResult` var_series/warnings 미반환 → trust-parity digest 공허 (i2_luxalgo 검증 vacuous)                                                     | Trust Layer CI 강화                                                            | S (2-4h)     | 2026-06-30 QA codex G2/diff                            |
| [BL-382](#bl-382) | qty=1.0 fallback sizing-source FE 미표면화 (자본초과 백테스트 투명성, mdd_exceeds_capital 은 표시됨)                                                           | sizing 투명성 sprint                                                           | S (2-4h)     | 2026-06-30 QA F1 (codex G2)                            |
| [BL-383](#bl-383) | v2_adapter catch-all 이 런타임 예외를 parse_failed 로 오분류 (관측성)                                                                                          | pine_v2 관측성 후속                                                            | S (2-3h)     | 2026-06-30 QA codex G2                                 |
| [BL-384](#bl-384) | ta.valuewhen 이 na-source occurrence skip (TV 는 na 기록)                                                                                                      | pine_v2 parity 후속                                                            | S (2-3h)     | 2026-06-30 QA codex G2 + 직접 재현                     |
| [BL-385](#bl-385) | PineVersion enum v6 부재 → `//@version=6` 가 v5 로 collapse (메타데이터 부정확)                                                                                | pine_v2 coverage 후속                                                          | XS (1-2h)    | 2026-06-30 QA F3                                       |
| [BL-386](#bl-386) | v4 bare math builtin `floor`/`ceil`/`round`/`sqrt` 미별칭 (preflight reject, over-strict)                                                                      | pine_v2 coverage 후속                                                          | XS (1-2h)    | 2026-06-30 QA F4                                       |
| [BL-387](#bl-387) | backtest sizing-canonical → config_payload 가 untyped `dict[str,Any]` seam 횡단 (key drift 시 silent 잘못된 sizing, money-path)                                | backtest deepening 또는 sizing 로직 변경 시                                    | S-M (3-5h)   | 2026-06-30 backtest-deepen (codex 최강 후보)           |
| [BL-388](#bl-388) | BacktestMetrics 24-field 가 4곳 평행 정의 (dataclass↔schema↔serializer↔_to_detail), field-parity 무검증 (leaky seam)                                           | backtest deepening 또는 BL-236 진행 시                                         | S-M (3-5h)   | 2026-06-30 backtest-deepen (codex 가 4번째 site 발견)  |
| [BL-392](#bl-392) | stress_test CA/PS "2D grid sweep" DTO 8-site 평행 정의 통합 (engine dataclass↔serializer↔OutSchema, untyped JSONB seam)                                        | stress_test deepening 또는 grid-cell 필드 추가 / 3번째 grid-sweep 타입 등장 시 | M (4-6h)     | 2026-06-30 stress_test-deepen (deepen-modules 1차)     |
| [BL-401](#bl-401) | ✅ Resolved (2026-07-23) — optimizer 3폼 field-level zod 에러 렌더 (`.field-error` + role=alert, 메시지 한국어화)                                              | ✅ `stage/functional-parity`                                                   | S-M (2-4h)   | 2026-07-05 PR #394 FE 리팩토링 번들 dogfood            |
| [BL-402](#bl-402) | ✅ Resolved (2026-07-23, 구조 소멸) — C 이식 네이티브 select 전환으로 4사이트 결함 자체 소멸 (실측 재확인, 코드 변경 0)                                        | ✅ `stage/functional-parity` (문서만)                                          | XS-S (1-2h)  | 2026-07-05 PR #394 FE 리팩토링 번들 dogfood            |

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
**출처:** [`docs/audit/2026-05-30-full-inspection.md`](audit/2026-05-30-full-inspection.md) appendix P1-9 + [`docs/dev-log/2026-06-30-stress_test-deepen.md`](dev-log/2026-06-30-stress_test-deepen.md) (deepen-modules stress_test 1차 audit — money-path 증거 + git 실증 sharpen)

**원인 / 영향:** `_execute_walk_forward`(`service.py:305-319`)/`_execute_cost_assumption_sensitivity`(`:366-384`)/`_execute_param_stability`(`:393-411`) 가 `strategy.find_by_id_and_owner → None가드 → provider.get_ohlcv → build_engine_config_from_db(bt)` prefix 를 복붙. **CA↔PS 본문은 19-LOC 중 3토큰만 차이**(에러문자열 + `run_*` engine fn + `*_to_jsonb` serializer fn). 이 분산된 boilerplate 가 실제 money-path silent corruption 으로 **한 번 물었음** — git `6c7adfba`(Sprint 52 BL-222: `build_engine_config_from_db` 를 CA/PS 에만 추가, **WF 누락**) → `ffb2299b`(WF 별도 패치). docstring `service.py:298-304` 가 증언: WF 의 IS/OOS 백테스트가 parent 의 fees/slippage/init_cash/leverage/sizing 대신 엔진 기본값으로 실행. config-build 변경 시 3곳(`:319/:377/:404`) 수동 동기화 의무 → 1곳 누락 = Celery run 성공·결과 silent 오염. 5번째 engine 도 동일 누락 위험.

**권장 접근:** `_load_run_context(st, bt) -> RunContext(strategy, ohlcv, backtest_config)` helper 추출(MC 는 equity_curve 기반이라 비대상) → `build_engine_config_from_db(bt)` single-site 화 = **BL-222 drift class 구조적 제거**. CA/PS 는 `_execute_grid_sweep(st, bt, *, engine_fn, to_jsonb)` 1메서드로 통합(engine 의미는 인자로 주입, 분리 유지). behavior-preserving 순수추출 — 기존 per-engine propagation 테스트(WF+CA+PS 각 1건) + state-isolation 가드가 안전망. **C2(BL-392) 와 묶으면 자연스러움**(grid-sweep DTO 통합과 동일 CA/PS 응집부).

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

**상태:** ✅ **Resolved (2026-06-29, `fix/pine-374-na-semantics`, commit `2cd1313`).** `_na_safe(compute)` 헬퍼(`(ArithmeticError, ValueError)` catch + complex 결과 → nan)를 `_eval_binop`(숫자 피연산자 한정 — 문자열 `%` 등 타입 오용은 fail-closed) + `math.sqrt/log/log10/exp` 에 적용, `math.pow` 는 `args[0] ** args[1]` → `math.pow()` 전환(bigint/complex 무음오염 차단). `PineRuntimeError`/`TypeError` 전파 유지(BL-362 fail-closed 유지). stdlib `ta_stdev/ta_bb` sqrt-clamp 는 G2 challenge 에서 2-pass variance ≥0 항상이라 dead-code 로 판명 → 제거(diff = `interpreter.py` + 신규 테스트만). 검증 = G1 codex plan eval + 3-candidate generator panel(core 6 edit byte-identical 수렴) + G2 codex challenge(F1 dead-clamp 제거 + F2 문자열 `%` over-catch → 숫자 한정 가드) + G3 fresh review(GO) + mutation 5/5 catch + full suite 2226 pass(cov 95.6%) + **Playwright E2E**(div-by-zero 백테스트 FAILED→COMPLETED, console.error 0). **잔여 deferred → [BL-376](#bl-376).**

---

### BL-376

**Title:** pine_v2 na/inf 소비 사이트 robustness — na→ta.\* length / na→strategy.entry qty / inf→math.floor·ceil·round
**Category:** Strategy / pine_v2 (interpreter robustness)
**Priority:** P3
**Trigger:** pine_v2 robustness 후속 또는 실자금 cutover 전 (BL-374 후속)
**Est:** M (4-6h)
**출처:** 2026-06-29 BL-374 G1 codex / G2 codex challenge / G3 fresh review + 3-candidate generator panel 합의

**원인 / 영향:** BL-374 가 산술/math _생성_ 사이트의 raw 예외를 na 로 정규화했으나, 그 na/inf 가 _소비_ 되는 다음 사이트는 여전히 raw 예외 escape 가능(전부 실측 검증, 동일 harm class = `run_historical` 밖 escape → 백테스트 FAILED / 라이브 세션 비활성):

- **na → ta.\* length:** `ta.sma(close, na)` 등이 `int(nan)`(ValueError) / `deque(maxlen=nan)`(TypeError). 단 실 TradingView 는 length=simple int 강제라 비-TV-valid 시나리오(우리 인터프리터 leniency). pre-existing.
- **na → strategy.entry qty:** `qty=close/0` → na qty → `_compute_metrics` 의 `Decimal('NaN')` 비교에서 `decimal.InvalidOperation` → status=error(**깨끗한 실패, 무음 오염 아님**). 라이브는 이미 nan qty 거부(`test_live_exit_surfacing`). 사이징을 div-by-zero 로 하는 전략은 본질적으로 broken.
- **non-raising inf → math.floor/ceil/round/subscript-int:** `1e308 * 10.0`(operator.mul, raise 안 함) → inf → `math.floor(inf)` 등 `OverflowError` escape. 3-candidate generator panel 전원 + G3 fresh review 독립 발견.

**권장 접근:** (a) ta.\* length 진입 시 na/non-finite → na 결과 정규화(또는 length 타입 강제). (b) strategy.entry/order qty 가 na/non-finite → 주문 skip(라이브 path 의 기존 nan→reject 미러). (c) inf 생성부 clamp 또는 floor/ceil/round/subscript int 변환 na-safe. 골든 테스트 동반.

**Risk:** 🟢 (전부 현재 깨끗한 실패 또는 비-TV-valid — BL-374 가 핵심 false-positive 해소, 본 BL 은 잔여 robustness).

**상태:** ✅ **Resolved (2026-06-30, `fix/pine-376-na-inf`).** 3 사이트 전부 닫음:

- **Site #1** `_coerce_length(value) -> int | None`(`not math.isfinite(value) or value < 1 → None`) 헬퍼를 14 ta 함수(sma/ema/rma/atr/rsi/highest/lowest/change/stdev/variance/wma/mom/hma/bb) + dispatcher(change/stdev/variance 의 `int()` 제거) + pivothigh/pivotlow 양 window 에 적용 → na 반환. `ta.valuewhen` occurrence 는 length 아님(0/음수 유효) → **별도 non-finite 가드**(`isinstance(occ_raw, (float, Decimal)) and not math.isfinite`). 실측 갱신: na 뿐 아니라 inf-length(`deque(maxlen=inf)` TypeError) + 초기 가드 없던 highest/lowest 의 length 0/-N(`max(empty)`/negative maxlen ValueError) 도 함께 해소.
- **Site #2** `StrategyState.entry` 에서 `not math.isfinite(qty)` → 주문 skip + warning(라이브 nan→reject 미러). 실측 갱신: **closed na-qty 는 깨끗한 실패였으나 _open_ na-qty 는 status='ok' 인데 equity NaN 무음 오염** = 실제 버그 → skip 으로 양쪽 통일. `qty<=0` 미skip(compute_qty 의 유한 0.0 보존).
- **Site #3 (소비부 가드, 사용자 결정)** `math.floor/ceil/round` per-branch `not math.isfinite → na`(공유 `any(_is_na)` 가드 미변경 → `math.abs/sign/max/min/sqrt/log` 의 inf 통과 유지) + subscript offset `not math.isnan` → `math.isfinite` + timestamp `int()` except 에 `OverflowError` 추가.

검증 = G1 codex plan eval(GO_WITH_FIXES) + 4-candidate generator panel(아키텍처 byte-수렴, judge 가 C4 isinstance pre-check=BL-362 위반 기각) + G2 codex challenge(P1 = valuewhen `Decimal('NaN')` occurrence 가 `isinstance(float)` 갭으로 escape, 실측 재현 → `(float, Decimal)` 확장 + 테스트; P2 ema/rma/rsi fractional truncation = 되돌리면 `Decimal('NaN')<=0` 재escape 라 유지) + G3 fresh review(SHIP) + **mutation harness 6/6 CAUGHT(false-green 0)** + full suite 2305 pass(cov ≥90, ruff+mypy clean, alembic head, **migration 0**) + **Playwright E2E**(na/inf 전략 백테스트 before=실패 "an integer is required" → after=완료, console.error 0). **잔여 deferred → [BL-377](#bl-377).**

---

### BL-378

**Title:** pine_v2 `ta.atr` rolling SMA → Wilder RMA (TradingView parity) ✅ **Resolved (2026-06-30, `fix/pine-378-atr-wilder`)**
**Category:** Strategy / pine_v2 (indicator 정확성)
**Priority:** P1 (harm-class, 트리거됨)
**출처:** 2026-06-30 실세계 8 전략 티어드 백테스트 QA (`docs/qa/2026-06-30-pine-tiered-backtest/report.md` finding B1)

**원인 / 영향:** `ta_atr`(stdlib.py) 가 True Range 의 단순 rolling SMA(`deque(maxlen=len)` → `sum/len`)를 계산. TradingView `ta.atr(len) = ta.rma(ta.tr, len)` = Wilder smoothing(alpha=1/len). 비-상수 TR 에서 발산(len=3, bar 3: 엔진 3.50000=SMA vs TV 3.05556=RMA, 14% 누적). 같은 파일 `ta_rma`(Wilder)는 정확하고 `rsi`가 이를 사용 → atr 만 고립 버그. ATR 사용 전 전략(DrFX supertrend / UtBot·RsiD 트레일링 / LuxAlgo slope) 백테스트가 TV 와 silent divergence. 상수 TR 슬라이스는 SMA=RMA 라 기존 테스트가 못 잡음.

**수정:** `ta_atr` 가 TR 계산 후 기존 Wilder `ta_rma(state, node_id, tr, _len)` 재사용(~2줄). seed=SMA(first len TRs) 로 현재와 동일, 이후 bar 부터 TV 정합. 비-상수 TR anti-circular 골든 테스트 2건(`test_ta_atr_matches_tradingview_wilder_rma` / `test_ta_atr_not_rolling_sma`) + trust-layer golden 재생성(s2_utbot/i1_utbot). **검증:** G1-G4(codex G1/G2/diff-challenge no-P1 + Workflow 12-agent panel + G3 fresh review + mutation 2/2 CAUGHT) + full 2301 pass + ruff/mypy clean. migration 0.

---

### BL-379

**Title:** pine_v2 user-function 지역변수 `x[1]` history = na (subscript in `=>` 깨짐)
**Category:** Strategy / pine_v2 (interpreter)
**Priority:** P2 (latent harm-class — 코퍼스 8종 미트리거, 흔한 패턴)
**Trigger:** pine_v2 robustness 후속
**Est:** M (4-6h)
**출처:** 2026-06-30 QA codex G2 challenge + 직접 재현

**원인 / 영향:** `_eval_subscript`(interpreter.py:653)가 `x[1]`을 `_var_series`에서만 조회하는데, user function(`f(s) => ...`) 지역변수는 `_var_series`에 append 되지 않음. 재현: `f(s) => prev = s[1]` → `[nan]*N`(항상 na) vs top-level `close[1]` 정상. 코퍼스 8종은 미트리거(전부 인라인/builtin) 이나 `f(x)=>...x[1]...` (지표 함수 내 history 참조) 는 흔한 패턴 → 해당 전략 silent divergence. **권장:** user-function 스코프 변수 history 추적 또는 명시적 unsupported reject.

---

### BL-380

**Title:** Track A INFORMATION/UNKNOWN alert 무경고 drop (docstring 계약 위반)
**Category:** Strategy / pine_v2 (Trust Layer / Track A)
**Priority:** P2 (신뢰 표면)
**Trigger:** Track A 신뢰 표면 sprint
**Est:** S-M (3-5h)
**출처:** 2026-06-30 QA LuxAlgo 0-trade 추적 + codex G2

**원인 / 영향:** `virtual_strategy.py:128-130` 가 INFORMATION/UNKNOWN alert 를 경고 없이 `continue` (docstring `:12` 은 "무시 + warning" 약속 — 계약 위반). LuxAlgo `alertcondition(.., 'Price broke the down-trendline upward')` → strict 기본 INFORMATION 키워드 `\btrendline\b` → 무경고 무시 → **0 trades, status=ok** (지표 수치는 정확). loose 모드(opt-in)면 directional. **추가:** 경고를 추가해도 `run_backtest_v2`(v2_adapter.py:181)가 `state.warnings`만 내보내 `VirtualRunResult.warnings` 유실. **권장:** (a) ignored actionable alert 시 wrapper.warnings 기록 + (b) VirtualRunResult.warnings → backtest parse warnings 전파. (strict 기본 정책 자체는 유지.)

---

### BL-381

**Title:** Track A `VirtualRunResult` var_series/warnings 미반환 → trust-parity digest 공허
**Category:** Strategy / pine_v2 (Trust Layer CI)
**Priority:** P2 (meta / 검증 인프라)
**Trigger:** Trust Layer CI 강화
**Est:** S (2-4h)
**출처:** 2026-06-30 QA codex G2 + diff-challenge

**원인 / 영향:** `VirtualRunResult`(virtual_strategy.py:61) 에 var_series 필드 부재 + 미반환. `test_trust_layer_parity.py:239` 의 golden 추출기가 `getattr(.., 'var_series', {})` → 빈 dict digest. 결과: Track A 전략(i2_luxalgo 등)의 지표 변화(예: ta.atr→slope)가 var_series_digest 에 반영 안 됨 → documented P-3 parity 검증이 부분 공허(BL-378 fix 시 i2_luxalgo baseline 불변이 이를 노출). **권장:** VirtualRunResult 에 var_series/warnings 노출 + 추출기 배선.

---

### BL-382

**Title:** qty=1.0 fallback sizing-source FE 미표면화 (자본초과 백테스트 투명성)
**Category:** Backtest / 투명성
**Priority:** P2 (투명성)
**Trigger:** sizing 투명성 sprint
**Est:** S (2-4h)
**출처:** 2026-06-30 QA F1 (codex G2 = harm-class 아닌 transparency)

**원인 / 영향:** `default_qty_type` 미지정 전략(PbR/UtBot)은 qty=1.0 (1 BTC/trade ≈ $42k notional vs $10k capital) → mdd=-16.95/-41.47, fees $156k. 엔진은 `mdd_exceeds_capital=True` 정직 flag + FE KPI 가 자본초과 손실 표시. **그러나** sizing_source 가 FE 결과 schema 부재(schemas.ts:254), AssumptionsCard 가 "1 BTC 고정수량 fallback" 미표면화(assumptions-card.tsx:88). **권장:** config 응답에 sizing_source/default_qty 포함 + fallback 시 경고 표시.

---

### BL-383

**Title:** v2_adapter catch-all 이 런타임 예외를 parse_failed 로 오분류 (관측성)
**Category:** Backtest / engine (관측성)
**Priority:** P3
**Trigger:** pine_v2 관측성 후속
**Est:** S (2-3h)
**출처:** 2026-06-30 QA codex G2 (G1 에서도 지적)

**원인 / 영향:** `v2_adapter.py:126-133` generic `except Exception` → `status="parse_failed"`. parse 성공 후 실행 중 예외(TypeError 등)도 "parse failed"로 표시 → 사용자 원인 분류 오도. BL-376 이 na/inf escape 는 닫았으나 catch-all 잔존. **권장:** 실행-단계 예외를 `status="error"` 로 분기(parse 단계와 구분).

---

### BL-384

**Title:** ta.valuewhen 이 na-source occurrence skip (TV 는 na 기록)
**Category:** Strategy / pine_v2 (indicator parity)
**Priority:** P3 (좁은 edge)
**Trigger:** pine_v2 parity 후속
**Est:** S (2-3h)
**출처:** 2026-06-30 QA codex G2 + 직접 재현

**원인 / 영향:** `stdlib.py:305-307` 가 `cond_bool and source not na` 일 때만 occurrence 기록. cond=true + source=na 인 occurrence 를 TV 는 기록(na 반환), QB 는 skip → 이전 non-na 반환. 재현: src=[10,na] → `valuewhen(cond,src,0)` QB=10, TV=na. RsiD `valuewhen(plFound, osc[lbR], 1)` (osc warmup 시 na) 후보. 좁은 edge. **권장:** cond=true occurrence 는 source 가 na 여도 기록.

---

### BL-385

**Title:** PineVersion enum v6 부재 → `//@version=6` 가 v5 로 collapse
**Category:** Strategy / pine_v2 (coverage / 메타데이터)
**Priority:** P3 (경미)
**Trigger:** pine_v2 coverage 후속
**Est:** XS (1-2h)
**출처:** 2026-06-30 QA F3

**원인 / 영향:** `PineVersion` enum(strategy/models.py)이 v4/v5 뿐 → `_detect_version`(strategy/service.py)이 `//@version=6`(PbR, bs)를 v5 로 보고. 메타데이터 부정확(실행엔 무영향). **권장:** v6 enum 값 추가(alembic enum-add 패턴, LESSON-066).

---

### BL-386

**Title:** v4 bare math builtin `floor`/`ceil`/`round`/`sqrt` 미별칭 (preflight reject)
**Category:** Strategy / pine_v2 (coverage)
**Priority:** P3 (경미, 안전 측 — silent 아님)
**Trigger:** pine_v2 coverage 후속
**Est:** XS (1-2h)
**출처:** 2026-06-30 QA F4

**원인 / 영향:** `SUPPORTED_FUNCTIONS` 의 `_V4_ALIASES` 가 abs/max/min 만 포함, `floor`/`ceil`/`round`/`sqrt`(유효 Pine builtin) 부재 → v4 스크립트의 `floor()` 가 unsupported flag(preflight 차단). over-strict 이나 silent 아님(안전). **권장:** v4 bare math builtin 을 `math.*` 로 재라우팅하는 alias 추가.

---

### BL-387

**Title:** backtest sizing-canonical → config_payload 가 untyped `dict[str,Any]` seam 으로 영속 경계 횡단 (key drift 시 silent 잘못된 sizing)
**Category:** Backtest / Architecture (shallow seam / money-path)
**Priority:** P2
**Trigger:** backtest deepening sprint 또는 sizing 로직 변경 시
**Est:** S-M (3-5h)
**출처:** [`docs/dev-log/2026-06-30-backtest-deepen.md`](dev-log/2026-06-30-backtest-deepen.md) (codex challenge 최강 후보)

**원인 / 영향:** `service.py:754-876` `_resolve_sizing_canonical` 이 6-key `dict[str, Any]` 를 반환하고 `service.py:188-212` 가 `.get('leverage', default)` 식으로 config_payload 를 손-조립한다. 두 dict 의 key 일치가 타입으로 보장되지 않아, resolve 쪽 key 가 rename 되면 조용히 default 로 떨어져 `sizing_source`/`leverage_basis` 가 잘못 영속될 수 있다(money-affecting). `dict[str, Any]` = Interface 가 거의 없는 shallow seam 이 백테스트 입력의 진실을 DB 경계로 흘려보낸다.

**권장 접근:** sizing 결정을 typed value object(`SizingCanonical`)로 만들어 `_resolve` 출력과 config 영속 사이 Seam 에 타입 부여 → key 불일치가 검증/타입 시점에 잡히게. `test_resolve_sizing_canonical` 8-case 존재하나 resolve 출력↔config_payload key-match 단언 부재 = 부분 gap.

**영향 파일:** `backtest/service.py` (`_resolve_sizing_canonical` + config_payload 조립), `config_mapper.py`.

**Risk:** 🟡 (money-path sizing — 영속 값 parity 검증 필요).

---

### BL-388

**Title:** BacktestMetrics 24-field 가 4곳 평행 정의 (engine dataclass ↔ schema ↔ serializer ↔ `_to_detail`) — field-parity 무검증 leaky seam
**Category:** Backtest / Architecture (locality / multi-SSOT)
**Priority:** P2
**Trigger:** backtest deepening sprint 또는 BL-236(objective_metric 노출) 진행 시
**Est:** S-M (3-5h)
**출처:** [`docs/dev-log/2026-06-30-backtest-deepen.md`](dev-log/2026-06-30-backtest-deepen.md) (codex challenge 가 4번째 site `_to_detail` 추가 발견)

**원인 / 영향:** 동일 지표 shape 가 `engine/types.py:101 BacktestMetrics`(dataclass) + `schemas.py:195 BacktestMetricsOut` + `serializers.py metrics_to/from_jsonb` + `service.py:668 _to_detail`(BacktestMetricsOut 손-매핑) **4곳**에 평행 정의된다. 지표 1개 추가 = 4 edit site 동시 수정 — Locality 가 도메인 전체로 퍼진 leaky Seam. round-trip serializer 테스트(`test_serializers`/`test_serializers_extended`)는 있으나 dataclass↔schema field-set parity 단언이 없어 두 정의가 silent drift 가능. BL-236 이 지표 노출 확대 시 추가 비용 증폭.

**권장 접근:** 지표 field 의 단일 정의를 SSOT 로 고정하고 나머지 표현(API/JSONB/detail)을 파생, 또는 최소 'dataclass field 집합 == schema field 집합' CI parity 가드(tripwire) 선추가로 drift 를 구조 차단.

**영향 파일:** `engine/types.py`, `schemas.py`, `serializers.py`, `service.py` (`_to_detail`).

**Risk:** 🟡 (직렬화는 round-trip 보호됨, parity 가드는 test-first 성격 약함).

---

### BL-392

**Title:** stress_test CA/PS "2D grid sweep" DTO 8-site 평행 정의 통합 (engine dataclass + serializer + OutSchema)
**Category:** Stress / Architecture (parallel definition / leaky JSONB seam)
**Priority:** P2
**Trigger:** stress_test deepening sprint, 또는 grid-cell 필드 추가 / 3번째 grid-sweep 타입 등장 시
**Est:** M (4-6h)
**출처:** [`docs/dev-log/2026-06-30-stress_test-deepen.md`](dev-log/2026-06-30-stress_test-deepen.md) (deepen-modules stress_test 1차 audit)

**원인 / 영향:** 7-field cell shape(`param1_value·param2_value·sharpe·total_return·max_drawdown·num_trades·is_degenerate`)가 **8 site 평행 정의** — engine dataclass×2(`CostAssumptionCell`≡`ParamStabilityCell` `engine/cost_assumption_sensitivity.py:42-52` / `engine/param_stability.py:51-61`, docstring 단어만 차이) + serializer to/from×4(`serializers.py:158-251`, ~70 LOC char-identical) + OutSchema×2(`CostAssumptionCellOut`≡`ParamStabilityCellOut` / `*ResultOut` `schemas.py:218-298`). `result` 는 untyped JSONB(`models.py:94`) → writer(`*_to_jsonb`)↔reader(`*_from_jsonb`) 계약 무검증 → 1곳 drift 시 비싼 Celery run 성공 **후** GET-detail 때 KeyError. 엔진 계산은 이미 `run_grid_sweep` 공유 + 필드명이 generic(`param1_value`, `fees` 아님) → author 가 한 개념임을 알면서 **절반만 deepen**(loop lift-up O / DTO 통합 X). `models.py:90-93` `result` docstring 이 CA/PS 누락 = SSOT 미유지 증거.

**권장 접근:** engine 공유 `GridSweepCell`/`GridSweepResult` dataclass 1개(param-name-generic) → CA/PS `run_*` 가 동일 타입 반환. serializer `grid_result_to_jsonb`/`from_jsonb` 1쌍. schema `GridSweepCellOut`/`GridSweepResultOut` 1클래스. **API 비파괴**: `StressTestDetail.cost_assumption_result`/`param_stability_result` 필드명 유지 + 둘 다 `GridSweepResultOut` 타입(JSON shape 동일 → FE 무영향). **over-abstraction 가드(필수)**: 엔진 _의미_(CA=fees×slippage cost 가정 / PS=pine input override) 진짜 다름 → DTO/serializer 만 통합, `run_cost_assumption_sensitivity`/`run_param_stability` fn·`_SUPPORTED_PARAM_KEYS`/`_SUPPORTED_INPUT_TYPES`·pre_validate 분리 유지(trading BL-370 over-abstraction 교훈). golden round-trip test(저장→로드 동일) + 구버전 JSONB row 하위호환 의무. **C4(cross-layer invariant: 9-cell cap·2-key·`{fees,slippage}` allowed-keys 상수 SSOT) 를 본 작업 시 자연 graft 권장**(deepen-modules 거부 항목, dev-log 보존).

**영향 파일:** `engine/cost_assumption_sensitivity.py` + `engine/param_stability.py`(dataclass → 공유 import), 신규 `engine/_grid_result.py`(또는 `engine/_common.py` 확장), `serializers.py`(4 fn → 2), `schemas.py`(CellOut/ResultOut ×2 → 1).

**예상 LOC delta:** +30 / -90 (net ~-60).

**Risk:** 🟡 (직렬화 round-trip + 응답 schema — golden test 필수, 구버전 row 하위호환). **C1(BL-363) 와 묶으면 CA/PS 응집부 단일 sprint.**

---

### BL-377

**Title:** pine_v2 non-finite 주문/청산 가격 + 초대형 유한 length OverflowError (BL-376 후속 잔여)
**Category:** Strategy / pine_v2 (interpreter robustness)
**Priority:** P3
**Trigger:** pine_v2 robustness 후속 또는 실자금 cutover 전 (BL-376 후속)
**Est:** S (2-4h)
**출처:** 2026-06-30 BL-376 G2 codex challenge [P1#3/#4] + G3 fresh review [LOW]

**원인 / 영향:** BL-376 이 na/inf 의 raw-예외-escape harm class 를 닫았으나, 다음 2종 잔여는 escape 가 아니거나(deterministic 오값) 별도 trigger 라 BL-376 scope 밖으로 이연:

- **non-finite 주문/청산 가격:** `strategy.entry(stop=inf)` / `strategy.exit(stop|limit|profit|loss|trail=inf)` 는 실측상 raw 예외 escape 가 **아니라** status='ok' + 무-NaN 의 deterministic false-fill(예: inf short-stop 이 다음 bar 체결). 라이브는 이미 `_to_decimal`(isfinite) 로 drop. 백테스트 path 에 동일 isfinite drop 미러 필요(entry `stop` = `interpreter.py:1265`, exit `_num` = `interpreter.py:1325-1340`).
- **초대형 유한 length OverflowError:** `_coerce_length` 는 na/inf/<1 만 차단 → `ta.sma(close, close*1e17)`(유한 ~1e19 > `sys.maxsize`) 는 통과 후 `deque(maxlen=int(huge))` 가 `OverflowError` escape(G3 실측). harm class 이나 trigger 가 비현실적이고 완전 수정은 sane max-length cap(제품 결정) 필요.
- (참고, 별도 boundary) `input.int` override `int()`(`interpreter.py:982`)에 `Decimal('NaN')` override 시 ValueError — optimizer 가 NaN override 미발행이라 도달 불가. config boundary(`BacktestConfig`) finite 검증이 더 적절.

**권장 접근:** (a) 백테스트 entry stop + `_num` exit level 에 `math.isfinite` drop 가드(라이브 `_to_decimal` 미러). (b) `_coerce_length` 에 sane upper-cap 추가(또는 `value > sys.maxsize` → None). 골든 테스트 동반.

**Risk:** 🟢 (전부 현재 deterministic 또는 비현실적 trigger — escape 아니거나 라이브 이미 안전. 실자금 cutover 전 처리 권장).

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
- **(c) reconcile-lag late filled_at** — `filled_at` 은 fill _처리_ 시각(`datetime.now(UTC)`)이지 거래소 체결 시각이 아님. reconcile 경로(watchdog/reconciler)에선 실제 체결보다 늦게 기록 → reopened `createdTime < filled_at` 이면 가드 통과. codex G1 [P1-3].
- **(d) worker clock-skew** — worker clock 이 거래소보다 >2s 느리면 정상 open 도 `createdTime > filled_at + 2s` 로 false-skip(저위험: trailing 미부착, bracket SL floor 유효). codex G2 [P2].

**권장 접근:** 근본 = **거래소 보고 체결 시각 소싱**. 4 fill-recording 경로(sync receipt / WS event / watchdog / reconciler)에서 exchange order/exec timestamp 추출 → 비교 기준으로 사용(전용 컬럼 또는 전달) → (c)(d) 해소. (a)(b) inherent race 는 거래소-side conditional(예 createdTime 조건부 trading-stop) 또는 placement 전 재확인(refetch-after-set verify)으로 좁힘. clock-skew 는 NTP 전제 문서화.

**Risk:** 🟡 (전부 narrow residual — common WS/sync path 는 BL-372 로 차단, 데모 bracket SL floor 보호. 실자금 cutover 전 처리 권장).

---

### BL-393

**Title:** pine_v2 `strategy.exit` trail_points/trail_offset 틱 단위 시맨틱스 (TV=틱\*mintick, QB=price-distance) + `syminfo.mintick` 0.01 하드코딩
**Category:** Strategy / pine_v2 (TV parity)
**Priority:** P2
**Trigger:** pine_v2 parity 후속 또는 틱 기반 exit 전략 사용자 등장 시
**Est:** M (4-6h — 실 심볼 mintick 소싱 결정 포함)
**출처:** 2026-07-05 TV-parity sprint — 사용자 전략(HMA+ATR+Curvature) 커버리지 판정

**원인 / 영향:** TV 의 `trail_points`/`profit`/`loss` 는 **틱 단위**(값 × syminfo.mintick = 가격 오프셋). QB 인터프리터는 price-distance 로 해석(`interpreter.py` `_num` 근사, mintick=0.01 고정 — `interpreter.py:1131`). ATR 값을 trail_points 에 넣는 전략(사용자 전략 포함)은 TV 에선 초미세 트레일링(예: ATR 500 → $5)이 되어 승률 98%+ 의 **가짜 성적**이 나오고, QB 는 저자 의도(가격 거리)에 가깝게 동작 — 즉 발산의 원인이 TV 쪽 함정. 그러나 틱 단위를 의도한 전략은 QB 에서 발산.

**권장 접근:** (a) 발산 방향/원인을 supported-indicators 문서에 명시(완료: 2026-07-05 노트) (b) 실 심볼 mintick 소싱(CCXT market precision) + 틱 해석 opt-in config. TV 정합 모드(fill_timing 과 묶음) 시 함께 검토.

**Risk:** 🟢 (현 동작이 보수적/의도-근접. 문서화 우선).

---

### BL-398

**Title:** Sharpe TV convention 정렬 (달력월 수익률 + RFR 2%/yr) — optimizer objective 영향 분석 동반
**Category:** Backtest / metrics (TV parity)
**Priority:** P2
**Trigger:** TV parity 2차 또는 사용자 Sharpe 값 문의 시
**Est:** M (4-6h — baseline 재생성 + optimizer `sharpe_ratio` objective 랭킹 영향 분석 의무)
**출처:** 2026-07-05 TV-parity sprint B3 (sortino 는 TV convention 으로 신규 구현, sharpe 는 blast radius 로 이연)

**원인 / 영향:** `_sharpe`(v2_adapter)는 bar 수익률 + RF=0 + √N — TV 는 달력월(2개월 미만 daily) + RFR 2%/yr + 비연율화. 동일 리포트에서 sortino(TV convention)와 sharpe(bar 기준)가 다른 척도로 병존(FE 는 "(bar 수익률 기준)" 라벨로 정직 고지 중). sharpe 변경은 trust-layer baseline + optimizer objective(`_SUPPORTED_OBJECTIVE_METRICS`) 랭킹에 영향.

**권장 접근:** engine/metrics.py `_periodic_returns` 재사용해 TV convention sharpe 구현 → baseline 재생성(diff = sharpe 키 한정 단언) + optimizer 랭킹 flip 여부 실측 후 교체.

**Risk:** 🟡 (optimizer objective 소비자 영향 — 분석 선행 의무).

---

### BL-401

**Title:** optimizer 3폼(grid/bayesian/genetic) field-level zod 에러 미렌더 — 검증 실패 시 사용자 무피드백 제출 차단 → ✅ **Resolved (2026-07-23, stage/functional-parity)**
**Category:** Frontend / optimizer 폼 UX
**Priority:** P2
**Trigger:** optimizer 폼 polish 또는 사용자 "제출 안 됨" 문의 시
**Est:** S-M (2-4h — 3폼 공통 필드 에러 표출 + 회귀 테스트)
**출처:** 2026-07-05 PR #394 FE 리팩토링 번들 (optimizer 폼 통합 작업 중 발견, 2026-07-05 코드 재검증)

**원인 / 영향:** `grid-search-form.tsx:47` / `bayesian-search-form.tsx:57` / `genetic-search-form.tsx:97` 은 `zodV4Resolver(FormSchema)` 를 쓰지만 `formState.errors` 를 어느 필드 컴포넌트(`optimizer-form-fields.tsx`/`param-rows-fieldset.tsx` — register/control 만 수신)에도 전달·렌더하지 않는다. 표출되는 에러는 mutation 실패 시 `FormErrorAlert`(GENERIC_ERROR_MSG) 뿐. `form-schemas.ts` 의 사용자향 검증 메시지("var_name required" :38 / superRefine "min < max 강제" :71 / "log_scale / log_uniform 은 min > 0 필요" :78 등)가 계산만 되고 화면에 도달하지 못해 `handleSubmit` 이 무피드백으로 제출만 차단한다. **스코프 노트:** backtest 폼은 zod resolver 미사용(RHF 네이티브 `useBacktestForm.ts:88`) + field 에러 정상 렌더(`backtest-form.tsx:111`, `BacktestCostFieldSet.tsx:36/69/93`) 확인 — 본 BL 스코프에서 제외. BL-350/354(✅ Resolved Sprint 62, `/optimizer` 리스트 row resilience)와 같은 도메인·같은 zod 지만 다른 표면(폼 입력)이다.

**권장 접근:** `waitlist-form-card.tsx:71` 의 field 에러 렌더 패턴대로 3폼 공통 필드 조각에 `errors` prop 전달 + 필드 하단 `text-destructive` 메시지 렌더. superRefine(param row 교차 검증)은 해당 row 하단 표출 위치 설계 동반.

**영향 파일:** `grid-search-form.tsx`, `bayesian-search-form.tsx`, `genetic-search-form.tsx`, `optimizer-form-fields.tsx`, `param-rows-fieldset.tsx`.

**Risk:** 🟢 (표출 전용 — 제출 페이로드 무변경. PR #394 characterization 스모크가 body 고정).

---

### BL-402

**Title:** optimizer 백테스트 picker `value={backtestId || undefined}` uncontrolled↔controlled 전환 콘솔 에러 + 트리거 raw UUID 노출 (BL-164 SSOT 미적용 회귀) → ✅ **Resolved (2026-07-23, 구조 소멸 — C 이식 네이티브 select 전환. 실측 재확인)**
**Category:** Frontend / optimizer UX
**Priority:** P2
**Trigger:** BL-401 과 묶음 권장 (동일 페이지)
**Est:** XS-S (1-2h)
**출처:** 2026-07-05 PR #394 FE 리팩토링 번들 dogfood (2026-07-05 코드 재검증)

**원인 / 영향:** `optimizer-page-view.tsx:66` 이 `value={backtestId || undefined}` — 초기 `""` → `undefined`(uncontrolled) → 선택 후 UUID 문자열(controlled) 전환으로 콘솔 경고 유발. 또한 raw `Select`+`SelectValue`(render prop 無, :65-90) 라 선택 후 트리거에 full UUID 가 그대로 표시된다(옵션 label 은 `${symbol} · ${timeframe} · ${id.slice(0,8)}` 인데 트리거만 raw value). `SelectWithDisplayName`(BL-164 SSOT, `select-with-display-name.tsx`) 미적용 — Compare picker 동일 결함을 PR #383 에서 고친 것과 같은 계열의 회귀다(BL-164/176/206 은 전부 archived, 활성 추적 부재였음).

**권장 접근:** `SelectWithDisplayName` 로 교체 — value 는 순수 string(빈 값 처리 내장), label 매핑 캡슐화. PR #383 의 `equity-chart-with-compare.tsx:76` 패턴 그대로.

**영향 파일:** `app/(dashboard)/optimizer/_components/optimizer-page-view.tsx` (:33, :65-90).

**2026-07-12 pine-batch QA 실측 확장 (3사이트 추가):** (a) `backtests/_components/forms/backtest-form.tsx:84-106` **strategy picker** — 옵션 실클릭 후 트리거 raw UUID 노출 Playwright 실측 + 소스 감사로 원인 확정 (raw `Select`+자식 없는 `SelectValue`). (b) `report/trade-ledger-table.tsx:98-125` (c) `trades/trade-filter-row.tsx:116-141,202-211` 방향/결과 필터 — 동일 클래스 (value≠label), 선택 후 raw 토큰 노출 추정. 전부 `SelectWithDisplayName` 교체로 일괄 처리 (`equity-chart-with-compare.tsx:76` 선례). 상세: `docs/qa/2026-07-12-pine-batch-1h4h/report.md` §6.1.

**Risk:** 🟢 (프리젠테이션 전용 — 선택 값 전달 로직 무변경).

---

## P3 — Nice-to-have / 컨벤션 정합

> 12 archived ([BL-050/051/052/053/054/055/056/057/138/139/151/153](refactoring-backlog/_archived.md#p3-전부-nice-to-have-컨벤션-정합)). **활성 P3 = 8** (BL-306/307 2026-05-15 CLAUDE.md align audit + BL-367/370/371 2026-06-26 trading-deepen-2 + BL-389/390/391 2026-06-30 backtest-deepen).

### BL-389

**Title:** backtest finance math 10 함수 (~250 LOC) 가 v2_adapter god-file 에 혼재 — `engine/metrics.py` Deep Module 추출 (locality)
**Category:** Backtest / Architecture (shallow-by-size / locality)
**Priority:** P3
**Trigger:** backtest deepening sprint
**Est:** M (4-6h)
**출처:** [`docs/dev-log/2026-06-30-backtest-deepen.md`](dev-log/2026-06-30-backtest-deepen.md) (codex DOWNGRADE → `metrics.py` 부재 직접 검증 후 KEEP 정정)

**원인 / 영향:** `v2_adapter.py`(964L)의 본 책임은 V2RunResult → BacktestOutcome 변환(orchestration)인데, Sharpe/MaxDD/CAGR/win-rate/streak/monthly 등 도메인-비종속 finance math 10 함수(`_v2_avg_holding_hours`~`_mean`, L707-912 ~250 LOC)가 같은 모듈에 혼재 = shallow-by-size, Locality 깨짐. (codex 가 `engine/metrics.py` 존재로 오판 DOWNGRADE → 실제 부재 확인, 모든 math 가 v2_adapter 내부 → KEEP 정정.) stress_test 재사용은 speculative(현재 `result.metrics` 만 소비)라 추출 정당화는 locality 중심.

**권장 접근:** finance 계산을 `engine/metrics.py` Deep Module 로 이동 — '(equity_curve, trades, config) → 지표 묶음' 작은 Interface 뒤에 큰 behavior 은닉. v2_adapter 는 호출만 남김. 이동(move)이라 golden oracle parity 로 회귀 0 보장.

**영향 파일:** `engine/v2_adapter.py`(L707-912 추출), 신규 `engine/metrics.py`.

**Risk:** 🟢 (move refactor — `test_golden_oracle_minimal` + `test_metrics_real_extract` parity 가드, 이동 전후 동일 oracle 재실행).

---

### BL-390

**Title:** backtest exit-leg maker/taker `fill_type` 라우팅이 v2_adapter 2곳 char-identical 복제 (주석은 SSOT 주장)
**Category:** Backtest / Architecture (DRY / locality, money-path)
**Priority:** P3
**Trigger:** backtest deepening 또는 `exit_kind` 의미 변경 시
**Est:** XS-S (1-3h)
**출처:** [`docs/dev-log/2026-06-30-backtest-deepen.md`](dev-log/2026-06-30-backtest-deepen.md)

**원인 / 영향:** exit leg maker/taker 분기 `fill_type_for(t.exit_kind) if t.exit_kind is not None else "taker"` 가 `v2_adapter.py:265`(\_build_raw_trades)와 `:568`(\_compute_metrics)에 character-identical 복제. L549 주석은 'SSOT 위임으로 중복 제거' 라 주장하나 실제 SSOT 는 `_leg_cost` 뿐이고 routing 분기는 미위임 → `exit_kind` 의미 변경 시 2곳 동시 수정(money-path 수수료/슬리피지). 작지만 확정된 Locality 결함.

**권장 접근:** `fill_type` 라우팅을 단일 헬퍼(또는 RawTrade 메서드)로 위임 → 두 소비 사이트가 같은 한 곳을 호출. 주석의 SSOT 주장과 코드 일치.

**영향 파일:** `engine/v2_adapter.py` (:265, :568).

**Risk:** 🟢 (refactor-safe — `test_exit_leg_cost_split` C14 불변식이 발산 가드).

---

### BL-391

**Title:** backtest trades→equity→metrics 3단 reconciliation 불변식 암묵 + cross-stage oracle 부재 (test-first)
**Category:** Backtest / Test surface (locality / pure-fn-extracted anti-pattern)
**Priority:** P3
**Trigger:** BL-389 metrics 추출과 묶음 또는 backtest test 강화 시
**Est:** S (2-4h)
**출처:** [`docs/dev-log/2026-06-30-backtest-deepen.md`](dev-log/2026-06-30-backtest-deepen.md) (codex DOWNGRADE → 좁은 oracle 범위로 축소)

**원인 / 영향:** `_build_raw_trades`(:145) → `_compute_equity_curve`(:154) → `_compute_metrics` 가 상호 의존(equity ← trade pnl, metrics ← 양쪽)하나 각각 isolation 으로만 테스트되고 단계 간 계약(`sum(trade.pnl)` ↔ equity 종가 delta)이 문서화/검증 안 됨 = 'testability 위해 추출된 순수함수' 안티패턴 → off-by-one 등 cross-stage 버그가 단위 테스트를 통과할 수 있다. (codex: golden/cost invariant 일부 존재 → 좁은 closed-trade·no-funding equity↔PnL oracle 만 추가, broad pipeline 재구성 아님.)

**권장 접근:** reconciliation 불변식 명시(docstring) + closed-trade·no-funding 케이스의 equity↔PnL cross-stage oracle 테스트 1건 선작성. BL-389 와 묶으면 자연스러움.

**영향 파일:** `tests/backtest/`(cross-stage oracle 신규), `engine/v2_adapter.py`(불변식 docstring).

**Risk:** 🟢 (test-first — 코드 변경은 docstring 수준).

---

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

### BL-394

**Title:** BE 거래 분포/수익구조 집계 엔드포인트 — `useAllBacktestTrades` 2000-cap 페이지 루프 대체
**Category:** Backtest / API + Frontend
**Priority:** P3
**Trigger:** 2000+ trades 백테스트가 흔해질 때
**Est:** M (4-6h)
**출처:** 2026-07-05 TV-parity sprint F1/F3 (FE 파생 분포·waterfall 은 표본 근사 캡션으로 정직 고지 중)

**원인 / 영향:** 수익 분포 histogram/거래 분포 donut/수익 구조 waterfall 이 FE 에서 전체 trades(최대 2000, 페이지 루프 10회)로 파생. 초과 시 "표본 기준" 근사. BE 집계 1 endpoint 면 정확+경량. **참고:** BE `gross_profit_abs`/`gross_loss_abs`/`per_side.*` 는 net(비용 차감 후) 기준 승/패 분해 — waterfall 용 비용 전(gross) 분해와 다름(FE `computeProfitStructure` 항등식 참조). 집계 endpoint 설계 시 두 정의 모두 제공 권장.

---

### BL-395

**Title:** lightweight-charts v5 업그레이드 spike — 네이티브 멀티-pane + 시간축 동기화
**Category:** Frontend / 차트 인프라
**Priority:** P3
**Trigger:** 차트 pane 4개+ 필요 또는 줌/팬 동기화 요구 시
**Est:** M (6-8h, spike)
**출처:** 2026-07-05 TV-parity sprint F2 (v4.2 는 멀티-pane API 부재 → 독립 인스턴스 3개 스택, 시간축 미동기화)

---

### BL-396

**Title:** `/backtests/[id]/trades` 상세 서브페이지에 TV 신규 컬럼(런업/드로다운/누적/fee split/exit_kind) 정렬
**Category:** Frontend UX
**Priority:** P3
**Trigger:** 원장(trade-ledger-table)과 서브페이지 컬럼 비정합 불편 접수 시
**Est:** S (2-3h)
**출처:** 2026-07-05 TV-parity sprint F4 (원장만 신규 컬럼 반영, 서브페이지는 무변경)

---

### BL-397

**Title:** 백테스트 리포트 섹션 탭 URL 딥링크 (`?section=`)
**Category:** Frontend UX
**Priority:** P3
**Trigger:** 리포트 특정 섹션 공유 요구 시
**Est:** XS-S (1-3h)
**출처:** 2026-07-05 TV-parity sprint F2 (탭 상태 비제어 유지 결정)

---

### BL-399

**Title:** `ta.sar` TV hand-oracle 부재 — parity 스팟 검증 미완
**Category:** Strategy / pine_v2 (indicator parity)
**Priority:** P3
**Trigger:** SAR 사용 전략 등장 시
**Est:** S-M (3-5h — AF/EP/flip 규칙 손유도)
**출처:** 2026-07-05 TV-parity sprint P1-4 (wma/bb/mom/obv/cross 는 스팟 판정 완료 — bb=population stdev=TV biased 기본 ✓, mom/obv/cross ✓. sar 만 오라클 미작성)

---

### BL-400

**Title:** optimizer 쿼리만 `enabled: userId != null` 가드 — 도메인 간 React Query enabled 정책 비일관 (통일 여부 결정 필요)
**Category:** Frontend / React Query 컨벤션
**Priority:** P3
**Trigger:** FE 훅 팩토리 후속 정비 시 (`use-auth-ctx` 소비 도메인 전수)
**Est:** S (2-3h — 정책 결정 + 일괄 적용)
**출처:** 2026-07-05 PR #394 FE 리팩토링 번들 (훅 팩토리 SSOT 작업 중 발견, 2026-07-05 코드 재검증)

**원인 / 영향:** `features/optimizer/hooks.ts:59,70` 만 `enabled: userId != null` 로 로그아웃 시 쿼리를 미발사한다. 나머지 도메인(backtest/strategy/trading/live-sessions/waitlist) list 훅은 가드 없이 `useAuthCtx` 의 `uid="anon"` sentinel + null token 으로 발사(401 → retry 1). PR #394 훅 팩토리(`use-auth-ctx`/`use-invalidating-mutation`/`query-poll`)는 폴링 가드만 SSOT 화했고 enabled 가드는 미흡수. 실버그는 아니나 로그아웃 시 도메인별 동작이 달라 디버깅·테스트 기대가 갈린다.

**권장 접근:** 결정 사안 — (a) 전 도메인 `enabled: userId != null` 통일(무의미 401 제거, `use-auth-ctx` 에 헬퍼 추가) vs (b) optimizer 가드 제거로 "anon 발사" 일원화. Grilling 1문항으로 결정 후 일괄 적용.

**Risk:** 🟢 (정책 결정 사안 — 어느 쪽도 회귀 표면 작음).

---

### BL-403

**Title:** recharts↔lightweight-charts(+optimizer inline-SVG) 차트 3원화 해소 — 라이브러리 수렴 결정
**Category:** Frontend / 차트 인프라
**Priority:** P3
**Trigger:** **BL-395(lwc v5 spike) 완료 후** — 멀티-pane/커스텀 시리즈 확보가 수렴 가능성 판정의 전제
**Est:** L (8-16h — 대상 플롯별 이식 난도 상이, spike 선행)
**출처:** 2026-07-05 PR #394 FE 리팩토링 번들 (차트 지연로딩 정리 중 3원화 실측)

**원인 / 영향:** 시계열=lightweight-charts(`trading-chart.tsx` 싱글턴 dynamic import + backtest equity/drawdown pane + live-sessions), 통계 플롯=recharts 5종(`charts/recharts-plots.ts` 단일 seam, 414KB), optimizer 2종(`genetic-generation-chart.tsx`/`bayesian-iteration-chart.tsx`)=recharts 의존 회피 목적의 손수 inline SVG — 사실상 3원화. 번들 이중 부담 + 스타일 토큰(`lib/chart-tokens.ts` 로 완충 중) 3중 유지보수 + 신규 차트마다 라이브러리 선택 부채. Sprint 30-β 결정("recharts 보존, 신규만 lwc")이 3원화로 표류했다.

**권장 접근:** BL-395 spike 결과로 lwc v5 가 histogram/donut/waterfall 급 통계 플롯을 감당하는지 판정 → (a) lwc 수렴 + recharts 제거 (b) recharts 유지 + inline-SVG 2종만 recharts 편입 (c) 현상 유지 재확인 중 택1. BL-235(N-dim viz — cross-page consistency 의무)와 라이브러리 결정 공유.

**영향 파일:** `charts/recharts-plots.ts` 계열 5플롯, `components/charts/trading-chart.tsx`, optimizer inline-SVG 2종, `lib/chart-tokens.ts`.

**Risk:** 🟡 (표면 넓음 — spike 선행 + 페이지별 스냅샷 회귀 필요).

---

### BL-405 — ❌ CLOSED: not-a-bug (오라클 전제 오류, 2026-07-12 재분류)

**Title:** ~~pine_v2 bool 시리즈 na→False 실체화 — 워밍업 스퓨리어스 시그널~~ → **재분류: 엔진이 TV 정답, 버그 아님**
**Category:** Backend / pine_v2 na-semantics
**Priority:** ~~P2~~ → **CLOSED**
**출처:** 2026-07-12 pine-batch QA 오라클 ② (`report.md` §4.2) → **2026-07-12 A+B+C Trust 번들에서 TV 공식문서로 반증**

**재분류 결론:** BL-405 의 전제("Pine 비교는 na 를 반환하고 bool 시리즈에 na 가 보존된다")는 **TradingView 공식 문서로 반증됨** (r.jina.ai 리더로 verbatim 확보):

- type-system: _"values of the 'bool' type are never na. Any 'bool' return type returns `false` instead of na if data is not available."_ → **bool 은 절대 na 아님**.
- type-system: _"The ==, != operators, and all other comparison operators always return `false` if at least one of the operands is … `na`."_ → 비교는 na 피연산자에 **concrete false** (na 전파 아님). `!=` 도 false (True 아님 — 오라클이 놓친 지점).
- type-system: bool history-ref on nonexistent bar → false. operators: _"If at least one operand is na, the result is also na."_ → **na 전파는 산술에만**.

→ **현재 pine_v2 동작(비교→False, bool never na, crossover→False, 산술→na)이 TV 정답이다.** 계획됐던 "비교/not/crossover 를 na 전파로 바꾸는 수정"은 TV 정합을 깨는 **회귀**였다 (미실행). 오라클 ②의 "TV=bar 15"는 bool na 전파를 잘못 가정한 계산 — 실제 TV 는 bool 을 na 로 만들지 않아 엔진처럼 bar 12 를 낸다(ta.ema 워밍업 동일 가정 하).

**조치 (엔진 동작 무변경):** TV-정합 동작을 잠그는 회귀 테스트 13건 추가 (`tests/strategy/pine_v2/test_na_bool_tv_parity.py`) + `_eval_compare`(interpreter.py) / `ta_crossover|crossunder|cross`(stdlib.py) 오해 유발 주석 정정 + `report.md` §4.2 erratum. **bs bar12↔bar15 실측 편차의 진짜 후보는 bool-na 가 아니라 ta.ema 워밍업 시딩 → BL-409 로 분리 추적.**

**Risk:** — (해소, 코드 동작 변경 없음).

---

### BL-406

**Title:** DrFXGOD 잔여 미지원 builtin 5종 — ta.alma / ta.dmi / time() 호출형 / ticker.new / request.security_lower_tf
**Category:** Backend / pine_v2 coverage
**Priority:** P3
**Trigger:** 사용자 DrFXGOD 류 대형 indicator 수요 재확인 시
**Est:** M (ta.alma/ta.dmi 각 2-3h + time() stub 1h) / ticker.new·security_lower_tf 는 별도 설계 필요
**출처:** 2026-07-12 pine-batch QA (`docs/qa/2026-07-12-pine-batch-1h4h/report.md` §2)

**원인 / 영향:** G2(array 15종) 이후 DrFXGOD_indicator_hard(=i3_drfx) 의 잔여 차단 표면. (a) `ta.alma`(Arnaud Legoux MA)·`ta.dmi`(DMI/ADX) 는 순수 지표 — stdlib 추가로 feasible. (b) `time("")` 호출형은 timestamp stub 확장으로 feasible. (c) `ticker.new` + `request.security_lower_tf` 는 멀티심볼·하위 TF 데이터 패러다임 — 단일 TF 백테스트 전제 밖(거부 유지가 정직). (a)+(b) 만 구현해도 DrFXGOD 는 (c) 로 여전히 차단 — **전체 지원 목표가 아니라 (a)(b) 의 범용 가치로 판단할 것**.

**권장 접근:** ta.alma/ta.dmi 를 `_names.TA_FUNCTIONS` + stdlib `_call` 에 추가 (BL-378 ta.atr Wilder 검증 프로토콜 재사용 — TV 문서 대조 + 수계산 오라클). time() 은 bar timestamp 반환 stub. (c) 는 workaround 텍스트 유지.

**Risk:** 🟢 (신규 함수 추가 — 기존 경로 무변경).

---

### BL-407

**Title:** 백테스트 리포트 낙폭(Drawdown) 차트 Y축 눈금 전부 "-0.1%" 동일 표기 — 축 포맷터 정밀도/단위 버그 → ✅ **Resolved (2026-07-13, PR #433 stage/fe-react-audit)**
**Category:** Frontend / backtest 리포트 차트
**Priority:** P3
**Trigger:** backtest 리포트 차트 polish 사이클
**Est:** XS (0.5-1h)
**출처:** 2026-07-12 pine-batch QA Playwright 실측 (`docs/qa/2026-07-12-pine-batch-1h4h/screenshots/03-backtest-report-1h.png`)

**해소 (2026-07-13):** 원인 실측 확정 — lightweight-charts **v4 `PercentageFormatter` 는 값에 ×100 을 하지 않으며**(파일 주석의 전제가 거짓), percent 타입 precision 이 priceScale 에서 1/2 단위 양자화되어 |값|∈[0.25,0.75) 눈금이 전부 "-0.1%" 로 붕괴하는 이중 결함. `type:"custom"` 포맷터(비율×100 + toFixed(2)%)로 함정 자체 회피. 실 리포트 스크린샷 육안 검증 PASS (0.00% ~ -44.91% 정상 렌더).

**원인 / 영향:** MDD -59.91% 인 리포트에서 낙폭 미니차트 Y축 눈금 4개가 모두 "-0.1%" 로 표기 (현재값 배지도 -0.1%). 시리즈 형상은 정상 변동 — 눈금 라벨 포맷터가 ratio(-0.0~-0.6)를 %로 변환할 때 정밀도가 뭉개지거나 tick 간격 계산이 단위 불일치로 보임. 시각 신뢰 훼손 (Surface Trust ADR-019 관점).

**권장 접근:** lightweight-charts drawdown pane 의 priceFormat/tickMarkFormatter 확인 — ratio→% 변환 위치와 `precision` 옵션 정합. 라이트/다크 양 테마 + 1M/3M/6M/전체 기간 스위치 회귀 확인.

**Risk:** 🟢 (표시 전용).

---

### BL-408

**Title:** 리포트/위저드 Precision Instrument 폴리시 잔여물 팩 (stale aria-label 색명 + radius/글래스/레이블 어휘 6건)
**Category:** Frontend / 디자인 시스템 정합
**Priority:** P3
**Trigger:** 다음 FE polish 사이클 (BL-402 처리와 묶음 권장 — 파일 겹침)
**Est:** S (2-3h — 전부 표시 전용)
**출처:** 2026-07-12 pine-batch QA 디자인 감사 (`docs/qa/2026-07-12-pine-batch-1h4h/report.md` §6.1)

**원인 / 영향:** W6 잔여물 + 리디자인 이후 미세 드리프트 묶음. (1) `charts/chart-legend.tsx:51`·`charts/equity-pane.tsx:78` aria-label "실선 녹색" — 실제 equity 색은 코퍼, 스크린리더에 틀린 색 전달 (P2급, 팩 내 최우선. E2E getByLabelText 2건 동반 수정). (2) `report/key-stats-strip.tsx:83`·`report/performance-chart.tsx:42` 히어로 카드 `rounded-xl`(14px) — DESIGN.md §5 카드 규격은 10px. (3) `charts/chart-legend.tsx:44` `bg-card/80 backdrop-blur` 글래스 잔존 — v3 플랫+1px 보더 원칙 위반 (스코프 내 유일). (4) `components/metric-tile.tsx:60` 레이블 sans 10px — §0.1 mono 11px tracking 0.14em 규격과 분열. (5) `report/trade-ledger-table.tsx` 금액 셀 mono/tabular 혼용. (6) `--destructive-light` alias 잔존 + 영문 aria-label("strategy select" 등). DESIGN.md §11 표의 "백테스트 결과 = Light" 는 v2 스냅샷 잔재 — 문서 정리 동반.

**권장 접근:** 항목별 1-line 수정 (전부 표시/문서 전용, 로직 무변경). BL-402 SelectWithDisplayName 교체 PR 에 동승 가능.

**Risk:** 🟢 (표시 전용 — 시각 스냅샷 확인만).

---

### BL-409

**Title:** pine_v2 워밍업 TV-parity 잔여 2건 — (a) ta.ema 시딩 정합 (bs bar12↔bar15 실측 편차 진짜 후보) (b) bool[n] 범위밖 과거참조 nan vs TV false
**Category:** Backend / pine_v2 warmup parity
**Priority:** P3
**Trigger:** 다음 pine_v2 TV-parity 사이클 (BL-405 재분류 후속) — 특히 (a)는 실제 TradingView 그라운드트루스 확보 시
**Est:** M ((a) ta.ema 시딩 조사 2-4h — 단 확정엔 실제 TV 실행 대조 필요 / (b) XS, 관측 무영향이라 저순위)
**출처:** 2026-07-12 A+B+C Trust 번들 — BL-405 재분류 과정에서 TV 문서 검증 + 회귀 테스트(`test_na_bool_tv_parity.py`)로 표면화

**원인 / 영향:**

- **(a) ta.ema 워밍업 시딩** — 엔진 `ta_ema`(stdlib.py:81-97)는 첫 `length-1` bar 를 nan 으로 두고 bar `length-1` 에서 SMA 로 시드. 실제 TradingView 의 ta.ema 워밍업 시작 bar/값이 다르면 emaSlow 가 다른 bar 에서 살아나 `bull != bull[1]` 첫 전환이 다른 bar 로 이동한다. **bs 4h 2024 의 엔진 bar 12 vs 오라클 주장 bar 15 편차의 진짜 후보** (bool-na 와 무관). 확정하려면 실제 TradingView 에서 bs 4h 2024 의 첫 시그널 bar + ta.ema(5)/ta.ema(13) 초기 시리즈를 관측해 엔진과 대조해야 함 (순수 pandas 오라클이 엔진과 같은 시딩을 가정하면 순환검증 — §7.3).
- **(b) bool[n] 범위밖 과거참조** — `_eval_subscript`(interpreter.py:882-884)가 범위밖 history 를 타입 무관 nan 반환. bool 변수의 `b[1]` 이 bar 0 에서 nan (TV 는 false). 소비(비교/제어흐름)에서 `_truthy`/비교가 nan→false 로 소거 → **거래·시그널 영향 0** (test_na_bool_tv_parity.py 가 관측 등가 잠금). raw 저장 값만 편차.

**권장 접근:** (a) 실제 TV ta.ema 초기 시리즈 캡처 → 엔진 시딩 규칙 대조/조정 (BL-378 ta.atr Wilder 검증 프로토콜 재사용 — TV 문서/실행 대조 + 수계산 오라클). (b) 관측 등가라 저순위 — 정적 bool 타입 추론 도입 시 함께 (pine_v2 동적 타입이라 난이도 있음).

**Risk:** 🟢 ((a) 조사 우선; (b) 관측 무영향).

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

### BL-410

**Title:** FE vercel-react-best-practices 감사 low 잔여 팩 (확정 8건 — 배럴 2 + localStorage 스키마 2 + js 최적화 3 + fitContent 설계 1)
**Category:** Frontend / 성능·컨벤션
**Priority:** P3
**Trigger:** 다음 FE polish 사이클 (BL-408 과 묶음 가능)
**Est:** S (2-4h — 전부 국소)
**출처:** 2026-07-13 vercel 70룰 멀티에이전트 감사 (파인더 6 + 반박형 검증, 원시 24 → 확정 18 중 high/medium 10건은 stage/fe-react-audit PR #433 에서 해소 — 본 팩은 low 8건)

**원인 / 영향:** (1) `components/ui/form.tsx:6` + `features/trading/index.ts:3` 배럴 import. (2) `features/strategy/webhook-secret-storage.ts:53` + `draft.ts:89` localStorage 버전 스키마 부재. (3) `features/backtest/utils.ts:218` 함수 결과 캐시 부재 + `equity-chart-v2.tsx:184` / `trade-stats-strip.tsx:113` filter/map 다중 순회. (4) `components/charts/trading-chart.tsx:300` data effect 의 `fitContent()` 가 매 sync 마다 실행되는 설계 — 근본 수정(최초 1회 제한)은 전 호출처 동작 변경이라 별도 검토 (PR #433 은 호출측 identity 안정화로 해소).

**권장 접근:** 항목별 1-line~소형 수정. (4)는 lightweight-charts v5 업그레이드 (BL-395) 와 함께 재검토.

**Risk:** 🟢.

---

### BL-411

**Title:** optimizer 422 에러 메시지 stale — "Sprint 55 supports {grid_search, bayesian}" 이 genetic 활성 후에도 미지원 안내 → ✅ **Resolved (2026-07-23, stage/functional-parity — `OptimizationKind` enum 파생 + Sprint 넘버 문구 중립화)**
**Category:** Optimizer / correctness (사용자 노출 메시지)
**Priority:** P3
**Trigger:** optimizer 다음 터치 시 동승
**Est:** XS (~0.5h)
**출처:** 2026-07-13 optimizer deepen 감사 후보 N3 (사용자 pick 제외 → BL 등재). `backend/src/optimizer/exceptions.py:43-76`

**원인 / 영향:** genetic 은 Sprint 56 활성인데 `OptimizationKindUnsupportedError` 메시지가 "genetic = Sprint 56+ 예정" 이라 안내 — kind mismatch 시 사용자가 틀린 지원 목록을 받음. `OptimizationParameterUnsupportedError` 의 "Sprint 54 MVP" 문구도 동류.

**권장 접근:** 지원 목록을 `OptimizationKind` enum 에서 파생해 drift 구조 차단 + `test_exceptions.py` 메시지 assert 갱신.

**Risk:** 🟢 (문자열).

---

### BL-412

**Title:** optimizer result read-side 판별 유니온 (C-full) — `OptimizationRunResponse.result: dict[str,Any]` 를 FE 동형 `OptimizationResultOut` 으로
**Category:** Optimizer / Arch (read-side 타입화)
**Priority:** P3
**Trigger:** optimizer 폼/리포트 다음 기능 사이클 (BL-235/236/364 중 아무거나 착수 시 동승 검토)
**Est:** M (+80~120 LOC, FE 동형 유지 의무)
**출처:** 2026-07-13 optimizer deepen 감사 후보 C-full (C-min 은 동일 세션 해소 — get/list 손상 row 방어 대칭화, PR feat/optimizer-cmin-n2)

**원인 / 영향:** BE 는 typed 역직렬화 역량(`*_from_jsonb`)을 갖고도 read 응답을 untyped dict 로 흘려 FE zod 가 유일한 검증층. writer 변경 시 drift 를 BE 테스트가 못 잡음 (BL-388/392 harm-class).

**권장 접근:** ADR-013 §7.2/§8.2 result grammar 를 정확히 mirror 하는 `OptimizationResultOut` 판별 유니온 추가 — 반드시 C-min 의 저하 경로(retro-incorrect row 404) 위에서 soft-validate. FE `schemas.ts` 와 필드 1:1 대조 테스트 동반.

**Risk:** 🟡 (구 row 실패율 상승 가능 — C-min 선행 완료로 완화됨).

---

### BL-413

**Title:** 주문 상세 조회 배선 — BE `GET /orders/{id}` 기존재하나 프로토타입 screen-11 에 상세 affordance(행 확장/드로어) 부재로 defer
**Category:** Frontend / orders
**Priority:** P3
**Trigger:** 주문 상세 화면/드로어가 디자인 캐논(프로토타입)에 추가될 때
**Est:** S (2-4h)
**출처:** 2026-07-23 functional-parity 스프린트 defer 판정

**원인 / 영향:** 원장 행이 이미 전 필드(오류 메시지 전문 포함)를 인쇄해 실해는 낮음. 디자인 근거 없는 UI 신설은 캐논 위반이라 배선만 보류.

**권장 접근:** 프로토타입에 상세 affordance 가 생기면 `GET /orders/{id}` (broker 원문/체결 상세) 배선.

---

### BL-414

**Title:** 스트레스 테스트 이력 리스트 UI — `GET /stress-tests` 목록 API 기존재하나 프로토타입 17벌에 이력 화면 부재로 defer (A7-lite 로 최신 1건 복원만 해소)
**Category:** Frontend / backtest 리포트
**Priority:** P3
**Trigger:** 스트레스 이력 화면이 디자인 캐논에 추가될 때
**Est:** S-M (3-5h)
**출처:** 2026-07-23 functional-parity 스프린트 defer 판정

**원인 / 영향:** 리로드 소실(기능 격차의 본질)은 A7-lite 가 해소. 과거 실행 브라우징만 미지원.

**권장 접근:** 이력 리스트 도입 시 `stressTestKeys.byBacktest` 캐시를 단일 Summary 에서 페이지 응답으로 재정의해야 함 (A7-lite 구현 노트).

---

### BL-415

**Title:** `.field-error` FieldError 컴포넌트 3사본 → 공용 컴포넌트 승격 + zod-v4-resolver 평탄 키의 per-field 재검증 stale 가능성
**Category:** Frontend / 폼 프리미티브
**Priority:** P3
**Trigger:** 다음 폼 터치 사이클 또는 4번째 사본 등장 시
**Est:** S (2-3h)
**출처:** 2026-07-23 BL-401 적대 평가 사소 지적 (waitlist/optimizer 2곳+@ 사본)

**원인 / 영향:** waitlist·optimizer 가 동일 FieldError 를 로컬 복제. 또 커스텀 resolver 가 평탄 키(`parameters.0.max`)로 에러를 만들면 RHF per-field 재검증(dotted-path unset)이 못 지워 제출 재시도까지 stale 에러가 남을 수 있음 (중첩 경로 폼 첫 소비 사례).

**권장 접근:** `components/` 공용 FieldError 승격 + resolver 평탄/중첩 키 정책 1개로 통일 + stale 재검증 재현 테스트.

---

### BL-416

**✅ Resolved (2026-07-24 trading-surface-pack)** — `cancelOrder.variables===o.id` 행별 disabled + 비-409 broad toast + 실 ACTIVE_ORDER_STATES import.

**Title:** 주문취소 FE polish 팩 — 행별 disabled(현재 전역 `isPending` 으로 전 행 잠김) + 비-409 에러 무피드백 + 테스트 mock 의 ACTIVE_ORDER_STATES 리터럴 드리프트
**Category:** Frontend / orders UX
**Priority:** P3
**Trigger:** 다건 미체결 운영이 일상화되거나 orders 다음 터치 시
**Est:** S (2-3h)
**출처:** 2026-07-23 A2 적대 평가 사소 지적 3건 묶음

**원인 / 영향:** 한 건 취소 중 다른 행 버튼도 잠김(기능 위반 아님, 거친 UX). 네트워크/500 실패 시 toast 무발화(도메인 관례와는 일치). 테스트 mock 이 실 상수 대신 Set 리터럴 복제라 드리프트 침묵.

**권장 접근:** mutation variables 기반 행별 pending + 비-409 공용 에러 toast 정책 결정 + mock 을 실 상수 import 로.

---

### BL-417

**Title:** `LiveSignalState.last_open_trades_snapshot` 이 실경로에서 항상 `{}` — 저장 가드가 리스트를 버림 (dead data 컬럼) → ✅ **Resolved (2026-07-24, stage/opspack-ws2)**
**Category:** Backend / trading live-signal
**Priority:** P2
**Trigger:** live_signal 다음 터치 또는 스냅샷 소비자 신설 시
**Est:** S (2-4h)
**출처:** 2026-07-24 tier-c G0 (codex) 발견 — 코드 대조 확정

**원인 / 영향:** `to_report()` 는 `open_trades` 를 **리스트**로 내는데(strategy_state.py:813) live_signal.py 업서트 가드는 `isinstance(dict)` 만 저장 → 컬럼이 영구 `{}`. tier-c 포지션 대조는 `last_strategy_state_report["open_trades"]` 로 우회했으나, 컬럼 자체는 죽은 데이터로 남아 미래 소비자를 오도한다.

**권장 접근:** 저장 계약을 리스트로 교정(소비자 전수 확인 후) 또는 컬럼 제거 마이그레이션. 어느 쪽이든 report 필드와의 SSOT 단일화.

---

### BL-418

**Title:** realtime 이벤트 payload 계약 미강제 — publisher/manager 가 임의 dict 통과 (worker 간 계약 drift 표면) → ✅ **Resolved (2026-07-24, stage/opspack-ws2)**
**Category:** Backend / realtime
**Priority:** P3
**Trigger:** 발행 지점 추가 또는 이벤트 타입 확장 시
**Est:** S (2-3h)
**출처:** 2026-07-24 tier-c 최종 diff 리뷰 (codex MINOR)

**원인 / 영향:** BE 에 타입별 payload Pydantic 모델이 선언돼 있으나 publish_realtime 은 dict 를 그대로 직렬화. 필수 필드 누락 발행 시 FE zod 가 조용히 drop — 현 13개 발행 지점은 전부 채우지만 신규 지점의 계약 위반을 못 잡는다.

**권장 접근:** publish_realtime 이 event_type 별 payload 모델로 validate (no-raise 유지 — 실패 시 skip+counter) + 계약 테스트.

---

### BL-419

**Title:** live_signal `result.errors` 경로의 세션 자동 비활성이 `session_state` 를 발행하지 않음 (최대 30s stale) → ✅ **Resolved (2026-07-24, stage/opspack-ws2)**
**Category:** Backend / realtime
**Priority:** P3
**Trigger:** realtime 다음 터치 시
**Est:** XS (1h)
**출처:** 2026-07-24 tier-c 최종 diff 리뷰 (codex MINOR — live_signal.py:533 부근)

**원인 / 영향:** preflight/런타임 오류 2경로는 발행하나 `result.errors` 비활성 경로는 누락 — 폴링(30s)까지 코크핏 활성 세션 수가 stale.

**권장 접근:** 해당 commit 직후 발행 1줄 + spy 테스트 (publish-be 패턴 미러).

---

### BL-420

**Title:** WS 인바운드 서버 하드닝 팩 — 비인증 소켓 글로벌 상한/rate-limit + auth→realtime 역참조 정리
**Category:** Backend / realtime 보안·아키텍처
**Priority:** P3
**Trigger:** Beta 공개 배포 전 또는 realtime 다음 터치 시
**Est:** S (2-4h)
**출처:** 2026-07-24 tc-realtime-be 적대 평가 잔여 리스크 2건

**원인 / 영향:** accept 후 5s auth 창을 쥔 미인증 소켓의 동시 수 상한이 없음(per-user 상한은 인증 후에만 작동, Origin 은 비브라우저가 위조 가능 — 인증 자체는 별도라 보안 붕괴는 아님). 또 `src/auth/dependencies.py` 가 feature 도메인 `src.realtime.auth` 를 import 하는 방향 역전.

**권장 접근:** pre-auth 소켓 글로벌 상한/접속 rate-limit + helper 를 `src/auth/` 로 이동하고 realtime 이 역참조. (부수: position 서비스의 spot 방어 분기 dead code — `market_type` 키는 실경로 저장 불가 — 함께 정리.)

---

### BL-421

**Title:** 미평가 라이브 세션의 `/state` 404 무한 폴링 — 콘솔 error 도배 (정상 과도상태를 error 로 표면화) → ✅ **Resolved (2026-07-24, stage/opspack-ws2)**
**Category:** Backend+Frontend / live-sessions
**Priority:** P2
**Trigger:** 라이브 세션 다음 터치 시
**Est:** S (2-3h)
**출처:** 2026-07-24 tier-c Opus dogfood 발견 #1 (기존재 동작 — tier-c 회귀 아님)

**원인 / 영향:** 신규 세션은 첫 evaluate tick 전까지 `GET /live-sessions/{id}/state` 가 404("not yet evaluated"). FE 는 2-3s 간격 폴링이라 세션 선택 직후 콘솔 error 가 무한 누적(~90+/10분 실측). beat 정지 시엔 영구 지속.

**권장 접근:** BE 를 200+`evaluated:false`(또는 204) pending 시맨틱으로 바꾸거나, FE 가 이 404 를 예상 상태로 흡수(에러 로그 억제 + 폴링 백오프). 콘솔 위생 게이트의 기지 예외 목록에 임시 등재 금지 — 근본 해소.

---

### BL-422

**Title:** 알림 규칙 생성 폼이 empty 상태에서만 노출 — 세션당 2번째 규칙(watchdog 등) UI 추가 불가 + 409 경로 UI 도달 불가 → ✅ **Resolved (2026-07-24, stage/opspack-ws2)**
**Category:** Frontend / alert-rules UX
**Priority:** P3
**Trigger:** 알림 규칙 실사용 개시 시
**Est:** XS-S (1-2h)
**출처:** 2026-07-24 tier-c Opus dogfood 발견 #2

**원인 / 영향:** 규칙 1개라도 있으면 "만들기" 어포던스가 사라져 loss_limit+watchdog 동시 운용을 UI 로 못 만든다 (BE 는 유형별 1개씩 허용). 409 안내 문구는 유닛으로만 검증됨.

**권장 접근:** ok 상태에도 "규칙 추가" 어포던스 유지 (rule_type 별 중복은 409 안내가 처리). 표기 nit 동반: threshold "5.00000000%" → trimming (dogfood 발견 #3).

---

### BL-423

**Title:** 비활성(과거) 세션의 진단 정보를 UI 로 열 수 없음 — `/live-sessions` 가 active 전용
**Category:** Frontend / live-sessions UX
**Priority:** P3
**Trigger:** 과거 세션의 규칙·포지션·상태 회고 필요 시
**Est:** S (2-4h)
**출처:** 2026-07-24 opspack-ws2 Opus dogfood — 검증자가 RQ 캐시 주입으로 우회해야 했음 (docs/opspack-ws2/context-notes.md #14)

**원인 / 영향:** BE `list_active()` 필터 + FE 리스트 클릭 전용 진입이라 비활성 세션의 알림 규칙/포지션 대조/state 를 볼 방법이 없다. 세션 종료 후 회고·규칙 정리가 불가.

**권장 접근:** 목록 API 에 `include_inactive` 쿼리 또는 별도 이력 뷰. 상세 진입의 URL 파라미터화 동반 검토.

---

### BL-424

**Title:** 대시보드 실현손익 카드 foot — 미실현(추정) 부기와 기존 문구가 시각적으로 밀착 (폭 부족)
**Category:** Frontend / dashboard 시각
**Priority:** P3
**Trigger:** 대시보드 polish 시
**Est:** XS (<1h)
**출처:** 2026-07-24 opspack-ws2 D8b dogfood 스크린샷 (docs/opspack-ws2/context-notes.md #18)

**원인 / 영향:** foot 문장 줄바꿈 + 부기 병치로 간격이 타이트. 판독은 가능하나 밀도 과다.

**권장 접근:** 부기를 별도 행/뱃지로 분리하거나 foot 문구 축약.

---

### BL-425

**✅ Resolved (2026-07-24 trading-surface-pack)** — alert-rule-form 사전 중복검사(마운트된 `rules.data.items` 재사용, 새 fetch·409 요청·broad 콘솔 allowlist 없음). dogfood 전 상호작용 콘솔 error 0.

**Title:** 예상된 alert-rules 409(중복 활성 규칙)가 브라우저 콘솔 error 로 노출
**Category:** Frontend / 관찰성
**Priority:** P3
**Trigger:** 콘솔 위생 게이트 강화 시
**Est:** XS (<1h)
**출처:** 2026-07-24 opspack-ws2 D8b dogfood (기능 무해 — FE 는 정상 캐치·안내)

**원인 / 영향:** fetch 의 4xx 응답은 브라우저가 네이티브 로그를 남긴다. 409 는 정상 흐름(중복 안내)이라 노이즈.

**권장 접근:** 사전 중복 검사(로컬 규칙 목록 대조)로 409 요청 자체를 회피하거나, 콘솔 게이트에서 409 전용 좁은 예외를 채택할지 결정 (404 류 브로드 예외 부활은 금지).

---

### BL-426

**Title:** ws_stream 워커 용량 정책 — 멀티계정 시 public ticker starvation 가능 + 스트림 태스크 루프 직접 유닛 부재
**Category:** Backend / trading websocket 인프라
**Priority:** P3
**Trigger:** 거래소 계정 2개 이상 등록 시 (현 로컬 1계정 무해)
**Est:** S-M (2-6h)
**출처:** 2026-07-24 opspack-ws2 codex G0 + WA 적대평가 P3 관찰

**원인 / 영향:** reconcile 이 활성 계정마다 장기 private stream 을 enqueue 하는데 계정 수 상한이 없어, 계정 N+1 > concurrency(3) 이면 public ticker 태스크가 큐에서 기아. 또한 60s refresh/lease-lost 루프는 코드 정독+프로브로만 검증(직접 단위 테스트 없음).

**권장 접근:** singleton public ticker 를 별도 큐·concurrency 1 워커로 분리하거나 계정 수 기반 concurrency 산정 + starvation 회귀 테스트. refresh 루프 유닛 동반.

---

### BL-427

**Title:** 전략 목록 파라미터 열 / 수명주기 칩(초안·검증·배포) 미렌더 — 백엔드 스키마 부재
**Category:** Frontend / backend schema
**Priority:** P3
**Trigger:** 전략 파라미터/수명주기 UI 요구 시
**Est:** M (4-8h, BE 스키마 + FE)
**출처:** 2026-07-24 perf-surface (캐논 프로토타입엔 존재하나 StrategyListItem 스키마에 파라미터·lifecycle 필드 없음 → §4.9 미렌더 유지)

**원인 / 영향:** 캐논 screen 은 전략별 파라미터 요약 + 수명주기 칩을 그리나, `StrategyListItem` 에 해당 필드가 없어 perf-surface 는 성과 3칸만 노출하고 파라미터/칩은 의도적으로 미렌더. 데이터 모델 확장 전까지 표면 불가.

**권장 접근:** Strategy 파라미터 요약 + lifecycle 상태를 list 응답에 파생/영속 후 FE 칩 렌더. 스키마 우선.

---

### BL-428

**Title:** 트레이드 구간 미니차트 share 페이지 미지원
**Category:** Frontend
**Priority:** P3
**Trigger:** 공개 share 리포트에 구간 차트 요구 시
**Est:** M (owner-authed OHLCV 엔드포인트를 token 기반 공개 경로로 확장)
**출처:** 2026-07-24 perf-surface A4 (TradeDetailTable 은 owner-authed `/trades/{i}/ohlcv` 사용 → share 페이지는 미렌더가 정직. 현재 share 는 trade 표 자체가 없음)

**원인 / 영향:** 미니차트 fetch 는 owner-authed 엔드포인트라 share(token) 컨텍스트에서 401. 현재 share 페이지는 Stat 카드+EquitySparkline 만 있고 trade 표가 없어 무해하나, 향후 share 에 trade 상세 도입 시 차트 공백.

**권장 접근:** token 기반 공개 OHLCV 조회 경로(민감도 낮음 — 과거 시세) 또는 share 렌더 시 차트 명시적 비활성 + 안내.

---

### BL-429

**Title:** 대시보드 §03 최적화 완료행 수익률/MDD 역산 미표시(`—` 고정)
**Category:** Frontend / backend
**Priority:** P3
**Trigger:** 대시보드에서 최적화 best 성과를 목록 단계에서 보고 싶을 때
**Est:** S-M (best_params 대응 backtest metric 역산 또는 denormalize)
**출처:** 2026-07-24 perf-surface A3 (§03 병합에서 최적화 행은 수익률/MDD 를 `—`+"결과는 최적화 상세에서 확인" 으로 고정. best 지표 역산은 후속)

**원인 / 영향:** OptimizationRun 은 param_space/result(iterations) 만 보유, best 조합의 백테스트 metric 은 목록에 없어 §03 최적화 행 성과 칸이 빈칸. 정직하나 정보 밀도 낮음.

**권장 접근:** result 의 best_params → 대응 backtest metric 매핑을 denormalize 하거나 best objective_value 만이라도 표기.

---

### BL-430

**Title:** 전략 목록 성과 정렬(수익률/샤프) SORT_OPTIONS 미제공
**Category:** Frontend
**Priority:** P3
**Trigger:** 전략을 최근 성과 순으로 정렬하고 싶을 때
**Est:** S (2-3h; BE latest_backtest 정렬 축 + FE SORT_OPTIONS 확장)
**출처:** 2026-07-24 perf-surface A2 stretch 미실행 (SORT_OPTIONS 는 recent/name 만; 성과 3칸은 표기만, 정렬 축 부재)

**원인 / 영향:** 성과 열은 노출됐으나 전략 목록은 마지막수정/이름 정렬만 지원. latest_backtest 성과 기준 정렬 부재로 우열 비교가 목록 단계에서 제한적.

**권장 접근:** `latest_completed_by_strategy_ids` 결과를 정렬 축으로 노출(서버 정렬) + FE SORT_OPTIONS 에 수익률/샤프 추가. 클라 정렬은 페이지 한정이라 지양.

---

### BL-431

**✅ Resolved (2026-07-24 trading-surface-pack)** — 포지션-보고 TP/SL read-time 2열 + reduce-only 시장가 청산(세션스코프 202, flatten 가드 bypass, 청산 leverage=포지션값). 완전 TP/SL 보고(조건부 주문 조인)는 BL-434 이연.

**Title:** 코크핏 §03 열린 포지션 표 TP/SL·청산 액션 열 미렌더 — API 부재
**Category:** Backend / Frontend
**Priority:** P2
**Trigger:** 코크핏에서 포지션 TP/SL 확인 또는 시장가 청산이 필요할 때
**Est:** M-L (BE bracket/close 조회·발주 API + FE 열/액션)
**출처:** 2026-07-24 position-cockpit B4 (캐논 screen-01 은 TP/SL·청산 열 보유하나 `/positions` verdict 응답에 없어 §4.9 미렌더)

**원인 / 영향:** 캐논 프로토타입은 열린 포지션 행에 TP/SL 값 + 시장가 청산 액션을 두나, 현재 PositionService 응답은 대조 verdict + 거래소 보고 포지션(size/side/entry/mark/uPnL/liq/leverage)만 제공. TP/SL 부착 상태 조회 API 와 청산 발주 API 부재로 정직하게 미렌더.

**권장 접근:** 거래소 conditional order(TP/SL) 조회를 positions 응답에 조인 + reduce-only 시장가 청산 엔드포인트 신설 후 표 열/액션 렌더.

---

### BL-432

**✅ Resolved (2026-07-24 trading-surface-pack)** — `useLiveSessionsPositions` per-query select 제거 → `combineLiveSessionPositions(sessions, results)` 인덱스 zip(형제 aggregate 패턴) + 고아 `makePositionsSelector`/`LiveSessionPositionQueryData` 삭제.

**Title:** 잔고/포지션 useQueries select 콜백이 렌더마다 새 클로저
**Category:** Frontend / perf
**Priority:** P3
**Trigger:** 코크핏 리렌더 프로파일링 또는 vercel-react 정리 시
**Est:** S (2-3h; per-session selector 메모 또는 combine 이관)
**출처:** 2026-07-24 position-cockpit W3 평가(hooks.ts:340 `select: makePositionsSelector(session)` 렌더마다 새 identity → select 재실행)

**원인 / 영향:** `useLiveSessionsPositions` 의 useQueries 각 쿼리 `select` 가 렌더마다 새 함수라 select 변환이 매 렌더 재실행. combine 산출은 structural sharing 되고 identity-민감 effect 없어 무해(cosmetic/perf-only). 기존 per-render 팩토리 컨벤션(makeXFetcher)과 동일 패턴이라 회귀 위험 고려해 이번 스프린트 미수정.

**권장 접근:** session-label 부착을 select 대신 combine 으로 이관(쿼리별 select 제거)하거나 session 키 기준 selector 메모. tsc/lint 무영향.

---

### BL-433

**✅ Resolved (2026-07-24 trading-surface-pack, metric 부분)** — `qb_ws_subscribe_rejected_total{account_id}` counter + position_fanout reject `.labels().inc()`. BL-423(비활성 세션 진단 UI) 연계는 별도 유지.

**Title:** WS subscribe negative-ack 관측이 warning 로그만 — metric counter 부재 + BL-423 연계
**Category:** Backend / observability
**Priority:** P3
**Trigger:** position 구독 거부의 silent 폴링 degrade 를 대시보드로 감지하려 할 때
**Est:** S (metric counter + BL-423 비활성 세션 진단 표기)
**출처:** 2026-07-24 position-cockpit (PrivateTopicRouter subscribe success:false → `ws_subscribe_rejected` warning 만; 진단 §08 에서 PositionDiagnostic 제거로 포지션 상태가 §03 표로 이관)

**원인 / 영향:** position 구독이 거부되면 warning 만 남기고 15s 폴링으로 조용히 degrade — Prometheus counter 부재로 집계 불가. 또한 결정 ⑤로 §08 진단의 PositionDiagnostic 제거되어 비활성 세션의 포지션 상태 노출이 §03 표(활성 세션만)로 이관 → BL-423(비활성 세션 진단 UI)과 연계 재검토 필요.

**권장 접근:** `qb_ws_subscribe_rejected_total` counter 추가 + BL-423 에서 비활성 세션 포지션 상태의 별도 진단 표기 여부 결정.

---

### BL-434

**Title:** 완전 TP/SL 보고 — 포지션-부착 외 조건부(Partial-mode limit-TP) 주문 미표시 + 청산 시 미스윕
**Category:** Backend / Frontend / trading
**Priority:** P3
**Trigger:** 코크핏 §03 이 걸어둔 모든 TP/SL 을 보여줘야 하거나, 청산 후 잔여 조건부 주문 정리가 필요할 때
**Est:** M (fetch_open_orders 조인 + 스키마 확장 + 청산 스윕)
**출처:** 2026-07-24 trading-surface-pack (BL-431 은 포지션 필드만 read — Partial-mode limit-TP 는 별도 conditional order 라 미표시, 각주로 정직)

**원인 / 영향:** ccxt `fetch_positions` 의 position 필드는 Full-mode SL + set-trading-stop 트레일링만 담는다. QB 가 tpslMode=Partial 로 부착한 limit-TP 는 별도 조건부 주문이라 §03 에 안 나온다(각주로 고지). 또 reduce-only 청산은 포지션만 flatten 하고 잔여 조건부 주문은 스윕하지 않는다(포지션-부착 TP/SL 은 Bybit 이 flat 시 자동취소).

**권장 접근:** `fetch_open_orders`(conditional) 조인으로 완전 TP/SL 표시 + 청산 시 열린 reduce-only 조건부 주문 취소.

---

### BL-435

**Title:** 수동 청산 후 §03 flat 반영 지연 — WS 미연결 창에서 캐시 TTL+폴 지연(~15-30s)
**Category:** Backend / Frontend / UX
**Priority:** P3
**Trigger:** 청산 즉시성 UX 개선 또는 WS 미연결 시나리오 다발 시
**Est:** S (청산 서비스에서 position 캐시 DEL)
**출처:** 2026-07-24 trading-surface-pack dogfood (청산 202 후 오라클 flat 이나 §03 는 WS 미연결 창에서 ~30s 뒤 빈복귀 — 사용자 확정 비동기 202 설계 내이나 WS 의존)

**원인 / 영향:** 청산 flat 반영은 WS position_update(fast) + 15s 폴링(fallback)에 의존. 신규 활성 세션은 ws-stream reconcile(300s) 전이라 WS 미푸시 → 폴 fallback 만 동작(캐시 15s TTL + 폴 간격). 머니-패스 정확(청산 성공)하나 즉시성 미흡.

**권장 접근:** 청산 서비스가 발주 직후 `qb_pos_snapshot:{session_id}` 캐시 DEL(WS position_update 핸들러 DEL 패턴 미러) → 폴 fallback 이 WS 독립으로 fresh. (거래소 체결 지연은 잔존.)

---

### BL-436

**Title:** 청산 create_order 가 settings.margin_mode 로 set_margin_mode — 포지션 실제 mode 불일치 시 실패 가능
**Category:** Backend / trading
**Priority:** P3
**Trigger:** 포지션 실제 margin_mode 와 전략 settings 가 어긋나는 수동/외부 포지션 청산 시
**Est:** S (PositionSnapshot 에 margin_mode 노출 후 포지션값 사용, leverage fix 와 동형)
**출처:** 2026-07-24 trading-surface-pack (최종 codex diff review — leverage 는 포지션값으로 fix, margin_mode 는 잔여)

**원인 / 영향:** `create_order`(providers.py:545-556)가 주문 전 `set_margin_mode(order.margin_mode)` 호출. 청산은 `settings.margin_mode` 사용 — 포지션 실제 mode 와 같으면 "not modified" no-op(관리 플로우), 다르면 Bybit 이 open position 의 margin 변경을 거부해 청산 503 가능. leverage 는 포지션값 사용으로 해소했으나 PositionSnapshot 에 margin_mode 필드 부재로 margin 은 잔여. live_signal 청산 경로도 동형(공유 특성).

**권장 접근:** PositionSnapshot 에 margin_mode 노출 → 청산 req 에 포지션값 사용(leverage 와 동일 원리, set_margin_mode no-op). 또는 reduce_only 경로에서 set_margin_mode/set_leverage skip.

---

## 운영 규약

### 신규 항목 추가

1. 적절한 priority 결정 (P0~P3 정의 표 참조)
2. 다음 BL ID 부여 (현재 사용 범위: BL-001~005, BL-010~433)
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

### functional-parity 스프린트 (2026-07-23)

- **C 디자인 이식 후 기능 격차 마감 (codex exec 4-generator 병렬 + Claude 적대 평가 교차 + Opus MCP dogfood)**: BL-401/BL-411 구현 Resolved + BL-402 구조 소멸 Resolved. 신규 배선 = 주문취소 액션 열(A2, "API unbacked" 미렌더 전제가 거짓 — CF4 완비 실측) / orders `state` 반복 Query + 미체결 nav-count(B2, 캐논 §4.6 복원) / `strategy.backtest_count` read-time GROUP BY(B1, COMPLETED 기준) / 스트레스 최신 결과 리로드 복원(A7-lite) / 대시보드 전략 링크 404 수정(A1) / dead code 정리(backtest-history-card·viewBacktestShare·StrategyWithPine stub). 적대 평가가 실버그 3건 사전 차단(RQ v5 undefined-resolve 영구 error / grid min==max 차단 회귀 / Sprint 54 문구 잔존). 신규 BL-413~416. 정본 = [`functional-parity/`](functional-parity/checklist.md).

### optimizer deepen + FE vercel 70룰 감사 (2026-07-13)

- **optimizer deepen 1차 (improve-codebase-architecture, 감사→같은 세션 구현)**: STOP 실측(repository.py 40%) → S0 test-first (40%→100%, 실 DB 11건) + A(디스패치 SSOT — service inline match 제거, seam 3이름→1이름) + B(serializer 공통 helper + `optimizer_result_to_jsonb` 진입점, golden byte-compat 실증) + N1(`engine/dispatch.py`→`select.py` rename — dispatcher.py 이름충돌 해소) + C-min(get/list 손상 row 방어 대칭화, get 500→404) + N2(pick-best·objective 화이트리스트 `_common` SSOT). PR #431/#432/feat/optimizer-cmin-n2 (base stage/optimizer-deepen). 적대 리뷰 P1 0건 + 실 celery worker 3-cell grid 풀 스모크 COMPLETED 검증. KILL/보류: N3→BL-411, C-full→BL-412, N4/N5(이미 deep/의도된 분리 — 재제안 금지).
- **FE vercel 70룰 감사** (파인더 6+반박 검증 30 에이전트, 원시 24→확정 18): high/medium 10건 수정 — **BL-407 Resolved** (lwc v4 PercentageFormatter ×100 부재+precision 양자화 이중결함, 육안 검증 PASS) + live-sessions 차트 identity churn(폴링마다 줌 리셋, "React Compiler 자동 memoize" 주석 거짓 전제 확인) + O(E×N)→O(E+N) + all-trades 병렬 페치 + clerk 배럴 4.9MB→95KB. PR #433 (base stage/fe-react-audit), live smoke 그린(authed 실패 8건은 main 과 동일 집합 = 기지 stale 베이스라인 실측 대조). low 잔여 → **신규 BL-410**.
- **신규 3건**: BL-410(P3 FE low 팩) + BL-411(P3 optimizer stale 422 메시지) + BL-412(P3 result read-side 유니온 C-full).

### pine-batch QA + 엔진 개선 루프 (2026-07-12)

- **신규 4건**: BL-405(P2, pine_v2 bool na→False 실체화 — 워밍업 경계 스퓨리어스 시그널, 오라클 수계산으로 확정) + BL-406(P3, DrFXGOD 잔여 5종 — alma/dmi/time feasible, ticker.new/security_lower_tf 패러다임 밖) + BL-407(P3, 낙폭 차트 Y축 눈금 "-0.1%" 뭉개짐) + BL-408(P3, 디자인 폴리시 잔여물 팩 — stale aria-label 색명 등 6건).
- **기존 확장 1건**: BL-402 에 3사이트 추가 — `backtests/new` strategy picker(UUID 실측+원인 확정) + 원장/필터 Select 2파일 동일 클래스.
- **디자인 감사 총평**: strategies/new + 리포트 페이지 AI-slop 판정 **명백한 부정** — raw hex 0/팔레트 클래스 0/이모지 0, 다크·라이트 양 테마 변수 완비.
- **엔진 즉시 해소 5건 (BL 미경유)**: G1 루프 silent skip / G2 array 15종 / G3 bare security degraded / G4 table.new positional / G5 label.style\_ drift — PR #422, 스위트 778→815 그린.
- **데이터 정직성**: `BTCUSDT_1h.csv` 합성 데이터(OHLC 위반 77%)를 실 Bybit perp 로 교체 + 4h/최근1년 3세트 신설 — PR #421.

- **신규 1건 + 즉시 해소**: BL-404(P1, watchdog `fetch_order` Bybit 전면 실패 — ccxt acknowledged 게이트 + futures 심볼 미정규화 2중 결함) ✅ Resolved 동일 PR. 데모 라이브 세션 실주문 dogfood(코크핏/블로터 3면 검증 PASS)에서 실측 발견.
- **미등재 관찰(후보)**: 신규 세션 첫 evaluate 전 `/state` 404 FE 콘솔 노이즈 / host 기동 `/healthz` celery inspect ping 상시 timeout / ws_stream 큐의 삭제된 계정 태스크 잔재 / `fetch_mark_price` spot 티커 근사(BL-404 본문 기재).

### PR #394 후속 FE 부채 등재 (2026-07-05)

- **신규 4건**: BL-401(optimizer 3폼 field-level zod 에러 미렌더) / BL-402(백테스트 picker uncontrolled↔controlled + raw UUID, BL-164 SSOT 회귀) P2 + BL-400(`enabled: userId` 가드 도메인 비일관 — 통일 결정) / BL-403(recharts↔lwc↔inline-SVG 3원화 해소, BL-395 완료 후) P3.
- **검증 노트**: backtest 폼은 field-level 에러 정상 렌더 확인(zod resolver 미사용) → BL-401 스코프에서 제외. 4건 모두 활성/archived/deferred 중복 grep 0건.

### TV-parity sprint (2026-07-05, 백테스팅 완성도 + 리포트 전문화)

- **신규 7건**: BL-393(trail 틱 시맨틱스+mintick) / BL-398(Sharpe TV convention) P2 + BL-394(BE 분포 집계) / BL-395(lightweight-charts v5 spike) / BL-396(trades 서브페이지 컬럼) / BL-397(섹션 딥링크) / BL-399(ta.sar oracle) P3.
- **코드 반영 (BL 미등재 직접 수정)**: ta.hma sqrt floor→round TV 정합(BL-378 패턴) / BL-388 tripwire 3종+`_to_detail` spread(4→3 site) / sortino·calmar 실구현(TV convention) / BacktestMetrics TV 팩(flat 14+nested 2) / BacktestTrade 10컬럼(MFE/MAE·fee split·exit_kind·comment·누적) / FE 리포트 IA 전면 재편(TV Strategy Tester 구조, Terminal Tape 유지).

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

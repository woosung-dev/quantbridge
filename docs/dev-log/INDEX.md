# Dev-log Index

> 본 디렉토리의 모든 개발 회고·ADR·dogfood 기록의 인덱스. AGENTS.md "현재 작업" 섹션에서 sprint history 가 빠진 후 컨텍스트 복원용.
>
> 새 항목 추가 시 본 INDEX 도 함께 갱신. 형식: `날짜 — 한 줄 요약 — [파일명](파일명)`

---

## H2 Sprint + dogfood (2026-04-24 ~ , 시간 역순)

- 2026-05-09 — **/deepen-modules pilot 3-domain audit** (신규 스킬 작성 + pine_v2 SSOT (1/3) + trading (2/3) + frontend cross-page primitive (3/3) — same-session 3 audit 일괄 검증, BL-200~206 7건 신규 등재, §7.5 영구 규칙 추가 + LESSON-063 정식 승격 (Triple SSOT / Cross-module dispatcher / Cross-page primitive 3 패턴), Sprint 47 = 7 BL 대형 deepening sprint 권고 (29-41h)) — [`2026-05-09-pine_v2-deepen-pilot.md`](2026-05-09-pine_v2-deepen-pilot.md) + [`2026-05-09-trading-deepen.md`](2026-05-09-trading-deepen.md) + [`2026-05-09-frontend-deepen.md`](2026-05-09-frontend-deepen.md)
- 2026-05-09 — **Sprint 45 회고** (Surgical Cleanup #4 + #3, #1 skip — 1 worker 단일 작업, 1 PR / 5 files / +250 / -190 / 회귀 0 / 603 → 603 PASS — dashboard-shell.tsx 235L → 60L slim Shell + DashboardSidebar 79L + DashboardHeader 51L + DashboardNavList 102L 4 컴포넌트 분리, Sprint 44 wc1 inline polish 보존, codex G.4 review GATE PASS — P1 = 0 / P2 = 1 (BL-195 qb-form-slide-down truncation 등재), 71007 = Next.js TypeScript plugin IDE-only 진단 결론 (build/tsc/lint/dev clean) → Sprint 44 close-out memo 갱신, LESSON-057~058 신규 후보 → Sprint 46 = dogfood Phase 2 결과 (1-2주 wall-clock) 따라 결정) — [`2026-05-09-sprint45-close.md`](2026-05-09-sprint45-close.md)
- 2026-05-07 — **Sprint 41 회고** (외부 demo 첫인상 패키지, 4 PR / 40 files / +2615 / -166 — Worker B 디자인 token + E UX 통일 + H share link + B-2 프로토타입 App Shell + 4 페이지 layout, 자율 병렬 cmux 5번째 실측 wall-clock ≈50분, Day 7 = 8/10 gate (a)+(b)+(c)+(d) 모두 PASS, codex P2 2건 즉시 fix (Worker H share race row lock + Worker B-2 status filter chip 비활성), Playwright 자동 검증 10/10 PASS, BL-190~192 신규 3건, LESSON-048~050 신규 후보 3건 → Sprint 42 = 지인 N=5 demo 오픈 + feedback loop) — [`2026-05-07-sprint41-master.md`](2026-05-07-sprint41-master.md)
- 2026-05-07 — **Sprint 39 회고** (polish iter 7, **코드 변경 0** — BL-189 measurement artifact 결론 + wrong fix detection layer 작동, Day 7 = 7/10 gate (a)+(d) PASS → Sprint 40 = stage→main + BL-003 + BL-005 본격, LESSON-047 신규 후보 1건 (Turbopack root wrong path = file watcher storm), single worker single day ~3h) — [`2026-05-07-sprint39-master.md`](2026-05-07-sprint39-master.md)
- 2026-05-07 — **Sprint 38 회고** (polish iter 6, 4 PR stage 머지 — main 미반영 / BL-188 v3 mirror + BL-181 Resolved, Day 7.5 mid-dogfood CPU loop 113% delta 검출 → BL-189 신규 P0, Day 7 = 5/10 gate (a)+(d) FAIL → Sprint 39 = polish iter 7. LESSON-038/039/040 영구 승격 + LESSON-041~046 신규 6건. 자율 병렬 cmux 4번째 실측) — [`2026-05-07-sprint38-master.md`](2026-05-07-sprint38-master.md)
- 2026-05-06 — **Sprint 37 회고** (polish iter 5, 7 PR 머지 + 사용자 hotfix `6434a1d` 안착, BL-183/184/185/187/187a/188a Resolved + BL-186/188 신규 deferred, Day 7 = 6/10 gate (a) FAIL → Sprint 38 = polish iter 6) — [`2026-05-06-sprint37-master.md`](2026-05-06-sprint37-master.md)
- 2026-05-06 — **dogfood Day 7 (Sprint 36)** (P-1~P-6 6/6 PASS, B시나리오 ⚠️ MC 요약 통계 FE 미노출, self-assess ≤6/10 = gate (a) FAIL, BL-183 신규 등록 → Sprint 37 = polish iter 5) — [`2026-05-06-dogfood-day7-sprint36.md`](2026-05-06-dogfood-day7-sprint36.md)
- 2026-05-05 — **Sprint 35 회고** (polish iter 3, 4 PR + codex G.0 1.34M tokens surgery 18건, BL-178 root cause = Docker worker stale 확정 + BL-180 engine golden oracle 8 tests GREEN, Slice 4a mid-dogfood 6/6 PASS, Day 7 self-assess 6/10 = gate (a) FAIL → Sprint 36 = polish iter 4) — [`2026-05-05-sprint35-master-retrospective.md`](2026-05-05-sprint35-master-retrospective.md)
- 2026-05-05 — **office-hours Sprint 35 분기 결정** (Wedge A backtest 단독 정밀화 + Approach C Gated 2-step + codex GO_WITH_FIXES surgery 5건 — P2 갱신 + NEW Slice 1.5 backtest golden oracle + Slice 2 축소 BL-176 만 + Slice 3 조건부 walk-forward 만 + Day 7 4중 AND gate. spec review 9.0/10 + codex VERDICT=HOLD/P1=1/Approach OK = GO_WITH_FIXES. BL-174 = Sprint 36+ defer. Sprint 28 design 1주 만에 Premise P1 무너짐 패턴 학습 결과 기록) — [`2026-05-05-office-hours-sprint-35-decision.md`](2026-05-05-office-hours-sprint-35-decision.md)
- 2026-05-05 — **Sprint 34 회고** (polish iter 2, 3 PR + codex G.0 P1 surgery 6건 적용, BL-175 본격 fix + BL-177 dense text shorten + BL-166 kill K-2 cancel, mid-dogfood Day 6.5 PASS, dogfood Day 7 = TBD) — [`2026-05-05-sprint34-master-retrospective.md`](2026-05-05-sprint34-master-retrospective.md)
- 2026-05-05 — **dogfood Day 6.5** (Sprint 34 mid-dogfood, BL-175 머지 직후 numeric, Surface Trust 차단 PASS + R-2 silent BUG 차단 + P1-3 fail-closed 정상 작동 + BL-178 신규 등록) — [`2026-05-05-dogfood-day-6.5.md`](2026-05-05-dogfood-day-6.5.md)
- 2026-05-05 — **Sprint 33 회고** (6.5 양다리 균형 패키지, 5 PR + codex G.0 P1 surgery 3건 적용, 자율 병렬 worker isolation 영구 차단 검증 — main worktree branch swap 0건, dogfood Day 6 = TBD) — [`2026-05-05-sprint33-master-retrospective.md`](2026-05-05-sprint33-master-retrospective.md)
- 2026-05-05 — **Sprint 32 회고** (Surface Trust Recovery, 7 PR + codex G.0 P1 4건 surgery, dogfood Day 5 = 6~7 borderline = +1.5 점, 자율 병렬 worker isolation 위반 lesson Worker C/D) — [`2026-05-05-sprint32-master-retrospective.md`](2026-05-05-sprint32-master-retrospective.md)
- 2026-05-05 — Sprint 31 Day 4 dogfood handoff (Sprint 31 6 PR 후 dogfood Day 4 = 5 점, +1 progress, Sprint 32 분기 Surface Trust Recovery 결정) — [`2026-05-05-sprint31-day4-handoff.md`](2026-05-05-sprint31-day4-handoff.md)
- 2026-05-05 — Sprint 31 Pine v6 호환 ADR (Sprint 31 plan 분기 결정 ADR) — [`2026-05-05-sprint31-pine-v6-compat-adr.md`](2026-05-05-sprint31-pine-v6-compat-adr.md)
- 2026-05-05 — **Sprint 30 회고** (Surface Trust Pillar 신규, 8 PR + dogfood Day 3 = 4 점 baseline, ADR-019) — [`2026-05-05-sprint30-master-retrospective.md`](2026-05-05-sprint30-master-retrospective.md)
- 2026-05-05 — **ADR-019 Surface Trust Pillar** (Backend Reliability + Risk Management + Security + Surface Trust 4 sub-pillar, dogfood Day 3 측정 기준) — [`2026-05-05-sprint30-surface-trust-pillar-adr.md`](2026-05-05-sprint30-surface-trust-pillar-adr.md)
- 2026-05-05 — Sprint 30 chart lib decision ADR (Sprint 30 β option B, 점진 마이그 결정, BL-150 trigger) — [`2026-05-05-sprint30-chart-lib-decision.md`](2026-05-05-sprint30-chart-lib-decision.md)
- 2026-05-04 — **Sprint 29 회고** (Pine Coverage Layer Hardening + DrFXGOD Schema, dual metric ALL PASS, 5/6 통과율 + 100% workaround + 4 invariant + codex G2 P0 fix degraded gate, self-assess 9/10) — [`2026-05-04-sprint29-coverage-hardening.md`](2026-05-04-sprint29-coverage-hardening.md)
- 2026-05-04 — Sprint 29 heikinashi Trust Layer 위반 ADR (D1=a, dogfood-only flag, Sprint 30+ ADR-009 trigger) — [`2026-05-04-sprint29-heikinashi-adr.md`](2026-05-04-sprint29-heikinashi-adr.md)
- 2026-05-04 — **Sprint 29 baseline snapshot** (6 fixture preflight 실측, 진입 3/6 50%, plan v2 stale 1건 추가 발견, LESSON-037 second validation) — [`2026-05-04-sprint29-baseline-snapshot.md`](2026-05-04-sprint29-baseline-snapshot.md)
- 2026-05-04 — **Sprint 29 v1→v2 pivot** (Pine Architectural Fix → Coverage Layer Hardening, codex+Opus 2-검토 frame change, LESSON-037 후보 first validation) — [`2026-05-04-sprint29-v1-to-v2-pivot.md`](2026-05-04-sprint29-v1-to-v2-pivot.md)
- 2026-05-04 — **Sprint 28 회고** (Beta prereq 종합, 5 PR cascade, dual metric 첫 측정) — [`2026-05-04-sprint28-retrospective.md`](2026-05-04-sprint28-retrospective.md)
- 2026-05-04 — Sprint 28 kickoff plan (Vertical Slice 4 + Stage 1~6 + 메타-방법론 4종) — [`2026-05-04-sprint28-kickoff.md`](2026-05-04-sprint28-kickoff.md)

- 2026-05-04 — Sprint 27 Beta prereq hotfix — BL-137 (settings UI) + BL-140 (Activity Timeline chart), self-assessment 8.5/10 — [`2026-05-04-sprint27-beta-prereq-hotfix.md`](2026-05-04-sprint27-beta-prereq-hotfix.md)
- 2026-05-04 — Sprint 26 Pine Signal Auto-Trading — Live Session daily flow (Beat + dispatch outbox + FE), Bybit Demo 5 orders filled, codex G.0 P1 #3-6 + G.2 P1 #10 fix, BL-122~125 — [`2026-05-04-sprint26-pine-signal-auto-trading.md`](2026-05-04-sprint26-pine-signal-auto-trading.md)
- 2026-05-04 — dogfood Day 1 — Sprint 27 launch (Auto-Loop §0.5 first run, self-assessment 8/10) — [`2026-05-04-dogfood-day1-sprint27-launch.md`](2026-05-04-dogfood-day1-sprint27-launch.md)
- 2026-05-03 — Sprint 25 Hybrid (FE E2E Playwright + Backend 강화 + codex G.0/G.2) — [`2026-05-03-sprint25-hybrid.md`](2026-05-03-sprint25-hybrid.md)
- 2026-05-03 — Sprint 24b Track 1 Backend E2E 자동 dogfood — [`2026-05-03-sprint24b-auto-dogfood.md`](2026-05-03-sprint24b-auto-dogfood.md)
- 2026-05-03 — Sprint 24a WebSocket 안정화 (BL-011/012/013/016) — [`2026-05-03-sprint24a-ws-stability.md`](2026-05-03-sprint24a-ws-stability.md)
- 2026-05-03 — Sprint 23 C-3 묶음 (Pine coverage parity + BL-091 follow-up) — [`2026-05-03-sprint23-c3-bundle.md`](2026-05-03-sprint23-c3-bundle.md)
- 2026-05-03 — Sprint 22 BL-091 ExchangeAccount.mode dynamic dispatch (architectural proper fix) — [`2026-05-03-sprint22-bl091-architectural.md`](2026-05-03-sprint22-bl091-architectural.md)
- 2026-05-03 — Sprint 21 Phase H dogfood Day 1 라이브 검증 — [`2026-05-03-sprint21.md`](2026-05-03-dogfood-day1-sprint21.md)
- 2026-05-02 — Sprint 21 BL-096 Coverage Expansion + 422 Shape + Alias Ordering Fix — [`2026-05-02-sprint21-bl096-coverage-expansion.md`](2026-05-02-sprint21-bl096-coverage-expansion.md)
- 2026-05-02 — Sprint 20 Dogfood Day 0 사전 준비 + 1차 broker 호출 검증 — [`2026-05-02-sprint20-dogfood-day0-setup.md`](2026-05-02-sprint20-dogfood-day0-setup.md)
- 2026-05-02 — Sprint 19 Path C Technical Debt (BL-081/083/084/085 ✅ Resolved) — [`2026-05-02-sprint19-technical-debt.md`](2026-05-02-sprint19-technical-debt.md)
- 2026-05-02 — Sprint 18 BL-080 Path C+ Persistent Worker Loop (Option C, ✅ Resolved) — [`2026-05-02-sprint18-bl080-architectural.md`](2026-05-02-sprint18-bl080-architectural.md)
- 2026-05-02 — Sprint 17 Path C Emergency: Prefork Async Engine Hardening (부분 진전) — [`2026-05-02-sprint17-prefork-fix.md`](2026-05-02-sprint17-prefork-fix.md)
- 2026-05-01 — Sprint 16 Live Verification + BL-027 + BL-010 Backfill (Path B Option A) — [`2026-05-01-sprint16-phase0-live-and-backfill.md`](2026-05-01-sprint16-phase0-live-and-backfill.md)
- 2026-05-01 — Sprint 15 Stuck Order Watchdog (BL-001 + BL-002) — [`2026-05-01-sprint15-watchdog.md`](2026-05-01-sprint15-watchdog.md)
- 2026-04-27 — Dogfood Day 3 — Sprint 14 Track UX-2 검증 (pre-merge) — [`2026-04-27-dogfood-day3.md`](2026-04-27-dogfood-day3.md)
- 2026-04-26 — Dogfood Day 2 — Sprint 13 Track UX 검증 (pre-merge) — [`2026-04-26-dogfood-day2.md`](2026-04-26-dogfood-day2.md)
- 2026-04-25 — Dogfood Day 1 — Sprint 12 인프라 첫 가동 — [`2026-04-25-dogfood-day1.md`](2026-04-25-dogfood-day1.md)
- 2026-04-24~ — Dogfood Week 1 — Path β 병행 운영 기록 — [`dogfood-week1-path-beta.md`](dogfood-week1-path-beta.md)

---

## Sprint 1-14 매트릭스 (회고 위치 cross-link)

> **정책 (2026-05-04 cleanup):** 별도 dev-log 가 없는 sprint 는 ADR 또는 `superpowers/plans/` 또는 `superpowers/specs/` 에서 회고/계획 추적. 모든 Sprint 1-27 은 본 매트릭스에서 발견 가능.

| Sprint                                   | 회고 위치                                                                                                                                                                                                                                                                                                   | 상태                                       |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| 1 (Scaffold)                             | [`001-tech-stack.md`](./001-tech-stack.md) + [`002-parallel-scaffold-strategy.md`](./002-parallel-scaffold-strategy.md)                                                                                                                                                                                     | ADR 회고 (병렬 스캐폴딩)                   |
| 2 (Pine MVP foundation)                  | [`superpowers/specs/2026-04-15-pine-parser-mvp-design.md`](../superpowers/specs/2026-04-15-pine-parser-mvp-design.md) + [`003-pine-runtime-safety-and-parser-scope.md`](./003-pine-runtime-safety-and-parser-scope.md) + [`004-pine-parser-approach-selection.md`](./004-pine-parser-approach-selection.md) | ADR + spec                                 |
| 3 (Strategy API)                         | [`superpowers/specs/2026-04-15-sprint3-strategy-api-design.md`](../superpowers/specs/2026-04-15-sprint3-strategy-api-design.md) + [`superpowers/plans/2026-04-15-sprint3-strategy-api.md`](../superpowers/plans/2026-04-15-sprint3-strategy-api.md)                                                         | spec + plan                                |
| 4 (Backtest API + vectorbt)              | [`superpowers/specs/2026-04-15-sprint4-backtest-api-design.md`](../superpowers/specs/2026-04-15-sprint4-backtest-api-design.md) + `superpowers/specs/2026-04-15-vectorbt-signal-fill-design.md`                                                                                                             | spec                                       |
| 5 Stage B (DateTime tz-aware)            | [`005-datetime-tz-aware.md`](./005-datetime-tz-aware.md) + [`superpowers/specs/2026-04-16-sprint5-stage-b-design.md`](../superpowers/specs/2026-04-16-sprint5-stage-b-design.md)                                                                                                                            | ADR + spec                                 |
| 6 (Trading Demo, Bybit testnet)          | [`006-sprint6-design-review-summary.md`](./006-sprint6-design-review-summary.md) + [`superpowers/specs/2026-04-16-trading-demo-design.md`](../superpowers/specs/2026-04-16-trading-demo-design.md)                                                                                                          | ADR (design review)                        |
| 7a (Bybit Futures + Cross Margin)        | [`007-sprint7a-futures-decisions.md`](./007-sprint7a-futures-decisions.md)                                                                                                                                                                                                                                  | ADR                                        |
| 7b (Edit Parse UX)                       | `superpowers/plans/2026-04-17-sprint7b-edit-parse-ux.md`                                                                                                                                                                                                                                                    | plan only                                  |
| 7c (Strategy UI + scope)                 | [`008-sprint7c-scope-decision.md`](./008-sprint7c-scope-decision.md) + `superpowers/plans/2026-04-17-sprint7c-strategy-ui.md`                                                                                                                                                                               | ADR + plan                                 |
| 7d (OKX + Trading Sessions)              | [`015-sprint-7d-okx-sessions.md`](./015-sprint-7d-okx-sessions.md)                                                                                                                                                                                                                                          | ADR                                        |
| 8a (pine_v2 Tier-0 foundation)           | [`012-sprint-8a-tier0-final-report.md`](./012-sprint-8a-tier0-final-report.md)                                                                                                                                                                                                                              | ADR (final report)                         |
| 8b (Tier-1 wrapper) + 8c (multi-return)  | [`014-sprint-8b-8c-pine-v2-expansion.md`](./014-sprint-8b-8c-pine-v2-expansion.md)                                                                                                                                                                                                                          | ADR (합본)                                 |
| FE Polish Bundle 1/2 (FE-01~04 + FE-A~F) | [`017-fe-polish-bundle-1-2-retro.md`](./017-fe-polish-bundle-1-2-retro.md)                                                                                                                                                                                                                                  | ADR (묶음 회고)                            |
| Sprint Y1 (Pine Coverage Analyzer)       | [`016-sprint-y1-coverage-analyzer.md`](./016-sprint-y1-coverage-analyzer.md)                                                                                                                                                                                                                                | ADR                                        |
| 9 (Monte Carlo)                          | `superpowers/plans/2026-04-24-h2-sprint9-phase-{a,b,c,d}.md` (4 phase)                                                                                                                                                                                                                                      | **미실행** [P2 — `REFACTORING-BACKLOG.md`] |
| 10 (Optimizer)                           | `superpowers/plans/2026-04-24-h2-sprint10-phase-{a1,a2,b,c,d}.md` (5 phase)                                                                                                                                                                                                                                 | **미실행** [P2]                            |
| 11 (Path β / x1x3)                       | `superpowers/plans/2026-04-23-stage2c-2nd-plan.md` + 5 x1x3 워커 plan + 20 review                                                                                                                                                                                                                           | spec/plan/review (실제 stage 1/2/2c 머지)  |
| 12 (WS Supervisor)                       | [`018-sprint12-ws-supervisor-and-exchange-stub-removal.md`](./018-sprint12-ws-supervisor-and-exchange-stub-removal.md)                                                                                                                                                                                      | ADR                                        |
| 13 (Track UX)                            | `2026-04-26-dogfood-day2.md` (회고 일부 수렴)                                                                                                                                                                                                                                                               | dogfood log 안 압축 [archive 의도]         |
| 14 (Track UX-2)                          | `2026-04-27-dogfood-day3.md` (회고 일부 수렴)                                                                                                                                                                                                                                                               | dogfood log 안 압축 [archive 의도]         |
| 15-27 + dogfood Day 0/1                  | 각각 별도 dev-log 존재 (위 H2 Sprint 시간 역순 섹션 참조)                                                                                                                                                                                                                                                   | dev-log 직접 작성                          |

> **누락 라벨:**
>
> - `[archive 의도]` — 별도 dev-log 작성하지 않은 의도적 결정 (dogfood log 또는 ADR 에 회고 수렴)
> - `[P2 — REFACTORING-BACKLOG.md]` — H2 Sprint 9 (Monte Carlo) / 10 (Optimizer) 는 plan 만 작성, 실제 미실행 (Beta 오픈 후 우선순위 결정)
> - 이 매트릭스 갱신: 신규 sprint 회고 추가 시 본 표 갱신 의무 (Sprint template C.1 trailer 와 연결)

---

## ADR + 사후 회고 (번호순, 신뢰도 높은 결정 기록)

- 018 — Sprint 12 WebSocket Supervisor + Sprint 15-A/B Architecture Cleanup — [`018-sprint12-ws-supervisor-and-exchange-stub-removal.md`](018-sprint12-ws-supervisor-and-exchange-stub-removal.md)
- 017 — FE Polish Bundle 1/2 묶음 회고 (FE-01~04 + FE-A~F) — [`017-fe-polish-bundle-1-2-retro.md`](017-fe-polish-bundle-1-2-retro.md)
- 016 — Sprint Y1 Pre-flight Pine Coverage Analyzer (Trust Layer 사용자 축) — [`016-sprint-y1-coverage-analyzer.md`](016-sprint-y1-coverage-analyzer.md)
- 015 — Sprint 7d 회고 (OKX Adapter + Trading Sessions + Passphrase 암호화) — [`015-sprint-7d-okx-sessions.md`](015-sprint-7d-okx-sessions.md)
- 014 — Sprint 8b + 8c 합본 회고 (pine_v2 Tier-1 래퍼 + 3-Track Dispatcher) — [`014-sprint-8b-8c-pine-v2-expansion.md`](014-sprint-8b-8c-pine-v2-expansion.md)
- 013 — Trust Layer CI — 3-Layer Parity (P-1/2/3) 설계 — [`013-trust-layer-ci-design.md`](013-trust-layer-ci-design.md)
- 012 — Sprint 8a Tier-0 Final Report (Week 1-3 완주, v3.0) — [`012-sprint-8a-tier0-final-report.md`](012-sprint-8a-tier0-final-report.md)
- 011 — Pine Script 실행 전략 v4 (Alert Hook Parser + 3-Track Architecture) — [`011-pine-execution-strategy-v4.md`](011-pine-execution-strategy-v4.md)
- 010b — Product Roadmap 프레임 & 입력 결정 (재작성본) — [`010b-product-roadmap.md`](010b-product-roadmap.md)
- 010a — Dev CPU Budget Policy + Next.js Anti-Pattern 15건 — [`010a-dev-cpu-budget.md`](010a-dev-cpu-budget.md)
- 010 — Product Roadmap 프레임 & 입력 결정 — [`010-product-roadmap.md`](010-product-roadmap.md)
- 009 — shadcn/ui v4 Nova Preset 규칙 예외 (form.tsx radix-ui + ui/ 직접 수정) — [`009-shadcn-v4-form-radix-exception.md`](009-shadcn-v4-form-radix-exception.md)
- 008 — Sprint 7c FE 따라잡기 — 스코프 결정 기록 — [`008-sprint7c-scope-decision.md`](008-sprint7c-scope-decision.md)
- 007 — Sprint 7a Bybit Futures + Cross Margin — 사전 결정 기록 — [`007-sprint7a-futures-decisions.md`](007-sprint7a-futures-decisions.md)
- 006 — Sprint 6 Trading 데모 설계 리뷰 결과 + 3 핵심 의사결정 — [`006-sprint6-design-review-summary.md`](006-sprint6-design-review-summary.md)
- 005 — DateTime tz-aware + AwareDateTime TypeDecorator 도입 — [`005-datetime-tz-aware.md`](005-datetime-tz-aware.md)
- 004 — Pine 파서 접근법 선택 근거 — [`004-pine-parser-approach-selection.md`](004-pine-parser-approach-selection.md)
- 003 — Pine 런타임 안전성 + 파서 범위 결정 — [`003-pine-runtime-safety-and-parser-scope.md`](003-pine-runtime-safety-and-parser-scope.md)
- 002 — 병렬 스캐폴딩 전략 — [`002-parallel-scaffold-strategy.md`](002-parallel-scaffold-strategy.md)
- 001 — 기술 스택 결정 — [`001-tech-stack.md`](001-tech-stack.md)

---

## 운영 규칙

- 신규 dev-log 작성 시 본 INDEX 에도 한 줄 추가 (시간 역순 또는 번호순 위치 유지)
- AGENTS.md 의 "현재 작업" 섹션은 **활성 sprint 1개 + 직전 완료 sprint 1개 + 다음 분기** 만 inline. 그 외 모든 회고는 본 INDEX 에서 발견
- BL ID 가 부여된 follow-up 은 [`docs/REFACTORING-BACKLOG.md`](../REFACTORING-BACKLOG.md) 에서 추적
- Sprint 1-14 의 별도 dev-log 가 없는 항목은 위 "Sprint 1-14 매트릭스" 에서 ADR/spec/plan/dogfood 위치 cross-link

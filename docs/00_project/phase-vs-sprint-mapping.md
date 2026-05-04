# Phase ↔ Sprint ↔ Horizon 매핑

> **목적:** PRD Phase 정의 (`requirements-overview.md` §4) ↔ 실제 Sprint 진행 ↔ Horizon (`roadmap.md`) 3-축 매핑. PRD 노후화 봉합.
> **SSOT:** Phase 정의 단일 진실 원천. PRD = phase 의 계획 정의, 본 문서 = 계획 vs 실제 매핑.
> **갱신 주기:** sprint 종료 시 (해당 sprint 의 phase 매핑 추가).
> **도입:** Sprint 28 Slice 1b (Phase B.3) — 첫 작성.

## 매핑 표 (Sprint 1-28)

| Sprint            | 계획 Phase (PRD)                               | 실제 Phase                               | 격차 사유                                  | Horizon               |
| ----------------- | ---------------------------------------------- | ---------------------------------------- | ------------------------------------------ | --------------------- |
| Sprint 1-4        | Phase 1 (Pine 파서 + 백테스트)                 | Phase 1 ✅                               | (계획 정합)                                | H1                    |
| Sprint 5          | Phase 1.5 (Infra Hardening + market_data)      | Phase 1.5 ✅                             | (계획 정합)                                | H1                    |
| Sprint 6          | Phase 3 (Demo Trading)                         | Phase 1.5b 신규 (Live Trading 조기 구현) | dogfood-first 우선 — Demo + Live 통합 진입 | H1                    |
| Sprint 7a         | Phase 3 (Demo + Futures)                       | Phase 1.5b                               | Bybit Futures + leverage cap 추가          | H1                    |
| Sprint 7b/c/d     | Phase 3 + FE 보강                              | Phase 1.5b + FE catchup                  | OKX 어댑터 + Strategy CRUD UI              | H1                    |
| Sprint 8a/b/c     | Phase 1.5b 확장 (Pine v2)                      | Phase 1.5b                               | Tier-0/1 + corpus + 3-Track dispatcher     | H1                    |
| Sprint FE-01~F    | Phase 1.5b FE                                  | FE catchup                               | TabParse + Backtest UI MVP + polish        | H1                    |
| Sprint 9-10       | Phase 1.5b nightly                             | Phase 1.5b nightly                       | nightly Bybit Demo broker test             | H1                    |
| Sprint 11 (Y1)    | Phase 1.5b Coverage                            | Phase 1.5b Coverage                      | Pine Coverage Analyzer                     | H1                    |
| Sprint 12         | Path β Trust Layer CI                          | Path β                                   | Trust layer CI 4 PR                        | H1                    |
| Sprint 13-14      | dogfood Track UX                               | dogfood Track UX                         | webhook commit fix + TestOrderDialog       | H1                    |
| Sprint 15-19      | dogfood + tech debt                            | dogfood + BL fix                         | LESSON-019 commit-spy 영구 규칙 등         | H1                    |
| Sprint 20-22      | Bybit Demo broker                              | Bybit Demo Day 0-1                       | EXCHANGE_PROVIDER fix + Coverage 확장      | H1                    |
| Sprint 23-25      | dogfood + WebSocket                            | dogfood + WS Stability                   | reject 0 + dispatch 안정                   | H1                    |
| Sprint 26         | Pine Signal Auto-Trading                       | Phase 1.5b Auto-Loop                     | PR #100, multi-account/symbol/timeframe    | H1                    |
| Sprint 27         | Beta prereq hotfix                             | Beta prereq hotfix                       | BL-137/140/144 fix                         | H1                    |
| **Sprint 28**     | Beta prereq 종합                               | **Phase 1.5b 마무리 + dogfood-first**    | Slice 1a/1b/2/3/4                          | **H1 → H2 진입 결정** |
| Sprint 29+ (가상) | Phase 2 (Stress Test) 또는 BL-001/002/003 처리 | TBD                                      | Beta path A1 결정 후                       | H2                    |
| Sprint N+M (가상) | Phase 3 (Optimizer)                            | TBD                                      | Beta open 후 외부 user dogfood 결과 보고   | H2 / H3               |

## Phase 종료 trigger 명시

| Phase          | 종료 trigger                                                               | 예상 sprint                    |
| -------------- | -------------------------------------------------------------------------- | ------------------------------ |
| Phase 1        | Pine 파서 + 백테스트 + 524 BE tests green                                  | ✅ Sprint 4 종료 (2026-04-16)  |
| Phase 1.5      | Infra Hardening + market_data hypertable                                   | ✅ Sprint 5 PR #6 (2026-04-16) |
| **Phase 1.5b** | **Sprint 28 Slice 2/3/4 모두 PR merge + dual metric 통과 + dogfood Day 7** | **Sprint 28 종료 시점**        |
| Phase 2        | Monte Carlo + Walk-Forward 본인 1회+ 사용                                  | Sprint 29-31 (가상)            |
| Phase 3        | Optimizer + Freemium 티어 결정                                             | Sprint 32+ (가상)              |

## Horizon 매핑

| Horizon         | Sprint 범위 | 대상 활동                                                             | 진입 조건                      |
| --------------- | ----------- | --------------------------------------------------------------------- | ------------------------------ |
| **H1** (0-1.5m) | Sprint 1-28 | Pine + 백테스트 + Live Trading + Path β + dogfood + Beta prereq       | (시작점)                       |
| **H2** (1.5-4m) | Sprint 29+  | 지인 Beta 5명 + Monte Carlo / Walk-Forward + 관측성 + US/EU geo-block | H1→H2 gate (roadmap.md L94-97) |
| **H3** (4-9m)   | TBD         | TV 커뮤니티 + 가격 실험 + 첫 $1 유료 사용자                           | H2→H3 gate                     |

## 갱신 이력

- 2026-05-04 — Sprint 28 Slice 1b 첫 작성. Phase 1.5b 신규 정의 (Live Trading 조기 구현, Sprint 6-28 ~12주). Phase 2/3 H2 이관 명시.

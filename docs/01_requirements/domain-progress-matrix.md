# Domain Progress Matrix

> **목적:** 7 primary 도메인 + 4 cross-cutting 도메인의 PRD 정의 vs 실제 구현 진행도 정량 매트릭스. PRD 노후화 봉합 + Beta path 결정 evidence base.
> **SSOT:** 본 문서 = 도메인별 진행도 단일 진실 원천. PRD = `requirements-overview.md`, Phase = `phase-vs-sprint-mapping.md`, Horizon = `roadmap.md`.
> **갱신 주기:** sprint 종료 시 (sprint-template.md §8 trailer 의무).
> **도입:** Sprint 28 Slice 1b (Phase B.2) — 첫 작성.

## 7 Primary 도메인 (PRD `requirements-overview.md` §6 정합)

| 도메인                                      | PRD 정의                                      | 실제 구현 % | 격차                                                       | 다음 step                          | 첫 sprint | 활성 sprint                    |
| ------------------------------------------- | --------------------------------------------- | ----------- | ---------------------------------------------------------- | ---------------------------------- | --------- | ------------------------------ |
| **Strategy** (Pine Script 파싱, CRUD)       | TV Pine 임포트 + AST 파싱 + Python 트랜스파일 | **95%**     | Whack-a-mole resolved (Sprint 11 Y1 Coverage Analyzer)     | Pine v5 syntax 확장 (후속 sprint)  | Sprint 1  | Sprint 27 BL-137 (settings UI) |
| **Backtest** (vectorbt, 지표)               | 벡터화 백테스트 + 7 지표 + 리포트             | **80%**     | UI disabled + ts.ohlcv 비어있음 (Sprint 28 Slice 2 BL-141) | UI 활성화 + backfill task (BL-141) | Sprint 4  | Sprint 28 Slice 2              |
| **Stress Test** (Monte Carlo, Walk-Forward) | TV 백테스터 보완 (slippage / drawdown)        | **0%**      | 미구현 (Phase 2 이관)                                      | H2 Sprint 후속                     | (없음)    | (deferred)                     |
| **Optimizer** (Grid/Bayesian/Genetic)       | 파라미터 최적화                               | **0%**      | 미구현 (Phase 3 이관)                                      | H2/H3 Sprint 후속                  | (없음)    | (deferred)                     |
| **Trading** (Demo/Live, KillSwitch)         | Bybit/OKX 자동 집행 + Risk Mgmt               | **90%+**    | EffectiveLeverageEvaluator 미구현 (BL-145 deferred)        | Slice 4 + 후속 BL                  | Sprint 6  | Sprint 28 Slice 4              |
| **Market Data** (OHLCV, TimescaleDB)        | TimescaleDB hypertable + CCXT + Beat          | **70%**     | ts.ohlcv backfill task 부재 (BL-141)                       | Slice 2 backfill + daily refresh   | Sprint 5  | Sprint 28 Slice 2              |
| **Exchange** (계정 관리, AES-256)           | 거래소 계정 + AES-256 + passphrase            | **95%**     | passphrase / mainnet runbook (BL-003)                      | mainnet runbook (Sprint 30+)       | Sprint 6  | Sprint 27                      |

## 4 Cross-cutting 도메인 (Sprint 28 office-hours Addendum)

처음 vision (2026-04-14) 미존재. dogfood 3개월 evidence 로 부상:

| Cross-cutting                      | 발견 sprint | 핵심 evidence                                                                                             | Active BL                      | 상태                              |
| ---------------------------------- | ----------- | --------------------------------------------------------------------------------------------------------- | ------------------------------ | --------------------------------- |
| **WebSocket Stability**            | Sprint 12   | metrics 정의 + Sprint 27 26h+ 무결 (reject 7 고착)                                                        | BL-001 / BL-011-016 (6건)      | partially Resolved (Sprint 12-19) |
| **Auth Trust Layer**               | Sprint 13   | OrderService outer commit broken bug 발견 (Sprint 6 패턴 재발) + LESSON-019 commit-spy 영구 규칙 + 15 ADR | LESSON-019 + commit-spy 자동화 | Resolved (Sprint 13-15)           |
| **Auto-Loop 자동화**               | Sprint 27   | Beat scheduler 26h+ 무중단 + dispatch rate 1.0/min + 5 sessions 동시                                      | (없음 — operational success)   | ✅ Resolved (Sprint 26-27)        |
| **Multi-account/symbol/timeframe** | Sprint 26   | PR #100, BTC/SOL 동시 + 1m/5m/15m/1h                                                                      | (없음 — feature complete)      | ✅ Resolved (Sprint 26)           |

## Quality Gate 측정 시점 + 결과

| 도메인      | Quality gate (SLO/KPI)                                                                | 측정 시점                 | 결과                                                     |
| ----------- | ------------------------------------------------------------------------------------- | ------------------------- | -------------------------------------------------------- |
| Strategy    | Pine 통과율 ≥50% (PbR / UtBot / RsiD / DrFXGOD / LuxAlgo / dogfood-smoke 6 indicator) | Sprint 21 dogfood Day 1   | ✅ 50% (3/6)                                             |
| Backtest    | "Sample 백테스트" 1회 60s 안 완주                                                     | Sprint 28 Slice 2 종료 시 | ⏳ pending                                               |
| Trading     | dispatch rate ≥1.0/min 24h+ + reject 0 변동                                           | Sprint 27 Day 0-4         | ✅ 26h+ 무결 (reject 7 고착)                             |
| Market Data | ts.ohlcv BTC/USDT 1H ≥30일 row                                                        | Sprint 28 Slice 2 종료 시 | ⏳ pending                                               |
| Exchange    | 두 ExchangeAccount 동시 active 검증                                                   | Sprint 26 PR #100         | ✅                                                       |
| WebSocket   | reconcile_skipped == 0 + duplicate_enqueue == 0                                       | Sprint 27 Day 4           | ✅                                                       |
| KillSwitch  | capital_base 동적 + Cross Margin leverage cap pass                                    | Sprint 28 Slice 4 종료 시 | ✅ partial (capital_base ✅, EffectiveLeverage deferred) |
| Auto-Loop   | Beat due_count 즉시 인식 + sessions 동시 평가                                         | Sprint 27 Day 0           | ✅                                                       |

## Beta open 결정 evidence (Path A1)

| Beta prereq                                    | 도메인                 | 책임 Slice          | 상태 |
| ---------------------------------------------- | ---------------------- | ------------------- | ---- |
| BL-141 Backtest UI + ts.ohlcv backfill         | Backtest + Market Data | Slice 2             | ⏳   |
| BL-140b LiveSignal real equity curve BE schema | Trading                | Slice 3             | ⏳   |
| BL-004 KillSwitch capital_base 동적 검증       | Trading (Risk Mgmt)    | Slice 4 ✅ Resolved | ✅   |

3 prereq 모두 Resolved 시점 = Beta path A1 trigger 도래 (자연 시간 1-2주 dogfood Day 7+ → 외부 5인 노출).

## 갱신 이력

- 2026-05-04 — Sprint 28 Slice 1b 첫 작성 (4 cross-cutting 도메인 + Slice 4 ✅ 반영)

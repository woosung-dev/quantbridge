# Dogfood Week 1 — Path β 병행 운영 기록

> **운영 기간:** 2026-04-24 ~
> **전략:** `s1_pbr.pine` (Pivot Breakout Reversal)
> **환경:** Bybit Demo Trading (`api-demo.bybit.com`)
> **연관 문서:** [h1-testnet-dogfood-guide.md](../07_infra/h1-testnet-dogfood-guide.md)
> **체크리스트:** [dogfood-checklist.md](../guides/dogfood-checklist.md)
>
> **2026-05-15 cleanup:** 본 file = Path β week 1 **baseline anchor** 전용. 실제 일일 운영 기록 + 주간 요약 + 에스컬레이션 절차는 아래 `## 일일 로그 cross-ref` 안 9 file (Sprint 21~36 dogfood-day series) 참조. template/skeleton 중복은 cleanup 으로 제거 (`dogfood-checklist.md` + `h1-testnet-dogfood-guide.md` 가 운영 SSOT).

---

## 초기 설정값 (Baseline anchor)

| 항목                                | 값                         |
| ----------------------------------- | -------------------------- |
| Symbol                              | BTC/USDT:USDT              |
| Timeframe                           | 1h                         |
| Leverage                            | 1x                         |
| Quantity                            | 0.001 BTC                  |
| Margin mode                         | cross                      |
| Order type                          | limit (market 주문 비활성) |
| Demo USDT 초기 잔고                 | — (시작 시 기입)           |
| KILL_SWITCH_CAPITAL_BASE_USD        | 10,000                     |
| KILL_SWITCH_DAILY_LOSS_USD          | 500                        |
| KILL_SWITCH_CUMULATIVE_LOSS_PERCENT | 5                          |
| BYBIT_FUTURES_MAX_LEVERAGE          | 1                          |

---

## 일일 로그 cross-ref

본 file 의 1차 Day 1 skeleton (2026-04-24) 은 미기입 상태로 남아있었음 — 실제 운영 기록은 다음 dev-log file 들에 누적되어 있음.

| Sprint                     | 날짜       | dev-log file                                                                               |
| -------------------------- | ---------- | ------------------------------------------------------------------------------------------ |
| Sprint 12 (Path β kickoff) | 2026-04-25 | [`2026-04-25-dogfood-day1.md`](2026-04-25-dogfood-day1.md)                                 |
| Sprint 13                  | 2026-04-26 | [`2026-04-26-dogfood-day2.md`](2026-04-26-dogfood-day2.md)                                 |
| Sprint 14                  | 2026-04-27 | [`2026-04-27-dogfood-day3.md`](2026-04-27-dogfood-day3.md)                                 |
| Sprint 20 (setup)          | 2026-05-02 | [`2026-05-02-sprint20-dogfood-day0-setup.md`](2026-05-02-sprint20-dogfood-day0-setup.md)   |
| Sprint 21 Day 1            | 2026-05-03 | [`2026-05-03-dogfood-day1-sprint21.md`](2026-05-03-dogfood-day1-sprint21.md)               |
| Sprint 27 launch           | 2026-05-04 | [`2026-05-04-dogfood-day1-sprint27-launch.md`](2026-05-04-dogfood-day1-sprint27-launch.md) |
| Sprint 36 Day 6            | 2026-05-05 | [`2026-05-05-dogfood-day6.md`](2026-05-05-dogfood-day6.md)                                 |
| Sprint 36 Day 6.5          | 2026-05-05 | [`2026-05-05-dogfood-day-6.5.md`](2026-05-05-dogfood-day-6.5.md)                           |
| Sprint 36 Day 7            | 2026-05-06 | [`2026-05-06-dogfood-day7-sprint36.md`](2026-05-06-dogfood-day7-sprint36.md)               |

---

## 운영 절차 SSOT (cross-ref)

본 file 1차 안 inline 되어있던 (1) 일일 체크리스트 (2) 주간 요약 template (3) Kill Switch 에스컬레이션 절차 (4) Smoke test 절차 (5) 잔여 포지션 정리 SQL = 모두 다음 SSOT file 로 위임.

- **체크리스트 + 주간 요약 template:** [`docs/guides/dogfood-checklist.md`](../guides/dogfood-checklist.md)
- **환경 + Smoke test + 에스컬레이션:** [`docs/07_infra/h1-testnet-dogfood-guide.md`](../07_infra/h1-testnet-dogfood-guide.md)

---

## 주간 요약 (week 1)

> `dogfood-checklist.md` L171 명세상 본 file = week 1 주간 리포트 storage. 향후 주간 row append 시 [`docs/guides/dogfood-checklist.md`](../guides/dogfood-checklist.md) §3.2 "주간 리포트 템플릿" 채택.

| week | D-A (Kill Switch)                    | D-B (체결 성공률) | D-C (Predicted vs Realized Sharpe) | 발견 사항                                                               |
| ---- | ------------------------------------ | ----------------- | ---------------------------------- | ----------------------------------------------------------------------- |
| 1    | — (위 dogfood-day1~3 cross-ref 참조) | —                 | —                                  | 1차 skeleton 미작성, 실제 운영 기록은 sprint-별 dogfood-dayN.md 에 분산 |

---

## 참조

- [ADR-011 Pine Execution Strategy v4](011-pine-execution-strategy-v4.md)
- [Path β Trust Layer CI 설계](013-trust-layer-ci-design.md)
- [Sprint Y1 Coverage Analyzer](016-sprint-y1-coverage-analyzer.md)
- [Dogfood Checklist](../guides/dogfood-checklist.md)
- [H2 Sprint 1 Phase A SDD](../superpowers/plans/2026-04-24-h2-sprint1-phase-a.md)

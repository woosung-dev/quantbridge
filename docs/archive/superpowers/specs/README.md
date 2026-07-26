# `superpowers/specs/` — 도메인 단위 detailed design spec

> **총 파일:** 7개 · **기간:** 2026-04-15 ~ 2026-04-17 · **출처:** superpowers `brainstorming` + plan-eng-review 산출물
> **상위 INDEX:** [`../INDEX.md`](../INDEX.md)

## 7 spec 시간 역순

| 작성일     | spec 파일                                   | 도메인                         | 관련 plan                                            | 관련 ADR                                                                                                                                   |
| ---------- | ------------------------------------------- | ------------------------------ | ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| 2026-04-17 | `2026-04-17-pine-execution-v4-design.md`    | Pine v4 execution              | `plans/2026-04-19-sprint-8c-user-function-3track.md` | [ADR-003](../../dev-log/003-pine-runtime-safety-and-parser-scope.md), [ADR (dev-log/011)](../../dev-log/011-pine-execution-strategy-v4.md) |
| 2026-04-16 | `2026-04-16-trading-demo-design.md`         | Trading domain (Bybit testnet) | `plans/2026-04-16-trading-demo.md`                   | (Sprint 6 회고)                                                                                                                            |
| 2026-04-16 | `2026-04-16-sprint5-stage-b-design.md`      | DateTime tz-aware Stage B      | `plans/2026-04-16-sprint5-stage-b.md`                | (Sprint 5 D8 교훈)                                                                                                                         |
| 2026-04-15 | `2026-04-15-vectorbt-signal-fill-design.md` | vectorbt signal fill 정확도    | `plans/2026-04-15-vectorbt-signal-fill.md`           | (Sprint 4 합치 검증)                                                                                                                       |
| 2026-04-15 | `2026-04-15-sprint4-backtest-api-design.md` | Backtest API                   | `plans/2026-04-15-sprint4-backtest-api.md`           | —                                                                                                                                          |
| 2026-04-15 | `2026-04-15-sprint3-strategy-api-design.md` | Strategy API                   | `plans/2026-04-15-sprint3-strategy-api.md`           | —                                                                                                                                          |
| 2026-04-15 | `2026-04-15-pine-parser-mvp-design.md`      | Pine parser MVP                | `plans/2026-04-15-pine-parser-mvp.md`                | [ADR-003](../../dev-log/003-pine-runtime-safety-and-parser-scope.md), [ADR-004](../../dev-log/004-pine-parser-approach-selection.md)       |

## 활용 정책

- 본 디렉토리 spec 은 **historical design reference**. 신규 spec 은 `dev-log/<번호>-<주제>.md` 또는 `04_architecture/<주제>-architecture.md` 에 작성 (활성 위치).
- 7 spec 모두 H1 Sprint 3~7 (BE 도메인 정착) 시점 산출물 — H2+ 에서 직접 변경 비권장.

## 중복 정리 (Phase A.5 결과)

| 주제             | SSOT                                                                                                     | Deprecated                                                                                           |
| ---------------- | -------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| Pine 실행 전략   | [`04_architecture/pine-execution-architecture.md`](../../04_architecture/pine-execution-architecture.md) | `dev-log/011-pine-execution-strategy-v4.md` + `2026-04-17-pine-execution-v4-design.md` (본 디렉토리) |
| Sprint 5 Stage B | [`2026-04-16-sprint5-stage-b-design.md`](./2026-04-16-sprint5-stage-b-design.md) (본 디렉토리, SSOT)     | `plans/2026-04-16-sprint5-stage-b.md` (compressed)                                                   |

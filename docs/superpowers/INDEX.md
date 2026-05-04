# `superpowers/` — H1 sprint 산출물 누적소

> **카테고리:** sprint plan / spec / review / report 누적
> **총 파일:** 72개 (plans 42 + specs 7 + reviews 20 + reports 3)
> **시작:** 2026-04-15 (Sprint 3 진입) ~ 2026-04-24 (H2 Sprint 9/10 plan)
> **정책:** Sprint 3 ~ H2 Sprint 9/10 plan 의 superpowers skill 산출물. **H2 Sprint 11+ 부터는 `dev-log/` 로 통합** (본 디렉토리 신규 추가 비권장).

## 정책 — Option A (가벼움)

본 디렉토리는 **H1 sprint plan 누적용 archive**. 다음 분기에는 다음과 같이 운용:

- **H2 Sprint 11+ 신규 plan**: `~/.claude/plans/<hash>.md` 또는 `docs/dev-log/sprint-XX-plan.md` 으로 직접 작성. 본 디렉토리 추가 X.
- **superpowers skill (writing-plans, brainstorming) 산출물**: 향후에도 누적 가능. 단 INDEX 갱신 의무.
- **H2 종료 시점**: 2026-Q3 분기에 본 디렉토리 → `_archive/2026-Q3-h2/superpowers/` 으로 일괄 이관 검토.

## 4 카테고리 구조

| 디렉토리               | 파일 수 | 용도                                                             | INDEX                         |
| ---------------------- | ------- | ---------------------------------------------------------------- | ----------------------------- |
| [plans/](./plans/)     | 42      | Sprint 단위 implementation plan (writing-plans skill)            | [README](./plans/README.md)   |
| [specs/](./specs/)     | 7       | 도메인 단위 detailed design spec (Sprint 3-7a + Pine v4)         | [README](./specs/README.md)   |
| [reviews/](./reviews/) | 20      | x1x3 5 sprint × 4 evaluator (codex/opus/sonnet) cross-validation | [README](./reviews/README.md) |
| [reports/](./reports/) | 3       | architecture survey + documentation audit + x1x3 final           | [README](./reports/README.md) |

## Sprint ↔ 파일 매핑 (압축본)

### H1 Sprint 3-7d (BE 도메인 정착)

| Sprint                             | plans/                                                                      | specs/                                                                                    |
| ---------------------------------- | --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| Sprint 3 (Strategy API)            | `2026-04-15-sprint3-strategy-api.md`                                        | `2026-04-15-sprint3-strategy-api-design.md`                                               |
| Sprint 4 (Backtest API)            | `2026-04-15-sprint4-backtest-api.md` + `2026-04-15-vectorbt-signal-fill.md` | `2026-04-15-sprint4-backtest-api-design.md` + `2026-04-15-vectorbt-signal-fill-design.md` |
| Pine MVP                           | `2026-04-15-pine-parser-mvp.md`                                             | `2026-04-15-pine-parser-mvp-design.md`                                                    |
| Sprint 5 (Stage B)                 | `2026-04-16-sprint5-stage-b.md`                                             | `2026-04-16-sprint5-stage-b-design.md`                                                    |
| Sprint 6 (Trading Demo)            | `2026-04-16-trading-demo.md`                                                | `2026-04-16-trading-demo-design.md`                                                       |
| Sprint 7a (Bybit Futures)          | `2026-04-17-sprint7a-bybit-futures.md`                                      | (없음)                                                                                    |
| Sprint 7b (Edit Parse UX)          | `2026-04-17-sprint7b-edit-parse-ux.md`                                      | (없음)                                                                                    |
| Sprint 7c (Strategy UI)            | `2026-04-17-sprint7c-strategy-ui.md`                                        | (없음)                                                                                    |
| Sprint 7d (OKX + Trading Sessions) | `2026-04-19-sprint7d-okx-trading-sessions.md`                               | (없음)                                                                                    |

### H1 Sprint 8 (pine_v2 deepening)

| Sprint                     | plans/                                                                                     | specs/                                   |
| -------------------------- | ------------------------------------------------------------------------------------------ | ---------------------------------------- |
| Sprint 8a (foundation)     | (별도 plan 없음 — dev-log 기반)                                                            | (없음)                                   |
| Sprint 8b (Tier-1 wrapper) | `2026-04-18-sprint-8b-tier1-rendering.md` + `2026-04-18-phase-minus-1-measurement-plan.md` | (없음)                                   |
| Sprint 8c (multi-return)   | `2026-04-19-sprint-8c-user-function-3track.md`                                             | `2026-04-17-pine-execution-v4-design.md` |

### H1 FE Polish (Bundle 1/2)

| Bundle                           | plans/                                                |
| -------------------------------- | ----------------------------------------------------- |
| FE-01 (TabParse 1Q)              | `2026-04-19-sprint-fe-01-tabparse-1q.md`              |
| FE-03 (Edit lift-up)             | `2026-04-19-sprint-fe03-edit-lift-up.md`              |
| FE-04 (Backtest UI MVP)          | `2026-04-19-sprint-fe04-backtest-ui-mvp.md`           |
| FE-A (Landing/Dashboard)         | `2026-04-19-sprint-fe-a-landing-dashboard.md`         |
| FE-B (Trading mobile/empty)      | `2026-04-19-sprint-fe-b-trading-mobile-empty.md`      |
| FE-C (Shortcut help/draft scope) | `2026-04-19-sprint-fe-c-shortcut-help-draft-scope.md` |
| FE-D (Chip tag input)            | `2026-04-19-sprint-fe-d-chip-tag-input.md`            |
| FE-E (Delete bottom sheet)       | `2026-04-19-sprint-fe-e-delete-bottom-sheet.md`       |
| FE-F (Edit→Backtest)             | `2026-04-19-sprint-fe-f-edit-to-backtest.md`          |

### H1 Trust Layer (Path β / x1x3 / Stage 2c)

| 영역                     | plans/ + reviews/                                                                                                            |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------- |
| H2 kickoff               | `2026-04-20-h2-kickoff.md`                                                                                                   |
| Kill Switch capital_base | `2026-04-20-kill-switch-capital-base.md`                                                                                     |
| Stage 2c 2nd             | `2026-04-23-stage2c-2nd-plan.md`                                                                                             |
| x1x3 5 워커 (W1-W5)      | `2026-04-23-x1x3-w[1-5]-*.md` (5 plan) + `reviews/2026-04-23-x1x3-w[1-5]-{codex/codex-self/opus/sonnet}-eval.md` (20 review) |

### H2 Sprint 1/9/10 (계획 단계, 일부 미실행)

| Sprint                    | plans/                                                    | 실행 상태                                   |
| ------------------------- | --------------------------------------------------------- | ------------------------------------------- |
| H2 Sprint 1 (phase a/b/c) | `2026-04-24-h2-sprint1-phase-{a,b,c}.md` (3 phase)        | 일부 실행 (Live Trading 으로 우선순위 변경) |
| H2 Sprint 9 (Monte Carlo) | `2026-04-24-h2-sprint9-phase-{a,b,c,d}.md` (4 phase)      | **미실행** (P2, REFACTORING-BACKLOG.md)     |
| H2 Sprint 10 (Optimizer)  | `2026-04-24-h2-sprint10-phase-{a1,a2,b,c,d}.md` (5 phase) | **미실행** (P2)                             |

## 후속 분기 (예상)

- 2026-Q3 (H2 종료) — 본 디렉토리 일괄 `_archive/2026-Q3-h2/superpowers/` 이관 검토
- 2026-Q4 (H3 종료) — 추가 cleanup

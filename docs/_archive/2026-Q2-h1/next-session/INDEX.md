# `next-session-*.md` Archive — H1 Sprint plan prompts

> **이동 일자:** 2026-05-04 (Sprint 27 hotfix 완료 + dogfood Day 1 진행 중)
> **원위치:** `docs/next-session-*.md` (모두 docs/ 루트)
> **이동 사유:** 모두 sprint 진입 직전 작성된 plan/prompt template. 해당 sprint 종료 후 미참조 상태로 6주+ 경과. 활성 docs/ 트리 noise 제거.

## 12 파일 한 줄 요약

| 파일                                           | 추정 sprint                 | 작성 시점  | 한 줄 요약                                                                       |
| ---------------------------------------------- | --------------------------- | ---------- | -------------------------------------------------------------------------------- |
| `next-session-after-fe-01-prompt.md`           | FE-01 후속                  | 2026-04-19 | TabParse 1질문 UX 후속 작업 prompt                                               |
| `next-session-fe-polish-autonomous.md`         | FE Polish Bundle 1          | 2026-04-19 | autonomous-parallel-sprints Bundle 1 prompt (FE-A/B/C)                           |
| `next-session-fe-polish-bundle2-autonomous.md` | FE Polish Bundle 2          | 2026-04-20 | autonomous Bundle 2 prompt (FE-D/E/F)                                            |
| `next-session-h2-sprint1.md`                   | H2 Sprint 1                 | 2026-04-20 | H2 진입 plan prompt (실제 Sprint 9~11 로 분기)                                   |
| `next-session-h2-sprint9.md`                   | H2 Sprint 9 (Monte Carlo)   | 2026-04-20 | Monte Carlo 1000회 + WFA 분석 prompt (미실행, P2)                                |
| `next-session-h2-sprint10.md`                  | H2 Sprint 10 (Optimizer)    | 2026-04-20 | Grid → Bayesian → Genetic 파라미터 최적화 prompt (미실행, P2)                    |
| `next-session-h2-sprint11.md`                  | H2 Sprint 11                | 2026-04-20 | H2 후속 plan (실제 Live Trading 로 우선순위 변경)                                |
| `next-session-sprint-8b-prompt.md`             | H1 Sprint 8b (Tier-1)       | 2026-04-18 | pine_v2 Tier-1 가상 strategy 래퍼 prompt (Sprint 8b PR #21 머지)                 |
| `next-session-sprint-8c-prompt.md`             | H1 Sprint 8c (multi-return) | 2026-04-19 | user function + multi-return + 3-Track dispatcher prompt (Sprint 8c PR #22 머지) |
| `next-session-sprint-bcd-autonomous.md`        | FE B/C/D 병렬               | 2026-04-19 | cmux 3 워커 자율 병렬 prompt (PR #29/#30/#31)                                    |
| `next-session-tabparse-fe-1q-prompt.md`        | FE-01 (TabParse)            | 2026-04-19 | TabParse 1질문 UX 신규 기능 prompt                                               |
| `next-session-testnet-dogfood-longrun.md`      | testnet dogfood longrun     | 2026-04-22 | testnet dogfood 1주+ longrun 진입 prompt (mainnet 으로 우선순위 변경)            |

## 활용 정책

- **참조 only**: 본 archive 의 파일은 git history + 활성 dev-log 에서 추적 가능. 신규 sprint 진입 시 본 위치 직접 참조 금지.
- **신규 prompt 작성 시**: `docs/superpowers/plans/` 또는 `~/.claude/plans/` 에 작성 → sprint 종료 후 본 archive 로 자연 이관.
- **삭제 금지**: H1 sprint plan 의 prompt template 패턴 학습 자료로 영구 보존.

## 후속 sprint 매핑 (추적 cross-link)

| 추정 sprint               | 실제 결과                                          | dev-log                                                                           |
| ------------------------- | -------------------------------------------------- | --------------------------------------------------------------------------------- |
| FE-01                     | PR #23 (feat) + PR #24 (CPU fix)                   | [`dev-log/.../sprint-fe01-tabparse-1q-cpu-fix.md`](../../../dev-log/) (검색 권장) |
| FE Polish Bundle 1        | PR #29 #30 #31                                     | [`dev-log/.../sprint-fe-a-b-c-bundle1.md`](../../../dev-log/)                     |
| FE Polish Bundle 2        | PR #33 #34 #35                                     | [`dev-log/.../sprint-fe-d-e-f-bundle2.md`](../../../dev-log/)                     |
| Sprint 8b                 | PR #21 머지                                        | [`dev-log/.../sprint8b-tier1-wrapper.md`](../../../dev-log/)                      |
| Sprint 8c                 | PR #22 머지                                        | [`dev-log/.../sprint8c-multi-return.md`](../../../dev-log/)                       |
| Sprint B/C/D              | PR #29/#30/#31                                     | [`dev-log/.../sprint-bcd-parallel.md`](../../../dev-log/)                         |
| H2 Sprint 9 (Monte Carlo) | **미실행** (P2 — `REFACTORING-BACKLOG.md` 등록 후) | N/A                                                                               |
| H2 Sprint 10 (Optimizer)  | **미실행** (P2)                                    | N/A                                                                               |
| testnet dogfood longrun   | mainnet 으로 우선순위 변경 (Sprint 21+)            | `dev-log/2026-05-04-dogfood-day1-sprint27-launch.md`                              |

> **note:** dev-log 파일명은 `git log --all --oneline -- docs/dev-log/ | grep sprint8` 식으로 검색.

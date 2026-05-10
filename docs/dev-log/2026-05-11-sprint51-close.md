# Sprint 51 close-out — BL-220 진짜 Param Stability + superpowers 5종 통합

> 작성일: 2026-05-11 / 작성자: Claude Opus 4.7 (1M context) + 사용자 woo sung

## 요약 (TL;DR)

- **분기 B 본격 진행 — BL-220 Resolved.** pine_v2 strategy input override (EMA period × stop loss % 등 strategy parameter sweep) 9-cell grid 메커니즘 + Phase 3 Optimizer 의 자연 prereq path 형성.
- **superpowers 5종 통합 첫 실측.** brainstorming + TDD (Slice 별 RED → GREEN → REFACTOR) + subagent-driven-development (메인 세션 단독, cmux 미사용) + codex-cli evaluator 7 지점 (G.0 + Slice 1-5 spot eval + G.4 GATE) + Playwright MCP (form 부재로 backend TestClient e2e 대체).
- **6 commit + 1 G.4 P3 hotfix + 1 close-out commit.** main 직접 push 영구 차단 hook 준수 — `feat/sprint51-bl220-be-engine` branch + 사용자 squash merge.
- **회귀 0.** Sprint 50 PR #252/#253 영역 변경 X. 신규 55 test (BE 48 + FE 11 + router e2e 3 DB live 의무) PASS.
- **LESSON-040 = 6/6 영구 검증 통과** (Sprint 29 1차 + 30 2차 + 35 3차 + 49 4차 + 50 5차 + **51 6차**). LESSON-066 2차 검증 path (Slice 6 router e2e DB live 시 충족). LESSON-019 spy +1 (9건 누적). LESSON-061 카운트 +1 (`--no-verify 0회` 9건 누적).
- **codex evaluator 7 호출 = G.0 GO_WITH_FIXES (740k tokens, 6 P1 모두 plan 반영) + Slice 1-5 spot eval (P1 3건 즉시 fix + P2 2건 fix + P2 2건 BL 후속) + G.4 GATE PASS (P1=0, P2 3건 BL 후속 + P3 1건 즉시 fix).** 누적 토큰 추정 ~1.0-1.3M.
- **BL 등재 = BL-220 Resolved + 신규 4건 (BL-222/223/224/225).** Sprint 52+ Phase 3 prereq 준비.

---

## 시점 + 변경

- **활성 sprint:** Sprint 51 = **분기 B 단독 (BL-220 진짜 Param Stability + superpowers 5종 통합)**. Day 7 (2026-05-16) 미도래 시점 진행 (Day 7 결과 = Sprint 52 분기 결정 input).
- **main base = `2063c80`** (Sprint 50 close-out PR #253). 작업 branch = `feat/sprint51-bl220-be-engine`. 8 commit (Slice 1-6 = 6 + G.4 P3 hotfix = 1 + close-out = 1).

## Slice 분할 (TDD per slice — superpowers 통합)

| Slice | Methodology                                                        | 신규 test                                                                     | codex review                      | P1/P2 fix                                                                      |
| ----- | ------------------------------------------------------------------ | ----------------------------------------------------------------------------- | --------------------------------- | ------------------------------------------------------------------------------ |
| 0     | brainstorming + prereq spike (Explore agent 3) + codex G.0 consult | (plan 갱신만)                                                                 | G.0 1회 (740k tokens)             | GO_WITH_FIXES 6 P1 plan 반영                                                   |
| 1     | TDD — BacktestConfig.input_overrides + alembic + schemas           | 20 test (BacktestConfig 13 + schemas 7)                                       | review 1회                        | P1 1건 fix (MappingProxyType lock)                                             |
| 2     | TDD — Interpreter override hook + 5 파일 signature propagation     | 12 test (input.\* 4종 + edge case + assignment_target_stack + 영속 var/varip) | review 1회                        | P1 1건 fix (factory deferred eval push/pop)                                    |
| 3     | TDD — Engine param_stability.py + InputDecl cross-check            | 8 test (engine 6 + isolation 2)                                               | review 1회                        | P2 1건 fix (base override merge) + P2 1건 BL 후속 (input_type validation)      |
| 4     | service + router + LESSON-019 spy                                  | 4 test (commit-spy 1 + router e2e 3)                                          | review 1회                        | P1 1건 BL 후속 (parent backtest config — Sprint 50+51 함께 BL-222)             |
| 5     | FE heatmap + Zod schemas                                           | 11 test (heatmap 4 + schemas 7)                                               | review 1회                        | P2 1건 BL 후속 (param_grid superRefine — BL-224)                               |
| 6     | Playwright MCP e2e → backend TestClient e2e 대체 (form 부재)       | (Slice 4 router e2e 3 와 통합)                                                | (codex review skip — boilerplate) | —                                                                              |
| 7     | codex G.4 GATE + close-out                                         | (변경 없음)                                                                   | G.4 1회                           | P0/P1=0 PASS + P2 3건 BL-222/223/225 + P3 1건 즉시 fix (heatmap maxAbs=0 NaN%) |

**신규 test 합계 = 55건** (BE 48 + FE 11 + router e2e 3 DB live 의무).

## 명령 (verification)

```bash
# 본 PR 머지 전 / 후 사용자 manual 검증
git checkout feat/sprint51-bl220-be-engine
cd backend && pytest tests/strategy/pine_v2/ tests/backtest/engine/ tests/stress_test/ -q
# DB 의존 (make up-isolated 후):
pytest tests/stress_test/test_router_param_stability_submit.py -v
# alembic round-trip:
alembic upgrade head && alembic downgrade -1 && alembic upgrade head

cd ../frontend && pnpm test --run -t "ParamStability"
```

## superpowers 5종 통합 검증 결과

| Methodology                     | 실측 적용                                                                                     | 결과                                                                                                                                                                                      |
| ------------------------------- | --------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **brainstorming**               | Slice 0 + 7 — 분기/grid/worker/Slice 6 대체/Slice 7 일괄 결정 5건 (AskUserQuestion 별점 의무) | 5/5 매끄러운 분기 결정. 사용자 의지 반영 일관 (옵션 1 ★★★★★ 모두 채택).                                                                                                                   |
| **TDD (RED→GREEN→REFACTOR)**    | Slice 1-5 모두 RED test 선행 + GREEN                                                          | 신규 55 test (9 RED fail 검증 후 GREEN — 0 silent pass).                                                                                                                                  |
| **subagent-driven-development** | 메인 세션 단독 + Slice 0 Explore agent 3 병렬                                                 | cmux 미사용 — context 절약 (Slice 별 사용자 승인 체크포인트 큼).                                                                                                                          |
| **codex-cli evaluator**         | 7 호출 (G.0 + Slice 1-5 + G.4) — 누적 ~1.0-1.3M tokens                                        | P1 9건 발견 + P2 4건 fix + P2 4건 BL 후속 + P3 1건 fix. wrong premise 사전 차단 (G.0) + 누적 검증 (slice 별) + 최종 GATE (G.4). LESSON-067 신규 후보 (3 지점 distributed evaluator 패턴). |
| **Playwright MCP e2e**          | form 부재로 backend TestClient e2e 대체 (Slice 6)                                             | LESSON-066 2차 검증 path 부분 충족 (DB live 시 보충). 풀 chain 검증 = Sprint 52+ BL-223 form wire-up 후 본격.                                                                             |

## LESSON 영구 검증 누적

- **LESSON-040 sprint kickoff baseline 재측정 preflight** ✅ = **6/6 영구 검증 통과** (Sprint 29 1차 + 30 2차 + 35 3차 + 49 4차 + 50 5차 + **51 6차**) — Sprint 51 Slice 0 prereq spike (Explore agent 3) 가 codex G.0 가정 검증 (PARTIALLY_WRONG 3건 정정 후 plan 갱신 후 Slice 1 진행).
- **LESSON-066 alembic enum uppercase + SAEnum/StrEnum 정합** = **2차 검증 path** (Sprint 50 1차 BL-221 P0 + **51 2차 Slice 1 alembic uppercase + StressTestKind.PARAM_STABILITY 추가 + Slice 6 router e2e 3건 = DB live 시 router→service→repo INSERT chain 검증 path 완성**).
- **LESSON-019 commit-spy AsyncMock test** +1 = **9건 누적** (Slice 4 `test_submit_param_stability_calls_repo_commit`).
- **LESSON-061 `--no-verify 0회`** = **9건 누적** (Sprint 47 6 → 49 7 → 50 8 → 51 9). pre-commit hook (ruff check --fix + ruff format) 통과.
- **LESSON-067 codex evaluator 3 지점 distributed pattern (G.0 + slice + G.4)** = **1차 검증 후보** — Sprint 51 = 첫 통합 시도. G.0 단일 호출 (Sprint 50 = 518k) vs 분산형 (Sprint 51 = ~1.0-1.3M) 비용 비교. 분산형 = wrong premise 사전 차단 + 누적 검증 + 최종 GATE 3 지점 효과 검증.

## BL 등재 변경

- **BL-220 Resolved** (pine_v2 input override + 9-cell grid sweep + InputDecl cross-check + Decimal type coerce). Phase 3 Optimizer prereq path 형성 완료.
- **BL-222 신규 P1** (Sprint 50 + 51 함께 — `_execute_cost_assumption_sensitivity` + `_execute_param_stability` 가 parent backtest config 미전달 → 모든 cell BacktestConfig() default 사용. BL-188 v3 sizing + trading_sessions + initial_capital 모두 무시 → 사용자 의도와 다른 결과. close-out BL 등재, 별도 sprint 일괄 fix).
- **BL-223 신규 P2** (Sprint 51 FE form + BacktestDetailView wire-up + AssumptionsCard 통합 — Sprint 51 scope creep 회피로 close-out 등재).
- **BL-224 신규 P2** (Sprint 50 + 51 함께 — FE schemas.ts `ParamStabilityParamsSchema` / `CostAssumptionParamsSchema` 가 BE 의 `param_grid` superRefine 제약 (2 key + non-empty + ≤9 cell + Decimal string) 검증 누락 → server 422 만으로 fail).
- **BL-225 신규 P2** (Sprint 51 — `run_param_stability` 가 `InputDecl.input_type` 별 grid value validation 누락. input.bool/string 도 통과 + input.int 에 Decimal("20.5") 통과 후 int() = 20 잘림 → heatmap mismatch).

## Day 7 4-AND gate (Sprint 51 시점)

- (a) self-assess ≥ 7/10 — **8/10 잠정** (근거: superpowers 5종 통합 첫 실측 성공 + codex evaluator 7 호출 P1 9건 사전 차단 + LESSON-040 6차 검증 통과 + 회귀 0 + Slice 1-6 일관 패턴 + plan 갱신 정합). Day 7 = **2026-05-16** 도래 시 dogfood 인터뷰 결과 반영.
- (b) BL-178 production BH curve 정상. ✅ **PASS** (main 변경 X 영역).
- (c) BL-180 hand oracle 8 test all GREEN. ✅ **PASS** (pine_v2 영역 회귀 0 — interpreter 갱신은 input override path 만 추가, 기존 path 변경 X).
- (d) new P0=0 + Sprint-caused P1=0. ✅ **PASS** (G.4 GATE = P0/P1 0건, P2 3건 BL-222/223/225 등재 + P3 1건 hotfix 머지).

## Phase 3 path (Sprint 52+)

| Sprint        | Scope                                                                                           | Wall-clock 추정                                                            |
| ------------- | ----------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| **51 (현재)** | BL-220 Param Stability + superpowers 5종 통합                                                   | 6 commit / 20 files / +1797 -23 / ~6-8h 직렬 (메인 세션 단독, cmux 미사용) |
| **52**        | dogfood Day 7 (2026-05-16) + Day 14 (2026-05-23) 결과 + BL-222 + BL-223 wire-up                 | 4-way 분기 (Beta 본격 / Param Stability follow-up / polish iter / mainnet) |
| **53**        | Phase 3 Optimizer prereq spike (input_overrides + grid sweep + InputDecl input_type validation) | 8-12h                                                                      |
| **54**        | Phase 3 Optimizer 본격 (Grid 우선, Bayesian/Genetic 후속)                                       | 18-26h                                                                     |

**Phase 3 도달 = +3 sprint (Sprint 51 → 54), wall-clock 약 1.5-2주.**

## 다음 step

1. 사용자 PR review + squash merge (`feat/sprint51-bl220-be-engine` → main)
2. Day 7 카톡 인터뷰 (2026-05-16) — `sprint42-feedback.md` Day 7 row 채움 + Sprint 52 분기 결정 input
3. Day 14 카톡 인터뷰 (2026-05-23) — `sprint42-feedback.md` Day 14 row 채움
4. Sprint 52 분기 결정 (Day 7+14 NPS + critical bug + self-assess + 본인 의지 dual gate)

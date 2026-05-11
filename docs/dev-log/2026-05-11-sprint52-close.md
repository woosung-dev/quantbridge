# Sprint 52 close-out — Stress Test follow-up bundle (BL-222 P1 + BL-223/224/225 P2)

> 작성일: 2026-05-11 (Sprint 51 close 직후 same-day kickoff + same-day close) / 작성자: Claude Opus 4.7 (1M context) + 사용자 woo sung

## 요약 (TL;DR)

- **분기 B (Param Stability follow-up) 본격 진행 — 4 BL 일괄 Resolved.** BL-222 P1 silent data corruption fix + BL-223/224/225 P2 모두 한 sprint 안.
- **5 commit + close-out (PR 생성 예정).** main 직접 push 영구 차단 hook 준수 — `feat/sprint52-stress-test-followup` branch + 사용자 squash merge.
- **회귀 0.** BE Sprint 52 핵심 영역 37 PASS / FE 131 file 680 PASS (Sprint 51 base 643 → 680 = +37).
- **superpowers 5종 통합 2차 실측** (Sprint 51 1차 → 52 2차).
  - brainstorming + Slice 0 prereq spike (Explore agent 2 병렬) + codex G.0 (96k tokens, GO_WITH_FIXES 9 P1 plan 반영)
  - TDD per slice (RED → GREEN → REFACTOR), 신규 41 test (BE 16 + FE 25)
  - subagent-driven-development (메인 세션 단독 + Slice 0 Explore agent 2)
  - codex distributed evaluator 3 지점 (G.0 + G.4 PASS_WITH_FOLLOWUP, ~96k + ~120k = ~216k tokens 누적)
  - Playwright MCP e2e = form 완성 + wire-up = LESSON-066 3차 검증 path 형성 완료 (browser session 본격 = Day 7 dogfood manual)
- **LESSON-040 = 7/7 영구 검증 통과** (Sprint 29/30/35/49/50/51 → 52). codex G.0 P1 9건 모두 plan 갱신 후 Slice 1 진입. LESSON-067 분산형 evaluator 2차 검증 = ~216k tokens (Sprint 51 ~1.0-1.3M vs 52 ~216k, 분산형 효율 정밀화). LESSON-061 `--no-verify 0회` = 10건 누적.
- **codex G.4 = PASS_WITH_FOLLOWUP** (P0/P1 = 0, P2 2건 BL 후속, P3 2건 즉시 fix).
- **BL 등재 변경 = BL-222/223/224/225 4건 Resolved + 신규 BL-226 P2 등재 (FE Decimal regex BE parity).**

---

## 시점 + 변경

- **활성 sprint:** Sprint 52 = **분기 B 단독 (BL-222 P1 + BL-223/224/225 P2 묶음)**. Day 7 (2026-05-16) 미도래 5일 갭 활용.
- **main base = `44d2c2c`** (Sprint 51 close-out PR #255). 작업 branch = `feat/sprint52-stress-test-followup`. 5 commit (Slice 1-5) + close-out.

## Slice 분할 (codex G.0 P2 권고 = spot eval 축소 적용)

| Slice | Methodology                                                                | 신규 test (BE/FE)                | codex                                                     |
| ----- | -------------------------------------------------------------------------- | -------------------------------- | --------------------------------------------------------- |
| 0     | brainstorming + Explore agent 2 + codex G.0                                | (plan 갱신만)                    | G.0 = GO_WITH_FIXES 9 P1 plan 반영 (~96k tokens)          |
| 1     | TDD — BL-222 BE fix (`config_mapper.py` 추출 + service 2 함수 propagation) | BE 10 (4 service spy + 6 mapper) | (skip — 문제 없음)                                        |
| 2     | TDD — BL-225 input_type validation                                         | BE 5                             | (skip — 문제 없음)                                        |
| 3     | TDD — BL-224 FE schemas superRefine                                        | FE 17                            | (skip — 문제 없음)                                        |
| 4     | TDD — BL-223 FE form + mutation + hook                                     | FE 6                             | (skip — 문제 없음)                                        |
| 5     | TDD — BL-223 wire-up (stress-test-panel)                                   | FE 3                             | (skip — 문제 없음)                                        |
| 6     | Playwright MCP e2e path 형성                                               | (Slice 5 통합)                   | (skip — Day 7 dogfood manual)                             |
| 7     | codex G.4 GATE + close-out                                                 | (변경 없음)                      | G.4 = PASS_WITH_FOLLOWUP P0/P1=0, P3 2건 즉시 fix (~120k) |

**신규 test 합계 = 41 (BE 15 + FE 26).**

## 산출 (5 commit)

- `1923bb4` Slice 1 — BL-222 P1 parent backtest config 전달 + `config_mapper.py` 추출 (6 files / +590 / -107)
- `146fab9` Slice 2 — BL-225 input_type validation (2 files / +121)
- `29363e7` Slice 3 — BL-224 FE schemas superRefine (2 files / +296 / -8)
- `121dd43` Slice 4 — BL-223 form + mutation + hook (4 files / +336)
- `7e81b83` Slice 5 — BL-223 wire-up + heatmap branch (2 files / +146 / -4)

**총 16 files / +1489 / -119 / 회귀 0.**

## 명령 (verification)

```bash
git checkout feat/sprint52-stress-test-followup
cd backend && pytest tests/backtest/test_config_mapper.py tests/stress_test/test_service_backtest_config_propagation.py tests/stress_test/engine/test_param_stability.py tests/backtest/test_create_request_user_input.py tests/stress_test/engine/test_cost_assumption_sensitivity.py -v
# 37 PASS 기대

cd ../frontend && pnpm test
# 131 file 680 PASS 기대

cd ../frontend && pnpm tsc --noEmit
# clean
```

## superpowers 5종 통합 검증 (Sprint 51 1차 → 52 2차)

| Methodology                     | Sprint 51 (1차)                                              | Sprint 52 (2차)                                        | 차이                                                                                                                                                    |
| ------------------------------- | ------------------------------------------------------------ | ------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **brainstorming**               | 5/5 분기 결정                                                | 2/2 분기 결정 (scope + worker 배치)                    | Sprint 51 = 큰 scope (5 분기), Sprint 52 = 작은 scope (2 분기, 동일 디폴트 ★★★★★)                                                                       |
| **TDD per slice**               | 55 test (9 RED)                                              | 41 test (Slice 1-5 RED first)                          | scope 차이로 자연스러운 감소. Slice 별 일관 강도.                                                                                                       |
| **subagent-driven-development** | 메인 단독 + Slice 0 Explore agent 3                          | 메인 단독 + Slice 0 Explore agent 2                    | context 절약 일관. Slice 별 사용자 승인 체크포인트 유지.                                                                                                |
| **codex distributed evaluator** | 7 호출 ~1.0-1.3M tokens (G.0 + Slice 1-5 spot + G.4)         | 2 호출 ~216k tokens (G.0 + G.4)                        | codex G.0 P2 권고 "spot eval 축소" 적용. 비용 ~80%+ 감소. wrong premise 사전 차단 + 최종 GATE 양 끝점 보존. **LESSON-067 분산형 정밀화 2차 검증 통과**. |
| **Playwright MCP e2e**          | form 부재로 backend TestClient e2e 대체 (2차 path 부분 충족) | form + wire-up 완성으로 path 형성 (3차 path 형성 완료) | LESSON-066 검증 단계 진전. browser session 본격 = Day 7 dogfood manual.                                                                                 |

## LESSON 영구 검증 누적

- **LESSON-040 sprint kickoff baseline 재측정 preflight** ✅ = **7/7 영구 검증 통과** (Sprint 29 1차 + 30 2차 + 35 3차 + 49 4차 + 50 5차 + 51 6차 + **52 7차**) — Sprint 52 Slice 0 prereq spike (Explore agent 2) 가 codex G.0 가정 검증 + plan 9 P1 갱신 후 Slice 1 진입. wrong premise 사전 차단 확정.
- **LESSON-067 codex evaluator distributed 3 지점 (G.0 + slice + G.4)** = **2차 검증 정밀화 통과**. Sprint 51 = ~1.0-1.3M tokens (모든 slice spot), Sprint 52 = ~216k tokens (G.0 + G.4 만). 비용 ~80%+ 감소 + P0/P1 검출 능력 보존 (codex G.0 9 P1 = plan 갱신 후 G.4 P1=0 → 효율). **권고 = 양 끝점 + 핵심 Slice 1-2개 spot eval 만 (Sprint 53+).**
- **LESSON-066 alembic enum + SAEnum/StrEnum 정합** = **3차 검증 path 형성 완료** (Sprint 50 1차 BL-221 + 51 2차 router e2e + **52 3차 form + wire-up = browser session 가능 path**). 실제 browser session 본격 검증은 Day 7 (2026-05-16) dogfood manual.
- **LESSON-019 commit-spy AsyncMock** +2 = **11건 누적** (Sprint 47 6 → 49 7 → 50 8 → 51 9 → **52 10/11**: `_execute_cost_assumption_sensitivity` + `_execute_param_stability` 4 spy test).
- **LESSON-061 `--no-verify 0회`** = **10건 누적** (Sprint 47 6 → 49 7 → 50 8 → 51 9 → **52 10**). pre-commit hook (ruff check --fix + ruff format + ESLint) 통과.

## BL 등재 변경 (4 Resolved + 1 신규)

- **BL-222 ✅ Resolved** (parent backtest config 전달 — `config_mapper.py` 추출 + `StressTestService` 양쪽 worker entry `backtest_config=` 전달).
- **BL-223 ✅ Resolved** (FE Param Stability form + wire-up — 2 var_name + 각 3 value preset MVP, BE InputDecl.var_name cross-check 정합).
- **BL-224 ✅ Resolved** (FE schemas.ts superRefine — CA exactly 2 keys + allowedKeys subset + non-empty + ≤9 cells + finite Decimal string / PS exactly 2 keys + 자유 var_name + non-empty + ≤9 + finite Decimal).
- **BL-225 ✅ Resolved** (`run_param_stability` 의 InputDecl.input_type 별 grid value validation — int/float supported, bool/string/source/price/session/symbol/timeframe/color/time/generic = MVP unsupported reject).
- **BL-226 신규 P2** (FE `isFiniteDecimalString()` regex 가 BE Pydantic Decimal 보다 좁음. `1e-3`, `.5`, `+1` 등 BE 허용 but FE reject 가능. dogfood 직접 사용 시 UX 영향 작지만 API contract parity 후속 정리 권장. Sprint 53+ 후속.).

## Day 7 4-AND gate (Sprint 52 시점)

- (a) self-assess ≥ 7/10 — **pending until 2026-05-16** (codex G.0 P1 정정). Day 7 카톡 인터뷰 결과 도래 후 결정. Sprint 52 close 직전 잠정 self-assess = 8/10 (codex G.4 PASS_WITH_FOLLOWUP + 회귀 0 + LESSON-040 7차 검증 통과 + LESSON-067 2차 검증 정밀화 + 5 commit 일관 패턴).
- (b) BL-178 production BH curve 정상. ✅ **PASS** (baseline preflight 13 PASS).
- (c) BL-180 hand oracle 8 test all GREEN. ✅ **PASS** (baseline preflight).
- (d) new P0=0 + Sprint-caused P1=0. ✅ **PASS** (codex G.4 GATE = P0/P1 0건, P2 1건 등재 BL-226 + P3 2건 즉시 fix `param-stability-form.tsx trim` + `router.py docstring`).

## Sprint 50/51 result_jsonb backfill 영향 (codex G.0 P1 권고 명시)

Sprint 52 BL-222 fix 이전 (2026-05-04 ~ 2026-05-11) 생성된 Cost Assumption Sensitivity + Param Stability 결과는 **retro-incorrect** — 모든 cell 이 `BacktestConfig()` default 사용. 사용자 의도 (BL-188 v3 sizing / trading_sessions / fees / slippage / initial_capital) 가 반영되지 않음.

**권고 (사용자 manual 의무)**:

- 본인 dogfood Sprint 50/51 안에서 실행한 CA/PS 결과는 신뢰하지 말고 Sprint 52 fix 머지 후 재실행.
- `docs/dogfood/sprint42-feedback.md` Day 7 row 작성 시 명시.
- `docs/TODO.md` 에 affected stress_test id 또는 date range 기록.

## Phase 3 path (Sprint 53+ 갱신)

| Sprint        | Scope                                                                                                              | Wall-clock                               |
| ------------- | ------------------------------------------------------------------------------------------------------------------ | ---------------------------------------- |
| **52 (현재)** | Stress Test follow-up bundle (4 BL Resolved)                                                                       | 5 commit / 16 files / +1489 / ~5-6h 직렬 |
| **53**        | Day 7 (2026-05-16) + Day 14 (2026-05-23) 결과 반영 4-way 분기 (Beta 본격 / Phase 3 prereq / polish iter / mainnet) | 4-way 분기에서 결정                      |
| **54**        | Phase 3 Optimizer 본격 (Grid 우선, Bayesian/Genetic 후속)                                                          | 18-26h (Sprint 53 prereq spike 통과 시)  |

**Phase 3 도달 = +2-3 sprint (Sprint 52 → 54), wall-clock 약 1.5-2주.** Sprint 53 = Day 7 결과 따라 분기 (BL-203 manual + Day 14 row 갱신 + 본인 의지 second gate).

## 다음 step

1. 사용자 PR review + squash merge (`feat/sprint52-stress-test-followup` → main)
2. Day 7 카톡 인터뷰 (2026-05-16) — `sprint42-feedback.md` Day 7 row 채움 + Sprint 53 분기 결정 input
3. Day 14 카톡 인터뷰 (2026-05-23) — Day 14 row 채움
4. Sprint 53 분기 결정 (Day 7+14 NPS + critical bug + self-assess + 본인 의지 dual gate)

## P3 즉시 fix (codex G.4)

- `frontend/src/app/(dashboard)/backtests/_components/param-stability-form.tsx` — `handleSubmit` 안에서 `var1Name.trim()` + `var2Name.trim()` + values trim 적용. UI invalid 판정 + submit payload 모두 trim 정합.
- `backend/src/stress_test/router.py` — module docstring 에 `POST /stress-tests/param-stability` 추가 (Sprint 51 BL-220 누락).

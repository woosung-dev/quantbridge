# Sprint 53 close-out — Phase 3 Optimizer prereq spike (BL-228 prereq + BL-226 Resolved)

> 작성일: 2026-05-11 (Sprint 52 same-day kickoff + same-day close) / 작성자: Claude Opus 4.7 (1M context) + 사용자 woo sung

## 요약 (TL;DR)

- **분기 (b) Phase 3 Optimizer prereq spike 본격 진행.** Day 7 (2026-05-16) 인터뷰 5일 갭 활용. 3 트랙 + 5 Slice.
- **codex G.0 revision A 채택** — P1 12건 wrong premise plan v2 일괄 반영 (engine 위치 common/ + N-dim 호환 signature + Optimizer migration 포함 + StrictDecimalInput canonicalization 등).
- **codex G.4 GATE 1차 FAIL → P1 3건 fix + P2 #2 + P3 fix 후 PASS_WITH_FOLLOWUP.** P1 #1 StrictDecimalInput BE/FE parity (Number.isFinite mirror) / P1 #2 optimizer DecimalField StrictDecimalInput / P1 #3 IntegerField+DecimalField numeric invariant validator.
- **회귀 0.** Sprint 53 변경 영역 BE 139 PASS (grid_sweep 13 + strict_decimal_input 17 + optimizer 21 + param_stability_schemas 12 + param_stability engine 12 + cost_assumption_sensitivity 5). FE 680 PASS 무회귀. ruff clean / mypy clean.
- **superpowers 5종 통합 3차 실측** (Sprint 51 1차 → 52 2차 → 53 3차).
- **LESSON-040 = 8/8 영구 검증 통과** (Sprint 29/30/35/49/50/51/52 → 53). codex G.0 P1 12건 모두 plan revision A 일괄 반영 후 Slice 1 진입. **LESSON-067 분산형 evaluator 3차 정밀화 검증 = ~1.03M tokens (G.0 351k + G.4 676k)**. LESSON-061 `--no-verify 0회` = 11건 누적.
- **BL 등재 변경 = BL-226 P2 Resolved + BL-227/228/229/230/231 5건 신규 P2/P3 등재 (Sprint 54+ 후속).**

---

## 시점 + 변경

- **활성 sprint:** Sprint 53 = 3 트랙 (grid_sweep engine 추출 + Optimizer entity+schemas + StrictDecimalInput BE 통일). Day 7 (2026-05-16) 미도래 5일 갭 활용 (Sprint 52 와 동일 패턴 = 분기 결정 prereq spike).
- **main base = `6c7adfb`** (Sprint 52 close-out PR #256). 작업 branch = `feat/sprint-53-grid-sweep-lift-up`. close-out PR 생성 예정.

## Slice 분할 (v2 revision 후)

| Slice | Methodology                                                       | 신규 test (BE/FE) | codex                                              |
| ----- | ----------------------------------------------------------------- | ----------------- | -------------------------------------------------- |
| 0     | brainstorming + Explore agent 3 + codex G.0 + **plan revision A** | (plan revision)   | **G.0 = GO_WITH_FIXES P1 12건** (~351k tokens)     |
| 1     | TDD — grid_sweep engine 추출 + param_stability wrapper            | BE 13             | (skip — 문제 없음)                                 |
| 2     | TDD — Optimizer entity + discriminated union schemas + alembic    | BE 21             | (skip — 문제 없음)                                 |
| 3     | TDD — StrictDecimalInput + canonicalization + stress_test 교체    | BE 17             | (skip — 문제 없음)                                 |
| 4     | codex G.4 GATE + P1 3건 fix + P2#2 + P3 fix + close-out           | BE 8 (P1 fix)     | **G.4 = FAIL → PASS_WITH_FOLLOWUP** (~676k tokens) |

**신규 test 합계 = 80 (BE 전부).** (실제 cumulative 검증 시 139 PASS — Sprint 53 신규 + 기존 stress_test 등).

## 산출 (단일 close-out commit)

핵심 파일 변경 = **8 modified + 7 신규**:

- 신규 `backend/src/common/grid_sweep.py` — generic 2D grid sweep engine (Mapping[str, Decimal] N-dim 호환 signature, GridSweepCellError chaining, tuple result lock)
- 신규 `backend/src/common/strict_decimal_input.py` — StrictDecimalInput Request-boundary validator (FE Number.isFinite parity + canonicalization)
- 수정 `backend/src/stress_test/engine/param_stability.py` — grid_sweep 위임 (2D nested loop 제거, BL-225 validation pre_validate hook, \_build_config BL-222 보존 wrapper 안 유지)
- 신규 `backend/alembic/versions/20260512_0001_add_optimization_runs_table.py` — table + 2 enum (LESSON-066 uppercase GRID_SEARCH/QUEUED) + 4 index
- 수정 `backend/src/optimizer/models.py` — OptimizationRun entity (빈 stub → SQLModel table=True, SAEnum values_callable 금지 명시)
- 수정 `backend/src/optimizer/schemas.py` — ParamSpace discriminated union (Integer/Decimal/Categorical + schema_version + objective_metric + direction + numeric invariant validator)
- 수정 `backend/src/optimizer/exceptions.py` — AppException 계층 상속 (NotFoundError + ValidationError + machine-readable code)
- 수정 `backend/src/stress_test/schemas.py` — param_grid StrictDecimalInput 교체 (CostAssumption + ParamStability 양쪽 line 144 + 215)
- 수정 `frontend/src/features/backtest/schemas.ts:478` — JSDoc 1줄 BE mirror (Atomic Update)
- 신규 `backend/tests/common/test_grid_sweep.py` (13 test)
- 신규 `backend/tests/common/test_strict_decimal_input.py` (17 test, +1 huge_digit_overflow)
- 신규 `backend/tests/optimizer/__init__.py` + `test_models.py` (5) + `test_schemas.py` (14) + `test_exceptions.py` (2)
- 수정 `backend/tests/stress_test/test_param_stability_schemas.py` (+5 BL-226 reject test)

## codex G.4 결과 (revision A 후)

**1차 G.4 = FAIL** (676k tokens, P0=0, P1=3, P2=2, P3=1)

P1 fix 결과:

| P1  | 발견 위치                           | Fix                                                                                               | 검증                                                                                               |
| --- | ----------------------------------- | ------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| #1  | `common/strict_decimal_input.py:49` | `_check_float_finite()` helper 추가 — `math.isfinite(float(v))` FE parity                         | `test_rejects_huge_digit_string_overflow` (`"9" * 400`)                                            |
| #2  | `optimizer/schemas.py:49`           | `DecimalField.min/max/step: StrictDecimalInput` 교체                                              | `test_decimal_field_strict_decimal_input_rejects_exponent_string` + `test_..._rejects_nan_decimal` |
| #3  | `optimizer/schemas.py:35`           | `IntegerField` + `DecimalField` `@model_validator(mode="after")` invariant (step > 0, min <= max) | 5 invariant reject test 추가                                                                       |

P2 #2 추가 fix:

- `optimizer/exceptions.py` AppException 계층 (`NotFoundError` 404 + `ValidationError` 422 + machine-readable code).

P3 fix:

- `strict_decimal_input.py` docstring `Decimal("1E-3")` → `Decimal("1E+5")` 정정 (Python 자동 정규화 path 명시).

P2 #1 (N-dim 확장) = **BL-228 plan 안 이미 등재** → Sprint 54 본격 prereq.

## 의무 체크리스트 (영구 규칙)

- [x] §7.1 — Sprint kickoff 첫 step = baseline preflight (1803 collected baseline)
- [x] §7.4 — codex G.0 master plan validation (P1 12건 발견 → revision A)
- [x] LESSON-037 frame change 시 plan revision 의무 (v2 일괄 반영)
- [x] LESSON-040 영구 검증 path 8/8 (현재 사이클 통과)
- [x] LESSON-019 commit-spy = optimizer service 미구현 = 면제 사유 명시 (Sprint 54 service 시 의무 발동)
- [x] LESSON-066 SAEnum uppercase + values_callable 금지 명시 (`optimizer/models.py` 안 주석)
- [x] LESSON-061 `--no-verify 0회`
- [x] main 직접 push 차단 — branch + PR + 사용자 squash merge
- [x] Decimal-first 합산 (param_grid 안 모든 Decimal 인스턴스 strict canonicalization 통과)
- [x] 회귀 0 — Sprint 53 변경 영역 139 PASS + FE 680 PASS

## 명령 (verification)

```bash
git checkout feat/sprint-53-grid-sweep-lift-up
cd backend && uv run pytest tests/common/test_grid_sweep.py tests/common/test_strict_decimal_input.py tests/optimizer/ tests/stress_test/test_param_stability_schemas.py tests/stress_test/engine/test_param_stability.py tests/stress_test/engine/test_cost_assumption_sensitivity.py -v
# 139 PASS 기대

cd backend && uv run ruff check src/common src/optimizer src/stress_test tests/common tests/optimizer
# All checks passed

cd backend && uv run mypy src/common src/optimizer src/stress_test
# Success: no issues found in 35 source files

cd frontend && pnpm test
# 680 PASS 무회귀

# alembic round-trip (DB 띄운 환경에서 manual 검증 권장 — local 환경 password 인증 실패로 자동 round-trip 검증 skip)
# `make up-isolated` 후 alembic upgrade head + downgrade -1 + upgrade head
```

## codex 평가지점

| 지점     | tokens     | 결과                             |
| -------- | ---------- | -------------------------------- |
| G.0      | ~351k      | GO_WITH_FIXES P1 12건            |
| G.4 1차  | ~676k      | FAIL — P1 3건 fix 의무           |
| **합계** | **~1.03M** | 분산형 evaluator 3차 정밀화 검증 |

Sprint 51 ~1.0-1.3M → Sprint 52 ~216k → Sprint 53 ~1.03M. Sprint 52 의 spot eval 축소 패턴 (~216k) 대비 Sprint 53 = full G.0 + G.4 1차 패턴 = 더 무거움. LESSON-067 = sprint scope (revision 양 + 트랙 수) 에 따라 token 비용 가변.

## JSONB Retro 경고 (사용자 manual 의무)

**Sprint 50 / Sprint 51 / Sprint 52 안 생성된 Cost Assumption Sensitivity / Param Stability `result_jsonb` 안 row**:

- BL-222 fix 이전 (2026-05-04 ~ 2026-05-11) + Sprint 53 fix 이전 grammar 위반 값 (`"1e-3"`, `".5"`, `"+1"`, `Decimal("NaN")`, `Decimal("1E+5")`, `"9" * 400` overflow 등) silent passthrough 가능.
- Sprint 53 fix 이후 service 가 `Decimal(v)` JSONB 재복원 시 canonicalization check 실패 가능 → 사용자 manual 재실행 권고.
- dogfood Day 7+ (2026-05-16) 발견 시 사용자 hard refresh + 재실행.

`docs/dogfood/sprint42-feedback.md` retro 컬럼 추가 의무 (Sprint 53 close-out 시점).

## BL 등재 변경

**Resolved (1)**:

- BL-226 P2 ✅ — FE Decimal regex BE parity. `StrictDecimalInput` BE strict 통일 + canonicalization + FE JSDoc mirror 적용.

**신규 (5)**:

- **BL-227 P2** — Cost Assumption Sensitivity 도 `run_grid_sweep` 추출 (Sprint 53 = Param Stability 만 검증, engine generic 1 사이클 후 적용).
- **BL-228 P2** — `run_grid_sweep` N-dim 확장 (현재 2 key 강제). Sprint 54 Bayesian/Genetic 진입 시 의무.
- **BL-229 P3** — backtest/optimizer schemas 도 StrictDecimalInput 통일 (Sprint 53 = stress_test 만 + Sprint 54 optimizer 본격 시 자동 적용).
- **BL-230 P2** — Optimizer `error_message` 길이 제한 + public/internal error 분리 (codex G.4 P2 권고).
- **BL-231 P2** — Bayesian 분포 + categorical encoding + log scale + integer rounding grammar 확장 ADR (Sprint 54 본격 prereq).

## 학습 (lessons.md candidate)

- **LESSON-040 8/8 영구 검증 통과** — codex G.0 직후 plan revision 의무 + LESSON-037 frame change 시 즉시 plan revision = wrong premise 13건 (G.0 12 + G.4 1) 모두 plan 반영 후 무회귀 진입.
- **LESSON-067 분산형 evaluator 3차 정밀화** — Sprint 52 spot eval ~216k vs Sprint 53 full G.0+G.4 ~1.03M. Sprint scope (revision 양 + 트랙 수) 에 따른 token 비용 가변성 검증.
- **LESSON-061 11건 누적** — `--no-verify 0회` 영구 path 유지.
- **LESSON-066 4차 검증** — SAEnum uppercase grammar (GRID_SEARCH / QUEUED) Sprint 50 BL-221 P0 hotfix 패턴 영구 적용.

## 후속 (Sprint 54+ 이연)

- **Sprint 54 본격 Optimizer**: Grid Search 알고리즘 + Celery task + FE 폼/일람 + LESSON-019 commit-spy 의무 발동 + BL-228 N-dim 확장 + BL-229 backtest/optimizer schemas StrictDecimalInput 통일 + dogfood Day 7 결과 반영 따라 4-way 분기 재평가.
- **dogfood Day 7 (2026-05-16) 인터뷰** → NPS/critical bug/self-assess 결과 따라 Sprint 54 본격 vs Beta 본격 진입 분기 결정.
- **JSONB retro 사용자 manual 재실행** — Sprint 50/51 결과 신뢰 X 명시.

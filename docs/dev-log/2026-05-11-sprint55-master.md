# Sprint 55 master — ADR-013 Bayesian 본격 구현 (Phase 3 Optimizer 자연 연속)

> **Sprint:** Sprint 55 / **Date:** 2026-05-11 (Day 0+5 → Day 7 = 2026-05-16, 5일 후)
> **Branch:** `feat/sprint-55-bayesian-optimizer` (PR pending)
> **Base:** `main @ 9c93fa7` (Sprint 54 PR #258 squash 머지 직후, 2026-05-11 05:00 UTC)
> **Plan:** [`~/.claude/plans/sprint-55-glistening-frog.md`](../../../../woosung/.claude/plans/sprint-55-glistening-frog.md) (693줄, 6 Slice 분해)
> **사용자 scope 결정:** ★★★★★ Bayesian 본격 (Sprint 56 = Genetic split). C 옵션 (Bayesian + Genetic 동시 묶음) 거부 = Explore agent 권장 split path 따름.

---

## 1. Scope & 사용자 결정

| 결정                        | 값                                                | 근거                                                                                                         |
| --------------------------- | ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| Sprint 55 트랙 (4-way 분기) | **A. Bayesian 본격** (ADR-013 §6 8-checklist)     | Day 7 (2026-05-16) 까지 5일 갭 = ADR-013 lock 활용 zero-friction + Phase 3 momentum 유지 + cadence 묶음 선호 |
| Scope 크기                  | ★★★★★ Bayesian 본격 (engine + service + FE)       | M (16-20h estimate, 단일 worker 1-1.5일)                                                                     |
| 외부 라이브러리             | **scikit-optimize (skopt) 0.10.x**                | scikit-learn 1.8.0 transitive dep 이미 설치 + ask-tell loop 패턴 + BSD-3 + random_state 결정성               |
| Genetic                     | ❌ ADR-013 grammar 만 보존 (Sprint 56)            | PR review 부담 + dogfood 검증 split (Explore agent 결론)                                                     |
| FE viz                      | acquisition_history line chart + best params 표   | N-dim acquisition surface viz Sprint 57+ (BL-235)                                                            |
| objective_metric whitelist  | 유지 (sharpe_ratio / total_return / max_drawdown) | 자유화 = Sprint 56+ (BL-236)                                                                                 |
| dedicated Celery queue      | 미설정 (default queue + max_evaluations≤50 강제)  | Sprint 56+ (BL-237)                                                                                          |

---

## 2. Slice 분해 + 예상 산출물

| Slice                                                              | 시간 | 신규/수정 산출                                                                                                                                                                                                                                                                                                                                                                                                                   | 검증 의무                                                                                 |
| ------------------------------------------------------------------ | ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| **0 preflight + kickoff docs + uv add**                            | 0.5h | working branch + sprint55-master.md + BACKLOG BL-232 + INDEX 갱신 + CLAUDE.md 활성 sprint 갱신 + `uv add scikit-optimize` + baseline 재측정                                                                                                                                                                                                                                                                                      | BE focused 40+ PASS / FE 680 PASS / `uv lock --check` PASS                                |
| **1 schemas.py grammar 확장 + cross-field validator**              | 1.5h | `optimizer/schemas.py` (BAYESIAN enum + Literal[1,2] + BayesianHyperparamsField + ParamSpaceField 4-variant + 5 optional 필드 + cross-field validator) + 5 신규 test                                                                                                                                                                                                                                                             | schemas test 17+ PASS / 회귀 0                                                            |
| **2 engine/bayesian.py + alembic enum + serializers + 15 test**    | 3h   | `optimizer/engine/bayesian.py` 신규 (skopt Optimizer.ask/tell loop, direction 부호 반전, degenerate `y=inf`, `_MAX_BAYESIAN_EVALUATIONS=50`) + `alembic/versions/2026MMDD_*_add_bayesian_to_optimization_kind.py` (uppercase BAYESIAN, swap downgrade) + `engine/__init__.py` export + `serializers.py` `bayesian_search_result_to_jsonb` (Decimal→str + None 보존 + best_iteration_idx) + `pyproject.toml` skopt + 15 신규 test | engine test 15 PASS / `uv lock` 정합 / `uv run pytest backend/tests/optimizer` 회귀 0     |
| **3 service.submit_bayesian + run() kind 분기 + router + 7 test**  | 2h   | `optimizer/service.py` (submit_bayesian + \_execute_bayesian + run() if-elif kind 분기) + `optimizer/router.py` (POST /optimizer/runs/bayesian 202, slowapi 5/minute) + `optimizer/exceptions.py` 메시지 갱신 + 4 commit-spy test + 3 exception test                                                                                                                                                                             | optimizer test 100+ PASS / AsyncSession audit grep empty / OpenAPI diff = 1 endpoint 신규 |
| **4 FE schemas + form + iteration-chart + best-params-table**      | 2.5h | `features/optimizer/schemas.ts` (z.discriminatedUnion("kind") + BayesianSearchResultSchema) + `api.ts` postBayesianSearch + `hooks.ts` useSubmitBayesianSearch + `_components/bayesian-search-form.tsx` 신규 + `_components/bayesian-iteration-chart.tsx` 신규 + `_components/bayesian-best-params-table.tsx` 신규 + `optimizer-run-detail.tsx` kind 분기 + `page.tsx` algorithm select                                          | FE 680 PASS / lint+tsc clean / 회귀 0 / 본인 dogfood manual 2-input bayesian 제출         |
| **5 ADR-013 §7 amendment + BACKLOG 갱신 (Slice 1/4 와 병렬 가능)** | 1h   | `2026-05-12-sprint54-bayesian-genetic-grammar-adr.md` §7 (skopt 채택 + normal sampler 자체 wrapper + ordinal only + UCB→LCB + \_MAX=50) + BACKLOG BL-232 Resolved + BL-233~237 신규                                                                                                                                                                                                                                              | ADR 5-section 구조 / BACKLOG row format 일관                                              |
| **6 Playwright e2e + alembic round-trip + close-out + codex G.4**  | 1.5h | `frontend/e2e/sprint55-optimizer-bayesian.spec.ts` 신규 + alembic round-trip (LESSON-066 6차) + `2026-05-1?-sprint55-close.md` 신규 + 라이브 worker (사용자 manual deferred) + codex G.4 외부 invocation (사용자 manual)                                                                                                                                                                                                         | e2e PASS / round-trip PASS / `psql enum_range = {GRID_SEARCH, BAYESIAN}`                  |

**총 wall-clock**: 8-12h ≈ 단일 worker 1-1.5일 (Sprint 54 = 8h, Sprint 55 = scope 0.7×).
**Day 7 buffer**: 2026-05-11 시작 → 1.5일 종료 → Day 7 (2026-05-16) 까지 **3일 buffer 확보**.

---

## 3. ADR-013 §6 8-checklist 처리 매핑

| Checklist 항목                                                           | Slice | 상태                                                       |
| ------------------------------------------------------------------------ | ----- | ---------------------------------------------------------- |
| (1) `ParamSpace.schema_version` `Literal[1,2]` 확장                      | 1     | ✅ (default=1 유지, cross-field validator)                 |
| (2) `BayesianHyperparamsField` discriminated union 등재                  | 1     | ✅ (kind="bayesian" + min/max/prior/log_scale + invariant) |
| (3) `OptimizationKind.BAYESIAN` enum + alembic                           | 1+2   | ✅ (uppercase BAYESIAN + LESSON-066 6차)                   |
| (4) `optimizer/engine/bayesian.py` 신규                                  | 2     | ✅ (skopt Optimizer.ask/tell)                              |
| (5) Service `submit_bayesian` + `_execute_bayesian` 분기                 | 3     | ✅ (LESSON-019 commit-spy 4건)                             |
| (6) FE schemas discriminated union mirror                                | 4     | ✅ (z.discriminatedUnion("kind"))                          |
| (7) `bayesian_n_initial_random` + `bayesian_acquisition` 5 optional 필드 | 1     | ✅ (Genetic 3종도 schema_version=2 reservation)            |
| (8) FE Bayesian form + viz                                               | 4     | ✅ (form + iteration-chart + best-params-table)            |

**ADR-013 §7 amendment 의무 (Slice 5)**:

- `prior=normal` skopt 미지원 → 자체 sampler wrapper 명시 (Slice 2 안 30분 시한 초과 시 normal Sprint 56+ 이연)
- `direction=maximize` 시 `-y` tell 부호 반전 (skopt minimization → 우리 maximization)
- `CategoricalField encoding` Sprint 55 = ordinal only (one_hot Sprint 56+ Genetic 진입 시 활성, BL-234)
- `bayesian_acquisition` Literal `EI / UCB / PI` (UCB = LCB 부호 반전)
- `_MAX_BAYESIAN_EVALUATIONS=50` 결정 근거

---

## 4. Slice 0 baseline (kickoff preflight)

### LESSON-037 baseline 재측정

| Test target              | 결과                                                                                   |
| ------------------------ | -------------------------------------------------------------------------------------- |
| BE focused optimizer     | **40 PASS** (`uv run pytest backend/tests/optimizer -q`, Sprint 54 종료 시점 baseline) |
| FE vitest                | **680 PASS** (Sprint 54 종료 시점 baseline, 별도 background 검증)                      |
| ruff / mypy / lint / tsc | clean (Sprint 54 종료 시점 baseline)                                                   |

### LESSON-040 prereq verification spike (5건)

1. ✅ `optimizer/schemas.py:104` `schema_version: Literal[1] = 1` lock 그대로 (확장 path 안전)
2. ✅ `optimizer/engine/grid_search.py:210` `_pick_best_cell_index` direction 분기 — Bayesian executor 에서 `_pick_best_iteration_idx` 로 mirror 가능
3. ✅ `optimizer/dispatcher.py` `dispatch_optimization(run_id)` 시그니처 kind 무관 → kind 분기 없이 재사용
4. ✅ `tasks/optimizer_tasks.py` `run_optimization_task` celery task = 단일 → kind 분기는 service.run() 안에서
5. ✅ FE `features/optimizer/schemas.ts` `OptimizationKindSchema = z.enum(["grid_search"])` 확장 지점 1군데 (z.enum → z.discriminatedUnion)

### `uv add scikit-optimize`

- 명령: `uv add 'scikit-optimize>=0.10.0,<0.11'`
- 의존성 충돌: ✅ 없음 (scikit-learn 1.8.0 + scipy + numpy 이미 설치)
- 신규 wheel 1개 (scikit-optimize) + transitive `pyaml` 정도 추가 예상

---

## 5. 메타 step 의무 이행 점검 계획

| LESSON / 규칙                                  | Slice        | 의무                                                                                                               |
| ---------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------------ |
| LESSON-037 Sprint kickoff baseline 재측정      | 0            | ✅ (본 §4)                                                                                                         |
| LESSON-040 codex G.0 prereq verification spike | 0            | ✅ (본 §4) — codex G.0 외부 invocation 사용자 manual                                                               |
| LESSON-019 commit-spy 회귀 의무                | 3            | 4건 (submit_bayesian / dispatcher raise rollback / run complete BAYESIAN / run fail BAYESIAN truncate)             |
| LESSON-038 docker worker auto-rebuild          | 6            | ⏳ PR 머지 후 사용자 manual `make up-isolated-build` 권장                                                          |
| LESSON-061 pre-push hook env quirk             | PR push 직전 | ⏳ PR push 시 `TEST_DATABASE_URL` + `TEST_REDIS_LOCK_URL` shell export 의무                                        |
| LESSON-066 alembic SAEnum + StrEnum round-trip | 6            | 6차 영구 검증 의무 (`upgrade head → downgrade -1 → upgrade head` PASS + `psql enum_range` 검증)                    |
| backend.md §3 service AsyncSession import 금지 | 3 grep audit | `grep "AsyncSession\|from sqlalchemy.ext.asyncio" src/optimizer/service.py` empty 강제                             |
| backend.md §11.1 `run_in_worker_loop` 강제     | 2/3 audit    | optimizer_tasks.py 미수정 (Sprint 54 기존 활용) → grep 회귀 0                                                      |
| backend.md §11.5 라이브 worker 검증            | 6            | ⏳ deferred — `optimizer.run` task 안 BAYESIAN 분기 추가 = 신규 task type 아님 → 라이브 검증 부담 경감 (의무 유지) |
| Playwright e2e SAEnum case mismatch 차단       | 6            | `sprint55-optimizer-bayesian.spec.ts` 신규                                                                         |

**의무 deferred 4건 (사용자 manual 영역, Sprint 54 mirror)**:

- backend.md §11.5 라이브 worker 30분 cycle 검증
- LESSON-038 PR merge 후 docker worker rebuild
- Playwright e2e 실행 (spec 작성은 Sprint 안 의무)
- codex G.0 / G.4 외부 invocation (Sprint 52 ~216k tokens 패턴 mirror 권장)

---

## 6. JSONB grammar (schema_version=2 result_jsonb)

```jsonc
{
  "schema_version": 2,
  "kind": "bayesian", // FE z.discriminatedUnion("kind") 의무
  "param_names": ["emaPeriod", "stopLossPct"],
  "iterations": [
    {
      "idx": 0,
      "params": { "emaPeriod": "14", "stopLossPct": "1.5" },
      "objective_value": "1.32", // Decimal → str (degenerate=null)
      "best_so_far": "1.32",
      "is_degenerate": false,
      "phase": "random", // "random" | "acquisition"
    },
  ],
  "best_params": { "emaPeriod": "14", "stopLossPct": "1.5" },
  "best_objective_value": "1.85",
  "best_iteration_idx": 7, // FE highlight (Sprint 50/51/52 retro-incorrect 차단)
  "objective_metric": "sharpe_ratio",
  "direction": "maximize",
  "bayesian_acquisition": "EI",
  "bayesian_n_initial_random": 10,
  "max_evaluations": 30,
  "degenerate_count": 4,
  "total_iterations": 30,
}
```

**Sprint 50/51/52 retro-incorrect 차단 4종 (Slice 2 의무)**:

1. Decimal → str 강제 (FE `Number.parseFloat` 가능 표기 `^-?\d+(\.\d+)?$`)
2. None 보존 (degenerate `objective_value=null` 명시)
3. iteration row insertion order 보존 (Python list 순서 = idx 순서)
4. `best_iteration_idx` 명시 필드 (Sprint 50/51/52 의 best_cell_index 누락 패턴 차단)

---

## 7. 위험 요소 & 완화

| 위험                                                                 | 완화                                                                                                                                                                             |
| -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **R1 회귀** (schema_version Literal 확장 cross-field validator 누락) | Slice 1 회귀 test 2건 (`test_param_space_v1_round_trip_unchanged_grid_search` + `test_param_space_schema_v1_rejects_bayesian_optional_fields`) + codex G.0 cross-field challenge |
| **R2 scope creep** (skopt API 학습 + numerical edge case)            | `Optimizer.ask/tell` 패턴만 사용 + `random_state=42` + `_MAX=50` 강제 + normal prior 30분 시한 (초과 시 Sprint 56 이연) + 8h progress check                                      |
| **R3 Day 7 누락**                                                    | 1.5일 estimate = 1-3일 buffer + Slice 6 dev-log close 의무 + 8h 시점 Slice 4 FE viz Sprint 56 이연 옵션 (minimal text table 대체)                                                |
| **R4 LESSON-066 회귀** (`ALTER TYPE` lowercase)                      | Slice 2 alembic uppercase 강제 + Slice 6 round-trip 영구 검증 + codex G.4 cross-check                                                                                            |
| **R5 dispatcher silent kind mismatch** (GENETIC kind silent fail)    | `OptimizationKindUnsupportedError` raise else 분기 + Slice 3 신규 test + mypy strict exhaustiveness                                                                              |
| **R6 FE result discriminated mismatch**                              | result_jsonb top-level `kind` echo (BE serializer + FE `z.discriminatedUnion("kind", ...)`)                                                                                      |
| **R7 50 evaluation 시간 초과** (`50 × 5s = 250s`)                    | max_evaluations=50 강제 상한 + dedicated queue Sprint 56+ (BL-237) + 본인 dogfood max=10~15 권장                                                                                 |

---

## 8. Day 7 4중 AND gate (영구 기준, Sprint 41+ 적용)

- (a) self-assess ≥7/10 (근거 ≥3 줄) — Day 7 (2026-05-16) 인터뷰 후 채움
- (b) BL-178 production BH curve 정상 — main 변경 X 영역 (회귀 0 의무)
- (c) BL-180 hand oracle 8 test all GREEN — main 변경 X 영역 (회귀 0 의무)
- (d) new P0=0 AND unresolved Sprint-caused P1=0 — Slice 6 close-out audit 의무

---

## 9. Sprint 56 prereq (Sprint 55 산출 활용)

Sprint 55 close-out 후 Sprint 56 candidate (4-way 분기, Day 7 결과 의존):

1. **Genetic 본격** (BL-233) — Sprint 55 Bayesian 패턴 mirror, scope M (16-20h, 단일 worker 1.5일)
2. **Beta 본격** (BL-070~075) — dogfood NPS≥7 + 본인 의지 second gate 통과 시
3. **mainnet** (BL-003/005) — 사용자 결정 도래 시
4. **polish iter** — dogfood critical bug 1+ 발견 시

**Sprint 55 산출 = Sprint 56 Genetic 의 zero-friction prereq**:

- ParamSpace.schema_version=2 + GeneticHyperparamsField reservation (Slice 1)
- alembic enum 확장 패턴 (Slice 2)
- service.run() kind 분기 패턴 (Slice 3)
- FE z.discriminatedUnion 패턴 (Slice 4)
- ADR-013 §7 amendment grammar lock (Slice 5)

→ Sprint 56 Genetic = engine + executor + FE form 신규만, scope ≈ Sprint 55 Bayesian 의 0.8×.

---

**End of Sprint 55 master.**

> 본 문서는 kickoff plan 기록. close-out 시 별도 `2026-05-1?-sprint55-close.md` 작성 의무.

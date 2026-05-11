# ADR-013 — Bayesian / Genetic Optimizer 알고리즘 ParamSpace grammar 확장 사전 lock

> **Status:** Accepted (BL-231 — Sprint 54 Slice 5, 코드 변경 X, 문서 lock 만)
> **Sprint:** Sprint 54 (Phase 3 Optimizer 본격 진입)
> **Date:** 2026-05-12
> **Authors:** woo sung + Claude (Sprint 54 cmux)
> **Related:** ADR-011 (pine_v2 SSOT), Sprint 53 PR #257 (Optimizer prereq spike), BL-228/230/231

---

## 1. Context

Sprint 53 prereq spike (`optimizer/schemas.py`) 가 ParamSpace pydantic 을 `schema_version: Literal[1] = 1` 로 lock 했다. 현 grammar 는 **Grid Search MVP 만 수용**한다:

- `ParamSpaceField = IntegerField | DecimalField | CategoricalField` discriminated union (Pydantic V2 `discriminator="kind"`).
- `ParamSpace` = `{schema_version=1, objective_metric, direction ∈ {maximize, minimize}, max_evaluations > 0, parameters: dict[str, ParamSpaceField]}`.

Sprint 54 본격 = Grid Search 구현만. **Bayesian / Genetic 알고리즘은 Sprint 55+ 이연 (사용자 ★★★★★ 결정)**. 그러나 grammar 확장 path 를 **Sprint 54 안 ADR 으로 사전 lock** 하지 않으면, Sprint 55+ 진입 시 schema_version=2 grammar 재논의로 리워크 위험.

본 ADR 은 **schema_version=2 시 추가될 union member + ParamSpace 필드 + 변환 rule** 을 명시한다. 코드 변경 0 — 본 ADR 이 Sprint 55+ kickoff 의무 참조다.

---

## 2. Decision

Sprint 55+ Bayesian / Genetic 진입 시 ParamSpace grammar 를 `schema_version: Literal[1, 2]` 로 union 확장. `schema_version=1` backward compat 보존 (기존 OptimizationRun JSONB row 그대로 deserialize). 새 grammar 는 다음 4 항을 추가한다.

### 2.1 신규 union member (ParamSpaceField 확장)

| Field 명                   | kind discriminator | 용도                                                      | 핵심 필드                                                                                           |
| -------------------------- | ------------------ | --------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| `BayesianHyperparamsField` | `"bayesian"`       | Bayesian Optimization 변수 (단일 변수 prior + scale 명시) | `min: Decimal`, `max: Decimal`, `prior ∈ {uniform, log_uniform, normal}`, `log_scale: bool = False` |
| `GeneticHyperparamsField`  | `"genetic"`        | Genetic Algorithm 변수 (gene encoding + mutation)         | `min: Decimal`, `max: Decimal`, `gene_type ∈ {real, integer}`, `mutation_sigma: Decimal`            |

기존 `IntegerField`, `DecimalField`, `CategoricalField` 보존 (Grid Search 에서도 동일 사용).

### 2.2 ParamSpace 본체 확장

`schema_version=2` 시 다음 optional 필드 추가:

```python
class ParamSpace(BaseModel):
    schema_version: Literal[1, 2] = 1
    objective_metric: str
    direction: Literal["maximize", "minimize"]
    max_evaluations: int = Field(gt=0)
    parameters: dict[str, ParamSpaceField]

    # schema_version=2 only — Sprint 55+
    population_size: int | None = None     # Genetic
    n_generations: int | None = None       # Genetic
    mutation_rate: Decimal | None = None   # Genetic
    bayesian_n_initial_random: int | None = None  # Bayesian — random warm-up cells
    bayesian_acquisition: Literal["EI", "UCB"] | None = None  # Bayesian acquisition fn
```

검증 invariant (model_validator):

- `schema_version=1` 시 위 5개 모두 `None` 강제 (extra="forbid" 와 별개의 cross-field guard).
- `kind="bayesian"` 또는 `"genetic"` field 가 1개 이상 있으면 `schema_version >= 2` 의무.

### 2.3 Integer rounding rule

- IntegerField 는 Grid Search 에서 step 으로 정확 정수 expand. Bayesian / Genetic 진입 시 continuous space sample → **bankers' rounding (banker's = even half)** 으로 정수 변환. `round(x)` Python 3 기본 동작 채택 (NOT `int(x + 0.5)`).
- 검증 fixture: `round(Decimal("2.5"), 0) == Decimal("2")`, `round(Decimal("3.5"), 0) == Decimal("4")`.

### 2.4 Categorical encoding rule (Bayesian / Genetic 전용)

Bayesian / Genetic 은 continuous space 만 sample 가능 → CategoricalField 사용 시 다음 encoding 강제:

| encoding              | 정책                                                          | 적용 알고리즘                   |
| --------------------- | ------------------------------------------------------------- | ------------------------------- |
| **one-hot**           | 각 categorical value 를 별도 binary dimension (값 = 0 또는 1) | Bayesian + Genetic 양쪽         |
| **ordinal (default)** | `values` 순서를 정수 (0, 1, 2, …) 로 mapping                  | Bayesian (`prior=uniform` 필수) |

Sprint 55+ 진입 시 사용자가 `CategoricalField` 에 `encoding: Literal["one_hot", "ordinal"] = "ordinal"` 필드 추가 의무. Grid Search 는 encoding 무시 (직접 values 순회).

### 2.5 Log-scale rule (Bayesian 전용)

- `prior="log_uniform"` 또는 `log_scale=True` 시 변수 sample 영역을 `log10(min) → log10(max)` 로 변환. min > 0 강제 (DecimalField 와 호환).
- 결과 cell 의 param_values JSONB 에는 **변환 전 raw Decimal** 만 저장 (log 변환은 executor 내부 sample 단계만).

---

## 3. Consequences

### Positive

- Sprint 55+ Bayesian/Genetic kickoff 시 grammar 재논의 0. 본 ADR 가 contract.
- `schema_version=1` 기존 OptimizationRun JSONB row deserialize 그대로 (forwards-compat).
- FE 도 Sprint 55+ 에서 동일 schemas pydantic mirror 가능 (`schema_version` discriminator).

### Negative

- ParamSpace 본체 optional 필드 5개 추가 → schema lock 표면적 커짐. 보완: `model_validator` cross-field guard 로 invalid combo reject 명시.
- `schema_version=2` 시 backward compat 코드 (`if schema_version == 1: ...`) Bayesian/Genetic 진입 sprint 마다 검토 의무.

### Neutral

- 본 ADR 은 **코드 변경 0**. Sprint 54 Optimizer Grid Search 는 `schema_version=1` 만 처리. Sprint 55+ executor 가 `schema_version=2` 분기.
- `objective_metric` 화이트리스트 (Sprint 54 = `{sharpe_ratio, total_return, max_drawdown}`) 는 별도 BL — Bayesian/Genetic 진입 시 자유화 검토 (separate ADR 권장).

---

## 4. Alternatives Considered

### Alt 1 — schema_version 없이 ParamSpace 그대로 확장

- 문제: Sprint 53 prereq 가 `schema_version: Literal[1] = 1` lock 했음. 변경 시 alembic enum + JSONB row 호환 깨짐.
- 거부 이유: backward compat 부재.

### Alt 2 — schema_version=2 별도 ParamSpaceV2 클래스

- 별 두 클래스 fork → discriminated union 안 `Union[ParamSpace, ParamSpaceV2]`. 분기 명확.
- 거부 이유: V1 = V2 의 strict subset. 별도 클래스 = 코드 중복. `Literal[1, 2]` union + optional 필드 + cross-field validator 가 더 간결.

### Alt 3 — Bayesian / Genetic 을 별도 도메인 모듈로 (optimizer_bayesian/, optimizer_genetic/)

- ParamSpace 통합 X, 도메인 격리.
- 거부 이유: 사용자가 "최적화" 단일 UX 기대 (FE 진입점 = `/optimizer` 하나). 도메인 분리 시 cross-page composability 손실. 본 ADR §2.1 의 union member 확장 path 가 더 자연.

### Alt 4 — Sprint 54 안 Bayesian/Genetic 초기 구현 + grammar 즉시 확장

- Sprint 54 scope ★★ (24-32h) 옵션 — 사용자 ★★★★★ (Grid Search MVP) 채택.
- 거부 이유: dogfood Day 7 (2026-05-16) 까지 5일 갭 + Grid Search 단독 dogfood 가치 검증 우선.

---

## 5. References

- **Sprint 53 PR #257** — `optimizer/schemas.py` schema_version=1 grammar lock (commit `2b00f8c`).
- **Sprint 54 Slice 2** — Grid Search executor (`optimizer/engine/grid_search.py`) IntegerField/DecimalField only 사용. CategoricalField = `OptimizationParameterUnsupportedError` (422).
- **Sprint 54 Slice 3** — Service `submit_grid_search` 가 `OptimizationKindOut.GRID_SEARCH` 만 수용. Bayesian/Genetic kind 진입 시 `OptimizationKindUnsupportedError` (422).
- **ADR-011 (pine_v2 SSOT)** — Bayesian/Genetic 도 동일 `run_backtest` 호출 — engine 통합 path 보장.
- **BL-231 (REFACTORING-BACKLOG.md)** — 본 ADR 등재 BL. Sprint 55+ Bayesian/Genetic 본격 구현 시 본 ADR §2.1~2.5 의무 참조.
- **scikit-optimize / Optuna API mirror** — Sprint 55+ executor 구현 시 prior enum naming 통일 검토.

---

## 6. Sprint 55+ kickoff 의무 checklist

본 ADR 을 referenced 하는 Sprint 55+ kickoff 시 다음 의무:

1. `optimizer/schemas.py` 의 `ParamSpace.schema_version` 을 `Literal[1, 2]` 로 확장 + 5 optional 필드 추가 + cross-field validator.
2. `optimizer/schemas.py` 의 `ParamSpaceField` discriminated union 에 `BayesianHyperparamsField`, `GeneticHyperparamsField` 추가.
3. `optimizer/models.py` 의 `OptimizationKind` enum 에 `BAYESIAN`, `GENETIC` 추가 + alembic migration uppercase 의무 (LESSON-066).
4. `optimizer/engine/bayesian.py` + `optimizer/engine/genetic.py` 신규 (Grid Search pattern mirror).
5. `optimizer/service.py` `submit_bayesian` / `submit_genetic` 분기 + `_execute_bayesian` / `_execute_genetic` worker entry.
6. LESSON-019 commit-spy — 신규 service entry 마다 spy 4건 (submit / run complete / run fail / dispatcher rollback).
7. FE `frontend/src/features/optimizer/schemas.ts` discriminated union mirror 갱신.
8. FE N-dim viz prototype (3D+ surface 또는 parallel-coord) — Sprint 54 deferred.

---

## 7. Sprint 55 amendment — Bayesian executor 본격 구현 (BL-232 Resolved)

> Sprint 55 (`feat/sprint-55-bayesian-optimizer`, 2026-05-11) close-out 시점 추가. §6 8-checklist 중 (1)~(7) 처리 + Bayesian-only 활성, Genetic 은 Sprint 56+ (BL-233) 로 이연.

### 7.1 외부 라이브러리 채택 — scikit-optimize (skopt) 0.10.x

§5 References 의 "scikit-optimize / Optuna API mirror" 항목 따라 skopt 채택. 근거 4종:

1. `scikit-learn 1.8.0` 이미 `backend/uv.lock` transitive dep — 신규 wheel 1개 (`scikit-optimize 0.10.2`) + `pyaml 26.2.1` 만 추가.
2. `Optimizer.ask() / tell()` ask-tell loop 가 §6 #4 의 "best_params + acquisition_history" 1:1 매핑.
3. `Real(low, high, prior)` (`prior ∈ {"uniform", "log-uniform"}`) + `Integer(low, high)` + `Categorical(values, transform="label")` 가 §2.1 BayesianHyperparamsField + §2.4 ordinal encoding 와 정확 매칭.
4. BSD-3 license + mature codebase + `random_state` 결정성 (dogfood Day 7 재현 가능).

### 7.2 보완 결정 (Sprint 55 lock)

- **`prior=normal` 미지원 (Sprint 56+ BL-234 묶음 검토)** — skopt 미지원. 자체 sampler wrapper 30분 시한 초과 시 deferred 결정. `optimizer/engine/bayesian.py:_param_space_to_skopt_dimensions` 안 `NotImplementedError` raise. schemas Literal 은 `{"uniform", "log_uniform", "normal"}` 그대로 유지 (Sprint 56+ activate 시 schema 변경 없이 engine 만 추가).
- **UCB → LCB 부호 변환** — skopt 가 minimization 전제 (LCB). Sprint 55 = `bayesian_acquisition="UCB"` 입력 시 engine 안 `acq_func="LCB"` 로 변환 + direction=maximize 시 `-y` tell 부호 반전 (wrapper 격리).
- **CategoricalField encoding** — Sprint 55 = `transform="label"` (ordinal) only. `one_hot` 은 Sprint 56+ Genetic 진입 시 활성 (BL-234).
- **`_MAX_BAYESIAN_EVALUATIONS=50` 강제 상한** — default queue + soft_time_limit 부재 상태에서 worker block 보호 (cell × 50 = ~250s+ 위험). dedicated queue + soft_time_limit relaxation 은 Sprint 56+ BL-237.
- **Degenerate cell penalty** — `objective_value=None` (num_trades=0 또는 sharpe_ratio is None) 시 `y=_DEGENERATE_PENALTY=1e10` 로 tell. `+inf` 사용 시 skopt GP Cholesky decomposition NaN propagation → fit fail. dynamic penalty (best+1e6) 도 가능하나 Sprint 55 = static 단순화.
- **`best_iteration_idx` 명시 필드 (JSONB grammar)** — §2.2 의 "best_params + acquisition_history" 외에 `best_iteration_idx` 명시 추가. Sprint 50/51/52 의 `best_cell_index` 누락 retro-incorrect 패턴 차단 (FE 가 다시 search 안 함).

### 7.3 acquisition Literal 확장

§2.2 의 `bayesian_acquisition: Literal["EI", "UCB"]` 를 Sprint 55 = `Literal["EI", "UCB", "PI"]` 로 확장. PI (Probability of Improvement) skopt 지원 — 사용자 옵션 폭 + numerical edge case 추가 검증 의무.

### 7.4 §6 checklist 처리 status

| 항목                                                                      | Sprint 55 status                    | 산출물                                                                                     |
| ------------------------------------------------------------------------- | ----------------------------------- | ------------------------------------------------------------------------------------------ |
| (1) ParamSpace.schema_version Literal[1,2] + 5 optional + cross-field     | ✅ Slice 1                          | `optimizer/schemas.py`                                                                     |
| (2) ParamSpaceField BayesianHyperparamsField + GeneticHyperparamsField    | 🟡 Bayesian 만 (Genetic Sprint 56+) | `optimizer/schemas.py`                                                                     |
| (3) OptimizationKind.BAYESIAN + alembic uppercase                         | ✅ Slice 1+2                        | `optimizer/models.py` + `alembic/.../20260513_0001_add_bayesian_to_optimization_kind.py`   |
| (4) optimizer/engine/bayesian.py 신규                                     | ✅ Slice 2                          | `optimizer/engine/bayesian.py` (skopt ask-tell)                                            |
| (5) service.submit_bayesian + run() kind 분기 + LESSON-019 commit-spy 4건 | ✅ Slice 3                          | `optimizer/service.py` + `optimizer/router.py` + `tests/optimizer/test_service_commits.py` |
| (6) FE schemas discriminated union mirror                                 | ✅ Slice 4                          | `frontend/src/features/optimizer/schemas.ts` (z.discriminatedUnion("kind"))                |
| (7) FE form + iteration-chart + best-params-table                         | ✅ Slice 4                          | 3 신규 component + `optimizer-run-detail.tsx` kind 분기 + `page.tsx` algorithm select      |
| (8) FE N-dim viz prototype                                                | ⏳ deferred Sprint 57+ (BL-235)     | —                                                                                          |

### 7.5 신규 BL 등재 (Sprint 56+ roadmap)

Sprint 55 close-out 시 `docs/REFACTORING-BACKLOG.md` 5건 신규:

- **BL-233** (P2, Sprint 56) — Genetic 본격 구현 (`GeneticHyperparamsField` + `optimizer/engine/genetic.py` + `service.submit_genetic`). Sprint 55 패턴 mirror, scope ≈ 0.8× (schema/alembic/router/FE 이미 활성).
- **BL-234** (P3, Sprint 56+) — `BayesianHyperparamsField.prior="normal"` 자체 sampler 활성 + CategoricalField `encoding="one_hot"` Bayesian 활성.
- **BL-235** (P3, Sprint 57+) — N-dim acquisition surface viz (3D+ surface 또는 parallel-coord, Bayesian 전용). §6 #8 deferred.
- **BL-236** (P2, Sprint 56+) — `objective_metric` whitelist 자유화 (BacktestMetrics 24+ 지표 노출 — Sprint 55 = 3종만).
- **BL-237** (P3, Sprint 56+) — Optimizer dedicated Celery queue + soft_time_limit relaxation (Bayesian 50 evaluation × 5s = 250s 시간 보호).

### 7.6 Sprint 55 검증 통과 evidence

- BE focused optimizer test 71 PASS (40 baseline → 71, 회귀 0). 신규 27 (schemas 6 + bayesian_engine 20 + commit-spy 4 + exception 3 — 일부 갱신 포함).
- FE vitest 680 PASS (회귀 0). FE tsc + lint clean.
- alembic migration `20260513_0001` 신규 — uppercase BAYESIAN + downgrade swap. Slice 6 round-trip 의무 (LESSON-066 6차 검증).

---

## 8. Sprint 56 amendment — Genetic executor 본격 구현 (BL-233 Resolved)

> Sprint 56 (`feat/sprint56-genetic-optimizer`, 2026-05-11) close-out 시점 추가. §6 8-checklist 중 (1)~(7) 처리 + Genetic 활성. (8) FE N-dim viz Sprint 57+ BL-235 이연 (Bayesian 와 공용).

### 8.1 GA 라이브러리 결정 — self-implementation (외부 dep 0)

§5 References 의 "Sprint 56+ Genetic" 항목 따라 검토. DEAP / PyGAD 양쪽 모두 our domain 부적합 결론 → ~250L self-impl 채택:

1. **DEAP** — LGPL-3 license (검토 필요) + Decimal/int discrete 지원 약함 (float lock + wrapper 비용 증가) + toolbox/creator boilerplate ~50L 오히려 noise.
2. **PyGAD** — numpy float 고정 (Decimal/int 직접 지원 X) + 마지막 릴리스 2023 + 소규모 maintenance.
3. **Self-implementation** (~250L) — `random.Random(_GENETIC_RANDOM_STATE)` 단일 인스턴스로 결정성 + Decimal/int param space 직접 처리 + 단일 objective + 소규모 (≤ 50 evaluations) 우리 dogfood scope 에 정확 fit. Sprint 57+ NSGA-II / multi-objective / island model 필요 시 DEAP 마이그레이션 검토 여지.

### 8.2 보완 결정 (Sprint 56 lock)

- **4 hyperparam — population_size / n_generations / mutation_rate / crossover_rate** — reserved 3 (population_size / n_generations / mutation_rate) + Sprint 56 신규 crossover_rate. `mutation_rate / crossover_rate ∈ (0, 1]` cross-field validator 강제. selection_method / elitism / island migration 은 hard-coded default (tournament size=3 / no elitism) — Sprint 57+ enum 확장 path (BL-234 묶음 후보).
- **GeneticHyperparamsField 별도 신규 안 함** — Bayesian 와 달리 variable level distribution 차이 없음 = IntegerField / DecimalField / CategoricalField 재사용. 4 신규 hyperparam 은 모두 ParamSpace level (§2.1 reservation 영역). 결과: `ParamSpaceField` discriminated union 변경 없음 (4-variant 그대로 유지).
- **Evaluation budget** — `population_size * (n_generations + 1) ≤ _MAX_GENETIC_EVALUATIONS=50` 강제. initial population + 각 generation 의 새 offspring 만 재평가 (부모 재평가 X, deterministic objective 가정). Sprint 57+ BL-237 = dedicated queue + relaxation.
- **Tournament selection (k=3) + single-point crossover + gaussian mutation (sigma=(max-min)\*0.1)** — 표준 GA 알고리즘. IntegerField mutation 은 Python3 `round()` (banker's) + clip [min, max]. CategoricalField 은 ordinal-style uniform reselect (one_hot Sprint 57+ BL-234).
- **`_GENETIC_RANDOM_STATE=42` 결정성** — `random.Random(seed)` 단일 인스턴스로 reproduce 보장 (사용자 reseed 옵션 Sprint 57+ 확장).
- **degenerate 우선순위 `_compare_for_selection`** — tournament 안 non-degenerate 항상 우선. Bayesian 의 `_DEGENERATE_PENALTY=1e10` 패턴 불필요 (self-impl 은 외부 optimizer 에 `y` 값 전달 안 함).
- **`best_iteration_idx` 명시 필드 + JSONB grammar** — Bayesian 와 동일 (Sprint 50/51/52 retro-incorrect 차단). `generation` field 추가 (phase 와 유사 역할).

### 8.3 §6 checklist 처리 status (Genetic 영역)

| 항목                                                                           | Sprint 56 status                                  | 산출물                                                                                                      |
| ------------------------------------------------------------------------------ | ------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| (1) ParamSpace.schema_version Literal[1,2] + crossover_rate 신규 + cross-field | ✅ Slice 1                                        | `optimizer/schemas.py` (4 hyperparam range validator 추가)                                                  |
| (2) ParamSpaceField + GeneticHyperparamsField                                  | ✅ N/A (별도 신규 안 함, 변수 level 재사용)       | `optimizer/schemas.py` 4-variant 유지                                                                       |
| (3) OptimizationKind.GENETIC + alembic uppercase                               | ✅ Slice 1                                        | `optimizer/models.py` + `alembic/.../20260514_0001_add_genetic_to_optimization_kind.py`                     |
| (4) optimizer/engine/genetic.py 신규                                           | ✅ Slice 2                                        | `optimizer/engine/genetic.py` (self-impl ~430L 포함 docstring)                                              |
| (5) service.submit_genetic + run() kind 분기 + LESSON-019 commit-spy 4건       | ✅ Slice 3+4                                      | `optimizer/service.py` + `optimizer/router.py` + `tests/optimizer/test_service_commits.py`                  |
| (6) FE schemas discriminated union mirror                                      | ✅ Slice 5                                        | `frontend/src/features/optimizer/schemas.ts` (GeneticSearchResultSchema 추가, OptimizationResult 3-variant) |
| (7) FE form + generation-chart + best-params-table                             | ✅ Slice 5                                        | 3 신규 component + `optimizer-run-detail.tsx` kind 분기 + `page.tsx` algorithm select                       |
| (8) FE N-dim viz prototype                                                     | ⏳ deferred Sprint 57+ (BL-235, Bayesian 와 공용) | —                                                                                                           |

### 8.4 신규 BL 등재 (Sprint 56 close-out)

- Sprint 56 = **0건 신규 BL**. Sprint 55 에서 등재한 BL-234/235/236/237 그대로 유지.
- BL-234 description 수정 (Genetic selection_method enum 묶음 검토 추가).

### 8.5 Sprint 56 검증 통과 evidence

- BE focused optimizer test 115 PASS (71 baseline → 115, 회귀 0). 신규 44 (schemas 7 + genetic_engine 23 + commit-spy 4 + 일부 갱신 포함).
- FE vitest 680 PASS (회귀 0). FE tsc + lint clean.
- alembic migration `20260514_0001` 신규 — uppercase GENETIC + downgrade swap. Slice 1 round-trip PASS (LESSON-066 **7차 영구 검증**).
- BE ruff clean (LESSON-068 후보 lint-staged silent skip 재현 차단 = 모든 `×` 곱셈 기호 `*` 변환 + S311 noqa with justification).

---

**End of ADR-013** (Sprint 55 + Sprint 56 amendment 적용).

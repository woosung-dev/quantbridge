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

**End of ADR-013.**
